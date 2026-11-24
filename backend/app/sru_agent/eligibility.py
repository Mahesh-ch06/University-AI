"""Admission eligibility: the ONE place where SRU Buddy decides whether marks meet a programme's minimum.

Every flow (fee intake, scholarship counselling, the admission journey, the AI's check_eligibility and
calculate_fee tools, the old chat endpoint) calls this module, so the answer can never differ between
flows. No threshold is written anywhere else.

Source of truth: ``fees_2027_28.json`` (built from the official 2027-28 fee card):
  * ``min_percent``                      - minimum on the 2027-28 fee card (current, authoritative);
  * ``fee_band_min_percent``             - where the fee card's fee band starts (CSE / ECE: 55%);
  * ``website_crosscheck.min_percent``   - the programme page on sru.edu.in (2026-27 pages, older).

These sources do not always agree (for B.Tech the fee card says 50%, the programme page 60% in PCM).
SRU Buddy never picks one of them:
  * below the LOWEST documented minimum      -> ``below_minimum``      (does not meet any source);
  * at / above the HIGHEST documented minimum -> ``meets_minimum``      (meets every source);
  * in between                                -> ``needs_confirmation`` (sources disagree; the
    Admissions Office confirms). The disputed value is never presented as confirmed.

Admission eligibility is separate from scholarship eligibility (scholarship slabs live in fees.py).
Minimums are inclusive: 50% meets a 50% minimum, 49.99% does not. Percentages are compared unrounded.
"""
from __future__ import annotations

import re

from . import config, fees

BELOW = "below_minimum"
MEETS = "meets_minimum"
CONFIRM = "needs_confirmation"
NEED_MARKS = "need_marks"
UNKNOWN_PROGRAM = "unknown_program"

ADMISSIONS_CONTACT = "the Admissions Office (833 100 3030, info@sru.edu.in)"

# Streams a student may name, and the words that identify them.
_STREAM_WORDS = {
    "MPC": r"\b(?:mpc|pcm|m\.?p\.?c|maths?,?\s*physics,?\s*(?:and\s+)?chemistry|physics,?\s*chemistry,?\s*(?:and\s+)?maths?(?:ematics)?)\b",
    "BiPC": r"\b(?:bipc|bi\.?p\.?c|pcb|biology|physics,?\s*chemistry,?\s*(?:and\s+)?biology)\b",
    "MEC": r"\b(?:mec|cec|hec|commerce|arts|humanities|civics|economics)\b",
}
_STREAM_LABEL = {"MPC": "Maths, Physics and Chemistry (MPC)", "BiPC": "Biology, Physics and Chemistry (BiPC)",
                 "MEC": "a non-science stream (MEC / CEC / HEC)"}


def percent_from_marks(raw, max_marks) -> float | None:
    """Exact percentage. 230 out of 1000 -> 23.0. Returns None for an impossible pair."""
    try:
        raw_f, max_f = float(raw), float(max_marks)
    except (TypeError, ValueError):
        return None
    if max_f <= 0 or raw_f < 0 or raw_f > max_f:
        return None
    return raw_f / max_f * 100.0


def show_percent(value: float) -> str:
    """23.0 -> '23%', 91.4893 -> '91.49%'. Display only; comparisons use the exact value."""
    v = round(float(value), 2)
    return f"{int(v)}%" if v == int(v) else f"{v:g}%"


def parse_stream(message: str) -> str | None:
    low = (message or "").lower()
    for code, pattern in _STREAM_WORDS.items():
        if re.search(pattern, low):
            return code
    return None


def stream_requirement(program_key: str) -> dict:
    """Subjects the fee card lists for the programme: {'any_of': [...], 'label': str} or {} if none / unstated."""
    prog = fees.load_data()["programs"].get(program_key) or {}
    note = (prog.get("eligibility_note") or "")
    low = note.lower()
    if prog.get("level") == "pg":
        return {}
    if "confirmed by the admissions office" in low:
        return {"unstated": True, "label": note}
    has_mpc = bool(re.search(r"\b(?:mpc|pcm)\b|maths, physics, chemistry", low))
    has_bipc = bool(re.search(r"\b(?:pcb|bipc)\b", low))
    if has_mpc and has_bipc:
        return {"any_of": ["MPC", "BiPC"], "label": "10+2 / Intermediate with PCM (MPC) or PCB (BiPC)"}
    if has_mpc:
        return {"any_of": ["MPC"], "label": "10+2 / Intermediate with Maths, Physics and Chemistry (MPC)"}
    if has_bipc:
        return {"any_of": ["BiPC"], "label": note}
    return {}


