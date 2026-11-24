"""v4.15.1: images uploaded in the admin panel, the student details in Admin -> Student chats, and the audit fixes."""
import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.config import settings
from app.main import app
from app.services import app_settings, media_store
from app.sru_agent import agent

ADMIN = {"X-Admin-Key": settings.ADMIN_API_KEY}


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    """Each test gets database connections on its own event loop (as tests/test_admin_conversations.py)."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    from app.db.session import get_db

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(media_store, "async_session_factory", maker)

    async def override():
        async with maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override
    yield
    app.dependency_overrides.pop(get_db, None)

# The smallest valid images of each accepted type (decoded by their first bytes, not by the file name).
WEBP = (b"RIFF\x1a\x00\x00\x00WEBPVP8L\x0d\x00\x00\x00/\x00\x00\x00\x10\x07\x10\x11\x11\x88\x88\xfe\x07\x00")
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def test_types_are_recognised_by_their_bytes_not_their_name():
    assert media_store.sniff_type(WEBP) == "image/webp"
    assert media_store.sniff_type(PNG) == "image/png"
    assert media_store.sniff_type(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert media_store.sniff_type(b"<svg onload=alert(1)>") is None
    assert media_store.sniff_type(b"<html>") is None


@pytest.mark.asyncio
async def test_upload_serve_and_reject():
    png = PNG + uuid.uuid4().bytes          # a different image every run (the id is its hash)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/api/v1/admin/media", headers=ADMIN,
                              files={"file": ("ad.png", io.BytesIO(png), "image/png")})
        assert r.status_code == 200, r.text
        url = r.json()["url"]
        assert media_store.is_media_path(url)
        media_store._cache.clear()           # served from the database, not only from memory
        got = await client.get(url)
        assert got.status_code == 200 and got.content == png and got.headers["content-type"] == "image/png"
        assert "immutable" in got.headers["cache-control"] and got.headers["x-content-type-options"] == "nosniff"
        again = await client.post("/api/v1/admin/media", headers=ADMIN,
                                  files={"file": ("again.png", io.BytesIO(png), "image/png")})
        assert again.json()["url"] == url    # the same image: the same id, stored once
        bad = await client.post("/api/v1/admin/media", headers=ADMIN,
                                files={"file": ("x.png", io.BytesIO(b"<svg onload=alert(1)>"), "image/png")})
        assert bad.status_code == 422 and "JPEG, PNG or WebP" in bad.json()["detail"]
        big = await client.post("/api/v1/admin/media", headers=ADMIN,
                                files={"file": ("b.png", io.BytesIO(PNG + b"0" * media_store.MAX_BYTES), "image/png")})
        assert big.status_code == 422
        no_key = await client.post("/api/v1/admin/media", files={"file": ("ad.png", io.BytesIO(png), "image/png")})
        assert no_key.status_code in (401, 403, 422)
        assert (await client.get("/api/v1/agent/media/" + "0" * 20)).status_code == 404


def test_ads_and_events_accept_an_uploaded_image_or_an_https_link_only():
    ok = {"id": "a1", "title": "Admissions open", "link_url": "https://apply.sru.edu.in"}
    assert app_settings.ChatAd(**ok, image_url="/api/v1/agent/media/" + "a" * 20).image_url.endswith("a" * 20)
    assert app_settings.ChatAd(**ok, image_url="https://sru.edu.in/x.webp")
    for bad in ("http://x.com/a.png", "/api/v1/agent/media/../../etc", "javascript:alert(1)"):
        with pytest.raises(ValidationError):
            app_settings.ChatAd(**ok, image_url=bad)
    with pytest.raises(ValidationError):
        app_settings.EventHighlight(id="e1", title="Lumina", image_url="ftp://x")


@pytest.mark.asyncio
async def test_student_chats_list_shows_who_the_student_is():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/admin/conversations", headers=ADMIN, params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    for c in r.json()["conversations"]:
        assert "student" in c                 # present (None when nothing is known about the student)


def test_programme_details_at_any_step_are_answered_first():
    waiting_board = {"fee_intake": {"waiting_for": "board", "counsellor_mode": True, "program": "btech_cse"}}
    assert agent._side_question("tell me about BBA", waiting_board)
    assert agent._side_question("b.des details", waiting_board)
    assert not agent._side_question("BBA fees", waiting_board)          # a fee question continues the steps
    assert not agent._side_question("cbse", waiting_board)
