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
