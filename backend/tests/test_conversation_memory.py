"""Conversation memory: continue the previous conversation or start a new one (v4.8.0, docs/32).

The database tests use the real PostgreSQL schema and are skipped when no database is reachable. The other
tests run on the agent's in-process memory with the production code paths.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.services import recovery_service
from app.sru_agent import agent, config, journey, memory
from app.services import card_service


def _run(coro):
    return asyncio.run(coro)


def _run_db(coro):
    """Database steps run in ONE event loop; the pooled connections are closed before the loop ends."""
    async def body():
        from app.db.session import engine
        await engine.dispose(close=False)   # connections opened by other tests belong to other event loops
        try:
            return await coro
        finally:
            await engine.dispose()
    return asyncio.run(body())


def _sid(tag: str) -> str:
    return f"mem-{tag}-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------- database helpers

def _db_available() -> bool:
    async def probe():
        from sqlalchemy import text
        from app.db.session import async_session_factory
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1 FROM conversations LIMIT 1"))
    try:
        _run_db(probe())
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(not _db_available(), reason="PostgreSQL with the app schema is not reachable")


async def _make_conversation(session_id: str, title: str, messages: list[tuple[str, str, datetime]]):
    from app.db.session import async_session_factory
    from app.models.conversation import Conversation
    from app.models.message import Message
    async with async_session_factory() as db:
        conv = Conversation(session_id=session_id, title=title)
        db.add(conv)
        await db.flush()
        for role, content, at in messages:
            msg = Message(conversation_id=conv.id, role=role, content=content)
            msg.created_at = at
            db.add(msg)
        await db.commit()
        return str(conv.id)


async def _cleanup(*session_ids: str):
    from sqlalchemy import delete
    from app.db.session import async_session_factory
    from app.models.conversation import Conversation
    async with async_session_factory() as db:
        await db.execute(delete(Conversation).where(Conversation.session_id.in_(session_ids)))
        await db.commit()


def _ago(**kw) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kw)


# ---------------------------------------------------------------- which conversation, and when to ask

@needs_db
def test_the_most_recently_active_conversation_is_offered():
    sid = _sid("latest")

    async def body():
        try:
            # Created first, but the student kept talking in it: it is the one to continue.
            active = await _make_conversation(sid, "B.Tech CSE fees", [
                ("user", "B.Tech CSE fees", _ago(days=2)), ("assistant", "...", _ago(days=2)),
                ("user", "What about hostel?", _ago(hours=3)), ("assistant", "...", _ago(hours=3))])
            await _make_conversation(sid, "Placements", [
                ("user", "placements", _ago(days=1)), ("assistant", "...", _ago(days=1))])
            return active, await recovery_service.get_recovery_context(sid)
        finally:
            await _cleanup(sid)

    active, ctx = _run_db(body())
    assert ctx.has_resumable_conversation and ctx.conversation_id == active
    assert ctx.total_messages == 4
    assert ctx.last_user_message == "What about hostel?"
    assert 170 <= ctx.inactive_minutes <= 190
    assert ctx.offer_choice is True


@needs_db
@pytest.mark.parametrize("gap,offer", [({"minutes": 5}, False), ({"minutes": 29}, False),
                                       ({"minutes": 31}, True), ({"hours": 1}, True),
                                       ({"hours": 3}, True), ({"days": 1}, True)])
def test_choice_offered_only_after_the_existing_inactivity_threshold(gap, offer):
    assert config.RECOVERY_RESUME_AFTER_MINUTES == 30
    sid = _sid("gap")

    async def body():
        try:
            await _make_conversation(sid, "Hostel", [("user", "hostel", _ago(**gap)),
                                                     ("assistant", "...", _ago(**gap))])
            return await recovery_service.get_recovery_context(sid)
        finally:
            await _cleanup(sid)

    ctx = _run_db(body())
    assert ctx.has_resumable_conversation
    assert ctx.offer_choice is offer
    assert ctx.resume_after_minutes == 30


@needs_db
def test_another_students_conversation_is_never_offered():
    mine, theirs = _sid("mine"), _sid("theirs")

    async def body():
        try:
            await _make_conversation(theirs, "Their chat", [("user", "my marks are 900", _ago(hours=2))])
            return await recovery_service.get_recovery_context(mine)
        finally:
            await _cleanup(mine, theirs)

    assert _run_db(body()).has_resumable_conversation is False


@needs_db
def test_conversation_without_messages_is_not_offered():
    sid = _sid("empty")

    async def body():
        try:
            await _make_conversation(sid, "New conversation", [])
            return await recovery_service.get_recovery_context(sid)
        finally:
            await _cleanup(sid)

    assert _run_db(body()).has_resumable_conversation is False


def test_no_previous_conversation_means_normal_welcome():
    ctx = _run_db(recovery_service.get_recovery_context(_sid("none")))
    assert ctx.has_resumable_conversation is False


def test_memory_fallback_keeps_the_real_conversation_id(monkeypatch):
    """Database down: a conversation held in memory is offered with ITS id (never an invented one)."""
    class Down:
        async def __aenter__(self):
            raise ConnectionError("database unavailable")

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(recovery_service, "async_session_factory", lambda: Down())
    sid, conv = _sid("fallback"), str(uuid.uuid4())
    _run(memory.append_history(sid, "B.Tech CSE fees", "Here are the fees.", conv))
    ctx = _run(recovery_service.get_recovery_context(sid))
    assert ctx.has_resumable_conversation and ctx.conversation_id == conv
    assert ctx.offer_choice is True          # time unknown: ask rather than guess
    assert ctx.last_user_message == "B.Tech CSE fees"


# ---------------------------------------------------------------- start a new conversation

def _profile_with_journey(sid: str, conv: str):
    _run(memory.update_profile(sid, name="Asha Rani", phone="9876543210", program_interest="btech_cse",
                               board="state_board", board_key="ts_state_board", raw_marks=850, max_marks=1000,
                               percent=85.0, marks_confirmed=True, stream="MPC", academic_conv=conv))
    _run(memory.update_conversation_state(sid, conv, active_program="btech_cse", waiting_for="done"))


def test_start_fresh_isolates_the_new_conversation_and_keeps_the_old_one():
    sid, old = _sid("fresh"), str(uuid.uuid4())
    _profile_with_journey(sid, old)
    resp = _run(recovery_service.reset_session_conversation(sid, old))
    assert resp.status == "ok" and resp.new_conversation_id and resp.new_conversation_id != old

    profile = _run(memory.get_profile(sid))
    # identity kept, conversation context gone
    assert profile["name"] == "Asha Rani" and profile["phone"] == "9876543210"
    for key in ("percent", "raw_marks", "board", "stream", "program_interest"):
        assert key not in profile, key
    # offered for one-tap reuse, never applied by itself
    assert profile["saved_academic"]["raw_marks"] == 850
    # the old conversation still knows everything it had
    old_state = _run(memory.get_conversation_state(sid, old))
    assert old_state["active_program"] == "btech_cse" and old_state["waiting_for"] == "done"
    assert old_state["academic"]["percent"] == 85.0
    assert old_state["program_interest"] == "btech_cse"


def test_continuing_the_old_conversation_later_restores_its_details_even_after_cache_expiry():
    sid, old = _sid("back"), str(uuid.uuid4())
    _profile_with_journey(sid, old)
    _run(recovery_service.reset_session_conversation(sid, old))
    _run(memory.clear_conversation_state(sid, old))          # a day later: the cached state has expired
    profile = _run(memory.get_profile(sid))
    profile = _run(journey.scope_profile(sid, old, profile, {}))
    assert profile["percent"] == 85.0 and profile["raw_marks"] == 850 and profile["board_key"] == "ts_state_board"


class _Recorder:
    """Records the prompt and the turns the agent sends to the model."""

    def __init__(self):
        self.prompts, self.turns = [], []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        from google.genai import types
        self.prompts.append(str(getattr(config, "system_instruction", "") or ""))
        self.turns.append(len(contents))
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text="Here is what I found in the official sources.")]))])


async def _say(message, sid, conv, client):
    return [e async for e in agent.run_agent(message, sid, conv, client=client)][-1]


def test_new_conversation_prompt_has_no_previous_context():
    sid, old = _sid("prompt"), str(uuid.uuid4())
    _profile_with_journey(sid, old)
    _run(memory.append_history(sid, "B.Tech CSE fees", "The CSE tuition is ...", old))
    new = _run(recovery_service.reset_session_conversation(sid, old)).new_conversation_id
    model = _Recorder()
    _run(_say("Tell me about the library", sid, new, model))
    assert model.prompts, "the model was not called"
    known = model.prompts[-1].split("WHAT YOU ALREADY KNOW ABOUT THIS STUDENT:")[1].split("\n")[0]
    for leaked in ("percent=85", "raw_marks", "btech_cse", "MPC"):
        assert leaked not in known
    assert model.turns[-1] == 1               # no earlier turns of another conversation


def test_continued_conversation_sends_its_history_to_the_model():
    sid, conv = _sid("cont"), str(uuid.uuid4())
    _run(memory.update_profile(sid, name="Asha Rani", phone="9876543210"))
    _run(memory.append_history(sid, "Tell me about the library", "The central library ...", conv))
    _run(memory.append_history(sid, "And the opening hours?", "It opens at 8 AM ...", conv))
    model = _Recorder()
    _run(_say("Is it open on Sundays?", sid, conv, model))
    assert model.turns[-1] == 5               # 2 earlier exchanges + the new question


# ---------------------------------------------------------------- cards are remembered per conversation

def test_cards_already_shown_are_remembered_per_conversation():
    sid = _sid("cards")
    card_service.clear_session_cards()
    a, b = f"{sid}:conv-a", f"{sid}:conv-b"
    card_service.record_session_card(a, "placement_highlights")
    assert "placement_highlights" in card_service.get_session_shown_cards(a)
    assert "placement_highlights" not in card_service.get_session_shown_cards(b)


def test_fee_comparison_table_still_shows_after_a_personal_fee_answer():
    """A card dropped by the agent (the generic table under a personal fee) must not be marked as shown."""
    sid, conv = _sid("feetable"), str(uuid.uuid4())
    _run(memory.update_profile(sid, name="Asha Rani", phone="9876543210", welcome_actions_shown=True))
    model = _Recorder()
    first = _run(_say("B.Tech CSE fees", sid, conv, model))
    assert any(c.get("type") == "calculate_fee" for c in first.get("cards") or [])
    second = _run(_say("Compare B.Tech fees for all branches", sid, conv, model))
    assert any(c.get("type") == "fee_breakdown" for c in second.get("cards") or [])