def thresholds(program_key: str) -> dict:
    """Every documented minimum for the programme, lowest and highest, and whether they disagree."""
    prog = fees.load_data()["programs"][program_key]
    sources = [{"source": f"the {config.ADMISSION_YEAR} fee card", "percent": float(prog["min_percent"])}]
    if prog.get("fee_band_min_percent"):
        sources.append({"source": f"the {config.ADMISSION_YEAR} fee card's fee band for this programme",
                        "percent": float(prog["fee_band_min_percent"])})
    site = prog.get("website_crosscheck") or {}
    if site.get("min_percent") is not None:
        sources.append({"source": "the university's programme page (2026-27)", "percent": float(site["min_percent"]),
                        "requirement": site.get("requirement"), "entrance": site.get("entrance")})
    values = [s["percent"] for s in sources]
    return {"floor": min(values), "ceiling": max(values), "sources": sources, "conflict": min(values) != max(values),
            "entrance_note": site.get("entrance")}


def lowest_minimum_any_program(level: str = "ug") -> float:
    """The lowest minimum of any programme at this level (used before the programme is known)."""
    progs = fees.load_data()["programs"].values()
    return min(float(p["min_percent"]) for p in progs if p.get("level", "ug") == level)


def assess(program_key: str | None, percent=None, stream: str | None = None) -> dict:
    """Decide admission eligibility on marks (and stream where the programme names one)."""
    if not program_key or program_key not in fees.load_data()["programs"]:
        return {"status": UNKNOWN_PROGRAM}
    prog = fees.load_data()["programs"][program_key]
    name = fees.clean_program_name(program_key)
    level = prog.get("level", "ug")
    if percent is None:
        return {"status": NEED_MARKS, "program_key": program_key, "program": name, "level": level}
    pct = float(percent)
    t = thresholds(program_key)
    req = stream_requirement(program_key)
    if pct < t["floor"]:
        status = BELOW
    elif pct >= t["ceiling"]:
        status = MEETS
    else:
        status = CONFIRM
    stream_ok = None
    if req.get("any_of") and stream:
        stream_ok = stream in req["any_of"]
    return {
        "status": status, "program_key": program_key, "program": name, "level": level, "percent": pct,
        "percent_text": show_percent(pct), "floor": t["floor"], "ceiling": t["ceiling"], "sources": t["sources"],
        "conflict": t["conflict"], "entrance_note": t["entrance_note"] if level == "ug" else None,
        "stream_requirement": req, "stream": stream, "stream_ok": stream_ok,
        # Asked only when the marks do not already rule the student out.
        "needs_stream": bool(req.get("any_of")) and stream is None and status != BELOW,
        "eligible": (False if status == BELOW or stream_ok is False else
                     True if status == MEETS and (stream_ok or not req.get("any_of")) else None),
    }


def explain(result: dict, score_text: str | None = None) -> str:
    """The wording every flow uses for an eligibility result. Never claims more than the data supports."""
    status = result.get("status")
    if status in (UNKNOWN_PROGRAM, NEED_MARKS):
        return ""
    name = result["program"]
    pct = result["percent_text"]
    qualifying = "your qualifying degree" if result.get("level") == "pg" else "10+2 / Intermediate"
    given = f"Based on the {score_text} you provided, your percentage is **{pct}**." if score_text else \
        f"Your percentage is **{pct}**."
    floor = show_percent(result["floor"])
    if status == BELOW:
        return (f"{given} That's below the official **{floor} minimum** for **{name}**, so you do not currently "
                f"meet the general eligibility criteria with these marks. If the marks aren't right, or to talk "
                f"about options, contact {ADMISSIONS_CONTACT}.")
    if result.get("stream_ok") is False:
        req = result["stream_requirement"]["label"]
        studied = _STREAM_LABEL.get(result.get("stream"), result.get("stream"))
        return (f"{given} But **{name}** needs {req}, and you took {studied}, so you don't meet its subject "
                f"requirement. The Admissions Office ({ADMISSIONS_CONTACT.split('(')[1].rstrip(')')}) can suggest "
                f"programmes that fit.")
    lines = []
    req = result.get("stream_requirement") or {}
    if status == CONFIRM:
        listed = "; ".join(f"{s['source']}: {show_percent(s['percent'])}" for s in result["sources"])
        lines.append(f"{given} The official sources list different minimum marks for **{name}** ({listed}). "
                     f"Your score meets the lowest of these but not the highest, so I can't confirm your "
                     f"eligibility. Please confirm it with {ADMISSIONS_CONTACT}.")
    else:
        subjects = (f", and you studied the required subjects ({', '.join(req['any_of'])})"
                    if req.get("any_of") and result.get("stream_ok") else "")
        lines.append(f"{given} This meets the minimum marks in {qualifying} listed for **{name}** in every "
                     f"official source (highest listed: {show_percent(result['ceiling'])}){subjects}.")
    if req.get("any_of") and not result.get("stream_ok"):
        lines.append(f"{name} also requires {req['label']}.")
    elif req.get("unstated"):
        lines.append("The required 10+2 subjects for this programme are confirmed by the Admissions Office.")
    closing = "Final admission depends on document verification and seat availability."
    if result.get("entrance_note") and status != BELOW:
        closing = (f"Note: the university's programme page also mentions: {result['entrance_note']}. The "
                   f"Admissions Office confirms whether this is needed for "
                   f"{config.ADMISSION_YEAR}. {closing}")
    lines.append(closing)
    return "\n\n".join(lines)


