"""Counsellor copilot (v4.12.0): who to call first, and a ready draft message, for the admissions team.

Rule-based and explainable (no model): every lead gets a score from the signals the chat recorded in its case
summary (sru_agent/case_summary.py) plus how recent and how far along it is. Each ranked lead lists the
reasons. Drafts are written from the same verified data; a counsellor reads, edits and sends them (nothing is
sent automatically).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import ProspectiveLead
from app.sru_agent import config as agent_config

_SIGNAL_POINTS = {
    "fee_summary_done": (3, "finished a fee summary"),
    "concession_pending": (2, "has a special concession pending"),
    "proof_ready": (1, "says the proof is ready"),
    "scholarship": (1, "qualifies for a merit scholarship"),
    "parent": (1, "parent enquiring"),
}


def _case(lead: ProspectiveLead) -> dict:
    meta = lead.metadata_ or {}
    case = meta.get("case")
    return case if isinstance(case, dict) else {}


def score(lead: ProspectiveLead, now: datetime | None = None) -> tuple[int, list[str], str]:
    """(points, reasons, tier) for one lead. Tier: hot / warm / later."""
    now = now or datetime.now(timezone.utc)
    meta = lead.metadata_ or {}
    case = _case(lead)
    points, reasons = 0, []
    kind = meta.get("request_type")
    if kind == "callback":
        live = "talk to a counsellor" in str(meta.get("preferred_time", ""))
        points += 4 if live else 3
        reasons.append("asked to talk to a counsellor now" if live else "asked for a callback")
    elif kind == "campus_visit":
        points += 2
        reasons.append("wants to visit the campus")
    for signal in case.get("signals") or []:
        if signal in _SIGNAL_POINTS:
            p, why = _SIGNAL_POINTS[signal]
            points += p
            reasons.append(why)
    created = lead.created_at
    if created is not None:
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = now - created
        if age <= timedelta(hours=24):
            points += 2
            reasons.append("asked in the last 24 hours")
        elif age <= timedelta(days=3):
            points += 1
            reasons.append("asked in the last 3 days")
    if "projected_marks" in (case.get("signals") or []):
        reasons.append("marks are projected: confirm after results")
    if lead.status in ("contacted", "applied", "enrolled", "rejected"):
        points -= 5
        reasons.append(f"already {lead.status}")
    tier = "hot" if points >= 7 else "warm" if points >= 4 else "later"
    return points, reasons, tier


async def priorities(db: AsyncSession, limit: int = 20, days: int = 14) -> list[dict]:
    """Open leads of the last `days` days, best first."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(ProspectiveLead).where(ProspectiveLead.created_at >= since,
                                      ProspectiveLead.status.notin_(("enrolled", "rejected", "cancelled")))
        .order_by(ProspectiveLead.created_at.desc()).limit(300))).scalars().all()
    ranked = []
    for lead in rows:
        points, reasons, tier = score(lead)
        case = _case(lead)
        ranked.append({
            "lead_id": str(lead.id), "name": lead.name, "phone": lead.phone,
            "program": case.get("program") or lead.program_interest, "status": lead.status,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "score": points, "tier": tier, "reasons": reasons, "case": case,
        })
    ranked.sort(key=lambda r: (r["score"], r["created_at"] or ""), reverse=True)   # best first, newest on a tie
    return ranked[:limit]


def draft(lead: ProspectiveLead) -> dict:
    """A short WhatsApp / SMS draft for this lead, from its case summary. The counsellor edits and sends it."""
    case = _case(lead)
    first = (lead.name or "").split()[0] if lead.name else ""
    lines = [f"Hi {first}," if first else "Hello,",
             "this is the SR University Admissions team, following up on your chat with SRU Buddy."]
    program = case.get("program") or lead.program_interest
    if program and case.get("scholarship"):
        lines.append(f"For {program}, your marks give you a {case['scholarship'].split(' ')[0]} merit scholarship.")
    elif program:
        lines.append(f"You were looking at {program}.")
    if case.get("fee"):
        lines.append(f"Your fee summary: {case['fee']}.")
    if case.get("concession"):
        category = case["concession"].split(":")[0]
        lines.append(f"Your special concession ({category}) is approved after we verify the proof, so please "
                     "keep the certificate ready.")
    lines.append("When is a good time to talk? You can also call us on " + agent_config.ADMISSIONS_PHONE + ".")
    text = " ".join(lines)
    digits = "".join(ch for ch in (lead.phone or "") if ch.isdigit())[-10:]
    return {"lead_id": str(lead.id), "text": text,
            "whatsapp_url": f"https://wa.me/91{digits}?text={quote(text)}" if len(digits) == 10 else None}
