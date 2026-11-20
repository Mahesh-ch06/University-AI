"""Unit tests for response caching service (P2-A)."""

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.cache_service import (
    bump_index_version,
    get_cached_answer,
    get_index_version,
    invalidate_cache,
    make_cache_key,
    set_cached_answer,
)


def test_make_cache_key_deterministic():
    key1 = make_cache_key("What is the hostel fee?")
    key2 = make_cache_key("what is the hostel fee?  ")
    assert key1 == key2
    assert key1.startswith("sru:rag:v1:")


def test_make_cache_key_different_for_different_queries():
    key1 = make_cache_key("What is the hostel fee?")
    key2 = make_cache_key("What are the placement packages?")
    assert key1 != key2


@pytest.mark.asyncio
async def test_get_cached_answer_none_client():
    res = await get_cached_answer(None, "sample query")
    assert res is None


@pytest.mark.asyncio
async def test_set_cached_answer_none_client():
    # Should safely return without exception
    await set_cached_answer(None, "sample query", "sample answer", [])


@pytest.mark.asyncio
async def test_get_cached_answer_hit():
    mock_redis = MagicMock()
    stored = {"answer": "Tuition is 1.4L per year.", "sources": [{"title": "Fee Doc"}]}
    mock_redis.get = AsyncMock(return_value=json.dumps(stored))

    result = await get_cached_answer(mock_redis, "what is the tuition fee?")
    assert result is not None
    answer, sources = result
    assert answer == "Tuition is 1.4L per year."
    assert len(sources) == 1
    assert sources[0]["title"] == "Fee Doc"


@pytest.mark.asyncio
async def test_get_cached_answer_miss():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)

    result = await get_cached_answer(mock_redis, "unknown query")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_answer_graceful_error_handling():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))

    result = await get_cached_answer(mock_redis, "any query")
    assert result is None


@pytest.mark.asyncio
async def test_set_cached_answer_success():
    from app.services.cache_service import _CACHE_TTL_SECONDS
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)

    await set_cached_answer(mock_redis, "hostel rules", "Curfew is 9:30 PM", [{"section": "Hostel"}])
    mock_redis.set.assert_called_once()
    args, kwargs = mock_redis.set.call_args
    assert kwargs.get("ex") == _CACHE_TTL_SECONDS
    payload = json.loads(args[1])
    assert payload["answer"] == "Curfew is 9:30 PM"


@pytest.mark.asyncio
async def test_set_cached_answer_skips_too_long():
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)

    huge_answer = "x" * 5000
    await set_cached_answer(mock_redis, "huge query", huge_answer, [])
    mock_redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_cache():
    mock_redis = MagicMock()
    mock_redis.delete = AsyncMock(return_value=1)

    await invalidate_cache(mock_redis, "some query")
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_get_index_version_none_client():
    assert await get_index_version(None) == 1


@pytest.mark.asyncio
async def test_get_index_version_success():
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value="5")
    assert await get_index_version(mock_redis) == 5


@pytest.mark.asyncio
async def test_bump_index_version_none_client():
    assert await bump_index_version(None) == 0


@pytest.mark.asyncio
async def test_bump_index_version_success():
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(return_value=3)

    async def fake_scan_iter(match=None, count=None):
        for k in [b"sru:rag:v1:abc", b"sru:rag:v1:def"]:
            yield k

    mock_redis.scan_iter = fake_scan_iter
    mock_redis.delete = AsyncMock(return_value=2)

    version = await bump_index_version(mock_redis)
    assert version == 3
    mock_redis.incr.assert_called_once()
    mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_bump_index_version_graceful_error():
    mock_redis = MagicMock()
    mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))

    version = await bump_index_version(mock_redis)
    assert version == 0

