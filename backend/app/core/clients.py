import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """Base class providing shared HTTP request execution with optional client reuse."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client

    @asynccontextmanager
    async def _get_client(
        self, timeout: float = 15.0
    ) -> AsyncGenerator[httpx.AsyncClient, None]:
        if self.client:
            yield self.client
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                yield client


class GeminiEmbeddingClient(BaseAPIClient):
    """Lightweight, async HTTP client for Google Gemini Embedding API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.RAG_EMBEDDING_MODEL
        # Dynamic dimension resolved from database model definition
        from app.modules.documents.models import DocumentChunk

        self.output_dim = DocumentChunk.embedding.type.dim

    async def get_embedding(self, text: str) -> list[float]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "content": {"parts": [{"text": text}]},
            # Map dynamic dimensions for database alignment
            "outputDimensionality": self.output_dim,
        }

        async with self._get_client(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> list[float]:
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

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")
        if not texts:
            return []

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        requests_payload = []
        for text in texts:
            requests_payload.append(
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.output_dim,
                }
            )
        payload = {"requests": requests_payload}

        async with self._get_client(timeout=20.0) as client:
            response = await client.post(url, json=payload)
            return self._parse_batch_response(response)

    def _parse_batch_response(self, response: httpx.Response) -> list[list[float]]:
        if response.status_code != 200:
            logger.error(
                f"Gemini Batch Embedding API error: {response.status_code} - {response.text}"
            )
            raise RuntimeError(
                f"Gemini API returned error status: {response.status_code}"
            )

        data = response.json()
        try:
            embeddings_list = [emb["values"] for emb in data["embeddings"]]
            return embeddings_list
        except KeyError as e:
            logger.error(f"Invalid Gemini Batch Embedding response payload: {data}")
            raise RuntimeError(
                "Failed to parse batch embeddings from Gemini API response."
            ) from e


class GeminiChatClient(BaseAPIClient):
    """Lightweight, async HTTP client for Google Gemini streaming Chat API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.RAG_CHAT_MODEL

    async def stream_chat(
        self, prompt: str, system_instruction: str | None = None
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured in settings.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?key={self.api_key}"

        # Build contents payload
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        async with self._get_client(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for chunk in self._stream_response(response):
                    yield chunk

    async def _stream_response(
        self, response: httpx.Response
    ) -> AsyncGenerator[str, None]:
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

            while True:
                buffer = buffer.strip()
                if not buffer:
                    break

                if buffer.startswith("["):
                    buffer = buffer[1:].strip()
                if buffer.startswith(","):
                    buffer = buffer[1:].strip()

                if not buffer.startswith("{"):
                    break

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

                json_str = buffer[: idx + 1]
                buffer = buffer[idx + 1 :].strip()

                try:
                    data = json.loads(json_str)
                    text_part = data["candidates"][0]["content"]["parts"][0]["text"]
                    yield text_part
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass


class CohereRerankClient(BaseAPIClient):
    """Lightweight, async HTTP client for Cohere Rerank API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self.api_key = settings.COHERE_API_KEY

    async def rerank(self, query: str, documents: list[str]) -> list[dict]:
        if not self.api_key:
            raise ValueError("COHERE_API_KEY is not configured in settings.")

        url = "https://api.cohere.com/v1/rerank"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "rerank-multilingual-v3.0",
            "query": query,
            "documents": documents,
            "top_n": len(documents),
        }

        async with self._get_client(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> list[dict]:
        if response.status_code != 200:
            logger.error(
                f"Cohere Rerank API error: {response.status_code} - {response.text}"
            )
            raise RuntimeError(
                f"Cohere API returned error status: {response.status_code}"
            )

        data = response.json()
        return data.get("results", [])
