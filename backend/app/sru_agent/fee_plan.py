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
    return {"label": best["label"], "amount": int(best["amount"])} if best else None


# How students describe themselves -> the official category (label as in the fee data). v4.13.0.
_DESCRIBED = (
    (r"\b(?:brother|sister|sibling|cousin\s+(?:brother|sister))\b.{0,50}\b(?:stud(?:y|ies|ying)|enrol\w*|"
     r"(?:at|in)\s+(?:sru|sr\s+university))", "Sibling (brother or sister) currently enrolled at SR University"),
    (r"\b(?:alumni|alumnus|alumna|passed\s+out\s+(?:of|from)\s+(?:sru|sr\s+university))\b", "SRU alumni"),
    (r"\b(?:father|mother|dad|daddy|mom|mum|amma|nanna|parent)\b.{0,30}\b(?:works?|working|employee|staff|faculty|"
     r"professor)\b.{0,25}\b(?:sru|sr\s+university|here|your\s+university)\b", "Children of regular SR University employees"),
    (r"\bsr\s+junior\s+college\b", "Students of SR Junior College"),
    (r"\b(?:army|navy|air\s*force|defen[cs]e|crpf|military|soldier|jawan|martyr)\b", "Children of Defence personnel"),
    (r"\b(?:police|constable)\b", "Children of State Police personnel"),
    (r"\b(?:single\s+(?:parent|mother|father|mom|dad)|divorced)\b", "Students with a single living parent"),
    (r"\b(?:orphan|lost\s+both\s+(?:my\s+)?parents)\b", "Students who have lost both parents"),
    (r"\bncc\b", "NCC 'C' certificate holders"),
    (r"\binternational[- ]level\s+(?:sports|player|athlete|champion)", "International-level sports achievers"),
    (r"\bnational[- ]level\s+(?:sports|player|athlete|champion)|\bsports\s+quota\b", "National-level sports achievers"),
    (r"\b(?:disab\w+|handicap\w*|pwd)\b", "Students with 50% or above disability"),
    (r"\bonly\s+girl\s+child\b", "Only girl child from Telangana"),
)


def infer_concession(text: str) -> dict | None:
    """The concession category a student describes ("my elder brother is studying at SRU" -> the sibling
    concession), from the official list; None if nothing fits. The exact label in the text wins."""
    exact = find_concession(text)
    if exact:
        return exact
    low = (text or "").lower()
    for pattern, label_start in _DESCRIBED:
        if re.search(pattern, low):
            for c in fees.load_data().get("special_concessions", []):
                if c["label"].lower().startswith(label_start.lower()):
                    return {"label": c["label"], "amount": int(c["amount"])}
    return None


def concession_fee(program: str, concession: dict, profile: dict | None = None) -> dict | None:
    """Tuition for the first year with a special concession. None if the programme is unknown."""
    merit = _merit_args(profile or {})
    fee = fees.calculate_fee(program, **{k: v for k, v in merit.items() if k != "board"},
                             board=merit.get("board") or "state_board")
    if fee.get("status") != "ok":
        return None
    tuition = _num(fee["tuition_first_year"])
    amount = int(concession["amount"])
    pct = int(fee.get("scholarship_percent") or 0)
    data = {
        "academic_year": fee.get("academic_year") or config.ADMISSION_YEAR,
        "program_key": fee.get("program_key"),
        "program": fees.short_name(fee["program_key"]),
        "concession": concession["label"],
        "concession_amount": fees.inr(amount),
        "tuition": fees.inr(tuition),
        "tuition_after_concession": fees.inr(max(tuition - amount, 0)),
        "per_semester_after_concession": fees.inr(max(tuition - amount, 0) // 2),
        "proof_note": PROOF_NOTE,
        "source": fee.get("source"),
    }
    if pct:
        after_merit = _num(fee["tuition_first_year_after_scholarship"])
        data.update({
            "merit_percent": pct,
            "tuition_after_merit": fees.inr(after_merit),
            "combine_note": COMBINE_NOTE.format(phone=config.ADMISSIONS_PHONE),
        })
    return data


def full_fee_chart(program: str, profile: dict | None = None, hostel: str = "none", transport: bool = False,
                   concession: dict | None = None) -> dict | None:
    """The complete first-year fee chart: every line the student pays, from the official fee data."""
    merit = _merit_args(profile or {})
    fee = fees.calculate_fee(program, hostel=hostel or "none", transport=bool(transport),
                             **{k: v for k, v in merit.items() if k != "board"},
                             board=merit.get("board") or "state_board")
    if fee.get("status") != "ok":
        return None
    pct = int(fee.get("scholarship_percent") or 0)
    rows = [{"item": "Tuition fee (first year)", "amount": fee["tuition_first_year"], "kind": "fee"}]
    if pct:
        rows.append({"item": f"Merit scholarship ({pct}%)", "amount": "− " + fee["saving_first_year"],
                     "kind": "discount", "note": fee.get("scholarship_basis_text") or None})
    rows.append({"item": "Other academic / university fees", "amount": fee["other_yearly_fees"], "kind": "fee",
                 "note": "per year"})
    rows.append({"item": "Enrollment fee", "amount": fee["one_time_enrollment_fee"], "kind": "fee",
                 "note": "one time"})
    hostel_info = fee.get("hostel") or {}
    if fee.get("has_hostel") and hostel_info.get("per_year"):
        rows.append({"item": f"Hostel ({hostel_info.get('type')})", "amount": hostel_info["per_year"], "kind": "fee",
                     "note": "includes meals"})
    if fee.get("transport_per_year"):
        rows.append({"item": "Transport (university bus)", "amount": fee["transport_per_year"], "kind": "fee",
                     "note": "varies by distance"})
    total = _num(fee["first_year_total_payable"])
    chart = {
        "academic_year": fee.get("academic_year") or config.ADMISSION_YEAR,
        "program_key": fee.get("program_key"),
        "program": fees.short_name(fee["program_key"]),
        "rows": rows,
        "first_year_total": fees.inr(total),
        "per_semester": fee.get("total_per_semester"),
        "application_fee": fee.get("one_time_application_fee"),
        "not_included": [x for x in (fee.get("not_included") or []) if x != "transport" or not transport],
        "source": fee.get("source"),
    }
    if concession:
        amount = int(concession["amount"])
        chart["concession"] = {
            "label": concession["label"],
            "amount": "− " + fees.inr(amount),
            "total_if_approved": fees.inr(max(total - amount, 0)),
            "note": PROOF_NOTE + (" " + COMBINE_NOTE.format(phone=config.ADMISSIONS_PHONE) if pct else ""),
        }
    return chart


def chart_share_text(chart: dict) -> str:
    """Plain text of the chart, for WhatsApp / copying (the card's Share button)."""
    lines = [f"SR University {chart['academic_year']} fee chart: {chart['program']}"]
    for r in chart["rows"]:
        lines.append(f"- {r['item']}: {r['amount']}" + (f" ({r['note']})" if r.get("note") else ""))
    lines.append(f"First-year total: {chart['first_year_total']}")
    if chart.get("concession"):
        c = chart["concession"]
        lines.append(f"With the {c['label']} concession, if approved: {c['total_if_approved']}")
    if chart.get("application_fee"):
        lines.append(f"Application fee (paid when applying): {chart['application_fee']}")
    lines.append("Source: official SR University fee card. Confirm with the Admissions Office: "
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
