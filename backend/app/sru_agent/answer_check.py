"""Self-check for answers written by the language model (v4.12.0).

Before an AI-written answer is sent, its numbers are checked against what the code knows for this turn:
  * a scholarship percentage stated next to the student's own fee calculation must be the calculator's;
    a different one is corrected;
  * every rupee amount must appear in a verified source of this turn (the fee calculation, the cards, the
    handbook / facts passages) or in the official fee data; if one does not, a short note asks the student to
    confirm with the Admissions Office (the text is not silently rewritten).
Answers written by the code itself come from the same data and pass unchanged.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from . import config, fees

_RUPEES = re.compile(r"(?:₹|rs\.?|inr)\s?(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_PCT_SCHOLARSHIP = re.compile(r"(\d{1,2})\s?%\s*(?:merit\s+)?(?:scholarship|waiver|fee\s+waiver)", re.IGNORECASE)
NOTE = ("\n\n_I couldn't verify every amount above against the official fee data; please confirm with the "
        "Admissions Office ({phone})._")


def _amounts(text: str) -> set[int]:
    out = set()
    for m in _RUPEES.finditer(text or ""):
        digits = m.group(1).replace(",", "").split(".")[0]
        if digits.isdigit():
            out.add(int(digits))
    return out


@lru_cache(maxsize=1)
def _fee_data_amounts() -> frozenset[int]:
    """Every whole-rupee number in the official fee data, plus halves (per semester)."""
    found: set[int] = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)) and v >= 1000:
            found.add(int(v))
            found.add(int(v) // 2)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            found.update(_amounts(v))

    walk(fees.load_data())
    found |= _engine_amounts()
    return frozenset(found)


def _engine_amounts() -> set[int]:
    """Every total the ONE fee engine can produce for a programme, slab and option (semester and year payables,
    course totals, per-year tuition): figures computed from the policy are verified figures."""
    found: set[int] = set()
    data = fees.load_data()
    pcts = sorted({0} | {s["percent"] for sets in data["slab_sets"].values() for t in sets.values() for s in t})
    for key in data["programs"]:
        for pct in pcts:
            for hostel in [None] + list(fees.hostel_per_year()):
                for bus in (False, True):
                    plan = fees.fee_schedule(key, pct, hostel=hostel, transport=bus)
                    for y in plan["years"]:
                        found.update({y["total"], y["annual_tuition"], y["scholarship"], y["tuition_before_scholarship"]})
                        for sem in y["semesters"]:
                            found.add(sem["total"])
                            found.update(abs(i["amount"]) for i in sem["items"])
                    if plan["course_total"]:
                        found.add(plan["course_total"])
    return {a for a in found if a >= 1000}


def check(text: str, *, fee_result: dict | None = None, sources: list | None = None) -> tuple[str, list[str]]:
    """(text to send, problems found). `sources`: strings or JSON-able objects verified for this turn."""
    if not text:
        return text, []
    problems = []
    out = text
    if fee_result and fee_result.get("status") == "ok":
        right = int(fee_result.get("scholarship_percent") or 0)

        def fix(m):
            n = int(m.group(1))
            if n != right and right > 0:
                problems.append(f"scholarship {n}% -> {right}%")
                return m.group(0).replace(m.group(1), str(right), 1)
            return m.group(0)

        out = _PCT_SCHOLARSHIP.sub(fix, out)
    verified = set(_fee_data_amounts())
    for src in list(sources or []) + ([fee_result] if fee_result else []):
        verified |= _amounts(src if isinstance(src, str) else json.dumps(src, ensure_ascii=False, default=str))
    unknown = sorted(a for a in _amounts(out) if a not in verified)
    if unknown:
        problems.append("unverified amounts: " + ", ".join(fees.inr(a) for a in unknown[:5]))
        out = out.rstrip() + NOTE.format(phone=config.ADMISSIONS_PHONE)
    return out, problems
