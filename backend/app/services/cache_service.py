"""Response cache service — Redis-backed cache for repeated RAG queries.

Caches grounded university answers to avoid redundant Gemini API + ChromaDB
round-trips for common repeated questions (e.g., 'What is minimum attendance?').

Cache policy:
- Only UNIVERSITY intent answers are cached (never STUDENT_SPECIFIC).
- Cache key: SHA-256 of the canonicalized query string.
- TTL: 3600 seconds (1 hour) — university facts change infrequently.
- Maximum cached answer length: 4000 characters (very long answers skipped).
- Cache is bypassed on error (graceful degradation, never raises).
"""

import hashlib
import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 86400  # 24 hours — university facts change at most once a semester;
                            # document uploads call bump_index_version() which invalidates stale keys
_MAX_ANSWER_LEN = 4000     # don't cache abnormally long answers
def _knowledge_fingerprint() -> str:
    """Short hash of the fee policy and handbook files: a fee or handbook change gives every cached answer a new
    key, so an answer cached under an older fee policy is never served again."""
    from pathlib import Path
    digest = hashlib.sha256()
    policy = Path(__file__).resolve().parent.parent / "sru_agent" / "fee_policy_2027_28.json"
    paths = [policy] + sorted((settings.DATA_DIR / "handbook").glob("*.md"))
    for path in paths:
        try:
            digest.update(path.read_bytes())
        except OSError:
            continue
    return digest.hexdigest()[:10]


_KEY_PREFIX = f"sru:rag:v{settings.RAG_CACHE_VERSION}:{_knowledge_fingerprint()}:"


def make_cache_key(canonical_query: str) -> str:
    """Return a Redis key for the given canonical query string."""
    digest = hashlib.sha256(canonical_query.lower().strip().encode("utf-8")).hexdigest()[:24]
    return f"{_KEY_PREFIX}{digest}"


async def get_cached_answer(
    redis_client: Any,
    canonical_query: str,
) -> tuple[str, list[dict]] | None:
    """Return (answer, sources) from cache, or None on miss or error."""
    if redis_client is None:
        return None
    try:
        key = make_cache_key(canonical_query)
        raw = await redis_client.get(key)
        if raw is None:
            return None
        data = json.loads(raw)
        logger.info("Cache HIT for query: %.60s", canonical_query)
        return data["answer"], data.get("sources", [])
    except Exception as exc:
        logger.warning("Cache get error (degrading gracefully): %s", exc)
        return None


async def set_cached_answer(
    redis_client: Any,
    canonical_query: str,
    answer: str,
    sources: list[dict],
) -> None:
    """Store (answer, sources) in Redis with TTL. Silently skips on error."""
    if redis_client is None:
        return
    if len(answer) > _MAX_ANSWER_LEN:
        logger.debug("Answer too long (%d chars) — skipping cache write", len(answer))
        return
    try:
        key = make_cache_key(canonical_query)
        payload = json.dumps({"answer": answer, "sources": sources}, ensure_ascii=False)
        await redis_client.set(key, payload, ex=_CACHE_TTL_SECONDS)
        logger.info("Cache SET for query: %.60s (TTL=%ds)", canonical_query, _CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Cache set error (degrading gracefully): %s", exc)


async def invalidate_cache(redis_client: Any, canonical_query: str) -> None:
    """Delete a cached answer for a specific query."""
    if redis_client is None:
        return
    try:
        key = make_cache_key(canonical_query)
        await redis_client.delete(key)
    except Exception as exc:
        logger.warning("Cache invalidate error: %s", exc)


INDEX_VERSION_KEY = "sru:rag:index_version"


async def get_index_version(redis_client: Any) -> int:
    """Get current index version from Redis."""
    if redis_client is None:
        return 1
    try:
        val = await redis_client.get(INDEX_VERSION_KEY)
        return int(val) if val else 1
    except Exception:
        return 1


async def bump_index_version(redis_client: Any) -> int:
    """Increment the index version in Redis and invalidate cached RAG answers.

    Called during document ingestion to ensure stale cached answers are cleared.
    """
    if redis_client is None:
        return 0
    try:
        new_version = await redis_client.incr(INDEX_VERSION_KEY)

        # Invalidate existing cache keys matching the RAG prefix
        try:
            if hasattr(redis_client, "scan_iter"):
                keys_to_delete = []
                async for key in redis_client.scan_iter(match=f"{_KEY_PREFIX}*", count=100):
                    keys_to_delete.append(key)
                if keys_to_delete:
                    await redis_client.delete(*keys_to_delete)
            elif hasattr(redis_client, "scan"):
                cursor = 0
                while True:
                    cursor, keys = await redis_client.scan(cursor=cursor, match=f"{_KEY_PREFIX}*", count=100)
                    if keys:
                        await redis_client.delete(*keys)
                    if not cursor:
                        break
        except Exception as scan_exc:
            logger.debug("Cache key scan/delete error (version counter still bumped): %s", scan_exc)

        logger.info("bump_index_version: bumped index_version to %s", new_version)
        return int(new_version)
    except Exception as exc:
        logger.warning("Could not bump index_version in Redis: %s", exc)
        return 0

