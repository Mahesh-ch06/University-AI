"""Fee enquiries: collect course, 10+2 board (all India boards), and marks/rank before calculating fees.

A personal fee depends on the programme and branch, the 10+2 board (Telangana / AP State Board,
CBSE, ICSE, NIOS, Other State Boards across India, or IB), 10+2 marks and, for B.Tech and B.Sc Agriculture,
a JEE Main percentile or TG / AP EAPCET rank.

decide() looks at the message, what the chat already knows and what was asked before, and says:
    {"action": "ask", "text": ..., "chips": [...], "cards": [...], "state": {...}}   ask with form card
    {"action": "calculate", "args": {...}}                                             all details known
    None                                                                               not a fee enquiry
"""
import re
from typing import Any

from app.services.card_service import (
    build_academic_details_form,
    build_fee_scholarship_form_card,
    build_counsellor_board_card,
    build_counsellor_stage_card,
    build_counsellor_marks_card,
    build_counsellor_route_card,
    build_counsellor_program_card,
)
from . import config, fees

FEE_PORTAL_URL = config.FEE_PORTAL_URL

_PAY_HOW_MUCH = re.compile(r"\bhow\s+much\b.{0,30}?\b(?:will|would|do|should|must|have\s+to)\s+(?:i\s+)?(?:have\s+to\s+)?pay\b|"
                           r"\bwhat\s+(?:will|would)\s+i\s+pay\b", re.IGNORECASE)
_FEE_WORDS = re.compile(
    r"\b(?:fee|fees|fess|feez|tuition|cost|costs|(?:schol\w*|s[ck]?h?o[lr]+[ae]?r?s+h?i*p+\w*)|how\s+much|per\s+sem\w*|payable|"
    r"calculate|calculation|estimate)\b",
    re.IGNORECASE,
)

# Fee questions that are not about a programme's tuition (other tools answer these).
_OTHER_FEE_TOPIC = re.compile(
    r"\b(?:hostel|mess|bus|transport|application\s+fee|form\s+fee|pay(?:ment)?s?\b|paid|refund\w*|instal\w*|emi|"
    r"loan|concession\w*|sibling|sports|defen[cs]e|single\s+parent|orphan|girl|disab\w*|vs|versus|compare|"
    r"comparison|difference|cheaper|cheapest|last\s+date|due\s+date|deadline|exam\s+fee|caution|deposit|"
    r"other\s+fees?|other\s+academic(?:\s*/\s*university|\s+university)?\s+charges?|other\s+charges?|annual\s+charges?|"
    r"university\s+charges?|additional\s+fees?|additional\s+charges?|enrolment\s+fee|enrollment\s+fee|application\s+form\s+fee|"
    r"specialisation\s+fee|specialization\s+fee|phd\s+fee|"
    r"fees?\s+(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee)|"
    r"(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee))\b",
    re.IGNORECASE,
)

_COUNSELLOR_TRIGGER = re.compile(
    r"\b(?:(?:schol\w*|s[ck]?h?o[lr]+[ae]?r?s+h?i*p+\w*)|waiver|concession|discount|scholarship\s+counsell?or|fee\s+counsell?or|fee\s+assessment|"
    r"scholarship\s+assessment|guided\s+assessment|potential\s+scholarship|calculate\s+(?:my\s+)?scholarship|"
    r"fee\s+after\s+scholarship|expected\s+scholarship)\b",
    re.IGNORECASE,
)

_STAGE_1ST = re.compile(
    r"\b(?:1st\s*(?:year|yr)|first\s*(?:year|yr)|11th|class\s*11|junior\s*inter|inter\s*1st)\b",
    re.IGNORECASE,
)
_STAGE_2ND = re.compile(
    r"\b(?:2nd\s*(?:year|yr)|second\s*(?:year|yr)|12th|class\s*12|senior\s*inter|inter\s*2nd)\b",
    re.IGNORECASE,
)
_STAGE_COMPLETED = re.compile(
    r"\b(?:completed|passed(?:\s*out)?|finished|dropper|passed|already\s*passed|passout|10\+2\s*completed|"
    r"a(?:y)?ipo(?:y)?indi|complete\s*a(?:y)?indi|pass\s*a(?:y)?(?:y|i)(?:a|anu|indi)?|"
    r"(?:pass|complete|khatam|khatm|finish)\s*(?:ho\s*)?(?:gaya|gayi|hogaya|ho\s+chuka)|done\s+with\s+(?:inter|12th))\b",
    re.IGNORECASE,
)

_ROUTE_TG_EAPCET = re.compile(r"\b(?:tg|ts)\s*eapcet\b|\b(?:tg|ts)\s*eamcet\b", re.IGNORECASE)
_ROUTE_AP_EAPCET = re.compile(r"\bap\s*eapcet\b|\bap\s*eamcet\b", re.IGNORECASE)
_ROUTE_JEE = re.compile(r"\bjee(?:\s*main)?\b", re.IGNORECASE)
_ROUTE_SRSAT = re.compile(r"\bsrsat\b|\bsr\s*(?:univ\w*|scholastic)?\s*aptitude(?:\s*test)?\b", re.IGNORECASE)
_ROUTE_NOT_DECIDED = re.compile(
    r"\bnot\s+decided(?:\s+yet)?\b|\bno\s+entrance\b|\bhaven'?t\s+decided\b|\bnot\s+sure\b|\bno\s+exam\b|"
    r"\binter(?:mediate)?\s+alone\b|\bmarks\s+alone\b|\bnone\b",
    re.IGNORECASE,
)
# "95% in inter": Intermediate is the Telangana / AP state board's name for 10+2. Used only with a percentage;
# raw marks ("850 in Intermediate") still ask the board, because the maximum marks differ between boards.
_INTER_HINT = re.compile(r"\b(?:in|from|my)\s+(?:inter|intermediate|ipe)\b|\b(?:inter|intermediate|ipe)\s+"
                         r"(?:marks|percentage|score|result)\b", re.IGNORECASE)

_ROUTE_OTHER = re.compile(r"\bother(?:\s+(?:entrance|exam|route))?\b", re.IGNORECASE)

_STATE_BOARD = re.compile(
    r"\b(?:state\s*board|tsbie|bieap|biets|board\s+of\s+intermediate|intermediate\s+board|inter\s+board|"
    r"(?:ts|tg|ap|telangana|andhra(?:\s+pradesh)?)\s*(?:state\s*)?(?:board|inter(?:mediate)?)|"
    # board abbreviations name a board by themselves; a state's name needs "board", "inter", "hsc"... after it
    # ("I'm from Delhi" is where the student lives, not their board).
    r"(?:msbshse|puc|tndge|dhse|up\s*board|bseb|mp\s*board|rbse|pseb|hbse|wbchse|gseb|chse|ahsec|cgbse|"
    r"other\s*state\s*board)|"
    r"(?:maharashtra|karnataka|tamil\s*nadu|kerala|uttar\s*pradesh|bihar|madhya\s*pradesh|rajasthan|delhi|punjab|"
    r"haryana|west\s*bengal|gujarat|odisha|assam|jharkhand|jac|chhattisgarh)\s*(?:state\s*)?"
    r"(?:board|inter(?:mediate)?|hsc|12th))\b",
    re.IGNORECASE,
)
# v4.15.0: the short answers students type to "which board?": "telangana", "ts", "AP", "andhra", "state".
_BARE_STATE = re.compile(
    r"\s*(?:i\s+(?:studied|am|was)\s+(?:in|from)\s+|from\s+|in\s+)?(?:ts|tg|ap|telangana|telengana|telagana|andhra(?:\s*pradesh)?"
    r"|state|ts\s*inter|ap\s*inter)(?:\s+(?:state|board|borad|bord|baord|state\s+(?:board|borad|bord)|inter))?"
    r"(?:\s+(?:pls|plz|please|bro|sir|madam|anna|ji))?\s*[.!?]*\s*",
    re.IGNORECASE,
)
_CBSE = re.compile(r"\bcbse\b", re.IGNORECASE)
_ICSE = re.compile(r"\b(?:icse|isc)\b", re.IGNORECASE)
_NIOS = re.compile(r"\b(?:nios|national\s+institute\s+of\s+open\s+schooling)\b", re.IGNORECASE)
_IB = re.compile(r"\b(?:ib|international\s+baccalaureate)\b", re.IGNORECASE)

_SCORE_WORDS = r"(?:eapcet|eamcet|emcet|emact|eamect|eamcent|ts\s*eapcet|ap\s*eapcet|tg\s*eapcet)"
_NO_ENTRANCE = re.compile(
    r"\b(?:no|not|didn'?t|did\s+not|haven'?t|have\s+not|never|without)\b[^.?!]{0,30}\b(?:jee|eapcet|eamcet|entrance|"
    r"rank|percentile)\b|\bno\s+(?:entrance|exam|jee|eapcet|eamcet)\b|\b(?:only|just)\s+(?:my\s+)?(?:inter|board|"
    r"12th|marks|percentage)\b|^\s*(?:no|nope|none|nothing|na|n/a|not\s+yet)\s*[.!]?\s*$",
    re.IGNORECASE,
)
_STANDARD_ONLY = re.compile(
    r"\b(?:standard|base|basic|normal|general|full)\s+fee|\bwithout\s+(?:any\s+)?scholarship|\bno\s+scholarship|"
    r"\bjust\s+(?:show\s+)?(?:the\s+)?(?:fee|fees|standard)\b|\bskip\b(?!\s*,?\s*use\s+my)",
    re.IGNORECASE,
)

_QUALIFYING_DEGREE = re.compile(
    r"\b(?:i\s+(?:did|have\s+done|completed|finished|studied|passed|am\s+doing|'?m\s+doing|am\s+in\s+final\s+year\s+of)"
    r"|(?:my\s+)?(?:degree|graduation|ug|qualification)\s*(?:is|was|:|in)?|graduated\s+(?:in|with)|done\s+(?:my\s+)?)"
    r"\s+(?:my\s+|a\s+|an\s+|the\s+)?(?P<deg>b\.?\s?(?:com|sc|tech|e|ba|ca|a|pharm|des)\b\.?(?:\s*\(?[a-z&]{2,10}\)?)?|bba|bca|"
    r"b\.?\s?com|engineering|commerce|science|arts)",
    re.IGNORECASE,
)
_WANTS_PROGRAM = re.compile(r"\b(?:want|wanna|interested|join|apply|admission|fees?\s+for|looking\s+for|planning|"
                            r"prefer|choose|opt)\b", re.IGNORECASE)

