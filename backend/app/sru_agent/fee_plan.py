"""Fee plans built from the official 2027-28 fee data (fees.calculate_fee): the fee with a special-category
concession, and the complete first-year fee chart a student can share.

Every amount comes from fees.calculate_fee and the concession list on the fee card; nothing is estimated
here. A special concession is shown separately from the totals' main line, because it applies only after
the student's proof is verified, and whether it combines with a merit scholarship is decided by the
Admissions Office (the fee card does not say).
"""
from __future__ import annotations

import re

from . import config, fees

PROOF_NOTE = ("Applies only after you submit valid proof for this category and the Admissions Office "
              "verifies it.")
COMBINE_NOTE = ("Whether it can be combined with your merit scholarship is confirmed by the Admissions "
                "Office ({phone}).")


def _num(text) -> int:
    """'₹2,55,000' -> 255000 (0 when missing)."""
    if text is None:
        return 0
    if isinstance(text, (int, float)):
        return int(text)
    digits = re.sub(r"[^0-9]", "", str(text))
    return int(digits) if digits else 0


def _merit_args(profile: dict) -> dict:
    """The scores the student gave in this conversation, in calculate_fee's terms."""
    p = profile or {}
    return {k: p.get(k) for k in ("percent", "board", "eapcet_rank", "jee_percentile", "ib_score")
            if p.get(k) not in (None, "")}


def find_concession(text: str) -> dict | None:
    """The concession whose fee-card label appears in the text (longest label wins), or None."""
    low = (text or "").lower()
    best = None
    for c in fees.load_data().get("special_concessions", []):
        label = c["label"].lower()
        if label in low and (best is None or len(label) > len(best["label"])):
            best = c
    return _item(best) if best else None


def _item(c: dict) -> dict:
    return {"key": c["key"], "label": c["label"], "amount": int(c["amount"])}


def _by_key(key: str) -> dict | None:
    c = next((c for c in fees.load_data().get("special_concessions", []) if c["key"] == key), None)
    return _item(c) if c else None


# How students describe themselves -> the official category key in the fee policy (labels come from the policy).
_DESCRIBED = (
    (r"\b(?:brother|sister|sibling|cousin\s+(?:brother|sister))\b.{0,50}\b(?:stud(?:y|ies|ying)|enrol\w*|"
     r"(?:at|in)\s+(?:sru|sr\s+university))", "sibling"),
    (r"\b(?:alumni|alumnus|alumna|old\s+student|passed\s+out\s+(?:of|from)\s+(?:sru|sr\s+university))\b", "alumni"),
    (r"\b(?:father|mother|dad|daddy|mom|mum|amma|nanna|parent)\b.{0,30}\b(?:works?|working|employee|staff|faculty|"
     r"professor)\b.{0,25}\b(?:sru|sr\s+university|here|your\s+university)\b", "staff_child"),
    (r"\bsr\s+junior\s+college\b", "sr_junior_college"),
    (r"\b(?:army|navy|air\s*force|defen[cs]e|crpf|military|soldier|jawan|martyr)\b", "defence"),
    (r"\b(?:police|constable)\b", "state_police"),
    (r"\b(?:single\s+(?:parent|mother|father|mom|dad)|divorced|one\s+parent)\b", "single_parent"),
    (r"\b(?:orphan|lost\s+both\s+(?:my\s+)?parents|both\s+parents\s+(?:not\s+alive|died|passed))\b", "orphan"),
    (r"\bncc\b", "ncc_c"),
    (r"\binternational[- ]level\s+(?:sports|player|athlete|champion)|\bsports\W+international\b", "sports_international"),
    (r"\bnational[- ]level\s+(?:sports|player|athlete|champion)|\bsports\s+quota\b|\bsports\W+national\b",
     "sports_national"),
    (r"\b(?:disab\w+|handicap\w*|pwd)\b", "disability"),
    (r"\b(?:only|single|one)\s+girl\s+child\b", "only_girl_child_telangana"),
    (r"\bsiblings?\b", "sibling"),
    (r"\blateral\s+entry\b|\becet\b", "lateral_entry"),
)


def infer_concession(text: str) -> dict | None:
    """The concession category a student describes ("my elder brother is studying at SRU" -> the sibling
    concession), from the official list; None if nothing fits. The exact label in the text wins."""
    exact = find_concession(text)
    if exact:
        return exact
    low = (text or "").lower()
    for pattern, key in _DESCRIBED:
        if re.search(pattern, low):
            return _by_key(key)
    return None