def stream_question(result: dict) -> str:
    req = result["stream_requirement"]
    return (f"One more thing: {result['program']} requires {req['label']}. Which subjects (group) did you "
            f"study in 10+2 / Intermediate?")


def stream_chips(result: dict) -> list[str]:
    return ["MPC (Maths, Physics, Chemistry)", "BiPC (Biology, Physics, Chemistry)", "MEC / CEC / Other"]


_OVERVIEW_ROWS = [
    ("B.Tech CSE / ECE", "btech_cse"),
    ("Other B.Tech branches", "btech_mech"),
    ("B.Sc (Hons.) Agriculture", "bsc_agri"),
    ("BBA", "bba"),
    ("B.Com", "bcom"),
    ("BCA", "bca"),
    ("B.Des", "bdes"),
    ("MBA", "mba"),
    ("MCA", "mca"),
    ("M.Tech", "mtech"),
]


def _minimum_cell(program_key: str) -> str:
    t = thresholds(program_key)
    if not t["conflict"]:
        return show_percent(t["floor"])
    parts = [f"{show_percent(s['percent'])} ({s['source'].replace('the ', '', 1)})" for s in t["sources"]]
    return "; ".join(parts)


def rule_text(program_key: str) -> str:
    """The eligibility rule for one programme, from the data file (v4.13.0): qualification, minimum marks (every
    documented minimum when the sources differ), the entrance note, and the closing caveat."""
    prog = fees.load_data()["programs"][program_key]
    t = thresholds(program_key)
    name = fees.clean_program_name(program_key)
    lines = [f"**Eligibility for {name} ({config.ADMISSION_YEAR})**", ""]
    lines.append(f"- Qualification: {prog.get('eligibility_note') or 'as listed by the Admissions Office'}")
    if t["conflict"]:
        parts = ", ".join(f"{show_percent(s['percent'])} in {s['source'].replace('the ', '', 1)}" for s in t["sources"])
        lines.append(f"- Minimum marks: the official sources differ ({parts}); the Admissions Office confirms the "
                     f"{config.ADMISSION_YEAR} figure ({config.ADMISSIONS_PHONE}).")
    else:
        lines.append(f"- Minimum marks: {show_percent(t['floor'])}")
    if t.get("entrance_note"):
        lines.append(f"- Entrance: {t['entrance_note']}")
    lines += ["", "Final admission depends on document verification and seat availability.",
              "", "Shall I check yours with your marks?"]
    return "\n".join(lines)


def overview_text() -> str:
    """Eligibility for the main programmes, built from the data file (never hand-written thresholds)."""
    data = fees.load_data()["programs"]
    lines = [f"### Admission eligibility at SR University ({config.ADMISSION_YEAR})", "",
             "Minimum marks differ by programme. Where the official sources list different minimums, both are "
             "shown and the Admissions Office confirms the 2027-28 figure.", "",
             "| Programme | Qualification | Minimum marks |", "|---|---|---|"]
    for label, key in _OVERVIEW_ROWS:
        if key in data:
            lines.append(f"| {label} | {data[key]['eligibility_note']} | {_minimum_cell(key)} |")
    lines += ["", "Final admission depends on document verification and seat availability."]
    return "\n".join(lines)
