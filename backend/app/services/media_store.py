"""Images uploaded in the admin panel (ads, event cards), kept in the database (v4.15.1).

Render's disk is wiped on every deploy, so an uploaded image cannot be a file. It is stored, base64-encoded, in the
existing `user_memories` table under a reserved system session (no schema change, like the chat settings):

    memory_key "media.<id>"      -> {"type": "image/webp", "size": 81234, "pieces": n}
    memory_key "media.<id>#<i>"  -> the i-th piece of the base64 text (240 characters each)

<id> is the first 20 hex characters of the image's SHA-256, so the same image uploaded twice is stored once. Only
JPEG, PNG and WebP are accepted (checked by their first bytes, not the name the browser gives): no SVG or HTML, which
could carry scripts. The admin panel shrinks images before upload; MAX_BYTES is the hard limit here.

Served publicly at GET /api/v1/agent/media/<id> (an ad or event image is public by nature), cached in memory.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.memory import UserMemory

SYSTEM_SESSION = "system:media"
PIECE = 240
MAX_BYTES = 450_000
MEDIA_PATH = "/api/v1/agent/media/"
ID_PATTERN = r"^[a-f0-9]{20}$"
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)
_cache: dict[str, tuple[bytes, str]] = {}
_CACHE_MAX = 64


class MediaError(ValueError):
    """An upload that can't be stored (wrong type, too big, empty)."""


def sniff_type(data: bytes) -> str | None:
    for magic, ctype in _MAGIC:
        if data.startswith(magic):
            return ctype
    if len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def is_media_path(value: str) -> bool:
    return bool(re.fullmatch(re.escape(MEDIA_PATH) + r"[a-f0-9]{20}", value or ""))


async def save(data: bytes) -> dict:
    """Store an image; returns {"id", "url", "type", "size"}. Raises MediaError for a bad upload."""
    if not data:
        raise MediaError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise MediaError(f"The image is too large ({len(data) // 1024} KB). The limit is {MAX_BYTES // 1024} KB.")
    ctype = sniff_type(data)
    if not ctype:
        raise MediaError("Only JPEG, PNG or WebP images can be uploaded.")
    media_id = hashlib.sha256(data).hexdigest()[:20]
    out = {"id": media_id, "url": MEDIA_PATH + media_id, "type": ctype, "size": len(data)}
    if async_session_factory is None:
        raise MediaError("Storage is not available right now.")
    encoded = base64.b64encode(data).decode("ascii")
    parts = [encoded[i:i + PIECE] for i in range(0, len(encoded), PIECE)]
    base = f"media.{media_id}"
    async with async_session_factory() as db:
        exists = (await db.execute(select(UserMemory.id).where(
            UserMemory.session_id == SYSTEM_SESSION, UserMemory.memory_key == base))).first()
        if exists:
            return out                                   # the same image is already stored
        rows = [UserMemory(id=uuid.uuid4(), session_id=SYSTEM_SESSION, memory_key=f"{base}#{i}", memory_value=p,
                           consented=True) for i, p in enumerate(parts)]
        # The index row last: an image is only "there" once every piece is written (same transaction anyway).
        rows.append(UserMemory(id=uuid.uuid4(), session_id=SYSTEM_SESSION, memory_key=base, consented=True,
                               memory_value=json.dumps({"type": ctype, "size": len(data), "pieces": len(parts)})))
        db.add_all(rows)
        await db.commit()
    _remember(media_id, data, ctype)
    return out


async def load(media_id: str) -> tuple[bytes, str] | None:
    """(bytes, content type) of a stored image, or None."""
    if not re.fullmatch(ID_PATTERN, media_id or ""):
        return None
    if media_id in _cache:
        return _cache[media_id]
    if async_session_factory is None:
        return None
    base = f"media.{media_id}"
    async with async_session_factory() as db:
        rows = (await db.execute(select(UserMemory.memory_key, UserMemory.memory_value).where(
            UserMemory.session_id == SYSTEM_SESSION, UserMemory.memory_key.like(base + "%")))).all()
    values = dict(rows)
    try:
        meta = json.loads(values[base])
        data = base64.b64decode("".join(values[f"{base}#{i}"] for i in range(int(meta["pieces"]))))
    except (KeyError, ValueError, TypeError):
        return None
    if hashlib.sha256(data).hexdigest()[:20] != media_id:   # an incomplete or altered image is never served
        return None
    _remember(media_id, data, meta.get("type") or sniff_type(data) or "application/octet-stream")
    return _cache[media_id]


def _remember(media_id: str, data: bytes, ctype: str) -> None:
    if len(_cache) >= _CACHE_MAX:
        _cache.pop(next(iter(_cache)))
    _cache[media_id] = (data, ctype)