# v4.15.0: a group the student names that has several official categories ("any concession for girls?",
# "sports quota?"): every matching category, from the official list (word -> label words).
_GROUPS = [(r"\bgirls?\b|\bdaughter\b|\bfemale\b|\bwomen\b", ("only_girl_child_telangana", "girl_child_outside_telangana")),
           (r"\bsports?\b|\bathlete|\bplayer\b|\bquota\b.*\bsports?\b", ("sports_national", "sports_international")),
           (r"^(?!.*\b(?:single|divorced|lost\s+both|orphan)\b).*\bparents?\b", ("orphan", "single_parent")),
           (r"\b(?:police|defen[cs]e|army|crpf|martyr|military)\b", ("defence", "state_police"))]


def concessions_for_group(text: str) -> list[dict]:
    """All official categories for a group the student names, when there are several (else [])."""
    low = (text or "").lower()
    for pattern, keys in _GROUPS:
        if re.search(pattern, low):
            hits = [h for h in (_by_key(k) for k in keys) if h]
            if len(hits) > 1:
                return hits
    return []


def _concession_ref(concession: dict) -> str:
    return concession.get("key") or concession["label"]


def concession_fee(program: str, concession: dict, profile: dict | None = None) -> dict | None:
    """First-year fee with a special concession, from the ONE fee engine. None if the programme is unknown."""
    merit = _merit_args(profile or {})
    args = {k: v for k, v in merit.items() if k != "board"}
    board = merit.get("board") or "state_board"
    fee = fees.calculate_fee(program, board=board, concessions=[_concession_ref(concession)], **args)
    if fee.get("status") != "ok":
        return None
    amount = int(concession["amount"])
    pct = int(fee.get("scholarship_percent") or 0)
    after_merit = _num(fee["tuition_first_year_after_scholarship"])
    data = {
        "academic_year": fee.get("academic_year") or config.ADMISSION_YEAR,
        "program_key": fee.get("program_key"),
        "program": fees.short_name(fee["program_key"]),
        "concession": concession["label"],
        "concession_amount": fees.inr(amount),
        "tuition": fee["tuition_first_year"],
        "tuition_after_concession": fees.inr(max(after_merit - amount, 0)),
        "sem1_payable": fee["sem1_total_payable"],
        "sem2_payable": fee["sem2_total_payable"],
        "first_year_total": fee["first_year_total_payable"],
        "semester_note": "Concession deducted from tuition in Semester 1 of each year (subject to verification).",
        "proof_note": PROOF_NOTE,
        "source": fee.get("source"),
    }
    if pct:
        data.update({
            "merit_percent": pct,
            "tuition_after_merit": fees.inr(after_merit),
            "combine_note": COMBINE_NOTE.format(phone=config.ADMISSIONS_PHONE),
        })
    return data


def full_fee_chart(program: str, profile: dict | None = None, hostel: str = "none", transport: bool = False,
                   concession: dict | None = None) -> dict | None:
    """The complete first-year fee chart, semester by semester, from the ONE fee engine (fees.calculate_fee)."""
    merit = _merit_args(profile or {})
    args = {k: v for k, v in merit.items() if k != "board"}
    board = merit.get("board") or "state_board"
    fee = fees.calculate_fee(program, hostel=hostel or "none", transport=bool(transport), board=board, **args)
    if fee.get("status") != "ok":
        return None
    pct = int(fee.get("scholarship_percent") or 0)
    rows = [{"item": "Tuition fee (first year)", "amount": fee["tuition_first_year"], "kind": "fee"}]
    if pct:
        rows.append({"item": f"Merit scholarship ({pct}%)", "amount": "− " + fee["saving_first_year"],
                     "kind": "discount", "note": fee.get("scholarship_basis_text") or None})
    notes = {"enrollment_fee": "one time", "other_fee": "per year", "exam_fee": "Year 1 only",
             "hostel": "includes meals", "electricity_deposit": "one time", "bus": "optional"}
    for item in fee["semester_1"]["items"] + fee["semester_2"]["items"]:
        if item["kind"] == "tuition":
            continue
        rows.append({"item": item["item"], "amount": item["amount"], "kind": "fee", "note": notes.get(item["key"])})
    chart = {
        "academic_year": fee.get("academic_year") or config.ADMISSION_YEAR,
        "program_key": fee.get("program_key"),
        "program": fees.short_name(fee["program_key"]),
        "rows": rows,
        "semesters": [{"semester": 1, **fee["semester_1"]}, {"semester": 2, **fee["semester_2"]}],
        "sem1_total": fee["sem1_total_payable"],
        "sem2_total": fee["sem2_total_payable"],
        "first_year_total": fee["first_year_total_payable"],
        "per_semester": fee.get("per_semester_after_scholarship"),
        "course_total": fee.get("full_course_total"),
        "duration_years": fee.get("duration_years"),
        "application_fee": fee.get("application_fee"),
        "not_included": list(fee.get("not_included") or []),
        "flags": fee.get("flags") or [],
        "source": fee.get("source"),
    }
    if concession:
        with_c = fees.calculate_fee(program, hostel=hostel or "none", transport=bool(transport), board=board,
                                    concessions=[_concession_ref(concession)], **args)
        chart["concession"] = {
            "label": concession["label"],
            "amount": "− " + fees.inr(int(concession["amount"])),
            "total_if_approved": with_c["first_year_total_payable"],
            "sem1_if_approved": with_c["sem1_total_payable"],
            "note": PROOF_NOTE + (" " + COMBINE_NOTE.format(phone=config.ADMISSIONS_PHONE) if pct else ""),
        }
    return chart


