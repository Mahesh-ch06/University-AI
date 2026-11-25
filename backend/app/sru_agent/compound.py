"""One message, several questions: when to answer each part separately (v4.13.0).

The decomposition service (app/services/decomposition_service.py) finds messages that ask more than one thing
("about sru and about hostels", "cse vs aiml and why sru"). Answering each part is good. It must never take a
message away from a flow that understands it better. So the agent splits a message only when ALL of these hold:

1. It carries no action and none of the student's own data: no digits (marks, ranks, phone numbers), no
   callback / counsellor / visit / apply / booking request, no "I got / I want / my marks...". Those go to the
   flows that save leads, calculate fees and book visits.
2. Every part is a topic answered from verified content (see `topic`). A part we can't place means: no split
   (the normal flow, or the model with the whole message, answers it).
3. At least two different topics ("food stalls and food options" is one topic: no split).
4. Fees: only when the programme is B.Tech CSE (named or already chosen) or not known at all (then the part
   asks which programme, never assumes CSE). Another programme named: no split (the fee flow handles it).

Pure functions: the agent does the I/O.
"""

from __future__ import annotations

import re

from app.services.decomposition_service import _fast_split, _is_compound_query
from app.sru_agent import fees

_ACTION = re.compile(
    r"\b(call\s*(?:me|back)|callback|contact\s+me|reach\s+me|ring\s+me|whats\s*app\s+me|talk\s+to|speak\s+(?:to|with)|"
    r"counsell?or|visit|tour|apply|application|register|registration|book|booking|schedule|enrol|enroll|"
    r"my\s+(?:marks?|percentage|rank|score|name|number|phone|mobile|son|daughter|child)|"
    r"i\s+(?:got|scored|have|am(?!\s+(?:leaving|from|coming|moving|relocating|shifting|travell?ing))|want|need|will|"
    r"would|wish))\b",
    re.IGNORECASE,
)

_CSE = re.compile(r"\b(?:cse|computer\s+science)\b", re.IGNORECASE)
_AIML = re.compile(r"\b(?:aiml|ai\s*(?:&|and)\s*ml|machine\s+learning|artificial\s+intelligence)\b", re.IGNORECASE)
_COMPARE = re.compile(r"\b(?:vs|versus|compare|comparison|difference\s+between)\b", re.IGNORECASE)
_WHY_SRU = re.compile(r"\bwhy\s+(?:should\s+i\s+)?(?:choose|join|pick)?\s*(?:sru|sr\s*university)\b|"
                      r"\b(?:reasons?|advantages?|benefits?)\b(?!.{0,20}\b(?:fees?|hostel)\b)", re.IGNORECASE)
# A number that only counts what is asked ("2 reasons") or a duration ("4 years"): not marks, a rank or a phone number.
_COUNT_OR_YEARS = re.compile(r"\b\d{1,2}\s+(?:reasons?|things?|points?|questions?|advantages?|benefits?|years?|yrs?)\b",
                             re.IGNORECASE)


_CONTEXT_ONLY = re.compile(
    r"^\W*(?:(?:hey|hi|hello|sir|madam|ok|so)\W+)*(?:i\s*(?:am|'?m)\s+(?:from|leaving|coming|moving|relocating|shifting)"
    r"\b[^?]*|hey|hi|hello)\W*$", re.IGNORECASE)

# States and big cities outside Telangana and Andhra Pradesh: the fee card's ₹15,000 concession for students from
# other states is then worth mentioning (it is applied only after proof is verified).
_OTHER_STATE = re.compile(
    r"\b(?:delhi|mumbai|maharashtra|pune|bihar|patna|odisha|orissa|bhubaneswar|bengal|kolkata|jharkhand|ranchi|"
    r"uttar\s+pradesh|lucknow|kanpur|noida|madhya\s+pradesh|bhopal|indore|rajasthan|jaipur|gujarat|ahmedabad|"
    r"surat|karnataka|bangalore|bengaluru|mysore|tamil\s*nadu|chennai|kerala|kochi|chhattisgarh|raipur|punjab|"
    r"haryana|gurgaon|gurugram|assam|guwahati|uttarakhand|dehradun|himachal|goa|nepal|bhutan)\b", re.IGNORECASE)


