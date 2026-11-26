"""Owned, idempotent chat turns. Publish messages and their staged agent memory together."""
import copy
import hashlib
import json
from contextlib import aclosing
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text, update

from app.db.session import async_session_factory
from app.models.agent_turn import AgentTurn
from app.models.conversation import Conversation
from app.models.message import Message
from app.services import agent_profile_store as store, conversation_service as chats
from app.services.message_context import card_preview, excerpt, offered_choices
from app.sru_agent import journey, memory, tools


class TurnRejected(Exception):
    """Safe student-facing explanation."""


def now():
    return datetime.now(timezone.utc)


async def lock_session(db, session_id):
    locked = await db.scalar(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))"),
                             {"key": "agent-turn:" + session_id})
    if not locked:
        raise TurnRejected("Another change is being saved. Please try again in a moment.")


async def clear_snapshots(db, conversation_id):
    await db.execute(update(AgentTurn).where(AgentTurn.conversation_id == conversation_id,
                     AgentTurn.expires_at.is_not(None)).values(snapshot=None, expires_at=None))


async def reserve(req):
    """Reserve the key durably before an external tool could be called, including on the first turn."""
    key = req.request_id or uuid4()
    digest = hashlib.sha256(req.model_dump_json(exclude={"request_id"}).encode()).hexdigest()
    async with async_session_factory.begin() as db:
        receipt = await db.get(AgentTurn, key)
        if receipt:
            conv = await db.get(Conversation, receipt.conversation_id)
            if not conv or conv.session_id != req.session_id or receipt.fingerprint != digest:
                raise TurnRejected("This submission is no longer available. Please refresh the conversation.")
            if receipt.effect_started and not receipt.answer_id:
                raise TurnRejected("An admissions request may already have been submitted. Please check its status.")
            return key, conv.id
        if req.conversation_id:
            try:
                cid = UUID(req.conversation_id)
            except ValueError:
                raise TurnRejected("Conversation unavailable.") from None
            conv = await db.scalar(select(Conversation).where(Conversation.id == cid,
                                                               Conversation.session_id == req.session_id))
            if not conv:
                raise TurnRejected("Conversation unavailable.")
        elif req.reply_to or req.edit_message_id or req.expected_message_id:
            raise TurnRejected("Open the original conversation first.")
        else:
            conv = await chats.get_or_create_conversation(db, req.session_id, None, title=excerpt(req.message, 50))
        db.add(AgentTurn(request_id=key, conversation_id=conv.id, fingerprint=digest))
        return key, conv.id


async def read_quote(db, cid, ref):
    if not ref:
        return None, None
    row = await db.scalar(select(Message).where(Message.id == UUID(str(ref["message_id"])),
                                                Message.conversation_id == cid))
    if row is None:
        raise TurnRejected("The original message is unavailable.")
    index = ref.get("card_index")
    card = None
    if index is not None:
        cards = (row.metadata_ or {}).get("cards") or []
        if not 0 <= index < len(cards):
            raise TurnRejected("The original card is unavailable.")
        card = cards[index]
    preview = card_preview(card, row.content) if card else excerpt(row.content)
    quote = {"message_id": str(row.id), "card_index": index, "preview": preview}
    # Bound the input and keep it in a user-role part, outside all system instructions.
    context = {"role": row.role, "historical_message": row.content[:3000]}
    if card:
        context["historical_card"] = json.dumps(card, ensure_ascii=False)[:10000]
    return quote, context