_BOARD_LABEL = {
    "state_board": "Telangana / AP / State Board (All India)",
    "cbse": "CBSE / ICSE / NIOS",
    "ib": "International Baccalaureate (IB)",
}
_ENTRANCE_PROGRAMS = ("btech_", "bsc_agri")
_ADD_ENTRANCE = re.compile(r"\badd\s+(?:my\s+)?(?:(?:tg|ap|ts)\s+)?(?:eapcet|eamcet|jee(?:\s+main)?)(?:\s+(?:rank|percentile|score))?\b",
                           re.IGNORECASE)


def _num(value):
    """850.0 -> 850 and 91.49 -> 91.49, so marks are shown the way a student writes them."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    return int(f) if f == int(f) else round(f, 2)


def _program_level(prog_key: str | None) -> str | None:
    if not prog_key:
        return None
    return fees.load_data()["programs"].get(prog_key, {}).get("level", "ug")


def _uses_entrance(prog_key: str | None) -> bool:
    """Only B.Tech and B.Sc Agriculture students are asked about EAPCET / JEE Main."""
    return bool(prog_key) and str(prog_key).startswith(_ENTRANCE_PROGRAMS)


def get_max_marks(board_key: str | None, stage_key: str | None) -> int:
    """Returns official maximum marks according to the board and academic stage."""
    if board_key in ("ts_state_board", "ap_state_board"):
        if stage_key in ("1st_year", "2nd_year"):
            return 470
        return 1000
    if board_key in ("cbse", "icse"):
        if stage_key == "1st_year":
            return 500
        return 100
    if board_key == "ib":
        return 45
    if stage_key in ("1st_year", "2nd_year"):
        return 500
    return 100


def get_marks_acknowledgment(
    score_str: str,
    percent: float,
    is_projected: bool = False,
    stage_label: str = "",
    variant_idx: int = 0,
) -> str:
    """Dynamic, diverse positive acknowledgment messages for scores >= 50%."""
    proj_note = f" (projected from your {stage_label or '1st year'} performance)" if is_projected else ""

    # Compliments on the marks only. Admission eligibility depends on the programme and is stated
    # separately by eligibility.py once the programme is known; these lines never claim it.
    if percent >= 90.0:
        variants = [
            f"🌟 **Outstanding academic performance!** **{score_str}**{proj_note} is a stellar score, and it puts you in line for a **strong merit scholarship** at SR University.",
            f"🏆 **Sensational achievement!** Scoring **{score_str}**{proj_note} places you among the top achievers, with a **valuable merit scholarship** in reach.",
            f"✨ **Brilliant academic record!** With **{score_str}**{proj_note}, you can expect a **generous tuition fee waiver**.",
            f"🥇 **Exceptional marks!** **{score_str}**{proj_note} reflects real academic excellence and earns **excellent merit scholarship benefits**.",
        ]
    elif percent >= 80.0:
        variants = [
            f"🎉 **Great performance!** **{score_str}**{proj_note} is a strong academic foundation, and it earns a **merit scholarship** at SR University.",
            f"🌟 **Impressive score!** **{score_str}**{proj_note} qualifies for a **substantial scholarship reduction** on tuition.",
            f"👏 **Fantastic achievement!** With **{score_str}**{proj_note}, you qualify for an **attractive merit scholarship**.",
            f"🚀 **Commendable marks!** **{score_str}**{proj_note} puts you in an excellent position for a **valuable merit scholarship**.",
        ]
    elif percent >= 60.0:
        variants = [
            f"👍 **Good marks!** **{score_str}**{proj_note} falls within our **merit scholarship slabs**.",
            f"🎯 **Solid score!** **{score_str}**{proj_note} puts you in line for **merit scholarship opportunities**.",
            f"✨ **Well done!** **{score_str}**{proj_note} is a competitive score for merit scholarship consideration.",
            f"👏 **Strong effort!** **{score_str}**{proj_note} qualifies you to explore **merit-based scholarships**.",
        ]
    else:  # below the 60% where merit scholarships start
        variants = [
            f"✅ Thanks! I've noted **{score_str}**{proj_note}.",
            f"📝 Got it: **{score_str}**{proj_note}.",
            f"👍 Noted, **{score_str}**{proj_note}.",
        ]

    return variants[abs(int(variant_idx)) % len(variants)]


def _known_percent(known: dict):
    """Exact percentage from what the student gave (percent, or raw marks with their total)."""
    from . import eligibility
    if known.get("degree_percent") is not None and known.get("level") == "pg":
        return float(known["degree_percent"])
    raw_m, max_m = known.get("raw_marks"), known.get("max_marks")
    if raw_m is not None and max_m and float(max_m) > 100:
        exact = eligibility.percent_from_marks(raw_m, max_m)  # unrounded: 499.99/1000 stays below 50
        if exact is not None:
            return exact
    if known.get("percent") is not None:
        try:
            return float(known["percent"])
        except (TypeError, ValueError):
            return None
    raw_m, max_m = known.get("raw_marks"), known.get("max_marks")
    if raw_m is not None and max_m:
        return eligibility.percent_from_marks(raw_m, max_m)
    return None


def is_below_minimum_eligibility(known: dict, prog_key: str | None = None) -> bool:
    """True when the marks are below the programme's minimum (or, before the programme is known, below the
    lowest minimum of every programme at that level). Thresholds come only from eligibility.py."""
    from . import eligibility
    pct = _known_percent(known)
    if pct is None:
        return False
    if prog_key:
        return eligibility.assess(prog_key, pct)["status"] == eligibility.BELOW
    return pct < eligibility.lowest_minimum_any_program(known.get("level") or "ug")


def _score_text(known: dict) -> str | None:
    raw_m, max_m = known.get("raw_marks"), known.get("max_marks")
    if raw_m and max_m and float(max_m) > 100:
        return f"{_num(raw_m)} marks out of {_num(max_m)}"
    return None


def format_ineligible_response(known: dict, state: dict, prog_key: str | None = None) -> dict:
    """Clear, polite reply when the marks are below the minimum. No fee or scholarship details, and no
    alternative pathways (none are documented in the official sources)."""
    from . import eligibility
    pct = _known_percent(known) or 0.0
    if prog_key:
        rejection_text = eligibility.explain(eligibility.assess(prog_key, pct), _score_text(known))
    else:
        level = known.get("level") or "ug"
        floor = eligibility.show_percent(eligibility.lowest_minimum_any_program(level))
        qualifying = "the qualifying degree" if level == "pg" else "10+2 / Intermediate"
        given = (f"Based on the {_score_text(known)} you provided, your percentage is **{eligibility.show_percent(pct)}**."
                 if _score_text(known) else f"Your percentage is **{eligibility.show_percent(pct)}**.")
        rejection_text = (
            f"{given} This is below **{floor}**, the lowest minimum in {qualifying} for any SR University "
            f"{'postgraduate' if level == 'pg' else 'undergraduate'} programme in the official sources, so you do "
            f"not currently meet the general eligibility criteria based on these marks.\n\n"
            f"If you think these marks are not right, or you would like to discuss your options, please contact "
            f"{eligibility.ADMISSIONS_CONTACT}."
        )
    chips = ["Change my academic details", "Explore other programmes", "📞 Admissions Office"]
    if state.get("ineligible") and prog_key:
        # Asked again with the same marks: a short reply, not the same paragraph again.
        name = fees.short_name(prog_key)
        floor = eligibility.show_percent(eligibility.thresholds(prog_key)["floor"])
        rejection_text = (f"Your {eligibility.show_percent(pct)} is still below the {floor} minimum for {name}, so a "
                          f"fee or scholarship estimate isn't possible yet. If your marks have changed, tap "
                          f"**Change my academic details**; or I can suggest programmes that fit your marks.")
    state_out = dict(state)
    state_out["waiting_for"] = None
    state_out["ineligible"] = True
    return {
        "action": "ineligible",
        "text": rejection_text,
        "chips": chips,
        "cards": [],
        "state": state_out,
    }


def _btech_branches_text() -> str:
    data = fees.load_data()["programs"]
    seen, lines = set(), []
    for key, prog in data.items():
        if not key.startswith("btech_"):
            continue
        fee = prog["tuition_per_year"]
        name = prog["name"].split(" (")[0]
        if (name, fee) in seen:
            continue
        seen.add((name, fee))
        lines.append(f"• {name}: {fees.inr(fee)} per year")
    return "\n".join(lines)


def _board_card_key(board: str | None, label: str | None) -> str:
    lbl = (label or "").lower()
    if "telangana" in lbl or "ts" in lbl:
        return "ts_state_board"
    if "ap" in lbl or "andhra" in lbl:
        return "ap_state_board"
    if "other" in lbl or any(k in lbl for k in ("maharashtra", "karnataka", "tamil", "kerala", "up", "bihar", "mp")):
        return "other_state_board"
    if board == "cbse":
        if "icse" in lbl:
            return "icse"
        if "nios" in lbl:
            return "nios"
        return "cbse"
    if board == "ib":
        return "ib"
    return "ts_state_board"


def parse_details(message: str) -> dict:
    """Everything fee-relevant the student typed in this one message."""
    low = (message or "").lower()
    out: dict = {}
    detected_p = fees.find_program(message or "")
    if detected_p:
        out["program"] = detected_p
    elif fees._is_generic_btech(low) or re.search(r"\b(?:b\.?\s?tech|btech|engineering)\b", low):
        out["generic_btech"] = True

    # Check specific B.Tech branches if program not yet matched
    if not out.get("program"):
        if re.search(r"\b(?:cse|computer\s+science|aiml|ai\s*&?\s*ml|data\s+science|cyber\s*security|quantum\s*ai)\b", low):
            out["program"] = "btech_cse"
        elif re.search(r"\b(?:ai\s*(?:and|&)\s*robotics|artificial\s+intelligence\s*(?:and|&)\s*robotics)\b", low):
            out["program"] = "btech_ai_robotics"
        elif re.search(r"\b(?:ece|electronics(?:\s*(?:and|&)\s*communication)?)\b", low):
            out["program"] = "btech_ece"
        elif re.search(r"\b(?:eee|electrical(?:\s*(?:and|&)\s*electronics)?)\b", low):
            out["program"] = "btech_eee"
        elif re.search(r"\b(?:mech|mechanical)\b", low):
            out["program"] = "btech_mech"
        elif re.search(r"\b(?:civil)\b", low):
            out["program"] = "btech_civil"
        elif re.search(r"\b(?:agri|agriculture)\b", low):
            out["program"] = "bsc_agri"

    if out.get("program") == "btech_cse":
        if re.search(r"\b(?:aiml|ai\s*&?\s*ml|ai\s*and\s*ml|ai/ml|aml|machine\s+learning)\b", low):
            out["specialization"] = "AIML"
            out["program_raw"] = "AIML"
        elif re.search(r"\b(?:data\s+science|datascience|ds)\b", low):
            out["specialization"] = "Data Science"
            out["program_raw"] = "Data Science"
        elif re.search(r"\b(?:cyber\s*security|cybersecurity|cyber|infosec)\b", low):
            out["specialization"] = "Cyber Security"
            out["program_raw"] = "Cyber Security"
        elif re.search(r"\b(?:quantum\s*ai|quantum)\b", low):
            out["specialization"] = "Quantum AI"
            out["program_raw"] = "Quantum AI"
        elif re.search(r"\brobotics(?:\s*(?:&|and)\s*automation)?\b", low):   # inside CSE: the R&A specialisation
            out["specialization"] = "Robotics & Automation"
            out["program_raw"] = "Robotics & Automation"
        elif re.search(r"\b(?:core\s*cse|core)\b", low):
            out["specialization"] = "Core CSE"
            out["program_raw"] = "Core CSE"
        else:
            out["program_raw"] = "CSE"

    # Board detection
    if _IB.search(message or ""):
        out["board"] = "ib"
        out["board_label"] = "International Baccalaureate (IB)"
        out["board_key"] = "ib"
    elif _CBSE.search(message or "") or _ICSE.search(message or "") or _NIOS.search(message or ""):
        out["board"] = "cbse"
        if _ICSE.search(message or "") and not _CBSE.search(message or ""):
            out["board_label"] = "ISC"
            out["board_key"] = "icse"
        elif _NIOS.search(message or "") and not _CBSE.search(message or ""):
            out["board_label"] = "NIOS"
            out["board_key"] = "nios"
        else:
            out["board_label"] = "CBSE"
            out["board_key"] = "cbse"
    elif _STATE_BOARD.search(re.sub(r"\b(?:borad|bord|baord)\b", "board", message or "", flags=re.I)) \
            or _BARE_STATE.fullmatch(message or "") \
            or (_INTER_HINT.search(message or "") and re.search(r"\d\s*%", message or "")):
        out["board"] = "state_board"
        if re.search(r"\b(?:ts|tg|telangana|telengana|telagana|tsbie|biets)\b", low):
            out["board_label"] = "Telangana Intermediate (TSBIE)"
            out["board_key"] = "ts_state_board"
        elif re.search(r"\b(?:ap|andhra|bieap)\b", low):
            out["board_label"] = "Andhra Pradesh Intermediate (BIEAP)"
            out["board_key"] = "ap_state_board"
        elif re.search(r"\b(?:other|maharashtra|msbshse|karnataka|puc|tamil|tndge|kerala|dhse|up|bihar|bseb|mp|rajasthan|rbse|"
                       r"delhi|punjab|pseb|haryana|hbse|bengal|wbchse|gujarat|gseb|odisha|chse|assam|ahsec|jharkhand|jac|"
                       r"chhattisgarh|cgbse)\b", low):
            out["board_label"] = "Other State Board"
            out["board_key"] = "other_state_board"
        else:
            out["board_label"] = "Telangana / AP State Board"
            out["board_key"] = "ts_state_board"

    # Stage detection. "Completed Intermediate / Class 12 (passed out)" is completed, not 2nd year (v4.15.0).
    if _STAGE_COMPLETED.search(message or "") and not re.search(
            r"\b(?:studying|currently|now\s+in|appearing|writing|not\s+(?:yet\s+)?(?:completed|finished|passed))\b", low):
        out["academic_stage"] = "completed"
        out["stage_label"] = "Completed Intermediate (Passed out)"
        out["is_projected"] = False
    elif _STAGE_2ND.search(message or "") and not (re.search(r"\b(?:completed|passed)\s+1st\s+year\b", low) and not re.search(r"\b(?:in|studying|currently|in\s+the)\s*2nd\b", low)):
        out["academic_stage"] = "2nd_year"
        out["stage_label"] = "Intermediate 2nd Year (12th)"
        out["is_projected"] = True
    elif _STAGE_1ST.search(message or "") and not re.search(r"\b2nd\s*year\b", low):
        out["academic_stage"] = "1st_year"
        out["stage_label"] = "Intermediate 1st Year (11th)"
        out["is_projected"] = True
    elif _STAGE_COMPLETED.search(message or ""):
        out["academic_stage"] = "completed"
        out["stage_label"] = "Completed Intermediate (Passed out)"
        out["is_projected"] = False

    # Admission route detection
    if _ROUTE_TG_EAPCET.search(message or ""):
        out["admission_route"] = "tg_eapcet"
        out["route_label"] = "TG EAPCET"
    elif _ROUTE_AP_EAPCET.search(message or ""):
        out["admission_route"] = "ap_eapcet"
        out["route_label"] = "AP EAPCET"
    elif _ROUTE_JEE.search(message or ""):
        out["admission_route"] = "jee_main"
        out["route_label"] = "JEE Main"
    elif _ROUTE_SRSAT.search(message or ""):
        out["admission_route"] = "srsat"
        out["route_label"] = "SR University SRSAT"
    elif _ROUTE_NOT_DECIDED.search(message or ""):
        out["admission_route"] = "not_decided"
        out["route_label"] = "Not decided yet"
        out["no_entrance"] = True
    elif _ROUTE_OTHER.search(message or ""):
        out["admission_route"] = "other"
        out["route_label"] = "Other"

    # CGPA parsing (e.g. "9.2 CGPA", "CGPA 8.8")
    cgpa_m = re.search(r"\b(?:cgpa\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)|(\d{1,2}(?:\.\d+)?)\s*cgpa)\b", low)
    if cgpa_m:
        cgpa_val = float(cgpa_m.group(1) or cgpa_m.group(2))
        if 0 < cgpa_val <= 10.0:
            out["cgpa"] = cgpa_val
            out["percent"] = round(cgpa_val * 9.5, 2)

    # Explicit fraction parsing (e.g. "890/1000", "890 out of 1000", "430/470", "430 out of 470")
    frac = re.search(r"(?<![\d.])(\d{2,4}(?:\.\d+)?)\s*(?:marks\s+)?(?:/|out\s+of)\s*(\d{2,4})", low)
    if frac and not out.get("percent"):
        obt, tot = float(frac.group(1)), float(frac.group(2))
        if 0 < obt <= tot:
            out["percent"] = round((obt / tot) * 100, 2)
            out["raw_marks"] = obt
            out["max_marks"] = tot

    # Percentage parsing
    m = re.search(r"(?<![\d.])(\d{2}(?:\.\d+)?)\s*(?:%|percent|per\s*cent|percentage)", low)
    if m and float(m.group(1)) <= 100 and not out.get("percent"):
        out["percent"] = float(m.group(1))

    # Raw 3-4 digit marks without maximum marks specified (e.g. "890 marks", "scored 430", "actually I scored 931")
    if not out.get("percent") and not out.get("raw_marks"):
        raw_marks_m = re.search(
            r"\b(?:scored|got|secured|obtained|have|actually\s+(?:i\s+)?(?:scored|got))\s*(\d{3,4})\b|"
            r"\b(\d{3,4})\s*marks\b|"
            r"\b(?:marks?\s*(?:are|is|=|:)\s*)(\d{3,4})\b",
            low,
        )
        if raw_marks_m:
            raw_val = int(raw_marks_m.group(1) or raw_marks_m.group(2) or raw_marks_m.group(3))
            if 100 < raw_val <= 1000:
                out["raw_marks"] = raw_val
                out["needs_marks_confirmation"] = raw_val

    # EAPCET rank
    m = re.search(
        rf"\b{_SCORE_WORDS}\b\D{{0,25}}(\d[\d,]{{0,6}})\b|\brank\D{{0,12}}(\d[\d,]{{0,6}})\b"
        rf"|(\d[\d,]{{0,6}})\s*(?:{_SCORE_WORDS}\s*)?(?:rank|in\s+{_SCORE_WORDS})\b"
        rf"|\b(\d{{1,3}})\s*k\s*(?:{_SCORE_WORDS}\s*)?rank\b",
        low,
    )
    if m:
        if m.group(4):
            out["eapcet_rank"] = int(m.group(4)) * 1000
        else:
            out["eapcet_rank"] = int((m.group(1) or m.group(2) or m.group(3)).replace(",", ""))
        if not out.get("admission_route"):
            out["admission_route"] = "tg_eapcet"
            out["route_label"] = "TG EAPCET"

    # JEE Main percentile
    m = re.search(r"\bjee(?:\s+main)?\D{0,25}(\d{1,2}(?:\.\d+)?)\b|(\d{1,2}(?:\.\d+)?)\s*(?:percentile|%ile)", low)
    if m:
        out["jee_percentile"] = float(m.group(1) or m.group(2))
        if not out.get("admission_route"):
            out["admission_route"] = "jee_main"
            out["route_label"] = "JEE Main"

    # IB score
    m = re.search(r"\bib\D{0,15}(\d{2})\b|(?<!\d)(\d{2})\s*(?:/\s*45|points|out\s+of\s+45)", low)
    if m and 0 < int(m.group(1) or m.group(2)) <= 45:
        out["ib_score"] = int(m.group(1) or m.group(2))
        out["board"] = "ib"
        out["board_label"] = "International Baccalaureate (IB)"
        out["board_key"] = "ib"

    # v4.15.0: "I did BCom" / "I completed B.Tech" / "my degree is BSc" is the student's own qualifying degree (an
    # answer to the MBA / M.Tech degree question), not a change of the programme they want to join.
    qual = _QUALIFYING_DEGREE.search(message or "")
    if qual and not _WANTS_PROGRAM.search(message or ""):
        out["qualifying_degree"] = re.sub(r"\s+", " ", qual.group("deg")).strip()
        for k_q in ("program", "program_raw", "specialization", "generic_btech"):
            out.pop(k_q, None)

    if _NO_ENTRANCE.search(message or ""):
        out["no_entrance"] = True
    if _STANDARD_ONLY.search(message or ""):
        out["standard_only"] = True
    if re.search(
        r"\bskip\b|\buse\s+(?:my|the)\s+rank\b|\bdon'?t\s+(?:know|remember)\b|\bnot\s+sure\b|"
        r"\bcalculate\s+(?:it\s+)?(?:now|anyway)\b|\bthat'?s\s+all\b",
        message or "",
        re.IGNORECASE,
    ):
        out["skip"] = True
    if _COUNSELLOR_TRIGGER.search(message or ""):
        is_broad = bool(re.search(
            r"\b(?:what\s+scholarships|which\s+scholarships|scholarships\s+available|scholarship\s+options|list\s+of\s+scholarships)\b",
            message or "",
            re.IGNORECASE,
        ))
        has_concrete_score = bool(out.get("eapcet_rank") or out.get("jee_percentile"))
        if not is_broad and not has_concrete_score:
            out["counsellor_triggered"] = True
    return out


_NOT_KNOWN = re.compile(r"\b(?:don'?t\s+know|dont\s+know|not\s+sure|no\s+idea|forgot|don'?t\s+remember|idk|dunno|"
                        r"theliyadu|pata\s+nahi?)\b", re.IGNORECASE)
_NONSENSE = re.compile(r"^\s*(?:abc|xyz|asdf|qwerty|nil|test|[^\w\s]+|(\w)\1{2,})\s*$", re.IGNORECASE)


def _num_text(v: float) -> str:
    return str(int(v)) if float(v) == int(v) else f"{v:g}"


def _marks_problem(message: str, said: dict, number, known: dict, waiting: str | None) -> str | None:
    """Why the marks in this answer can't be used, or None (fine, or not a marks answer at all)."""
    low = (message or "").lower().strip()
    b_key, s_key = known.get("board_key"), known.get("academic_stage") or "completed"
    # Only boards with a known total are checked against it (another state's board has none: the student is
    # asked "out of how many?"); CBSE / ICSE final marks are a percentage.
    fixed_total = b_key in ("ts_state_board", "ap_state_board", "cbse", "icse", "ib")
    percent_only = waiting == "degree_percent" or (fixed_total and get_max_marks(b_key, s_key) <= 100)
    max_m = 100 if percent_only else (get_max_marks(b_key, s_key) if fixed_total else None)
    frac = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:marks\s+)?(?:/|out\s+of)\s*(\d+(?:\.\d+)?)", low)
    if frac:
        obt, tot = float(frac.group(1)), float(frac.group(2))
        if obt > tot:
            return f"**{_num_text(obt)}** is more than the maximum of {_num_text(tot)}, so it can't be right."
        if obt <= 0 or tot <= 0:
            return "Marks can't be zero or negative."
        return None
    if re.search(r"(?:^|\s)-\s*\d", low):
        return "Marks can't be negative."
    pct = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per\s*cent|percentage)", low)
    if pct:
        value = float(pct.group(1))
        # "866%" with a 1000 total: marks typed with a % by mistake; "150%" is not (it can't be passing marks)
        if value > 100 and not (max_m and max_m > 100 and max_m * 0.35 <= value <= max_m):
            return "A percentage can't be more than 100."
        return None
    raw = said.get("raw_marks") if said.get("raw_marks") is not None else number
    if raw is not None and max_m:
        raw = float(raw)
        if raw <= 0:
            return "Marks can't be zero or negative."
        if max_m > 100 and raw < 35:
            return (f"**{_num_text(raw)}** looks too low. Please enter your marks out of {max_m} (for example "
                    f"{int(max_m * 0.87)}) or your percentage (for example 87%).")
        if max_m > 100 and raw > max_m and not (35 <= raw <= 100):
            return f"**{_num_text(raw)}** is more than the maximum of {max_m} marks, so it can't be right."
        if max_m <= 100 and raw > 100:
            return ("That looks like marks, not a percentage. Please enter your percentage (for example 87.5), or "
                    "your marks with the total (for example 435 out of 500).")
        return None
    if _NOT_KNOWN.search(low):
        return ("No problem. An approximate figure is fine for an estimate (you can correct it any time), or tap "
                "**Just show the fee** for the standard fee.")
    if _NONSENSE.match(low):
        return "I need your marks as a number."
    return None