def chart_share_text(chart: dict) -> str:
    """Plain text of the chart, for WhatsApp / copying (the card's Share button)."""
    lines = [f"SR University {chart['academic_year']} fee chart: {chart['program']}"]
    for r in chart["rows"]:
        lines.append(f"- {r['item']}: {r['amount']}" + (f" ({r['note']})" if r.get("note") else ""))
    if chart.get("sem1_total"):
        lines.append(f"Semester 1: {chart['sem1_total']} | Semester 2: {chart['sem2_total']}")
    lines.append(f"First-year total: {chart['first_year_total']}")
    if chart.get("concession"):
        c = chart["concession"]
        lines.append(f"With the {c['label']} concession, if approved: {c['total_if_approved']}")
    if chart.get("application_fee"):
        lines.append(f"Application fee (paid when applying): {chart['application_fee']}")
    lines.append("Source: official SR University 2027-28 fee circular. Confirm with the Admissions Office: "
                 f"{config.ADMISSIONS_PHONE}.")
    return "\n".join(lines)


# ---------------------------------------------------------------- the concessions picker (v4.12.0)
# The fee card's 19 categories in five groups, so a student opens only the group that may apply. The
# sensitive ones (lost parents, single parent, disability) sit in "Other circumstances": never asked about,
# chosen privately. Every key must exist in the fee data (test_v412 checks that all 19 are placed once).
CONCESSION_GROUPS = [
    {"key": "state", "title": "Your state", "hint": "Andhra Pradesh, other states, outside India",
     "items": ["andhra_pradesh", "non_local", "girl_child_outside_telangana", "only_girl_child_telangana",
               "international"]},
    {"key": "family", "title": "Family link to SRU", "hint": "Sibling here, alumni family, SR staff, SR Junior College",
     "items": ["sibling", "alumni", "staff_child", "sr_junior_college"]},
    {"key": "service", "title": "Parent in service or honoured", "hint": "Defence / CRPF, State Police, Padma, Gallantry",
     "items": ["defence", "state_police", "padma_gallantry"]},
    {"key": "sports", "title": "Sports or NCC", "hint": "International, national, NCC 'C'",
     "items": ["sports_international", "sports_national", "ncc_c"]},
    {"key": "other", "title": "Other circumstances", "hint": "Lateral entry and personal circumstances",
     "private": True, "items": ["lateral_entry", "single_parent", "orphan", "disability"]},
]


def concession_groups() -> list[dict]:
    """The groups with each category's label and yearly amount from the fee data."""
    by_key = {c["key"]: c for c in fees.load_data().get("special_concessions", [])}
    out = []
    for g in CONCESSION_GROUPS:
        items = [{"category": by_key[k]["label"], "per_year": fees.inr(by_key[k]["amount"])}
                 for k in g["items"] if k in by_key]
        if items:
            out.append({"key": g["key"], "title": g["title"], "hint": g["hint"],
                        "private": bool(g.get("private")), "items": items})
    return out


def concession_card(program: str | None = None, in_evaluation: bool = False) -> dict:
    """The special concessions card, in the form the admin panel has chosen (grouped or the full table)."""
    from app.services import app_settings

    mode = app_settings.get("concession_picker")
    data = {**fees.special_concessions(), "program": program, "mode": mode, "allow_none": in_evaluation}
    if mode == "grouped":
        data["groups"] = concession_groups()
    return {"type": "get_special_concessions", "data": data}


def apply_card_settings(cards) -> None:
    """Cards made elsewhere (for example by a model tool call) follow the admin panel's choice too."""
    from app.services import app_settings

    for c in cards or ():
        if isinstance(c, dict) and c.get("type") == "get_special_concessions" and isinstance(c.get("data"), dict):
            d = c["data"]
            if "mode" not in d:
                d["mode"] = app_settings.get("concession_picker")
                d.setdefault("allow_none", False)
            if d["mode"] == "grouped" and not d.get("groups"):
                d["groups"] = concession_groups()
