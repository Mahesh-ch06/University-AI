"""Security tests for the API layer (security/SECURITY_TEST_RESULTS.md, abuse cases 1-7).

They run against the real FastAPI app and the real middleware / dependencies. Only the
database session and the model are kept out of the way (none of these checks reach them).
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import security
from app.config import settings
from app.main import app
from app.sru_agent import memory

STRONG_KEY = "test-admin-key-" + "x" * 32
SID = "sec-test-" + uuid.uuid4().hex  # a valid session id (16-64 URL-safe characters)


def _request(headers: dict | None = None, client_host: str = "10.0.0.5") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/x", "headers": raw,
                    "client": (client_host, 1234), "query_string": b""})


@pytest.fixture
def api():
    """The real app; dependencies that need a database or an API key are replaced by stubs."""
    from app.api.v1 import deps
    from app.db.session import get_db

    async def no_db():
        yield None

    app.dependency_overrides.update({
        get_db: no_db,
        deps.get_llm_provider: lambda: None,
        deps.get_embedding_provider: lambda: None,
        deps.get_rag_service: lambda: None,
        deps.get_redis: lambda: None,
    })
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _fresh_counters():
    memory._local.clear()
    yield
    memory._local.clear()


# ---------------------------------------------------------------- production detection (SEC-01, SEC-20)

def test_production_when_app_env_says_so(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "APP_DEBUG", True)  # even with debug left on
    monkeypatch.delenv("RENDER", raising=False)
    assert security.is_production()
    assert not security.docs_enabled()


def test_production_on_render_even_when_debug_was_forgotten(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "APP_DEBUG", True)
    monkeypatch.setenv("RENDER", "true")
    assert security.is_production()


def test_development_machine_is_not_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "APP_DEBUG", True)
    monkeypatch.delenv("RENDER", raising=False)
    assert not security.is_production()
    assert security.docs_enabled()


def test_placeholder_admin_key_refused_in_production(monkeypatch):
    from app.api.v1 import deps
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "ADMIN_API_KEY", security.PLACEHOLDER_ADMIN_KEY)
    with pytest.raises(HTTPException) as err:
        asyncio.run(deps.verify_admin_key(security.PLACEHOLDER_ADMIN_KEY))
    assert err.value.status_code == 503


def test_placeholder_admin_key_refused_over_http_on_render(monkeypatch, api):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(settings, "ADMIN_API_KEY", security.PLACEHOLDER_ADMIN_KEY)
    res = api.get("/api/v1/admin/stats", headers={"X-Admin-Key": security.PLACEHOLDER_ADMIN_KEY})
    assert res.status_code == 503


def test_startup_warnings_name_the_problem_without_the_value(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "APP_DEBUG", True)
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "short-real-key")
    text = " ".join(security.startup_warnings())
    assert "shorter than" in text and "APP_DEBUG" in text
    assert "short-real-key" not in text


# ---------------------------------------------------------------- client IP (SEC-03)

def test_forged_first_forwarded_for_entry_is_ignored(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "")
    req = _request({"X-Forwarded-For": "1.2.3.4, 203.0.113.9"})
    assert security.client_ip(req) == "203.0.113.9"


def test_client_ip_without_proxy_uses_socket(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "")
    req = _request({"X-Forwarded-For": "1.2.3.4"}, client_host="198.51.100.7")
    assert security.client_ip(req) == "198.51.100.7"


def test_client_ip_header_option(monkeypatch):
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "cf-connecting-ip")
    req = _request({"CF-Connecting-IP": "203.0.113.50", "X-Forwarded-For": "1.1.1.1"})
    assert security.client_ip(req) == "203.0.113.50"
    req = _request({"CF-Connecting-IP": "not-an-ip"}, client_host="198.51.100.8")
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
    assert security.client_ip(req) == "198.51.100.8"


def test_admin_brute_force_limit_survives_forged_ip_rotation(monkeypatch, api):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", STRONG_KEY)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    codes = []
    for i in range(8):
        res = api.get("/api/v1/admin/stats",
                      headers={"X-Admin-Key": f"guess-{i}", "X-Forwarded-For": f"10.9.8.{i}, 203.0.113.77"})
        codes.append(res.status_code)
    assert codes[:5] == [403] * 5
    assert set(codes[5:]) == {429}


# ---------------------------------------------------------------- admin key never in URLs (SEC-02)

def test_admin_key_in_query_string_grants_nothing(monkeypatch, api):
    from app.services import conversation_service
    seen = {}

    async def fake_get(db, conversation_id, session_id, is_admin=False):
        seen["is_admin"] = is_admin
        return None

    async def no_history(*a, **k):
        return []

    monkeypatch.setattr(settings, "ADMIN_API_KEY", STRONG_KEY)
    monkeypatch.setattr(conversation_service, "get_conversation", fake_get)
    monkeypatch.setattr(memory, "get_history", no_history)
    res = api.get(f"/api/v1/conversations/{uuid.uuid4()}",
                  params={"session_id": SID, "admin_key": STRONG_KEY})
    assert res.status_code == 404          # not 200, and no longer a 500
    assert seen["is_admin"] is False


def test_admin_header_on_conversation_view_is_checked_like_admin_routes(monkeypatch, api):
    from app.services import conversation_service

    async def fake_get(db, conversation_id, session_id, is_admin=False):
        return None

    async def no_history(*a, **k):
        return []

    monkeypatch.setattr(settings, "ADMIN_API_KEY", STRONG_KEY)
    monkeypatch.setattr(conversation_service, "get_conversation", fake_get)
    monkeypatch.setattr(memory, "get_history", no_history)
    wrong = api.get(f"/api/v1/conversations/{uuid.uuid4()}", params={"session_id": SID},
                    headers={"X-Admin-Key": "wrong-key"})
    assert wrong.status_code == 403


# ---------------------------------------------------------------- session ids (SEC-11)

@pytest.mark.parametrize("bad", ["a", "short-id", "x" * 65, "has space in it 123", "semi;colon-1234567"])
def test_weak_or_malformed_session_ids_are_refused(api, bad):
    assert api.get("/api/v1/agent/profile", params={"session_id": bad}).status_code == 422
    assert api.get("/api/v1/conversations", params={"session_id": bad}).status_code == 422
    res = api.post("/api/v1/agent/stream", json={"session_id": bad, "message": "hi"})
    assert res.status_code == 422


def test_browser_uuid_session_id_is_accepted():
    assert security.valid_session_id(str(uuid.uuid4()))


# ---------------------------------------------------------------- AI usage limits (SEC-04)

def test_session_rotation_cannot_bypass_the_per_ip_limit(monkeypatch, api):
    import app.sru_agent.router as agent_router

    async def fake_run_agent(message, session_id, conversation_id=None, **kw):
        yield {"type": "done", "answer": "ok", "tools_used": []}

    monkeypatch.setattr(agent_router, "run_agent", fake_run_agent)
    monkeypatch.setattr(agent_router, "_conversation_resolver", None)
    monkeypatch.setattr(agent_router, "_on_turn_complete", None)
    monkeypatch.setattr(settings, "AI_IP_RATE_LIMIT_PER_MIN", 5)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    refused = 0
    for i in range(8):
        res = api.post("/api/v1/agent/stream",
                       json={"session_id": f"rotating-session-{i:04d}", "message": "hello"},
                       headers={"X-Forwarded-For": f"9.9.9.{i}, 203.0.113.10"})
        assert res.status_code == 200
        if '"type": "error"' in res.text:
            refused += 1
    assert refused == 3                  # turns 6, 7 and 8 from the same network


def test_daily_budget_stops_ai_turns(monkeypatch):
    monkeypatch.setattr(settings, "AI_IP_RATE_LIMIT_PER_MIN", 0)
    monkeypatch.setattr(settings, "AI_IP_DAILY_LIMIT", 0)
    monkeypatch.setattr(settings, "AI_DAILY_TURN_BUDGET", 2)
    req = _request()
    results = [asyncio.run(security.ai_turn_refusal(req, f"budget-session-{i:04d}")) for i in range(3)]
    assert results[:2] == [None, None]
    assert results[2] == security.DAILY_MESSAGE


def test_per_ip_daily_limit(monkeypatch):
    monkeypatch.setattr(settings, "AI_IP_RATE_LIMIT_PER_MIN", 0)
    monkeypatch.setattr(settings, "AI_IP_DAILY_LIMIT", 2)
    monkeypatch.setattr(settings, "AI_DAILY_TURN_BUDGET", 0)
    req = _request()
    results = [asyncio.run(security.ai_turn_refusal(req, f"daily-session-{i:04d}")) for i in range(3)]
    assert results[2] == security.DAILY_MESSAGE


def test_legacy_chat_route_has_the_same_limits(monkeypatch, api):
    monkeypatch.setattr(settings, "AI_IP_RATE_LIMIT_PER_MIN", 1)
    from app.services import chat_service

    async def fake_handle(*a, **k):
        raise RuntimeError("should not be reached after the limit")

    monkeypatch.setattr(chat_service, "handle_chat", fake_handle)
    api.post("/api/v1/chat", json={"session_id": "legacy-session-0001", "message": "hi"})
    res = api.post("/api/v1/chat", json={"session_id": "legacy-session-0002", "message": "hi"})
    assert res.status_code == 429


# ---------------------------------------------------------------- request size (SEC-14)

def test_oversized_body_rejected_before_parsing(api):
    res = api.post("/api/v1/agent/stream", content=b"{" + b" " * (settings.MAX_REQUEST_BYTES + 10) + b"}",
                   headers={"content-type": "application/json"})
    assert res.status_code == 413


def test_upload_path_has_its_own_larger_limit():
    mw = security.BodySizeLimitMiddleware(app=None, default_limit=100, upload_limit=1000,
                                          upload_paths=("/api/v1/admin/documents",))
    assert mw._limit_for("/api/v1/admin/documents") == 1000
    assert mw._limit_for("/api/v1/agent/stream") == 100


def test_chunked_body_without_length_is_counted():
    sent = []

    async def app_reads_body(scope, receive, send):
        while True:
            message = await receive()
            if not message.get("more_body"):
                break

    chunks = [{"type": "http.request", "body": b"x" * 60, "more_body": True},
              {"type": "http.request", "body": b"x" * 60, "more_body": False}]

    async def receive():
        return chunks.pop(0)

    async def send(message):
        sent.append(message)

    mw = security.BodySizeLimitMiddleware(app_reads_body, default_limit=100, upload_limit=100)
    with pytest.raises(HTTPException) as err:
        asyncio.run(mw({"type": "http", "path": "/x", "headers": []}, receive, send))
    assert err.value.status_code == 413


# ---------------------------------------------------------------- CORS (SEC-12)

@pytest.mark.parametrize("origin,allowed", [
    ("https://university-ai-companion.vercel.app", True),
    ("https://university-ai-companion-git-main-team.vercel.app", True),
    ("https://www.sru.edu.in", True),
    ("https://attacker.vercel.app", False),
    ("https://sru.edu.in.attacker.com", False),
])
def test_cors_only_for_project_origins(api, origin, allowed):
    res = api.options("/api/v1/agent/programs", headers={
        "Origin": origin, "Access-Control-Request-Method": "GET"})
    assert (res.headers.get("access-control-allow-origin") == origin) is allowed


# ---------------------------------------------------------------- feedback ownership (SEC-10)

def test_feedback_on_someone_elses_message_is_refused(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    from app.schemas.chat import FeedbackRequest
    from app.services import conversation_service

    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db.add = MagicMock()
    remove = AsyncMock()
    monkeypatch.setattr("app.services.exemplar_service.ExemplarService.remove_exemplar", remove)
    request = FeedbackRequest(session_id=SID, conversation_id=uuid.uuid4(), message_id=uuid.uuid4(), rating=-1)
    result = asyncio.run(conversation_service.create_feedback(db, request, embeddings=MagicMock()))
    assert result is None
    db.add.assert_not_called()
    remove.assert_not_called()           # a thumbs-down cannot prune another student's verified answer


def test_feedback_route_answers_404_for_foreign_message(monkeypatch, api):
    from app.services import conversation_service

    async def not_owned(db, request, embeddings=None):
        return None

    monkeypatch.setattr(conversation_service, "create_feedback", not_owned)
    res = api.post("/api/v1/feedback", json={"session_id": SID, "conversation_id": str(uuid.uuid4()),
                                             "message_id": str(uuid.uuid4()), "rating": -1})
    assert res.status_code == 404


# ---------------------------------------------------------------- headers and errors

def test_docs_hidden_in_production_build(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert security.docs_enabled() is False


def test_api_security_headers(api):
    res = api.get("/live")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
