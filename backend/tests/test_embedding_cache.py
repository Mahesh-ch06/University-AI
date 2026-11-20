"""Tests for in-process LRU cache in GeminiEmbeddingProvider."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.providers.embedding_gemini import GeminiEmbeddingProvider


@pytest.mark.asyncio
async def test_embed_single_lru_cache_hit():
    """Verify that repeat calls with identical text do not make duplicate network calls."""
    provider = GeminiEmbeddingProvider(api_key="test-api-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": {"values": [0.1, 0.2, 0.3]}}

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp

        # First call: cache miss, triggers HTTP call
        emb1 = await provider.embed_single("What is the hostel fee?")
        assert emb1 == [0.1, 0.2, 0.3]
        assert mock_post.call_count == 1

        # Second call: cache hit, returns from LRU without calling HTTP post
        emb2 = await provider.embed_single("what is the hostel fee? ")
        assert emb2 == [0.1, 0.2, 0.3]
        assert mock_post.call_count == 1  # count did not increase!

        # Different query: cache miss, triggers HTTP call
        emb3 = await provider.embed_single("What is the CSE tuition fee?")
        assert emb3 == [0.1, 0.2, 0.3]
        assert mock_post.call_count == 2

    await provider.close()


@pytest.mark.asyncio
async def test_embed_single_item_batch_uses_cache():
    """Verify that single-item embed([text]) also benefits from the query cache."""
    provider = GeminiEmbeddingProvider(api_key="test-api-key")

    # Prime cache manually
    provider._set_cached_embedding("placement stats", [0.5, 0.6])

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        result = await provider.embed(["placement stats"])
        assert result == [[0.5, 0.6]]
        mock_post.assert_not_called()

    await provider.close()
