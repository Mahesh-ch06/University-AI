"""Chat behaviour settings the admissions team can switch in the admin panel (v4.12.0), without code changes.

Stored in the existing `user_memories` table under a reserved system session ("system:app-settings", which a
student session ID can never be: those match SESSION_ID_PATTERN, no colon), one row per setting with the key
prefix "setting.". No new table, so no migration is needed and a change works on the live server at once.

Reads are served from an in-process cache refreshed at most every CACHE_SECONDS (the agent calls refresh()
at the start of each turn); an update is written to the database and applied to the cache immediately. If the
database cannot be reached, the last known values (or the defaults) are used, so the chat never breaks.
"""
from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

log = logging.getLogger(__name__)

SYSTEM_SESSION = "system:app-settings"
PREFIX = "setting."
CACHE_SECONDS = 20


class ChatSettings(BaseModel):
    """Every switch, with its default. Field descriptions are shown in the admin panel."""

    concession_picker: Literal["grouped", "table"] = Field(
        "grouped",
        description="How special concessions are shown: 'grouped' (5 folded groups + 'None of these apply') "
                    "or 'table' (all 19 rows).")
    connect_enabled: bool = Field(
        True, description="'Talk to a counsellor' rings the admin panel and waits before arranging a callback.")
    connect_wait_seconds: int = Field(30, ge=10, le=120, description="How long the student waits for a counsellor.")
    office_hours_start: str = Field("09:00", description="Counsellors available from (India time, HH:MM).")
    office_hours_end: str = Field("18:00", description="Counsellors available until (India time, HH:MM).")
    office_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5],
                                   description="Working days, 0 = Monday ... 6 = Sunday.")

    @field_validator("office_hours_start", "office_hours_end")
    @classmethod
    def _hhmm(cls, v: str) -> str:
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", v or ""):
            raise ValueError("use HH:MM, 24-hour (for example 09:00)")
        return v

    @field_validator("office_days")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        days = sorted(set(v))
        if any(d < 0 or d > 6 for d in days):
            raise ValueError("days are 0 (Monday) to 6 (Sunday)")
        return days


_cache: dict[str, Any] = ChatSettings().model_dump()
_loaded_at = 0.0
_meta: dict[str, Any] = {"updated_at": None}


def get(name: str) -> Any:
    """The current value of one setting (from the cache; never raises)."""
    return _cache.get(name, ChatSettings.model_fields[name].get_default(call_default_factory=True))


def current() -> dict:
    return dict(_cache)


def meta() -> dict:
    return dict(_meta)


async def refresh(force: bool = False) -> dict:
    """Reload from the database when the cache is older than CACHE_SECONDS (or when forced)."""
    global _loaded_at
    if not force and time.monotonic() - _loaded_at < CACHE_SECONDS:
        return current()
    _loaded_at = time.monotonic()
    try:
        from sqlalchemy import select

        from app.db.session import async_session_factory
        from app.models.memory import UserMemory

        async with async_session_factory() as db:
            rows = (await db.execute(select(UserMemory).where(UserMemory.session_id == SYSTEM_SESSION))).scalars().all()
        stored = {}
        latest = None
        for row in rows:
            if row.memory_key.startswith(PREFIX):
                try:
                    stored[row.memory_key[len(PREFIX):]] = json.loads(row.memory_value)
                except (TypeError, ValueError):
                    continue
                if row.updated_at and (latest is None or row.updated_at > latest):
                    latest = row.updated_at
        merged = {**ChatSettings().model_dump(), **{k: v for k, v in stored.items() if k in ChatSettings.model_fields}}
        _cache.update(ChatSettings(**merged).model_dump())   # a bad stored value falls back to validation error
        _meta["updated_at"] = latest.isoformat() if latest else None
    except Exception as exc:  # database unreachable or a stored value invalid: keep the last known values
        log.warning("chat settings not refreshed (%s); using the last known values", type(exc).__name__)
    return current()


async def update(changes: dict) -> dict:
    """Validate and save some settings. Raises ValueError (with a readable message) on bad values."""
    merged = {**current(), **changes}
    try:
        valid = ChatSettings(**merged).model_dump()
    except Exception as exc:
        raise ValueError(str(exc)) from exc
    changed = {k: valid[k] for k in changes if k in ChatSettings.model_fields}
    try:
        from sqlalchemy import select

        from app.db.session import async_session_factory
        from app.models.memory import UserMemory

        async with async_session_factory() as db:
            rows = (await db.execute(select(UserMemory).where(UserMemory.session_id == SYSTEM_SESSION))).scalars().all()
            existing = {row.memory_key: row for row in rows}
            for key, value in changed.items():
                encoded = json.dumps(value)
                row = existing.get(PREFIX + key)
                if row is None:
                    db.add(UserMemory(id=uuid.uuid4(), session_id=SYSTEM_SESSION, memory_key=PREFIX + key,
                                      memory_value=encoded, consented=True))
                else:
                    row.memory_value = encoded
            await db.commit()
    except Exception as exc:
        raise RuntimeError("The settings could not be saved right now. Please try again.") from exc
    _cache.update(valid)
    global _loaded_at
    _loaded_at = time.monotonic()
    _meta["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return current()


def set_for_tests(**values) -> None:
    """Tests only: set values in the cache without a database."""
    global _loaded_at
    _cache.update(ChatSettings(**{**current(), **values}).model_dump())
    _loaded_at = time.monotonic() + 10_000


def reset_for_tests() -> None:
    global _loaded_at
    _cache.clear()
    _cache.update(ChatSettings().model_dump())
    _loaded_at = 0.0
