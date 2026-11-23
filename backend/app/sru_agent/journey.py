"""The admission journey's academic details, scoped to ONE conversation.

Every flow (the eligibility journey, scholarship counselling, fee questions, the academic details form and the
AI's tools) reads the student's academic details from the profile. That keeps a single source of truth inside a
conversation, so nothing the student said is asked again.

Across conversations the details must not be carried over silently: a genuinely new admission journey starts
with a clean form. The profile therefore records which conversation its academic details belong to
(``academic_conv``). When a different conversation speaks:

* the details are filed with the conversation they came from (its conversation state ``academic``), so going
  back to that chat finds them again;
* a compact copy is kept as ``saved_academic``: the student can reuse it with one tap ("Use my saved details"),
  never automatically;
* this conversation's own details (if any) are loaded.

Profiles saved before this existed have no owner: their details are adopted by the conversation that uses them
next, so nothing already collected is lost.
"""
from __future__ import annotations

from . import memory

# Facts about the student's 10+2 / degree marks that belong to one admission journey.
ACADEMIC_KEYS = (
    "board", "board_label", "board_key", "academic_stage", "stage_label", "is_projected", "raw_marks",
    "max_marks", "percent", "marks_confirmed", "stream", "admission_route", "route_label", "eapcet_rank",
    "jee_percentile", "ib_score", "no_entrance", "degree_percent", "scholarship_percent",
)
# What is kept for one-tap reuse in a later conversation (small enough for one database row).
_SAVED_KEYS = ("board_key", "academic_stage", "raw_marks", "max_marks", "percent", "stream",
               "admission_route", "eapcet_rank", "jee_percentile", "ib_score")

_BOARD_LABELS = {
    "ts_state_board": ("state_board", "Telangana Intermediate (TSBIE)"),
    "ap_state_board": ("state_board", "Andhra Pradesh Intermediate (BIEAP)"),
    "cbse": ("cbse", "CBSE"),
    "icse": ("cbse", "ISC / ICSE"),
    "other_state_board": ("state_board", "Other State Board"),
    "ib": ("ib", "International Baccalaureate (IB)"),
}
_STAGE_LABELS = {
    "1st_year": "Intermediate 1st Year (11th)",
    "2nd_year": "Intermediate 2nd Year (12th)",
    "completed": "Completed Intermediate (Passed out)",
}


def board_fields(board_key: str | None) -> dict:
    if board_key not in _BOARD_LABELS:
        return {}
    board, label = _BOARD_LABELS[board_key]
    return {"board_key": board_key, "board": board, "board_label": label}


def stage_fields(stage: str | None) -> dict:
    if stage not in _STAGE_LABELS:
        return {}
    return {"academic_stage": stage, "stage_label": _STAGE_LABELS[stage], "is_projected": stage != "completed"}


def snapshot(profile: dict) -> dict:
    return {k: profile[k] for k in ACADEMIC_KEYS if profile.get(k) not in (None, "")}


def _compact(details: dict) -> dict:
    return {k: details[k] for k in _SAVED_KEYS if details.get(k) not in (None, "")}


def expand(saved: dict) -> dict:
    """Saved compact details -> full profile fields (labels re-derived from the keys)."""
    out = dict(saved or {})
    out.update(board_fields(out.get("board_key")))
    out.update(stage_fields(out.get("academic_stage")))
    if out.get("raw_marks") is not None or out.get("percent") is not None:
        out["marks_confirmed"] = True
    return out


async def scope_profile(session_id: str, conversation_id, profile: dict, conv_state: dict) -> dict:
    """Make the profile hold THIS conversation's academic details. Returns the profile to use."""
    key = str(conversation_id or "")
    owner = profile.get("academic_conv")
    if owner == key or not key:
        return profile
    current = snapshot(profile)
    if owner is None:
        # Details from before conversation scoping (or none yet): they belong to this conversation.
        profile["academic_conv"] = key
        await memory.replace_profile(session_id, profile)
        return profile
    if current:
        await memory.update_conversation_state(session_id, owner, academic=current)
        profile["saved_academic"] = _compact(current)
    for k in ACADEMIC_KEYS:
        profile.pop(k, None)
    profile.update(conv_state.get("academic") or {})
    profile["academic_conv"] = key
    await memory.replace_profile(session_id, profile)
    return profile


def saved_summary(profile: dict) -> str | None:
    """'670/1000, Telangana Intermediate (TSBIE), MPC' for the details saved from an earlier conversation."""
    saved = expand(profile.get("saved_academic") or {})
    if not saved:
        return None
    parts = []
    if saved.get("raw_marks") and saved.get("max_marks") and float(saved["max_marks"]) > 100:
        parts.append(f"{_num(saved['raw_marks'])}/{_num(saved['max_marks'])}")
    elif saved.get("percent") is not None:
        parts.append(f"{_num(saved['percent'])}%")
    if saved.get("board_label"):
        parts.append(saved["board_label"])
    if saved.get("stream"):
        parts.append(saved["stream"])
    return ", ".join(parts) or None


async def restore_saved(session_id: str, profile: dict) -> dict:
    """Use the saved details in this conversation (only when the student asks for it)."""
    saved = expand(profile.get("saved_academic") or {})
    if saved:
        profile.update(saved)
        await memory.replace_profile(session_id, profile)
    return profile


def _num(value):
    f = float(value)
    return int(f) if f == int(f) else round(f, 2)