def _bare_number(message: str):
    m = re.fullmatch(r"\s*(\d{1,6}(?:\.\d+)?)\s*%?\s*", message or "")
    return float(m.group(1)) if m else None


_BARE_SCORE_OR_MARKS = re.compile(
    r"^\s*(?:i\s+(?:got|scored|have|secured|obtained)\s+)?\d{2,4}(?:\.\d+)?\s*(?:marks?|%|percent)?\s*$",
    re.IGNORECASE,
)


def is_fee_enquiry(message: str) -> bool:
    from . import intents
    if intents.is_branch_guidance_query(message or ""):
        return False
    if intents._ADMISSION_GUARANTEE_PATTERN.search(message or ""):
        return False
    if intents._FUTURE_YEAR_FEE_PATTERN.search(message or ""):
        return False
    # "How much do I pay for AI & Robotics?" is the programme fee (v4.15.0), not a payment-method question.
    msg_core = _PAY_HOW_MUCH.sub(" fee ", message or "")
    if _OTHER_FEE_TOPIC.search(msg_core):
        return False
    if bool(_FEE_WORDS.search(msg_core)):
        return True
    if _COUNSELLOR_TRIGGER.search(message or ""):
        return True
    if _BARE_SCORE_OR_MARKS.match((message or "").strip()):
        return True
    num = _bare_number(message)
    if num is not None and (35 <= num <= 1000):
        return True
    return False


