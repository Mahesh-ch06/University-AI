"""Durable turn invariants against PostgreSQL, with a deterministic agent at the model boundary."""
import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.agent_turn import AgentTurn
from app.models.conversation import Conversation
from app.models.memory import UserMemory
from app.models.message import Message
from app.services import agent_turns as turns, agent_profile_store as store
from app.sru_agent import memory, tools
from app.sru_agent.router import AgentRequest


@pytest.fixture
async def chat(monkeypatch):
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    db = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(turns, "async_session_factory", db)
    monkeypatch.setattr(store, "async_session_factory", db)
    sid = str(uuid4())

    def body(message, **fields):
        return AgentRequest(session_id=sid, request_id=uuid4(), message=message, **fields)

    async def run(req, agent=None):
        return [e async for e in turns.stream(req, agent or scripted)]

    yield body, run, db
    async with db.begin() as session:
        await session.execute(delete(Conversation).where(Conversation.session_id == sid))
        await session.execute(delete(UserMemory).where(UserMemory.session_id == sid))
    await engine.dispose()


async def scripted(message, sid, cid, quote=None, **kwargs):
    if message == "action":
        await tools.before_action.get()()
    if quote:
        assert "historical_message" in quote
    await memory.update_profile(sid, percent=int(message) if message.isdecimal() else 5)
    await memory.update_conversation_state(sid, cid, step=message)
    await memory.append_history(sid, message, "next", cid)
    if message == "failed":
        yield {"type": "error", "detail": "Unavailable"}
        return
    choices = [] if message == "stop" else [{"label": "MPC"}]
    yield {"type": "done", "answer": "next", "cards": [{"type": "counsellor_choice", "options": choices}],
           "suggestions": [], "tools_used": []}


async def test_edit_replays_offered_card_choices_once(chat):
    body, run, db = chat
    first = (await run(body("87")))[-1]
    cid = first["conversation_id"]
    last = (await run(body("MPC", source="button", conversation_id=cid)))[-1]
    edit = body("95", conversation_id=cid, edit_message_id=first["user_message_id"], expected_message_id=last["message_id"])
    assert (await run(edit))[-1]["reload"]
    assert (await run(edit))[-1]["reload"]
    async with db() as session:
        rows = (await session.scalars(select(Message).where(Message.conversation_id == cid).order_by(Message.created_at))).all()
        assert [m.content for m in rows] == ["95", "next", "MPC", "next"]
        assert str(rows[0].id) == first["user_message_id"] and rows[0].metadata_["edited"]
        latest = str(rows[-1].id)
    await run(body("stop", conversation_id=cid, edit_message_id=first["user_message_id"], expected_message_id=latest))
    assert (await store.load_conversation_state(edit.session_id, cid)) == {"step": "stop"}


@pytest.mark.parametrize("failure", ["expired", "invalid", "other student", "stale view", "failed", "action"])
async def test_rejected_edits_keep_transcript_and_state(chat, failure):
    body, run, db = chat
    req = body("87")
    item = (await run(req))[-1]
    cid = item["conversation_id"]
    if failure in ("expired", "invalid"):
        async with db.begin() as session:
            rec = await session.get(AgentTurn, req.request_id)
            if failure == "expired":
                rec.expires_at = turns.now() - timedelta(minutes=1)
            else:
                rec.snapshot = {"version": 2}
    edit = body(failure, conversation_id=cid, edit_message_id=item["user_message_id"],
                expected_message_id=uuid4() if failure == "stale view" else item["message_id"])
    if failure == "other student":
        edit.session_id = str(uuid4())
    with pytest.raises(turns.TurnRejected):
        await run(edit)
    assert await store.load_conversation_state(req.session_id, cid) == {"step": "87"}
    assert (await store.load_profile(req.session_id))["percent"] == 87
    assert [h["text"] for h in await store.load_history(req.session_id, cid)] == ["87", "next"]


async def test_quote_loads_only_owned_card_and_preserves_academics(chat):
    body, run, db = chat
    req = body("87")
    item = (await run(req))[-1]
    cid = item["conversation_id"]
    ref = {"message_id": item["message_id"], "card_index": 0}
    reply = body("Explain", conversation_id=cid, reply_to=ref)
    result = (await run(reply))[-1]
    assert result["reply_to"]["message_id"] == ref["message_id"]
    assert (await store.load_profile(req.session_id))["percent"] == 87
    for invalid in (dict(ref, message_id=uuid4()), dict(ref, card_index=1)):
        with pytest.raises(turns.TurnRejected):
            await run(body("Explain", conversation_id=cid, reply_to=invalid))
    foreign = body("Explain", conversation_id=cid, reply_to=ref)
    foreign.session_id = str(uuid4())
    with pytest.raises(turns.TurnRejected):
        await run(foreign)
    async with db() as session:
        row = await session.get(Message, result["user_message_id"])
        assert row.metadata_["reply_to"] == result["reply_to"]


async def test_later_admissions_action_invalidates_checkpoint(chat):
    body, run, _ = chat
    first = (await run(body("87")))[-1]
    cid = first["conversation_id"]
    action = body("action", source="button", conversation_id=cid)
    last = (await run(action))[-1]
    assert last["external_action"] and (await run(action))[-1]["reload"]
    with pytest.raises(turns.TurnRejected):
        await run(body("95", conversation_id=cid, edit_message_id=first["user_message_id"],
                       expected_message_id=last["message_id"]))


async def test_concurrent_turn_and_interrupted_stream(chat):
    body, run, _ = chat
    req = body("87")
    started = asyncio.Event()

    async def interrupted(message, sid, cid, **kwargs):
        await memory.update_profile(sid, percent=87)
        started.set()
        await asyncio.Event().wait()
        yield {}

    task = asyncio.create_task(run(req, interrupted))
    await asyncio.wait_for(started.wait(), 5)
    try:
        with pytest.raises(turns.TurnRejected):
            await run(req)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert "percent" not in await store.load_profile(req.session_id)
    assert (await run(req))[-1]["user_message_id"]