async def edit_plan(db, cid, req):
    checkpoint = await db.scalar(select(AgentTurn).where(AgentTurn.conversation_id == cid,
        AgentTurn.user_message_id == req.edit_message_id, AgentTurn.expires_at > now()))
    snap = checkpoint.snapshot if checkpoint else None
    if (not isinstance(snap, dict) or snap.get("version") != 1 or
            not isinstance(snap.get("profile"), dict) or not isinstance(snap.get("state"), dict) or
            not isinstance(snap.get("history"), list) or
            any(not isinstance(h, dict) or h.get("role") not in ("user", "model") or
                not isinstance(h.get("text"), str) for h in snap["history"])):
        raise TurnRejected("This message can no longer be edited. Send the correction as a new message.")
    user = await db.get(Message, req.edit_message_id)
    if not user or user.conversation_id != cid or (user.metadata_ or {}).get("source") != "typed":
        raise TurnRejected("This message is unavailable for editing.")
    tail = (await db.scalars(select(Message).where(Message.conversation_id == cid,
        Message.created_at > user.created_at).order_by(Message.created_at, Message.role.desc()))).all()
    if (not tail or len(tail) % 2 != 1 or any(
        (row.role != "assistant" or (row.metadata_ or {}).get("external_action") or
         "tools_used" not in (row.metadata_ or {})) if i % 2 == 0 else
        (row.role != "user" or (row.metadata_ or {}).get("source") != "button")
        for i, row in enumerate(tail))):
        raise TurnRejected("A later message or admissions action needs to be kept. Send a new correction.")
    return user, tail, snap


async def finish_memory(db, session_id, values):
    profile = values[f"sru:profile:{session_id}"]
    await store.write_profile(db, session_id, profile)
    prefix = f"sru:state:{session_id}:"
    for key, value in values.items():
        if key.startswith(prefix):
            await store.write_state(db, session_id, key[len(prefix):], value)