def _counsellor_pg(prog_key: str, known: dict, said: dict, state: dict, intake: dict) -> dict:
    """Scholarship counselling for a PG programme: one question (the degree %), then the result.
    No board, year of study or entrance exam: PG slabs use the qualifying-degree percentage."""
    degree_pct = known.get("degree_percent")
    prog_name = fees.clean_program_name(
        prog_key, specialization=known.get("specialization"), user_text=known.get("program_raw"),
    )
    wants_standard = bool(said.get("standard_only") or said.get("skip"))
    if degree_pct is None and not wants_standard and said.get("qualifying_degree") \
            and intake.get("waiting_for") == "degree_percent":
        state["waiting_for"] = "degree_percent"
        deg = said["qualifying_degree"]
        text = (f"Noted, your degree is **{deg}**. What percentage did you score (or expect to score) in it?")
        card = build_counsellor_marks_card(
            board_key=None, stage_key="completed", max_marks=100, board_label="your qualifying degree",
            title="What percentage did you score in your degree?",
            subtitle="Enter your aggregate percentage in the qualifying degree (final or expected).",
            step_label="Step 1: Degree Percentage",
        )
        return {"action": "ask", "text": text, "chips": ["70%", "80%", "90%", "Just the standard fee"],
                "cards": [card], "state": state}
    if degree_pct is None and not wants_standard:
        state["waiting_for"] = "degree_percent"
        text = (
            f"Got it. For **{prog_name}**, the merit scholarship is based on your percentage in the "
            "qualifying degree (for example B.Tech, B.Sc, B.Com or BBA), not your 12th marks.\n\n"
            "What percentage did you score (or expect to score) in your degree?"
        )
        card = build_counsellor_marks_card(
            board_key=None, stage_key="completed", max_marks=100, board_label="your qualifying degree",
            title="What percentage did you score in your degree?",
            subtitle="Enter your aggregate percentage in the qualifying degree (final or expected).",
            step_label="Step 1: Degree Percentage",
        )
        return {"action": "ask", "text": text, "chips": ["70%", "80%", "90%", "Just the standard fee"],
                "cards": [card], "state": state}

    state["waiting_for"] = "done"
    state["program"] = prog_key
    args = {"program": prog_key}
    if degree_pct is not None:
        args["percent"] = degree_pct
    return {
        "action": "calculate",
        "args": args,
        "state": state,
        "counsellor": True,
        "counsellor_details": {
            "level": "pg",
            "board_label": "Qualifying degree",
            "percent": degree_pct,
            "program": prog_key,
            "program_name": prog_name,
            "specialization": known.get("specialization"),
            "program_raw": known.get("program_raw"),
            "re_query": intake.get("waiting_for") == "done",
            "ack_shown": False,
        },
    }


_ACADEMIC_FIELDS = ("board", "board_label", "board_key", "academic_stage", "stage_label", "raw_marks", "max_marks",
                    "percent", "is_projected", "admission_route", "route_label", "eapcet_rank", "jee_percentile",
                    "ib_score", "stream", "no_entrance", "marks_confirmed")


def decide(message: str, profile: dict, intake: dict | None, first_name: str | None = None) -> dict | None:
    """What to do with a fee enquiry (see _decide). v4.13.0: the older consolidated "Fee & Merit Scholarship
    Assessment Form" card is never shown in the chat (its marks field was a percentage, so "867" became "867%").
    The intake itself is unchanged (it calculates as soon as enough is known, asks only what changes the result);
    where it asked with that form, the small step card for the detail being asked is shown instead. Marks typed
    before the board are kept and read once the board gives the total (Telangana / AP Intermediate: out of 1000)."""
    result = _decide(message, profile, intake, first_name)
    if not result or not any((c or {}).get("type") == "fee_scholarship_form" for c in result.get("cards") or []):
        return result
    state = dict(result.get("state") or {})
    waiting = state.get("waiting_for")
    if waiting == "marks_max" and not state.get("board_key") and not state.get("board"):
        # "867" with no board yet: the board says out of what, so ask the board (marks kept), step by step.
        # (A board without a fixed total, e.g. another state's, keeps the "out of how many marks?" question.)
        st = {k: v for k, v in state.items() if k not in ("waiting_for", "needs_marks_confirmation")}
        st["counsellor_mode"] = True
        stepwise = _decide(message, profile, st, first_name)
        if stepwise and not any((c or {}).get("type") == "fee_scholarship_form" for c in stepwise.get("cards") or []):
            return stepwise
    cards = [c for c in result.get("cards") or [] if (c or {}).get("type") != "fee_scholarship_form"]
    step_card = None
    if waiting == "program":
        step_card = build_counsellor_program_card(selected_program=state.get("program"), step_label="Preferred Programme")
    elif waiting in ("board", None) and not state.get("board_key") and not state.get("board") \
            and _program_level(fees.find_program(str(state.get("program") or ""))) != "pg":
        step_card = build_counsellor_board_card(selected_board=state.get("board_key"))
    elif waiting in ("marks", "marks_max", "percent") and state.get("board_key"):
        b_key, s_key = state.get("board_key"), state.get("academic_stage") or "completed"
        step_card = build_counsellor_marks_card(board_key=b_key, stage_key=s_key, max_marks=get_max_marks(b_key, s_key),
                                                board_label=state.get("board_label") or "your board",
                                                default_val=state.get("raw_marks"))
    if step_card:
        program = fees.find_program(str(state.get("program") or ""))
        if program:
            step_card["program"] = program
        cards.append(step_card)
    return {**result, "cards": cards}


