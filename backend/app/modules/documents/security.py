import hashlib
import re
from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import ServiceError


@dataclass(frozen=True)
class DLPPattern:
    name: str
    pattern: re.Pattern[str]
    severity: str


DEFAULT_PATTERNS: list[DLPPattern] = [
    DLPPattern("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "CRITICAL"),
    DLPPattern(
        "CREDIT_CARD",
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
        "CRITICAL",
    ),
    DLPPattern(
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "HIGH",
    ),
    DLPPattern(
        "API_KEY",
        re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b"),
        "CRITICAL",
    ),
    DLPPattern(
        "BEARER_TOKEN",
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
        "CRITICAL",
    ),
    DLPPattern(
        "PHONE",
        re.compile(r"\b\+?1?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b"),
        "MEDIUM",
    ),
    DLPPattern(
        "IP_ADDRESS",
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "LOW",
    ),
]


@dataclass(frozen=True)
class DLPMatch:
    pattern_name: str
    severity: str
    start: int
    end: int
    value: str


class DLPScanner:
    def __init__(self, patterns: list[DLPPattern] | None = None) -> None:
        self.patterns = patterns or DEFAULT_PATTERNS

    def scan(self, text: str) -> list[DLPMatch]:
        """Scan text for all configured DLP patterns and return matching locations."""
        matches: list[DLPMatch] = []
        for pattern in self.patterns:
            for match in pattern.pattern.finditer(text):
                matches.append(
                    DLPMatch(
                        pattern_name=pattern.name,
                        severity=pattern.severity,
                        start=match.start(),
                        end=match.end(),
                        value=match.group(0),
                    )
                )
        return sorted(matches, key=lambda m: m.start)


_DEFAULT_SCANNER = DLPScanner()


def mask_pii(text: str, matches: list[DLPMatch]) -> tuple[str, dict[str, str]]:
    """Replace PII matches with deterministic, reversible tokens."""
    if not matches:
        return text, {}

    vault: dict[str, str] = {}
    result = text
    offset = 0

    for match in matches:
        token_hash = hashlib.sha256(match.value.encode()).hexdigest()[:4]
        token = f"[PII_{match.pattern_name}_{token_hash}]"
        vault[token] = match.value
        start = match.start + offset
        end = match.end + offset
        result = result[:start] + token + result[end:]
        offset += len(token) - (match.end - match.start)

    return result, vault


def unmask_pii(text: str, vault: dict[str, str] | None = None) -> str:
    """Replace PII tokens back with their original unmasked values."""
    if not vault:
        return text
    result = text
    for token, original_val in vault.items():
        result = result.replace(token, original_val)
    return result


def apply_dlp(
    text: str,
    workspace_dlp_rules: dict | None = None,
) -> tuple[str, list[str], dict[str, str]]:
    """Scan text and apply configured DLP actions like mask, reject, or log."""
    rules = workspace_dlp_rules or {}
    action = (rules.get("action") or settings.RAG_DLP_ACTION).upper()
    if action == "DISABLED":
        return text, [], {}

    enabled_patterns = rules.get("enabled_patterns")
    if enabled_patterns is not None:
        patterns = [p for p in DEFAULT_PATTERNS if p.name in enabled_patterns]
        scanner = DLPScanner(patterns)
    else:
        scanner = _DEFAULT_SCANNER

    matches = scanner.scan(text)
    if not matches:
        return text, [], {}

    warnings = [f"DLP match: {m.pattern_name} ({m.severity})" for m in matches]

    if action == "REJECT":
        raise ServiceError.unprocessable(
            f"Content rejected: {matches[0].pattern_name} pattern detected."
        )

    if action == "MASK":
        masked, vault = mask_pii(text, matches)
        return masked, warnings, vault

    return text, warnings, {}
