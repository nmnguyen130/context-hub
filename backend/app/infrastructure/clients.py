import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseAPIClient:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client

    @asynccontextmanager
    async def _client(self, timeout: float) -> AsyncGenerator[httpx.AsyncClient, None]:
        if self.client:
            yield self.client
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                yield client

    def _raise_if_error(self, response: httpx.Response, provider: str) -> None:
        if response.status_code != 200:
            logger.error(
                f"{provider} API error: {response.status_code} - {response.text}"
            )
            raise RuntimeError(f"{provider} API error: {response.status_code}")


class GeminiEmbeddingClient(BaseAPIClient):
    """Gemini Embedding API client."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.RAG_EMBEDDING_MODEL

        from app.modules.documents.models import DocumentChunk

        self.output_dim = DocumentChunk.embedding.type.dim

    def _url(self, method: str) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:{method}?key={self.api_key}"
        )

    async def get_embedding(self, text: str) -> list[float]:
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY")

        payload = {
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self.output_dim,
        }

        async with self._client(timeout=10.0) as client:
            response = await client.post(self._url("embedContent"), json=payload)
            self._raise_if_error(response, "Gemini")
            return response.json()["embedding"]["values"]

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY")
        if not texts:
            return []

        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": self.output_dim,
                }
                for text in texts
            ]
        }

        async with self._client(timeout=20.0) as client:
            response = await client.post(self._url("batchEmbedContents"), json=payload)
            self._raise_if_error(response, "Gemini")
            return [x["values"] for x in response.json()["embeddings"]]


class _StreamParser:
    """Decodes Gemini stream JSON objects using raw_decode."""

    def __init__(self) -> None:
        self.decoder = json.JSONDecoder()

    def feed(self, buffer: str) -> tuple[list[str], str]:
        """Parses complete JSON chunks from the accumulated buffer."""
        outputs: list[str] = []
        idx = 0

        while (start := buffer.find("{", idx)) != -1:
            try:
                obj, end = self.decoder.raw_decode(buffer, start)
            except json.JSONDecodeError:
                break

            idx = end
            try:
                if text := obj["candidates"][0]["content"]["parts"][0]["text"]:
                    outputs.append(text)
            except (KeyError, IndexError):
                pass

        return outputs, buffer[idx:]


class GeminiChatClient(BaseAPIClient):
    """Gemini streaming Chat API client."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.RAG_CHAT_MODEL

    def _url(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:streamGenerateContent?key={self.api_key}"
        )

    async def stream_chat(
        self, prompt: str, system_instruction: str | None = None
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY")

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        parser = _StreamParser()
        buffer = ""
        async with self._client(timeout=30.0) as client:
            async with client.stream("POST", self._url(), json=payload) as response:
                self._raise_if_error(response, "Gemini Chat")

                async for text_chunk in response.aiter_text():
                    buffer += text_chunk
                    outputs, buffer = parser.feed(buffer)
                    for text in outputs:
                        yield text


class CohereRerankClient(BaseAPIClient):
    """Cohere Rerank API client."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        super().__init__(client)
        self.api_key = settings.COHERE_API_KEY

    async def rerank(self, query: str, documents: list[str]) -> list[dict]:
        if not self.api_key:
            raise ValueError("Missing COHERE_API_KEY")

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

        async with self._client(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            self._raise_if_error(response, "Cohere Rerank")
            return response.json().get("results", [])


def get_embedding_client(provider: str = "gemini"):
    if provider == "gemini":
        return GeminiEmbeddingClient()
    raise ValueError(f"Unsupported embedding provider: {provider}")


def get_chat_client(provider: str = "gemini"):
    if provider == "gemini":
        return GeminiChatClient()
    raise ValueError(f"Unsupported chat provider: {provider}")


def get_reranker(provider: str = "context_boost"):
    match provider:
        case "context_boost":
            from app.modules.chat.rerankers import ContextBoostReranker

            return ContextBoostReranker()
        case "cohere":
            return CohereRerankClient()
        case _:
            raise ValueError(f"Unsupported reranker: {provider}")
