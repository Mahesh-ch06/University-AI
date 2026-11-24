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
# memory_value is VARCHAR(255): a longer value (the Quick Start tiles) is saved in numbered pieces
# ("setting.welcome_tiles#0", "#1", ...) under a small index row, and put back together on load. No migration.
CHUNK = 240

WELCOME_ICONS = ("calculator", "graduation-cap", "briefcase", "heart", "award", "building", "home", "map-pin",
                 "phone", "book", "wallet", "send")


class WelcomeTile(BaseModel):
    """One Quick Start tile under the opening welcome message (Admin -> Agent -> Quick Start tiles)."""

    id: str = Field(..., pattern=r"^[a-z0-9_-]{1,24}$")
    title: str = Field(..., min_length=1, max_length=32)
    badge: str = Field("", max_length=16, description="Short highlight on the tile (verified facts only)")
    icon: Literal[WELCOME_ICONS] = "building"  # type: ignore[valid-type]
    prompt: str = Field(..., min_length=1, max_length=120, description="The message sent when the tile is tapped")
    subtitle: str = Field("", max_length=48, description="Shown as the tile's tooltip")
    enabled: bool = True

    @field_validator("title", "badge", "prompt", "subtitle")
    @classmethod
    def _plain(cls, v: str) -> str:
        v = re.sub(r"\s+", " ", v or "").strip()
        if re.search(r"[<>]", v):
            raise ValueError("no < or > characters")
        return v


# Verified badges only: fee card slabs (up to 40%), NIRF 2025 Engineering #91, THE Research Quality #6 in India,
# placements page (highest 51 LPA), special concessions on the fee card (15,000 to 50,000 a year).
DEFAULT_WELCOME_TILES = [
    {"id": "calculate_scholarship", "title": "Calculate My Scholarship", "badge": "Up to 40% off", "icon": "calculator",
     "prompt": "Calculate my scholarship", "subtitle": "Instant fee estimate in a few steps"},
    {"id": "explore_programs", "title": "Explore Programmes", "badge": "NIRF #91", "icon": "graduation-cap",
     "prompt": "Explore programs offered at SR University", "subtitle": "B.Tech, MBA, Agriculture & more"},
    {"id": "placements", "title": "Placements & Careers", "badge": "₹51 LPA", "icon": "briefcase",
     "prompt": "Tell me about placements at SRU", "subtitle": "150+ recruiters, 1,300+ offers"},
    {"id": "special_consideration", "title": "Special Consideration", "badge": "₹15K–₹50K/yr", "icon": "heart",
     "prompt": "Special consideration", "subtitle": "Concessions you may qualify for"},
    {"id": "why_sru", "title": "Why Choose SRU?", "badge": "#6 Research", "icon": "award",
     "prompt": "Why should I choose SR University?", "subtitle": "Rankings, research and campus life"},
]


class ChatSettings(BaseModel):
    """Every switch, with its default. Field descriptions are shown in the admin panel."""

    concession_picker: Literal["grouped", "table"] = Field(
        "grouped",
        description="How special concessions are shown: 'grouped' (5 folded groups + 'None of these apply') "
                    "or 'table' (all 19 rows).")
    connect_enabled: bool = Field(
        True, description="'Talk to a counsellor' rings the admin panel and waits before arranging a callback.")
    fee_questions: Literal["evaluate_first", "fee_card"] = Field(
        "evaluate_first",
        description="A fee question ('B.Tech CSE fees'): 'evaluate_first' checks the student's marks and eligibility, "
                    "merit scholarship and special concessions, then gives the final fee (a 'Just show the fee' "
                    "button gives the standard fee at once); 'fee_card' shows the standard fee card at once.")
    suggestion_chips: Literal["questions_only", "always"] = Field(
        "questions_only",
        description="Quick-response buttons under an answer: 'questions_only' (when SRU Buddy asks the student "
                    "something, plus the answer options of a step) or 'always' (after every answer).")
    welcome_tiles: list[WelcomeTile] = Field(
        default_factory=lambda: [WelcomeTile(**t) for t in DEFAULT_WELCOME_TILES],
        description="The Quick Start tiles under the opening welcome message, in order (at most 8).")
    ai_answers: bool = Field(
        False, description="Answers written by the AI from the verified facts (on), or the verified texts as they "
                          "are (off: no AI call for them, e.g. when the daily AI quota runs low). Cards, numbers and "
                          "workflows are the same either way.")
    connect_wait_seconds: int = Field(30, ge=10, le=120, description="How long the student waits for a counsellor.")
    office_hours_start: str = Field("09:00", description="Counsellors available from (India time, HH:MM).")
    office_hours_end: str = Field("18:00", description="Counsellors available until (India time, HH:MM).")
    office_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4, 5],
                                   description="Working days, 0 = Monday ... 6 = Sunday.")

    @field_validator("welcome_tiles")
    @classmethod
    def _tiles(cls, v: list) -> list:
        if len(v) > 8:
            raise ValueError("at most 8 Quick Start tiles")
        ids = [t.id for t in v]
        if len(set(ids)) != len(ids):
            raise ValueError("each tile needs its own id")
        return v

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
        stored, pieces = {}, {}
        latest = None
        for row in rows:
            if not row.memory_key.startswith(PREFIX):
                continue
            name = row.memory_key[len(PREFIX):]
            if "#" in name:
                key, _, idx = name.partition("#")
                pieces.setdefault(key, {})[int(idx)] = row.memory_value
                continue
            try:
                stored[name] = json.loads(row.memory_value)
            except (TypeError, ValueError):
                continue
            if row.updated_at and (latest is None or row.updated_at > latest):
                latest = row.updated_at
        for key, value in list(stored.items()):
            if isinstance(value, dict) and set(value) == {"__pieces__"}:
                try:
                    parts = pieces.get(key) or {}
                    stored[key] = json.loads("".join(parts[i] for i in range(int(value["__pieces__"]))))
                except (KeyError, TypeError, ValueError):
                    stored.pop(key, None)   # incomplete: the default is used
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

            def put(memory_key: str, text: str):
                row = existing.get(memory_key)
                if row is None:
                    db.add(UserMemory(id=uuid.uuid4(), session_id=SYSTEM_SESSION, memory_key=memory_key,
                                      memory_value=text, consented=True))
                else:
                    row.memory_value = text

            for key, value in changed.items():
                encoded = json.dumps(value, ensure_ascii=False)
                parts = [encoded[i:i + CHUNK] for i in range(0, len(encoded), CHUNK)] if len(encoded) > CHUNK else []
                put(PREFIX + key, json.dumps({"__pieces__": len(parts)}) if parts else encoded)
                for i, part in enumerate(parts):
                    put(f"{PREFIX}{key}#{i}", part)
                for mkey, row in existing.items():   # pieces left over from a longer earlier value
                    if mkey.startswith(f"{PREFIX}{key}#") and int(mkey.rsplit("#", 1)[1]) >= len(parts):
                        await db.delete(row)
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