async def stream(req, run_agent):
    sid = req.session_id
    async with async_session_factory() as db:
        await lock_session(db, sid)
        key, cid = await reserve(req)
        receipt = await db.get(AgentTurn, key)
        if receipt.answer_id:
            yield {"type": "done", "conversation_id": str(cid), "reload": True}
            return
        latest = await db.scalar(select(Message.id).where(Message.conversation_id == cid)
                                 .order_by(Message.created_at.desc(), Message.role.asc()).limit(1))
        if req.expected_message_id and latest != req.expected_message_id:
            raise TurnRejected("The conversation changed. Refresh it before sending this message.")
        conv = await db.get(Conversation, cid)
        ref = req.reply_to.model_dump(mode="json") if req.reply_to else None
        user, tail, checkpoint = None, [], None
        if req.edit_message_id:
            user, tail, checkpoint = await edit_plan(db, cid, req)
            ref = (user.metadata_ or {}).get("reply_to")
        quote, context = await read_quote(db, cid, ref)
        yield {"type": "start", "conversation_id": str(cid)}
        profile = await memory.get_profile(sid)
        # These records are authoritative after a restart, even if Redis still holds an older turn.
        durable = await store.load_profile(sid)
        profile = {**{k: v for k, v in profile.items() if k not in store.DURABLE_KEYS}, **durable}
        state = await store.load_conversation_state(sid, str(cid))
        history = await store.load_history(sid, str(cid))
        values = memory.turn_memory(sid, str(cid), profile, state, history)
        edit = user is not None
        effect = False
        blocked = False

        async def before_effect():
            nonlocal effect, blocked
            if edit or context:
                blocked = True
                raise TurnRejected("Send a new message to request an admissions action.")
            if not effect:
                async with async_session_factory.begin() as fence:
                    await fence.execute(update(AgentTurn).where(AgentTurn.request_id == key).values(effect_started=True))
                    await clear_snapshots(fence, cid)
                effect = True

        token = tools.before_action.set(before_effect)
        try:
            with memory.stage_turn(values):
                profile = await journey.scope_profile(sid, str(cid), profile, state)
                if edit:
                    # Preserve contact/lead changes from settings or other conversations.
                    restored = dict(checkpoint["profile"])
                    for field in ("phone", "name", "phone_saved", "last_lead_id", "last_lead_type",
                                  "last_lead_key", "open_request", "address_by_name"):
                        restored.pop(field, None)
                        if field in profile:
                            restored[field] = profile[field]
                    values.update(memory.turn_memory(sid, str(cid), restored, checkpoint["state"], checkpoint["history"]))
                    profile, state, history = restored, checkpoint["state"], checkpoint["history"]
                snapshot = copy.deepcopy({"version": 1, "profile": profile, "state": state, "history": history})
                source = "form" if req.form else req.source
                steps = [(req.message, source)] + [(row.content, "button") for row in tail if row.role == "user"]
                turns = []
                for i, (message, origin) in enumerate(steps):
                    if i and message not in offered_choices(turns[-1][2]):
                        break
                    result = None
                    async with aclosing(run_agent(message, sid, str(cid), source="button" if origin == "form" else origin,
                            require_contact_details=True, form=req.form.model_dump() if req.form else None,
                            quote=context if i == 0 else None)) as events:
                        async for event in events:
                            if event["type"] == "error":
                                raise TurnRejected(event["detail"])
                            if event["type"] == "done":
                                result = event
                            elif not edit and event["type"] == "token" and event.get("delta"):
                                yield event
                            elif event["type"] == "tool" and event.get("status") == "running":
                                yield {"type": "tool", "status": "running", "label": event.get("label", "Working…")}
                    if blocked or not result or not (result.get("answer", "").strip() or result.get("cards")):
                        raise TurnRejected("This change could not be completed. Please send a new message.")
                    turns.append((message, origin, result))
                if context:
                    # A quote explains a past turn. Model tool calls cannot replace the active estimate.
                    values.update(memory.turn_memory(sid, str(cid), snapshot["profile"], snapshot["state"],
                        (snapshot["history"] + [{"role": "user", "text": req.message},
                         {"role": "model", "text": turns[0][2]["answer"]}])[-memory.MAX_HISTORY:]))
        finally:
            tools.before_action.reset(token)

        if edit:
            await db.execute(delete(Message).where(Message.conversation_id == cid, Message.created_at > user.created_at))
        if source != "button" or effect:
            await clear_snapshots(db, cid)
        # Discard expired private copies on traffic, including abandoned conversations.
        await db.execute(update(AgentTurn).where(AgentTurn.expires_at <= now()).values(snapshot=None, expires_at=None))
        keep_snapshot = source == "typed" and not effect
        expiry = now() + timedelta(hours=24) if keep_snapshot else None
        for i, (message, origin, event) in enumerate(turns):
            meta = {"source": origin}
            if i == 0:
                if quote:
                    meta["reply_to"] = quote
                if edit:
                    meta["edited"] = True
                if expiry:
                    meta["editable_until"] = expiry.isoformat()
            if i == 0 and edit:
                user.content, user.metadata_ = message, meta
                question = user
            else:
                question = await chats.add_message(db, cid, "user", message, metadata=meta, created_at=now())
            answer = await chats.add_message(db, cid, "assistant", event["answer"], model=event.get("model"),
                sources=event.get("sources", []), metadata={"tools_used": event.get("tools_used", []),
                "cards": event.get("cards", []), "suggestions": event.get("suggestions", []),
                "external_action": effect, "channel": req.channel}, created_at=now())
            if not i:
                receipt.user_message_id = question.id
        receipt.answer_id = answer.id
        receipt.snapshot = snapshot if keep_snapshot else None
        receipt.expires_at = expiry
        conv.updated_at = now()
        from app.sru_agent import intents
        if not intents.small_talk(req.message) and (not conv.title or conv.title == "Chat" or intents.small_talk(conv.title)):
            conv.title = excerpt(req.message, 50)
        await finish_memory(db, sid, values)
        await db.commit()
        store._last_saved.pop(sid, None)
        await memory.publish_turn(values)
        yield {**event, "conversation_id": str(cid), "user_message_id": str(receipt.user_message_id),
               "message_id": str(answer.id), "reply_to": quote, "editable_until": expiry.isoformat() if expiry else None,
               "card_previews": [card_preview(c, event["answer"]) for c in event.get("cards", [])],
               "external_action": effect, "reload": edit, "profile": memory.public_profile(values[f"sru:profile:{sid}"])}
