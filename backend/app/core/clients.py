import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
COHERE_BASE = "https://api.cohere.com/v2"


class GeminiClient:
    """Client wrapper for Gemini AI embedding and generation APIs."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured")

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts using the Gemini API."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for embeddings")

        model = model or settings.RAG_EMBEDDING_MODEL
        url = f"{GEMINI_BASE}/models/{model}:batchEmbedContents"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json={
                    "requests": [
                        {
                            "model": f"models/{model}",
                            "content": {"parts": [{"text": t}]},
                        }
                        for t in texts
                    ]
                },
            )
            response.raise_for_status()
            data = response.json()

        return [item["values"] for item in data["embeddings"]]

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
    ) -> str:
        """Generate text content from a prompt using the Gemini API."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for generation")

        model = model or settings.RAG_CHAT_MODEL
        url = f"{GEMINI_BASE}/models/{model}:generateContent"

        contents: list[dict[str, Any]] = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_output_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def stream_generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Stream text generation chunks from a prompt using the Gemini API."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is required for generation")

        model = model or settings.RAG_CHAT_MODEL
        url = f"{GEMINI_BASE}/models/{model}:streamGenerateContent"

        contents: list[dict[str, Any]] = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": self.api_key},
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_output_tokens,
                    },
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break

                    chunk = json.loads(payload)
                    parts = (
                        chunk.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [])
                    )
                    for part in parts:
                        text = part.get("text")
                        if text:
                            yield text


class CohereClient:
    """Client wrapper for the Cohere Rerank API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.COHERE_API_KEY

    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        model: str = "rerank-english-v3.0",
        top_n: int = 10,
    ) -> list[tuple[int, float]]:
        """Re-rank a list of document strings relative to a search query."""
        if not self.api_key:
            raise RuntimeError("COHERE_API_KEY is required for reranking")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{COHERE_BASE}/rerank",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                },
            )
            response.raise_for_status()
            data = response.json()

        return [(r["index"], r["relevance_score"]) for r in data["results"]]
