"""'Talk to a counsellor' (v4.12.0): a real, short attempt to reach a counsellor, then a callback.

  student asks  ->  callback lead saved at once (so nothing is lost if they leave)
                ->  a request rings in the admin panel for `connect_wait_seconds` (default 30)
                ->  a counsellor taps "I'll call now"   => the student sees "A counsellor will call you now"
                ->  nobody accepts in time               => "All our counsellors are busy ... we'll call you back"

There is no chat takeover: an accepted request means a phone call now. Requests live in the agent's short-term
store (Redis, or server memory) for a day; the lead itself is in PostgreSQL. Outside office hours (admin
settings) no request rings: the callback is arranged straight away.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.services import app_settings
from app.sru_agent import memory

IST = ZoneInfo("Asia/Kolkata")
INDEX = "live:index"
_ACTIVE_FOR_SECONDS = 30 * 60   # a request this recent counts as the student's current one (no duplicates)


def _key(request_id: str) -> str:
    return f"live:req:{request_id}"


def in_office_hours(now: datetime | None = None) -> bool:
    now = (now or datetime.now(IST)).astimezone(IST)
    if now.weekday() not in app_settings.get("office_days"):
        return False
    start = app_settings.get("office_hours_start")
    end = app_settings.get("office_hours_end")
    hhmm = now.strftime("%H:%M")
    return start <= hhmm < end


def next_opening(now: datetime | None = None) -> str:
    """'tomorrow morning at 09:00', 'Monday at 09:00', or 'today at 09:00'."""
    now = (now or datetime.now(IST)).astimezone(IST)
    start = app_settings.get("office_hours_start")
    days = app_settings.get("office_days") or [0, 1, 2, 3, 4, 5]
    for add in range(0, 8):
        day = now + timedelta(days=add)
        if day.weekday() not in days:
            continue
        if add == 0 and now.strftime("%H:%M") >= start:
            continue
        when = "today" if add == 0 else "tomorrow" if add == 1 else day.strftime("%A")
        return f"{when} at {start}"
    return f"at {start} on the next working day"


def hours_text() -> str:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    days = app_settings.get("office_days") or []
    span = f"{names[days[0]]}–{names[days[-1]]}" if days and days == list(range(days[0], days[-1] + 1)) \
        else ", ".join(names[d] for d in days)
    return f"{span}, {app_settings.get('office_hours_start')}–{app_settings.get('office_hours_end')}"


def _public(req: dict, now: float | None = None) -> dict:
    """What the student's card may see (no full number, no case notes)."""
    now = now or time.time()
    left = max(0, int(round(req["deadline"] - now))) if req["status"] == "waiting" else 0
    return {"request_id": req["id"], "status": req["status"], "seconds_left": left,
            "wait_seconds": req["wait_seconds"], "phone_last4": req["phone_last4"],
            "first_name": req.get("first_name") or "", "counsellor": req.get("accepted_by") or None}


async def _resolve(req: dict) -> dict:
    """A waiting request past its deadline becomes 'busy' (the callback lead already exists)."""
    if req["status"] == "waiting" and time.time() >= req["deadline"]:
        req["status"] = "busy"
        await memory._set(_key(req["id"]), req)
    return req


async def create(session_id: str, conversation_id, name: str, phone: str, lead_id: str | None,
                 case: dict | None) -> dict:
    wait = int(app_settings.get("connect_wait_seconds"))
    req = {"id": uuid.uuid4().hex, "session_id": session_id, "conversation_id": str(conversation_id or ""),
           "first_name": (name or "").split()[0][:40] if name else "", "phone": phone,
           "phone_last4": phone[-4:], "lead_id": lead_id, "case": case or {}, "status": "waiting",
           "created_at": time.time(), "deadline": time.time() + wait, "wait_seconds": wait,
           "accepted_by": None, "accepted_at": None}
    await memory._set(_key(req["id"]), req)
    index = [i for i in (await memory._get(INDEX, [])) if i != req["id"]]
    await memory._set(INDEX, (index + [req["id"]])[-60:])
    await memory.update_conversation_state(session_id, conversation_id, live_request=req["id"])
    return _public(req)


async def current_for(session_id: str, conversation_id) -> dict | None:
    """The student's recent request (waiting or accepted), if any: asked again, they get the same one."""
    state = await memory.get_conversation_state(session_id, conversation_id)
    rid = state.get("live_request")
    if not rid:
        return None
    req = await memory._get(_key(rid), None)
    if not req or time.time() - req["created_at"] > _ACTIVE_FOR_SECONDS:
        return None
    return _public(await _resolve(req))


async def status(request_id: str, session_id: str) -> dict | None:
    """The student's card polls this. None: unknown request, or not this student's."""
    req = await memory._get(_key(request_id), None)
    if not req or req.get("session_id") != session_id:
        return None
    return _public(await _resolve(req))


async def waiting() -> list[dict]:
    """Requests ringing now, for the admin panel (full details: it is staff only)."""
    out = []
    for rid in reversed(await memory._get(INDEX, [])):
        req = await memory._get(_key(rid), None)
        if not req:
            continue
        req = await _resolve(req)
        if req["status"] == "waiting":
            out.append({"request_id": req["id"], "first_name": req["first_name"], "phone": req["phone"],
                        "case": req.get("case") or {}, "seconds_left": max(0, int(req["deadline"] - time.time())),
                        "lead_id": req.get("lead_id")})
    return out


async def accept(request_id: str, counsellor: str | None) -> tuple[str, dict | None]:
    """('ok', request) | ('gone', None) | ('too_late', request). The first counsellor to accept wins."""
    req = await memory._get(_key(request_id), None)
    if not req:
        return "gone", None
    req = await _resolve(req)
    if req["status"] != "waiting":
        return "too_late", req
    req.update(status="accepted", accepted_by=(counsellor or "").strip()[:40] or None, accepted_at=time.time())
    await memory._set(_key(request_id), req)
    return "ok", req
