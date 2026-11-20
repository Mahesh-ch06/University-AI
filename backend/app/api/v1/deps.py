"""Dependencies for API routes."""

import secrets
from typing import TYPE_CHECKING, Any
from fastapi import Depends, Header, HTTPException, Request, status

from app.config import settings
from app.db.session import get_db
from app.providers.base import LLMProvider
from app.providers.embedding_base import EmbeddingProvider
from app.providers.factory import create_embedding_provider, create_llm_provider

if TYPE_CHECKING:
    from app.services.rag_service import RAGService

# Singletons (created once, reused)
_llm_provider: LLMProvider | None = None
_embedding_provider: EmbeddingProvider | None = None
_rag_service: Any = None


def get_llm_provider() -> LLMProvider:
    """Get or create the LLM provider singleton."""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = create_llm_provider()
    return _llm_provider


def get_embedding_provider() -> EmbeddingProvider:
    """Get or create the embedding provider singleton."""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = create_embedding_provider()
    return _embedding_provider


def get_rag_service(
    llm: LLMProvider = Depends(get_llm_provider),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
):
    """Get or create the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        from app.services.rag_service import RAGService

        _rag_service = RAGService(llm, embeddings)
    return _rag_service


async def verify_admin_key(
    request: Request,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
) -> str:
    """Verify the admin API key from request header.

    The placeholder key that ships in the source code is public, so outside local debugging
    (APP_DEBUG=false) it is refused: the admin panel stays locked until a real key is set.
    """
    from app.sru_agent import memory

    if isinstance(request, str):
        x_admin_key = request
        client_ip = "unknown"
    else:
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )[:64]

    if settings.admin_key_is_default() and not settings.APP_DEBUG:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin access is disabled until ADMIN_API_KEY is set on the server.",
        )

    is_valid = secrets.compare_digest(
        x_admin_key.encode(), (settings.ADMIN_API_KEY or "").encode()
    )

    if not is_valid:
        # Rate-limit failed admin key attempts (max 5 failed attempts per minute per IP)
        allowed = await memory.allow_request(f"admin_fail:{client_ip}", limit=5)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed admin key attempts. Access temporarily locked.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )

    return x_admin_key


def get_redis(request: Request) -> Any | None:
    """Return the Redis client from app state, or None if not configured."""
    return getattr(request.app.state, "redis", None)