_ASKS = re.compile(r"\b(?:give|tell|show|what|how|why|which|when|where|can|could|is|are|does|do|need|want|explain|"
                   r"reasons?|fees?|hostel|placements?|scholarships?)\b|\?", re.IGNORECASE)


def context_only(part: str) -> bool:
    """A part that only gives context ("I am from Delhi", "hi") and asks nothing."""
    return bool(_CONTEXT_ONLY.match(part or "")) and not _ASKS.search(part or "")


def from_other_state(text: str) -> bool:
    return bool(re.search(r"\b(?:from|leaving|in|live\s+in|coming\s+from)\b", text or "", re.IGNORECASE)
                and _OTHER_STATE.search(text or ""))


def verified_topic(part: str) -> str | None:
    """'qf' when quick_facts answers this part exactly, 'campus:<key>' for a campus-life topic, else None."""
    from app.sru_agent import campus_life, quick_facts
    if quick_facts.answer(part):
        return "qf"
    key = campus_life.topic(part)
    return f"campus:{key}" if key else None


def model_note(message: str) -> str | None:
    """For the AI model: a message that asks several things gets the list of its parts, to answer each in turn
    (v4.15.1). None for a single question."""
    text = (message or "").strip()
    if not text or not _is_compound_query(text):
        return None
    parts = [p for p in _fast_split(text) if not context_only(p)]
    if len(parts) < 2:
        return None
    listed = "; ".join(f"{i}) {p.strip()}" for i, p in enumerate(parts, 1))
    note = (f"THIS MESSAGE ASKS {len(parts)} THINGS: {listed}. Answer every one, in this order, each under a short "
            "bold label; when a number is asked (\"2 reasons\"), give exactly that many. Keep each part brief.")
    if from_other_state(text):
        note += (" The student is from outside Telangana and Andhra Pradesh: mention the fee card's special concession "
                 "for students from other states (amount from the fee data, applied after proof is verified).")
    return note


def asked_count(text: str) -> int | None:
    """How many items the student asked for ("give me 2 reasons" -> 2), 1-6, or None."""
    m = re.search(r"\b([1-6])\s+(?:reasons?|things?|points?|advantages?|benefits?)\b", text or "", re.IGNORECASE)
    return int(m.group(1)) if m else None
_ABOUT_SRU = re.compile(r"\b(?:about|overview\s+of|describe)\s+(?:sru|sr\s*university|the\s+university)\b", re.IGNORECASE)
_HOSTEL = re.compile(r"\b(?:hostels?|accommodation|residential|residence)\b", re.IGNORECASE)
_CURFEW = re.compile(r"\b(?:curfew|in-?time|out-?pass)\b", re.IGNORECASE)
_TIMINGS_RULES = re.compile(r"\b(?:timings?|rules?)\b", re.IGNORECASE)
_MESS = re.compile(r"\b(?:mess|dining|meals?)\b", re.IGNORECASE)
_FOOD = re.compile(r"\bfood\b", re.IGNORECASE)
_SAFETY = re.compile(r"\b(?:safe|safety|security|warden|cctv)\b", re.IGNORECASE)
_FEE = re.compile(r"\b(?:fees?|tuition|cost|price|charges?)\b", re.IGNORECASE)
_PLACEMENT = re.compile(r"\b(?:placements?|packages?|salary|salaries|recruiters?)\b", re.IGNORECASE)
_SCHOLARSHIP = re.compile(r"\b(?:scholarships?|waivers?)\b", re.IGNORECASE)

TOPICS = (
    "cse_vs_aiml", "why_sru", "about_sru", "hostel_curfew", "hostel_mess", "hostel_fee", "hostel_safety",
    "hostel_info", "fees", "fees_ask", "placements", "scholarships",
)