def _decide(message: str, profile: dict, intake: dict | None, first_name: str | None = None) -> dict | None:
    """What to do with a fee enquiry. Multi-step intake with counsellor workflow and anti-repetition.
    first_name: given only when using it now would read naturally (the agent leaves it out when the
    previous reply already used the name)."""
    from . import intents
    if intents._ADMISSION_GUARANTEE_PATTERN.search(message or "") or intents._FUTURE_YEAR_FEE_PATTERN.search(message or ""):
        return None
    intake = dict(intake or {})
    # "Add my EAPCET rank" / "Add my JEE Main percentile" after an estimate: ask just that score; the rest
    # of the details are reused for the new calculation.
    add = _ADD_ENTRANCE.search(message or "")
    if add and intake.get("counsellor_mode") and intake.get("program"):
        low_add = add.group(0).lower()
        route = "jee_main" if "jee" in low_add else ("ap_eapcet" if re.search(r"\bap\b", low_add) else "tg_eapcet")
        label = {"jee_main": "JEE Main", "ap_eapcet": "AP EAPCET", "tg_eapcet": "TG EAPCET"}[route]
        state = {**intake, "waiting_for": "rank", "admission_route": route, "route_label": label,
                 "no_entrance": None, "asked": sorted(set(intake.get("asked", [])) | {"rank"})}
        question = ("What is your JEE Main percentile?" if route == "jee_main" else f"What is your {label} rank?")
        chips = ["92 percentile", "85 percentile"] if route == "jee_main" else ["Rank 5000", "Rank 15000"]
        return {"action": "ask", "text": f"Sure! {question}", "chips": chips, "cards": [], "state": state}
    said = parse_details(message)
    from . import eligibility
    # The 10+2 subject group (MPC / BiPC / other). Acronyms are read anywhere; words like "commerce" or
    # "arts" only as the answer to our own subjects question.
    stream = eligibility.parse_stream(message)
    if stream and (stream in ("MPC", "BiPC") and re.search(r"\b(?:mpc|pcm|bipc|pcb)\b|maths?\W{0,3}(?:and\s+)?physics|"
                                                           r"physics\W{0,3}(?:and\s+)?(?:chemistry|biology)|biology\W{0,3}"
                                                           r"(?:and\s+)?physics", (message or "").lower())
                   or (intake or {}).get("waiting_for") == "stream"):
        said["stream"] = stream
    active = bool(intake) and int(intake.get("turns", 0)) < 10
    number = _bare_number(message)

    # v4.15.0: marks that can't be right ("1200 out of 1000", "-5", "985" when the total is 470, "150%", "abc")
    # are not used: the same marks question again, with what was wrong. Nothing is saved from them.
    if active and intake.get("waiting_for") in ("marks", "marks_max", "percent", "degree_percent"):
        problem = _marks_problem(message, said, number, {**{k: profile.get(k) for k in ("board_key", "academic_stage")}, **intake}, intake.get("waiting_for"))
        if problem:
            again = _decide("Calculate my scholarship", profile, dict(intake), first_name)
            if again and again.get("action") == "ask":
                return {**again, "text": f"{problem}\n\n{again.get('text') or ''}".strip(), "state": dict(intake)}

    if number is None and active and intake.get("waiting_for") in ("marks", "percent", "degree_percent") \
            and said.get("percent") is None and said.get("max_marks") is None:
        nums = re.findall(r"(?<![\d.])\d{2,4}(?:\.\d+)?(?![\d.])", message or "")
        if len(nums) == 1 and not (said.keys() - {"raw_marks", "needs_marks_confirmation", "generic_btech"}):
            number = float(nums[0])
    if not is_fee_enquiry(message):
        # Only a reply to our own question continues the intake (a number, a board, "no JEE"...).
        reply_like = (bool(said.keys() - {"generic_btech"}) or number is not None
                      or intake.get("waiting_for") == "confirm_details")
        if intake.get("waiting_for") == "marks_max" and re.search(
            r"\b(?:1000|thousand|yes|correct|right|inter|intermediate|600|out\s+of)\b", (message or "").lower()
        ):
            reply_like = True
        if not (active and reply_like):
            return None
        if intake.get("waiting_for") == "done" and not (set(said) & set(_ACADEMIC_FIELDS)):
            return None   # the steps are finished: a programme named in another question is not an answer (v4.15.0)

    # Determine whether counsellor mode is active or newly requested
    counsellor_mode = bool(intake.get("counsellor_mode")) or bool(said.get("counsellor_triggered"))

    # Known facts aggregation from profile, previous intake state, and current message
    known = {}
    for k in (
        "board",
        "board_label",
        "board_key",
        "academic_stage",
        "stage_label",
        "raw_marks",
        "max_marks",
        "percent",
        "is_projected",
        "admission_route",
        "route_label",
        "eapcet_rank",
        "jee_percentile",
        "ib_score",
        "program",
        "no_entrance",
        "pending_raw_marks",
        "generic_btech",
        "degree_interest",
        "stream",
    ):
        if profile.get(k) not in (None, ""):
            known[k] = profile[k]
    if profile.get("degree_interest") == "btech" or profile.get("generic_btech"):
        known["generic_btech"] = True
    if not known.get("program") and profile.get("program_interest") and not said.get("generic_btech"):
        known["program"] = profile["program_interest"]

    for k, v in intake.items():
        if v not in (None, ""):
            known[k] = v

    for k, v in said.items():
        if v not in (None, "") and k not in ("generic_btech", "needs_marks_confirmation"):
            known[k] = v

    # Programme switch detection
    if said.get("program") and intake.get("program"):
        old_prog_key = fees.find_program(str(intake["program"]))
        new_prog_key = fees.find_program(str(said["program"]))
        if old_prog_key and new_prog_key and old_prog_key != new_prog_key:
            data = fees.load_data()
            old_level = data.get("programs", {}).get(old_prog_key, {}).get("level", "ug")
            new_level = data.get("programs", {}).get(new_prog_key, {}).get("level", "ug")
            known["program"] = said["program"]
            if old_level != new_level:
                for k_clr in (
                    "percent", "board", "board_label", "board_key", "academic_stage", "stage_label",
                    "raw_marks", "max_marks", "is_projected", "admission_route", "route_label",
                    "eapcet_rank", "jee_percentile", "ib_score", "pending_raw_marks"
                ):
                    known.pop(k_clr, None)
                    intake.pop(k_clr, None)
                intake.pop("waiting_for", None)
                intake.pop("pending_raw_marks", None)
                counsellor_mode = False
                intake["counsellor_mode"] = False

    # Handle bare numbers based on what we are waiting for
    if active:
        waiting = intake.get("waiting_for")
        if waiting == "marks":
            b_key = known.get("board_key")
            s_key = known.get("academic_stage")
            max_m = get_max_marks(b_key, s_key)
            if said.get("percent") is not None and said.get("raw_marks") is None:
                # "92%" when asked for marks out of 1000: a percentage, never 92 marks (v4.15.0)
                known["percent"] = float(said["percent"])
                for k_p in ("raw_marks", "max_marks", "pending_raw_marks", "needs_marks_confirmation"):
                    known.pop(k_p, None)
                number = None
            if number is not None:
                if max_m > 100 and 35 <= number <= 100:
                    # "87" when asked for marks out of 1000: a percentage (87 marks would be 8.7%) (v4.15.0)
                    known["percent"] = number
                    for k_p in ("raw_marks", "max_marks", "pending_raw_marks", "needs_marks_confirmation"):
                        known.pop(k_p, None)
                elif max_m > 100:
                    if number <= max_m:
                        known["raw_marks"] = number
                        known["max_marks"] = max_m
                        known["percent"] = round((number / max_m) * 100, 2)
                    elif 35 <= number <= 100:
                        known["percent"] = number
                        known["raw_marks"] = number
                else:
                    known["percent"] = number
                    known["raw_marks"] = number
        elif waiting == "rank":
            if number is not None:
                if known.get("admission_route") == "jee_main" or number <= 100:
                    known["jee_percentile"] = number
                else:
                    known["eapcet_rank"] = int(number)
            elif said.get("skip") or _ROUTE_NOT_DECIDED.search(message) or _NO_ENTRANCE.search(message):
                known["no_entrance"] = True
        elif waiting == "ib" and number is not None and number <= 45:
            known["ib_score"] = int(number)
        elif waiting == "degree_percent":
            pass  # read below, once the programme level is known
        elif waiting == "marks_max":
            raw = intake.get("pending_raw_marks")
            total = None
            if said.get("max_marks"):
                total = float(said["max_marks"])
            elif number is not None:
                if number >= (raw or 0) and (raw or 0) > 0:
                    total = float(number)
                elif 35 <= number <= 100:
                    known["percent"] = float(number)
            elif re.search(r"\b(?:1000|thousand|inter|intermediate)\b", (message or "").lower()):
                total = 1000.0
            elif re.match(r"^\W*(?:yes|yeah|yep|yup|correct|right|ha+|haan|avunu|ok(?:ay)?)\b", (message or "").lower()):
                # "Yes" to "Did you mean 866 out of 1000?": the total offered (the board's, else 1000).
                board_total = get_max_marks(known.get("board_key"), known.get("academic_stage") or "completed") \
                    if known.get("board_key") else 1000
                total = float(board_total if board_total >= (raw or 0) else 1000)
            elif re.search(r"\b600\b", (message or "").lower()):
                total = 600.0
            elif re.search(r"\b500\b", (message or "").lower()):
                total = 500.0
            if total and raw:
                known["raw_marks"], known["max_marks"] = float(raw), total
                known["percent"] = round((float(raw) / total) * 100, 2)
            if known.get("percent") is not None:
                known.pop("needs_marks_confirmation", None)
                known.pop("pending_raw_marks", None)
        elif number is not None:
            if 35 <= number <= 100:
                known.setdefault("percent", number)
            elif 100 < number <= 1000:
                if counsellor_mode and not known.get("board_key"):
                    # Marks given before the board: kept, and read once the board says out of what (v4.13.0).
                    known["pending_raw_marks"] = number
                elif counsellor_mode:
                    b_key = known.get("board_key")
                    s_key = known.get("academic_stage")
                    max_m = get_max_marks(b_key, s_key)
                    if number <= max_m:
                        known["raw_marks"] = number
                        known["max_marks"] = max_m
                        known["percent"] = round((number / max_m) * 100, 2)
                else:
                    said["needs_marks_confirmation"] = int(number)
                    known["needs_marks_confirmation"] = int(number)
            elif number > 1000:
                known.setdefault("eapcet_rank", int(number))

    # Marks given before the board (v4.13.0): read them once the board and status give the total.
    if known.get("pending_raw_marks") and known.get("percent") is None and known.get("board_key") \
            and known.get("academic_stage") and intake.get("waiting_for") != "marks_max":
        max_m = get_max_marks(known["board_key"], known["academic_stage"])
        raw = float(known["pending_raw_marks"])
        if max_m > 100 and 0 < raw <= max_m:
            known.update(raw_marks=raw, max_marks=float(max_m), percent=round(raw / max_m * 100, 2))
        known.pop("pending_raw_marks", None)

    # Update is_projected
    if known.get("academic_stage") in ("1st_year", "2nd_year"):
        known["is_projected"] = True
    elif known.get("academic_stage") == "completed":
        known["is_projected"] = False

    # Check program key
    prog_key = fees.find_program(str(known.get("program") or ""))
    if prog_key:
        known["program"] = prog_key

    asked = set(intake.get("asked", []))
    if intake.get("board"):
        asked |= {"board", "entrance"}
    state = {**{k: v for k, v in known.items() if k != "standard_only"}, "asked": sorted(asked),
             "turns": int(intake.get("turns", 0)) + 1}
    if counsellor_mode:
        state["counsellor_mode"] = True

    # A percentage above 100 ("656% marks") is a typo, usually marks out of 1000: ask, never calculate with it.
    bad_pct = re.search(r"(?<![\d.])(\d{3,4}(?:\.\d+)?)\s*(?:%|percent)", message or "")
    board_total = get_max_marks(known.get("board_key"), known.get("academic_stage") or "completed") \
        if known.get("board_key") else None
    if bad_pct and float(bad_pct.group(1)) > 100 and board_total and board_total > 100 \
            and float(bad_pct.group(1)) <= board_total:
        # The board is known (e.g. Telangana Intermediate, out of 1000): "867% marks" means 867 out of 1000.
        raw_v = float(bad_pct.group(1))
        pct_v = round(raw_v / board_total * 100, 2)
        known.update(raw_marks=raw_v, max_marks=float(board_total), percent=pct_v)
        state.update(raw_marks=raw_v, max_marks=float(board_total), percent=pct_v)
        known.pop("pending_raw_marks", None)
        state.pop("pending_raw_marks", None)
        bad_pct = None
    if bad_pct and float(bad_pct.group(1)) > 100:
        n = _num(float(bad_pct.group(1)))
        for k_bad in ("percent", "raw_marks", "max_marks"):
            state.pop(k_bad, None)
        state["pending_raw_marks"] = float(bad_pct.group(1))
        state["waiting_for"] = "marks_max"
        return {"action": "ask", "profile_clear": ["percent", "raw_marks", "max_marks"],
                "text": f"{n}% isn't possible (percentages go up to 100). Did you mean **{n} out of 1000**?",
                "chips": [f"{n} out of 1000", f"{n} out of 600"], "cards": [], "state": state}

    # PG scholarships use the qualifying-degree percentage, never the 12th marks.
    pg_counsellor = counsellor_mode and _program_level(prog_key) == "pg"
    if pg_counsellor:
        degree_val = None
        if intake.get("waiting_for") == "degree_percent":
            degree_val = number if number is not None else said.get("percent")
        elif said.get("percent") is not None:
            degree_val = said.get("percent")
        if degree_val is not None and 0 < float(degree_val) <= 100:
            known["degree_percent"] = float(degree_val)
            state["degree_percent"] = float(degree_val)

    # Strict eligibility check: if marks are below 50%, immediately reject and withhold fee details
    eligibility_basis = {"percent": known.get("degree_percent"), "level": "pg"} if pg_counsellor else known
    if is_below_minimum_eligibility(eligibility_basis, prog_key):
        return format_ineligible_response(eligibility_basis, state, prog_key)

    # =========================================================================
    # GUIDED ADMISSION COUNSELLOR WORKFLOW
    # =========================================================================
    if counsellor_mode:
        if pg_counsellor:
            return _counsellor_pg(prog_key, known, said, state, intake)

        if known.get("eapcet_rank") is not None:
            if not known.get("board"):
                known["board"] = "state_board"
                known["board_key"] = "ts_state_board"
                known["board_label"] = "Telangana / AP State Board"
            if not known.get("admission_route"):
                known["admission_route"] = "tg_eapcet"
                known["route_label"] = "TG EAPCET"
            if not known.get("academic_stage") and (known.get("percent") is not None or known.get("raw_marks") is not None):
                known["academic_stage"] = "completed"
                known["stage_label"] = "Completed Intermediate (Passed out)"
                known["is_projected"] = False

        if known.get("jee_percentile") is not None:
            if not known.get("admission_route"):
                known["admission_route"] = "jee_main"
                known["route_label"] = "JEE Main"
            if not known.get("academic_stage") and (known.get("percent") is not None or known.get("raw_marks") is not None):
                known["academic_stage"] = "completed"
                known["stage_label"] = "Completed Intermediate (Passed out)"
                known["is_projected"] = False

        has_board = bool(known.get("board"))
        has_stage = bool(known.get("academic_stage"))
        has_marks = bool(known.get("percent") is not None or known.get("raw_marks") is not None)
        has_route = bool(known.get("admission_route"))
        has_prog = bool(prog_key)

        # Single-shot query completion: if user gave course, board and marks in a single message, don't block on stage/route
        is_single_shot = bool(said.get("program") and said.get("board") and (said.get("percent") is not None or said.get("raw_marks") is not None))
        if is_single_shot and has_prog and has_board and has_marks:
            if not has_stage:
                known["academic_stage"] = "completed"
                known["stage_label"] = "Completed Intermediate (Passed out)"
                known["is_projected"] = False
                has_stage = True
            if not has_route:
                known["admission_route"] = "not_decided"
                known["route_label"] = "Not decided yet"
                known["no_entrance"] = True
                has_route = True
        # What was assumed above (stage, route, board for an EAPCET rank) is kept for the next turns too: the
        # state was copied from `known` before these assumptions (v4.15.0: a later marks correction asked the
        # stage again).
        for _k in ("academic_stage", "stage_label", "is_projected", "admission_route", "route_label", "no_entrance",
                   "board", "board_key", "board_label"):
            if known.get(_k) is not None:
                state[_k] = known[_k]

        # Check if this is a re-query (all details were already known)
        needs_route = _uses_entrance(prog_key)
        is_all_known = has_board and has_stage and has_marks and has_prog and (has_route or not needs_route)
        is_re_query = is_all_known and (
            intake.get("waiting_for") == "done"
            or (not intake.get("waiting_for") and int(intake.get("turns", 0)) == 0)
        )

        def _score_plain() -> str:
            raw_v, pct_v = known.get("raw_marks"), known.get("percent")
            max_v = known.get("max_marks") or get_max_marks(known.get("board_key"), known.get("academic_stage"))
            if raw_v and max_v and max_v > 100:
                if pct_v is None:
                    pct_v = round(float(raw_v) / float(max_v) * 100, 2)
                return f"{_num(raw_v)}/{_num(max_v)} ({_num(pct_v)}%)"
            return f"{_num(pct_v)}%"

        def _ack() -> str:
            """The marks compliment, shown once: on the first step after the marks were given."""
            if not has_marks or intake.get("ack_shown"):
                return ""
            state["ack_shown"] = True
            return get_marks_acknowledgment(
                _score_plain(), float(known.get("percent") or 0), is_projected=bool(known.get("is_projected")),
                stage_label=known.get("stage_label", ""), variant_idx=int(state.get("turns", 0)),
            ) + "\n\n"

        # The scholarship journey reuses everything already known in this conversation (from the eligibility
        # check, the form or the chat) and asks only for what is missing:
        #   programme first (scholarship rules and entrance options differ by programme), then
        #   2+ of board / status / marks missing -> ONE consolidated form, pre-filled with what is known;
        #   exactly 1 missing                    -> only that field;
        #   nothing missing                      -> calculate. An entrance score is optional (form field, or
        #   "Add my EAPCET rank" afterwards); it is never a mandatory step.
        name_bit = f", {first_name}" if first_name else ""
        if not has_prog:
            state["waiting_for"] = "program"
            if said.get("generic_btech") or known.get("generic_btech"):
                text = (f"Sure{name_bit}! Which B.Tech branch would you like the scholarship details for? For example, "
                        f"Computer Science, AI & Robotics, Electronics or Mechanical Engineering.")
                chips = ["B.Tech CSE", "B.Tech AI & Robotics", "B.Tech ECE", "B.Tech Mechanical"]
            else:
                text = f"Sure{name_bit}! Which programme would you like the scholarship details for?"
                chips = ["B.Tech", "BBA", "MBA", "B.Sc Agriculture"]
            card = build_counsellor_program_card(selected_program=known.get("program"), step_label="Preferred Programme")
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        short = fees.short_name(prog_key)
        req = eligibility.stream_requirement(prog_key)
        needs_stream = bool(req.get("any_of")) and not known.get("stream")
        has_entrance = bool(known.get("eapcet_rank") or known.get("jee_percentile") or known.get("no_entrance"))
        missing = [f for f, ok in (("board", has_board), ("stage", has_stage), ("marks", has_marks)) if not ok]
        first_turn = not intake.get("waiting_for")
        lead = (f"Absolutely{name_bit}! I can help you understand the scholarship details for **{short}**. "
                if first_turn else "Thanks! ")
        have = []
        if has_marks:
            have.append(_score_plain())
        if known.get("stream"):
            have.append(known["stream"])
        if has_board and known.get("board_label"):
            have.append(known["board_label"])
        if has_stage and known.get("stage_label"):
            have.append(known["stage_label"])
        reuse = f"I'll use the details you've already shared ({', '.join(have)}). " if have and first_turn else ""

        # One small question at a time (v4.9.0): board -> current status -> marks -> 10+2 group (when the
        # programme names one). Each step shows "Step n of N" and only the field still missing.
        sequence = ["board", "stage", "marks"] + (["stream"] if req.get("any_of") else [])
        todo = missing + (["stream"] if needs_stream else [])
        if todo:
            step = todo[0]
            n_total, n_now = len(sequence), sequence.index(step) + 1
            step_label = f"Step {n_now} of {n_total}"
            opener = (f"Sure{name_bit}! Let's work out your scholarship for **{short}**. " if first_turn else "")
            if first_turn and have:
                opener += f"Noted: {', '.join(have)}. "
            saved = None
            if first_turn and not have and profile.get("saved_academic"):
                from . import journey
                saved = journey.saved_summary(profile)
            chips_saved = [f"Use my saved details ({saved})"] if saved else []
            if step == "board":
                state["waiting_for"] = "board"
                if known.get("pending_raw_marks"):
                    opener = f"Noted: **{_num(float(known['pending_raw_marks']))}** marks. " + opener
                card = build_counsellor_board_card(selected_board=known.get("board_key"))
                card.update(title="Which board did you study under?", subtitle=None, step_label=step_label,
                            program=prog_key)
                return {"action": "ask", "text": f"{opener}{step_label}: which board did you study under?",
                        "chips": chips_saved, "cards": [card], "state": state}
            if step == "stage":
                state["waiting_for"] = "stage"
                card = build_counsellor_stage_card(board_label=known.get("board_label"),
                                                   selected_stage=known.get("academic_stage"))
                card.update(title="Are you still studying, or have you finished Intermediate?", subtitle=None,
                            step_label=step_label, program=prog_key)
                return {"action": "ask", "text": f"{opener}{step_label}: where are you in Intermediate right now?",
                        "chips": [], "cards": [card], "state": state}
            if step == "marks":
                state["waiting_for"] = "marks"
                b_key = known.get("board_key") or "ts_state_board"
                s_key = known.get("academic_stage") or "completed"
                board_lbl = known.get("board_label") or "your board"
                max_m = get_max_marks(b_key, s_key)
                which = ("your 1st-year marks" if s_key == "1st_year" else
                         "your marks so far" if s_key == "2nd_year" else "your final marks")
                card = build_counsellor_marks_card(board_key=b_key, stage_key=s_key, max_marks=max_m,
                                                   board_label=board_lbl, default_val=known.get("raw_marks"))
                card.update(step_label=step_label, program=prog_key)
                hint = f" (out of {max_m})" if max_m > 100 else ""
                return {"action": "ask", "text": f"{opener}{step_label}: what are {which}{hint}?",
                        "chips": [], "cards": [card], "state": state}
            if step == "stream":
                state["waiting_for"] = "stream"
                from app.services.card_service import _FORM_STREAM_OPTIONS
                card = {"type": "counsellor_choice", "step_label": step_label, "program": prog_key,
                        "title": "Which group did you take in Intermediate?", "subtitle": None,
                        "options": [{"key": o["key"], "label": o["label"], "desc": ""} for o in _FORM_STREAM_OPTIONS],
                        "selected_stage": known.get("stream")}
                return {"action": "ask", "text": f"{opener}{step_label}: which group did you take?",
                        "chips": [], "cards": [card], "state": state}

        # 10+2 subjects: a known mismatch is stated plainly; an unknown group does not block the scholarship
        # estimate (the assessment notes the requirement).
        if req.get("any_of") and known.get("stream"):
            verdict = eligibility.assess(prog_key, _known_percent(known), known.get("stream"))
            if verdict.get("stream_ok") is False:
                state["waiting_for"] = None
                return {"action": "ineligible", "text": eligibility.explain(verdict, _score_text(known)),
                        "chips": ["📞 Admissions Office", "Explore other programmes", "📋 Eligibility Criteria"],
                        "cards": [], "state": state}

        # Step 5b: Entrance rank (skippable) if entrance route selected but score missing
        if (
            needs_route
            and known.get("admission_route") in ("tg_eapcet", "ap_eapcet", "jee_main")
            and not known.get("no_entrance")
            and not known.get("eapcet_rank")
            and not known.get("jee_percentile")
            and "rank" not in asked
        ):
            state["waiting_for"] = "rank"
            state["asked"] = sorted(asked | {"rank"})
            route_lbl = known.get("route_label") or "entrance exam"
            if "jee" in (known.get("admission_route") or ""):
                text = (
                    f"Got it! What is your JEE Main percentile? If you haven't received your percentile yet or "
                    f"haven't appeared, you can skip this step and we'll calculate based on your Intermediate marks alone."
                )
                chips = ["85 percentile", "92 percentile", "Skip this step", "Not appeared yet"]
            else:
                text = (
                    f"Got it! What is your {route_lbl} rank? If you haven't received your rank yet or haven't "
                    f"appeared, you can skip this step and we'll calculate based on your Intermediate marks alone."
                )
                chips = ["Rank 5000", "Rank 15000", "Skip this step", "Not appeared yet"]
            return {"action": "ask", "text": text, "chips": chips, "cards": [], "state": state}

        # Asked again after an estimate: confirm the saved details first (use them, or change them).
        low_msg = (message or "").lower()
        if intake.get("waiting_for") == "confirm_details":
            if re.search(r"\b(?:change|edit|update|different|new|wrong)\b", low_msg):
                for k_clr in _ACADEMIC_FIELDS:
                    state.pop(k_clr, None)
                state.update(waiting_for="board", ack_shown=False)
                card = build_counsellor_board_card()
                card.update(title="Which board did you study under?", subtitle=None,
                            step_label=f"Step 1 of {3 + (1 if req.get('any_of') else 0)}")
                return {"action": "ask", "profile_clear": list(_ACADEMIC_FIELDS),
                        "text": "No problem, let's update them. Which board did you study under?",
                        "chips": [], "cards": [card], "state": state}
        elif intake.get("waiting_for") == "done" and not (set(said) & set(_ACADEMIC_FIELDS)):
            summary = ", ".join(have) if have else "your earlier details"
            state["waiting_for"] = "confirm_details"
            return {"action": "ask",
                    "text": f"I already have your details: **{summary}**. Use them for {short}, or change them?",
                    "chips": ["Use these details", "Change my details"], "cards": [], "state": state,
                    "exact_chips": True}

        # Step 6: All details known -> Calculate!
        state["waiting_for"] = "done"
        state["ack_shown"] = True  # the assessment shows the marks compliment once; a recalculation does not
        state["program"] = prog_key
        args = {"program": prog_key}
        if known.get("percent") is None and known.get("raw_marks") is not None:
            max_m = known.get("max_marks") or get_max_marks(known.get("board_key"), known.get("academic_stage"))
            if max_m and max_m > 0:
                known["percent"] = round((float(known["raw_marks"]) / float(max_m)) * 100, 2)
        if known.get("percent") is not None:
            args["percent"] = known["percent"]
        if known.get("board") in ("cbse", "state_board", "ib"):
            args["board"] = "cbse" if known["board"] == "cbse" else "state_board"
        if needs_route and known.get("eapcet_rank") is not None:
            args["eapcet_rank"] = known["eapcet_rank"]
        if needs_route and known.get("jee_percentile") is not None:
            args["jee_percentile"] = known["jee_percentile"]
        if known.get("ib_score") is not None:
            args["ib_score"] = known["ib_score"]

        prog_name = fees.clean_program_name(
            prog_key,
            specialization=known.get("specialization"),
            user_text=known.get("program_raw"),
        )

        return {
            "action": "calculate",
            "args": args,
            "state": state,
            "counsellor": True,
            "counsellor_details": {
                "board": known.get("board"),
                "board_label": known.get("board_label") or _BOARD_LABEL.get(known.get("board") or "", "Intermediate Board"),
                "board_key": known.get("board_key") or "ts_state_board",
                "academic_stage": known.get("academic_stage"),
                "stage_label": known.get("stage_label") or ("Completed Intermediate" if not known.get("is_projected") else "Intermediate 1st Year"),
                "raw_marks": known.get("raw_marks"),
                "max_marks": known.get("max_marks") or get_max_marks(known.get("board_key"), known.get("academic_stage")),
                "percent": known.get("percent"),
                "is_projected": bool(known.get("is_projected")),
                "admission_route": known.get("admission_route"),
                "route_label": known.get("route_label") or ("Not provided (marks-based estimate)" if needs_route
                                                             else "Direct Merit / 10+2 Marks"),
                "has_entrance_score": bool(known.get("eapcet_rank") or known.get("jee_percentile")),
                "eapcet_rank": known.get("eapcet_rank"),
                "jee_percentile": known.get("jee_percentile"),
                "ib_score": known.get("ib_score"),
                "program": prog_key,
                "program_name": prog_name,
                "specialization": known.get("specialization"),
                "program_raw": known.get("program_raw"),
                "re_query": is_re_query,
                "ack_shown": bool(intake.get("ack_shown")),
                "level": "ug",
                "uses_entrance": needs_route,
                "stream": known.get("stream"),
            },
        }

    # =========================================================================
    # STANDARD FEE FORM INTAKE (for generic university fee structure queries)
    # Since v4.13.0 a question for missing details here is asked step by step instead (see decide()): the old
    # consolidated form card is never shown in the chat.
    # =========================================================================
    if not prog_key:
        answered_total = intake.get("waiting_for") == "marks_max" and known.get("percent") is not None
        if "program" in asked and not answered_total:
            return None
        state["asked"] = sorted(asked | {"program"})
        state["waiting_for"] = "program"

        raw_val = (
            said.get("needs_marks_confirmation")
            or (int(number) if number is not None and 100 < number <= 1000 else None)
            or (int(said["raw_marks"]) if said.get("raw_marks") else None)
        )
        pct_val = said.get("percent") or known.get("percent")
        if raw_val or pct_val:
            from . import eligibility
            if pct_val is None and not said.get("max_marks"):
                # "230" or "I got 230 marks": the total is not known, so ask for it instead of assuming 1000.
                state["waiting_for"] = "marks_max"
                state["pending_raw_marks"] = raw_val
                return {
                    "action": "ask",
                    "text": (f"Thanks! Out of how many total marks is **{raw_val}**? For example, 1000 for "
                             f"TS / AP Intermediate, or 500 / 600 for some other boards."),
                    "chips": [f"{raw_val} out of 1000", f"{raw_val} out of 600", f"{raw_val} out of 500"],
                    "cards": [],
                    "state": state,
                }
            raw_k, max_k = known.get("raw_marks"), known.get("max_marks")
            exact = (eligibility.percent_from_marks(raw_k, max_k) if raw_k and max_k and float(max_k) > 100
                     else float(pct_val))
            state["percent"] = pct_val
            if is_below_minimum_eligibility({"percent": exact}):
                return format_ineligible_response({**known, "percent": exact}, state)
            # Scholarship (by Intermediate marks) is separate from admission eligibility, which depends on
            # the programme: ask for the programme before saying anything about eligibility.
            sch = fees.scholarship_for("btech_cse", percent=exact, board=known.get("board") or "state_board")
            score = (f"**{_num(raw_k)}/{_num(max_k)} ({eligibility.show_percent(exact)})**"
                     if raw_k and max_k and float(max_k) > 100 else f"**{eligibility.show_percent(exact)}**")
            if sch["percent"] > 0:
                text = (f"Thanks! With {score}, your Intermediate marks fall in the **{sch['percent']}% merit "
                        f"scholarship** slab (subject to your board and programme).\n\n")
            else:
                text = f"Thanks! I've noted {score}.\n\n"
            text += ("Which programme are you interested in? I'll check the admission eligibility and exact fee "
                     "for that programme.")
            chips = ["B.Tech CSE", "B.Tech ECE", "BBA", "B.Sc Agriculture"]
            form_card = build_fee_scholarship_form_card(level="ug")
            return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

        if said.get("generic_btech") or fees._is_generic_btech((message or "").lower()):
            text = ("B.Tech fees depend on the branch. The {year} standard tuition (before any scholarship, as per "
                    "the Admissions Office) is:\n{branches}\n\nWhich branch are you interested in? Tell me your "
                    "board, Intermediate / 12th marks and JEE Main or EAPCET score too, and I will work out your "
                    "scholarship and exact fee.").format(year=config.ADMISSION_YEAR, branches=_btech_branches_text())
            chips = ["B.Tech CSE", "B.Tech AI and Robotics", "B.Tech ECE", "B.Tech Mechanical"]
            form_card = build_fee_scholarship_form_card(level="ug")
            return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}
        else:
            low_msg = (message or "").lower()
            level = "ug"
            if re.search(r"\b(?:pg|postgrad|postgraduate|master|mba|mca|m\.?tech|m\.?sc)\b", low_msg) or profile.get("degree_level") == "pg":
                level = "pg"

            if level == "pg":
                text = (
                    "Which programme are you asking about? For postgraduate studies, we offer MBA, MCA, M.Tech and M.Sc.\n\n"
                    "To calculate your fee and check eligible merit scholarships, please select or tell me your **intended PG programme**.\n"
                    "In the next step, you can enter your qualifying degree percentage."
                )
                chips = ["MBA", "MCA", "M.Tech CSE", "MBA in Agri-Business"]
            else:
                text = (
                    "Which programme are you asking about? We offer B.Tech, BBA, BCA, B.Sc Agriculture, MBA, MCA, M.Tech and Ph.D. "
                    "(for B.Tech, please mention the branch).\n\n"
                    "To calculate your fee and check your eligible scholarship (up to 40% waiver), please select your course and your "
                    "10+2 / Intermediate Board (Telangana, AP, CBSE, ICSE, Other State Boards across India, NIOS, or IB).\n\n"
                    "In the next step, you can enter your 10+2 marks or entrance rank. "
                    "You can also use the interactive assessment form below."
                )
                chips = ["B.Tech CSE", "B.Tech ECE", "BBA", "B.Sc Agriculture", "MBA"]

            form_card = build_fee_scholarship_form_card(level=level)
            return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    known["program"] = prog_key
    state["program"] = prog_key
    prog = fees.load_data()["programs"][prog_key]
    level = prog.get("level", "ug")
    name = prog["name"]
    standard = (f"The {config.ADMISSION_YEAR} standard tuition for **{name}** is **{fees.inr(prog['tuition_per_year'])} "
                f"per year** ({fees.inr(prog['tuition_per_year'] // 2)} per semester), before any scholarship, as "
                f"per the Admissions Office.")
    portal = f"You can also check it on the official calculator: {FEE_PORTAL_URL}"
    has_score = any(known.get(k) not in (None, "") for k in ("percent", "eapcet_rank", "jee_percentile", "ib_score"))

    def calculate():
        args = {"program": str(known["program"])}
        for k in ("percent", "eapcet_rank", "jee_percentile", "ib_score"):
            if known.get(k) not in (None, ""):
                args[k] = known[k]
        if known.get("board") in ("cbse", "state_board", "ib") and level != "pg":
            args["board"] = "cbse" if known["board"] == "cbse" else "state_board"
        return {
            "action": "calculate",
            "args": args,
            "state": state,
            "details": {
                "board": _BOARD_LABEL.get(known.get("board") or "", ""),
                "board_label": known.get("board_label"),
                "no_entrance": known.get("no_entrance"),
            },
        }

    # "Just the standard fee" / "skip"
    if (said.get("standard_only") and not has_score) or said.get("skip"):
        return calculate()

    # IB students need their IB points, not a percentage
    if level != "pg" and known.get("board") == "ib" and not known.get("ib_score") and "ib" not in asked:
        state["asked"] = sorted(asked | {"ib"})
        state["waiting_for"] = "ib"
        form_card = build_fee_scholarship_form_card(selected_program=prog_key, selected_board="ib", level=level, only_selected=True)
        return {
            "action": "ask",
            "text": f"Got it! For **{name}** under **International Baccalaureate (IB)**:\nWhat is your IB Diploma score (points out of 45)? The IB scholarship slabs use points, not a percentage.",
            "chips": ["30", "34", "38"],
            "cards": [form_card],
            "state": state,
        }

    # Confirmation: Raw 3-digit marks without maximum marks
    if (said.get("needs_marks_confirmation") or known.get("needs_marks_confirmation")) and not known.get("percent") and not has_score:
        raw_val = said.get("needs_marks_confirmation") or known.get("needs_marks_confirmation")
        state["waiting_for"] = "marks_max"
        state["pending_raw_marks"] = raw_val
        # The total is unknown: ask for it. Never assume 1000 and never state eligibility from a guess.
        text = (
            f"Thanks! For **{name}**, out of how many total marks is **{_num(raw_val)}**? For example, 1000 for "
            f"TS / AP Intermediate, or 500 / 600 for some other boards. I'll then check your eligibility and fee."
        )
        chips = [
            f"{_num(raw_val)} out of 1000",
            f"{_num(raw_val)} out of 600",
            f"{_num(raw_val)} out of 500",
        ]
        board_key = _board_card_key(known.get("board"), known.get("board_label"))
        form_card = build_fee_scholarship_form_card(
            selected_program=prog_key,
            selected_board=board_key,
            level=level,
            only_selected=True,
        )
        return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    # UG: ask for 10+2 board first if not known
    if not has_score:
        if "scores" in asked:
            return calculate()

        if level == "pg":
            state["asked"] = sorted(asked | {"scores"})
            state["waiting_for"] = "percent"
            text = (
                f"{standard}\n\n"
                f"To calculate your fee and merit scholarship for **{name}**, please provide your "
                f"percentage in the qualifying degree (for example B.Tech, B.Sc or BBA).\n\n{portal}"
            )
            chips = ["My degree % is 75", "My degree % is 85", "Just the standard fee"]
            form_card = build_fee_scholarship_form_card(selected_program=prog_key, level="pg", only_selected=True)
            return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

        if not known.get("board"):
            if "board" in asked:
                return calculate()
            state["asked"] = sorted(asked | {"board", "entrance"})
            state["waiting_for"] = "board"
            text = (
                f"{standard}\n\n"
                f"Which board (10+2 / Intermediate Board) did you study under?\n"
                f"• **Telangana State Board (TS BIE)**\n"
                f"• **AP State Board (BIEAP)**\n"
                f"• **CBSE / ICSE / NIOS**\n"
                f"• **Other State Boards across India** (Maharashtra, Karnataka, Tamil Nadu, UP, Bihar, etc.)\n"
                f"• **IB (International Baccalaureate)**\n\n"
                f"In the next step, I'll ask for your marks or entrance rank (JEE Main percentile or TG / AP EAPCET rank) "
                f"to calculate your exact scholarship and fee. {portal}\n"
                f"You can also use the assessment form below."
            )
            chips = [
                "Telangana State Board",
                "AP State Board",
                "CBSE / ICSE",
                "Other State Board across India",
                "IB",
            ]
            form_card = build_fee_scholarship_form_card(selected_program=prog_key, level=level, only_selected=True)
            return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

        if "marks" in asked:
            return calculate()
        state["asked"] = sorted(asked | {"marks"})
        state["waiting_for"] = "percent"
        board_disp = known.get("board_label") or _BOARD_LABEL.get(known.get("board"), "your board")
        board_card_key = _board_card_key(known.get("board"), known.get("board_label"))
        text = (
            f"Got it! For **{name}** under **{board_disp}**:\n"
            f"Please provide your **10+2 marks** (percentage, or marks out of 1000) or your "
            f"**Entrance Exam Rank** (JEE Main percentile or TG / AP EAPCET rank).\n\n"
            f"Based on your marks or rank, I will calculate your merit scholarship (up to 40% fee waiver) "
            f"and exact net tuition."
        )
        chips = [
            "85% in 10+2",
            "92% in 10+2",
            "96% in 10+2",
            "JEE 85 percentile",
            "EAPCET rank 15000",
            "Just the standard fee",
        ]
        form_card = build_fee_scholarship_form_card(
            selected_program=prog_key,
            selected_board=board_card_key,
            level=level,
            only_selected=True,
        )
        return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    # Only entrance score given
    if (level != "pg" and known.get("percent") is None and not known.get("ib_score")
            and "marks" not in asked and "scores" not in asked and not known.get("skip")):
        state["asked"] = sorted(asked | {"marks"})
        state["waiting_for"] = "percent"
        form_card = build_fee_scholarship_form_card(
            selected_program=prog_key,
            selected_board=_board_card_key(known.get("board"), known.get("board_label")),
            level=level,
            only_selected=True,
        )
        return {
            "action": "ask",
            "chips": ["State Board, 85%", "CBSE, 90%", "Skip, use my rank"],
            "cards": [form_card],
            "state": state,
            "text": (
                "Thanks. What were your Intermediate / 12th marks, and which board (Telangana / AP State "
                "Board, CBSE, ICSE or IB)? Board marks can earn a scholarship too, and the best one is applied."
            ),
        }

    pct = known.get("percent")
    if level != "pg" and pct is not None and not known.get("board") and "board" not in asked:
        as_state = fees.scholarship_for(prog_key, percent=pct, board="state_board")["percent"]
        as_cbse = fees.scholarship_for(prog_key, percent=pct, board="cbse")["percent"]
        if as_state != as_cbse:
            state["asked"] = sorted(asked | {"board"})
            state["waiting_for"] = "board"
            form_card = build_fee_scholarship_form_card(
                selected_program=prog_key,
                level=level,
                only_selected=True,
            )
            return {
                "action": "ask",
                "chips": ["Telangana State Board", "AP State Board", "CBSE", "ICSE"],
                "cards": [form_card],
                "state": state,
                "text": (
                    f"Which board did you study under? With {pct:g}% the scholarship is "
                    f"{as_state}% for Telangana / AP State Board and {as_cbse}% for CBSE / ICSE, so it "
                    f"matters for your fee."
                ),
            }

    if (level != "pg" and prog_key.startswith(_ENTRANCE_PROGRAMS) and "entrance" not in asked
            and not known.get("no_entrance") and not known.get("eapcet_rank") and not known.get("jee_percentile")):
        board = "cbse" if known.get("board") == "cbse" else "state_board"
        best = fees.scholarship_for(prog_key, percent=pct, board=board, ib_score=known.get("ib_score"))["percent"]
        if best < 40:
            state["asked"] = sorted(asked | {"entrance"})
            state["waiting_for"] = "rank"
            form_card = build_fee_scholarship_form_card(
                selected_program=prog_key,
                selected_board=_board_card_key(known.get("board"), known.get("board_label")),
                level=level,
                only_selected=True,
            )
            return {
                "action": "ask",
                "chips": ["No entrance exam", "EAPCET rank 12000", "JEE 85 percentile"],
                "cards": [form_card],
                "state": state,
                "text": (
                    f"Got it. Did you also write JEE Main or TG / AP EAPCET? Your marks give a {best}% "
                    f"scholarship; a JEE Main percentile of 80+ or an EAPCET rank up to 20,000 can give "
                    f"more, and the best one is applied. Share your score, or say \"no entrance exam\"."
                ),
            }

    return calculate()

