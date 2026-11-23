"""Google Gemini embedding provider implementation."""

import asyncio
from collections import OrderedDict
import hashlib
import logging
import httpx

from app.providers.embedding_base import EmbeddingProvider
from app.providers.key_pool import APIKeyPool

logger = logging.getLogger(__name__)

# Gemini's current text embedding model — outputs 3072-dimensional vectors
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
_EMBED_CACHE_MAX_ENTRIES = 200


def _cache_key(text: str) -> str:
    """Return a deterministic hash of normalized text for LRU cache indexing."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using Google Gemini's text embedding models with multi-key pool failover
    and an in-process LRU cache for query embeddings to avoid redundant network round-trips.
    """

    def __init__(
        self,
        api_key: str | list[str] = "",
        model: str = GEMINI_EMBEDDING_MODEL,
        api_keys: list[str] | str | None = None,
    ):
        raw_keys = api_keys if api_keys is not None else api_key
        if not raw_keys:
            raise ValueError("Gemini API key is required for embeddings.")
        self.key_pool = APIKeyPool(raw_keys)
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        # In-process LRU cache for query embeddings (saves 300-500ms on repeat/similar queries)
        self._lru_cache: OrderedDict[str, list[float]] = OrderedDict()

    @property
    def api_key(self) -> str:
        """Current active key for backwards compatibility."""
        return self.key_pool.get_current_key()

    def _get_cached_embedding(self, text: str) -> list[float] | None:
        key = _cache_key(text)
        if key in self._lru_cache:
            self._lru_cache.move_to_end(key)
            return self._lru_cache[key]
        return None

    def _set_cached_embedding(self, text: str, embedding: list[float]) -> None:
        key = _cache_key(text)
        self._lru_cache[key] = embedding
        self._lru_cache.move_to_end(key)
        if len(self._lru_cache) > _EMBED_CACHE_MAX_ENTRIES:
            self._lru_cache.popitem(last=False)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using Gemini batchEmbedContents with multi-key failover."""
        if not texts:
            return []

        # Check if single item is already in LRU cache
        if len(texts) == 1:
            cached = self._get_cached_embedding(texts[0])
            if cached is not None:
                return [cached]

        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]},
                "taskType": "RETRIEVAL_DOCUMENT",
            }
            for t in texts
        ]

        url = f"{self.base_url}/models/{self.model}:batchEmbedContents"
        total_keys = len(self.key_pool)
        last_response = None
        max_attempts = max(total_keys * 2, 5)

        for attempt in range(max_attempts):
            active_key = self.key_pool.get_next_key(advance=True)
            try:
                response = await self._client.post(
                    url,
                    json={"requests": requests},
                    headers={"x-goog-api-key": active_key},
                )
                last_response = response
                if response.status_code == 200:
                    self.key_pool.mark_success(active_key)
                    data = response.json()
                    embeddings = [item["values"] for item in data.get("embeddings", [])]
                    if len(texts) == 1 and embeddings:
                        self._set_cached_embedding(texts[0], embeddings[0])
                    return embeddings
                elif response.status_code in (401, 403, 429, 500, 502, 503):
                    logger.warning(
                        "Gemini embedding key %s hit HTTP %d. Rotating key (attempt %d/%d).",
                        self.key_pool.label(active_key),
                        response.status_code,
                        attempt + 1,
                        max_attempts,
                    )
                    self.key_pool.mark_rate_limited(active_key)
                    backoff = 3.0 * (attempt + 1) if response.status_code == 429 else 1.0
                    await asyncio.sleep(backoff)
                    continue
                else:
                    response.raise_for_status()
            except httpx.TimeoutException:
                logger.warning("Gemini embedding request with key %s timed out. Retrying...", self.key_pool.label(active_key))
                await asyncio.sleep(2.0)
                continue

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("All Gemini API keys exhausted or rate-limited for embeddings.")

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single query text using Gemini embedContent with LRU caching and multi-key failover."""
        # 1. Fast path: check in-process LRU cache
        cached = self._get_cached_embedding(text)
        if cached is not None:
            logger.debug("Embedding LRU cache HIT for query: %.40s", text)
            return cached

        # 2. Cache miss: fetch from Gemini API
        url = f"{self.base_url}/models/{self.model}:embedContent"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_QUERY",
        }
        total_keys = len(self.key_pool)
        last_response = None

        for attempt in range(max(total_keys, 3)):
            active_key = self.key_pool.get_next_key(advance=True)
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    headers={"x-goog-api-key": active_key},
                )
                last_response = response
                if response.status_code == 200:
                    self.key_pool.mark_success(active_key)
                    data = response.json()
                    embedding = data["embedding"]["values"]
                    self._set_cached_embedding(text, embedding)
                    return embedding
                elif response.status_code in (401, 403, 429, 500, 502, 503):
                    logger.warning(
                        "Gemini query embedding key %s hit HTTP %d. Rotating key.",
                        self.key_pool.label(active_key),
                        response.status_code,
                    )
                    self.key_pool.mark_rate_limited(active_key)
                    await asyncio.sleep(0.5)
                    continue
                else:
                    response.raise_for_status()
            except httpx.TimeoutException:
                logger.warning("Gemini query embedding with key %s timed out. Retrying...", self.key_pool.label(active_key))
                await asyncio.sleep(1.0)
                continue

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError("All Gemini API keys exhausted or rate-limited for single embedding.")

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