def topic(part: str, whole: str) -> str | None:
    """The verified topic one part of the message asks about, or None when it is not one we can place.
    `whole` is the full message (a part like "timings" belongs to the hostel when the message is about it)."""
    q = part or ""
    hostel_context = bool(_HOSTEL.search(q) or _HOSTEL.search(whole or ""))
    if _COMPARE.search(q) and _CSE.search(q) and _AIML.search(q):
        return "cse_vs_aiml"
    if _WHY_SRU.search(q):
        return "why_sru"
    if _ABOUT_SRU.search(q):
        return "about_sru"
    if _CURFEW.search(q) or (hostel_context and _TIMINGS_RULES.search(q)):
        return "hostel_curfew"
    if _MESS.search(q) or (hostel_context and _FOOD.search(q)):
        return "hostel_mess"
    if _HOSTEL.search(q) and _FEE.search(q):
        return "hostel_fee"
    if hostel_context and _SAFETY.search(q):
        return "hostel_safety"
    if _HOSTEL.search(q):
        return "hostel_info"
    if _FEE.search(q):
        return "fees"
    if _PLACEMENT.search(q):
        return "placements"
    if _SCHOLARSHIP.search(q):
        return "scholarships"
    return None


def plan(message: str, profile: dict | None = None) -> list[tuple[str, str]] | None:
    """[(part, topic), ...] when the message should be answered part by part, else None (see the module rules)."""
    text = (message or "").strip()
    if not text or not _is_compound_query(text):
        return None
    if re.search(r"\d", _COUNT_OR_YEARS.sub(" ", text)) or _ACTION.search(text):
        return None
    parts = _fast_split(text)
    if len(parts) < 2:
        return None
    planned: list[tuple[str, str]] = []
    for part in parts:
        t = topic(part, text)
        if t == "hostel_info" and verified_topic(part) == "qf":
            t = "qf"          # "is wifi there in hostel": the exact answer, not the general hostel text
        if t is None:
            if context_only(part):
                continue          # "I am from Delhi", "hi": context for the answer, not a question of its own
            t = verified_topic(part)          # v4.15.1: a quick fact or campus-life answer, else the AI answers all
            if t is None:
                return None
        planned.append((part, t))
    if len(planned) < 2:
        return None
    def _distinct(part: str, t: str) -> str:
        if t != "qf":
            return t
        from app.sru_agent import quick_facts           # quick facts: different answers are different topics
        qa = quick_facts.answer(part)
        return "qf:" + (qa.text[:80] if qa else part)
    if len({_distinct(p, t) for p, t in planned}) < 2:
        return None
    if any(t == "fees" for _, t in planned):
        program = fees.find_program(text) or (profile or {}).get("program_interest")
        if program and program != "btech_cse":
            return None
        if not program:
            planned = [(p, "fees_ask" if t == "fees" else t) for p, t in planned]
    return planned


def scholarship_overview_text(program_key: str = "btech_cse") -> str:
    """Merit scholarship slabs, written from the official fee data (never typed by hand)."""
    data = fees.load_data()
    prog = data["programs"][program_key]
    slab_set = data["slab_sets"].get(prog["slab_set"], {})
    label = {
        "state_board": "Intermediate (state board)",
        "cbse": "CBSE / ICSE",
        "jee_percentile": "JEE Main percentile",
        "eapcet_rank": "TG / AP EAPCET rank",
        "ib": "IB score",
    }
    lines = []
    for kind in ("state_board", "cbse", "jee_percentile", "eapcet_rank", "ib"):
        table = slab_set.get(kind) or []
        if not table:
            continue
        slabs = sorted(table, key=lambda s: -s["percent"])
        lines.append(
            f"• **{label[kind]}**: "
            + " · ".join(f"{fees._range_text(kind, s)} → **{s['percent']}%**" for s in slabs)
        )
    concessions = data.get("special_concessions") or data.get("concessions") or []
    # The programme as a student says it, not the fee card's whole group of specialisations (docs/36 rule 4).
    name = "B.Tech CSE" if program_key == "btech_cse" else (prog.get("name") or program_key)
    text = (
        "### 🎓 Merit scholarships (2027–28)\n\n"
        f"A tuition waiver from your best score: only the highest one applies. For **{name}**:\n\n"
        + "\n".join(lines)
    )
    if concessions:
        text += (
            f"\n\nOn top of that, **{len(concessions)} special-category concessions** are evaluated separately, "
            "with proof."
        )
    text += "\n\nSlabs can differ by programme. Share your marks or rank and I'll calculate your exact scholarship."
    return text


FEES_ASK_TEXT = (
    "### 💰 Fees\n\n"
    "Fees depend on the programme. Which programme are you considering? I'll show its official 2027–28 fee "
    "and your scholarship."
)
FEES_ASK_CHIPS = ["B.Tech CSE fees", "MBA fees", "BBA fees"]
