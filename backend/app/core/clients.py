import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingClient:
    """Lightweight, async HTTP client for Google Gemini Embedding API."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.RAG_EMBEDDING_MODEL

    async def get_embedding(self, text: str) -> list[float]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "content": {"parts": [{"text": text}]},
            # Map default 768 dimensions for database alignment
            "outputDimensionality": 768,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code != 200:
                logger.error(
                    f"Gemini Embedding API error: {response.status_code} - {response.text}"
                )
                raise RuntimeError(
                    f"Gemini API returned error status: {response.status_code}"
                )

            data = response.json()
            try:
                embedding_vector = data["embedding"]["values"]
                return embedding_vector
            except KeyError as e:
                logger.error(f"Invalid Gemini Embedding payload structure: {data}")
                raise RuntimeError(
                    "Failed to parse embedding from Gemini API response."
                ) from e


class GeminiChatClient:
    """Lightweight, async HTTP client for Google Gemini streaming Chat API."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.RAG_CHAT_MODEL

    async def stream_chat(
        self, prompt: str, system_instruction: str = None
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?key={self.api_key}"

        # Build contents payload
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(
                        f"Gemini Chat API error: {response.status_code} - {error_text.decode('utf-8')}"
                    )
                    raise RuntimeError(
                        f"Gemini Chat API returned error status: {response.status_code}"
                    )

                # Parse the streaming JSON chunks
                buffer = ""
                async for chunk in response.iter_text():
                    buffer += chunk

                    # Clean up the JSON streaming array brackets/commas if sent as a raw JSON array
                    # Google Gemini stream API returns either line-delimited JSON objects or a single JSON array.
                    # We can parse objects by locating balanced brackets or parsing line by line.
                    while True:
                        buffer = buffer.strip()
                        if not buffer:
                            break

                        # Strip opening bracket of a JSON array if present at start
                        if buffer.startswith("["):
                            buffer = buffer[1:].strip()
                        # Strip separating commas
                        if buffer.startswith(","):
                            buffer = buffer[1:].strip()

                        # Locate end of current JSON object
                        if not buffer.startswith("{"):
                            break

                        # Balance curly braces to find the boundary of the JSON chunk
                        brace_count = 0
                        idx = 0
                        found = False
                        for idx, char in enumerate(buffer):
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    found = True
                                    break

                        if not found:
                            break

                        # Extract and parse the full JSON object
                        json_str = buffer[: idx + 1]
                        buffer = buffer[idx + 1 :].strip()

                        try:
                            data = json.loads(json_str)
                            text_part = data["candidates"][0]["content"]["parts"][0][
                                "text"
                            ]
                            yield text_part
                        except (json.JSONDecodeError, KeyError, IndexError):
                            # Ignore parsing errors of partial or metadata chunks
                            pass


class CohereRerankClient:
    """Lightweight, async HTTP client for Cohere Rerank API."""

    def __init__(self):
        self.api_key = settings.COHERE_API_KEY

    async def rerank(self, query: str, documents: list[str]) -> list[dict]:
        if not self.api_key:
            raise ValueError("COHERE_API_KEY is not configured in settings.")

        url = "https://api.cohere.com/v1/rerank"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Use Cohere's multi-lingual model for Vietnamese support
        payload = {
            "model": "rerank-multilingual-v3.0",
            "query": query,
            "documents": documents,
            "top_n": len(documents),
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(
                    f"Cohere Rerank API error: {response.status_code} - {response.text}"
                )
                raise RuntimeError(
                    f"Cohere API returned error status: {response.status_code}"
                )

            data = response.json()
            return data.get("results", [])
