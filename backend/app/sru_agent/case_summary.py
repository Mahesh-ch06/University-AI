"""The counsellor's case summary (v4.12.0): what the student has done in the chat, in one glance.

Saved with a callback / counsellor request (lead metadata "case") and shown in the admin panel and the
counsellor copilot. Built only from what the student gave and what the code calculated (fee_journey), never
from model text. Mobile numbers typed in questions are masked.
"""
from __future__ import annotations

import re

from . import fee_journey, fees, fee_intake

_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")


def _mask(text: str) -> str:
    return _PHONE.sub(lambda m: "******" + re.sub(r"\D", "", m.group(0))[-4:], text or "")


def _marks(profile: dict) -> str | None:
    p = profile or {}
    num = fee_intake._num
    parts = []
    if p.get("raw_marks") and p.get("max_marks") and float(p["max_marks"]) > 100:
        parts.append(f"{num(p['raw_marks'])}/{num(p['max_marks'])}")
    elif p.get("percent") not in (None, ""):
        parts.append(f"{num(p['percent'])}%")
    if p.get("board_label") or p.get("board"):
        parts.append(str(p.get("board_label") or p.get("board")).replace("_", " "))
    if p.get("stream"):
        parts.append(str(p["stream"]))
    if p.get("eapcet_rank"):
        parts.append(f"EAPCET rank {p['eapcet_rank']}")
    if p.get("jee_percentile"):
        parts.append(f"JEE {p['jee_percentile']} %ile")
    if not parts:
        return None
    return " · ".join(parts) + (" (projected)" if p.get("is_projected") else "")


def build(profile: dict, conv_state: dict | None, history: list | None) -> dict:
    """A short, structured summary. Keys are absent when unknown."""
    profile = profile or {}
    conv_state = conv_state or {}
    out: dict = {}
    st = conv_state.get(fee_journey.KEY) or {}
    program = st.get("program") or conv_state.get("active_program") or profile.get("program_interest")
    key = fees.find_program(str(program)) if program else None
    if key:
        out["program"] = fees.short_name(key)
    marks = _marks(profile)
    if marks:
        out["marks"] = marks
    signals = []
    if st.get("active") and key:
        data = fee_journey.evaluate({**st, "program": key}, profile)
        if data:
            sch, cons = data["scholarship"], data["special_consideration"]
            if sch.get("amount"):
                out["scholarship"] = f"{sch['label'].split(' ')[0]} ({sch['status']})"
                signals.append("scholarship")
            if cons.get("category"):
                out["concession"] = f"{cons['category']}: {cons['label']}"
                signals.append("concession_pending")
                if st.get("proof") == "ready":
                    signals.append("proof_ready")
            if st.get("hostel") not in (None, "none"):
                out["hostel"] = fees.HOSTEL_LABELS.get(st["hostel"], st["hostel"])
            elif st.get("hostel") == "none":
                out["hostel"] = "Day scholar" + (" + bus" if st.get("transport") else "")
            out["fee"] = data["payable_confirmed"] + " confirmed" + (
                f" · {data['payable_after_approval']} if approved" if data.get("payable_after_approval") else "")
            if st.get("final_shown"):
                signals.append("fee_summary_done")
    if profile.get("is_projected"):
        signals.append("projected_marks")
    asked = [_mask(h.get("text", ""))[:120] for h in (history or []) if h.get("role") == "user"]
    asked = [a for a in asked if len(a.split()) >= 3][-3:]
    if asked:
        out["asked"] = asked
    if profile.get("is_parent"):
        signals.append("parent")
    out["signals"] = signals
    return out


def lines(case: dict) -> list[str]:
    """The summary as readable lines (admin panel, drafts)."""
    labels = (("program", "Course"), ("marks", "Marks"), ("scholarship", "Scholarship"),
              ("concession", "Concession"), ("hostel", "Hostel"), ("fee", "Fee"))
    out = [f"{label}: {case[k]}" for k, label in labels if case.get(k)]
    if case.get("asked"):
        out.append("Asked: " + " | ".join(f'"{a}"' for a in case["asked"]))
    return out
