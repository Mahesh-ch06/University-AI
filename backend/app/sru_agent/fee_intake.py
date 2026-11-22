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
    build_fee_scholarship_form_card,
    build_counsellor_board_card,
    build_counsellor_stage_card,
    build_counsellor_marks_card,
    build_counsellor_route_card,
    build_counsellor_program_card,
)
from . import config, fees

FEE_PORTAL_URL = config.FEE_PORTAL_URL

_FEE_WORDS = re.compile(
    r"\b(?:fee|fees|fess|feez|tuition|cost|costs|schol\w*|how\s+much|per\s+sem\w*|payable|"
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
    r"\b(?:schol\w*|waiver|concession|discount|scholarship\s+counsell?or|fee\s+counsell?or|fee\s+assessment|"
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
    r"\b(?:completed|passed(?:\s*out)?|finished|dropper|passed|already\s*passed|passout|10\+2\s*completed)\b",
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
_ROUTE_OTHER = re.compile(r"\bother(?:\s+(?:entrance|exam|route))?\b", re.IGNORECASE)

_STATE_BOARD = re.compile(
    r"\b(?:state\s*board|tsbie|bieap|biets|board\s+of\s+intermediate|intermediate\s+board|inter\s+board|"
    r"(?:ts|tg|ap|telangana|andhra(?:\s+pradesh)?)\s*(?:state\s*)?(?:board|inter(?:mediate)?)|"
    r"(?:maharashtra|msbshse|karnataka|puc?|tamil\s*nadu|tndge|kerala|dhse|up\s*board|uttar\s*pradesh|"
    r"bihar|bseb|mp\s*board|madhya\s*pradesh|rajasthan|rbse|delhi|punjab|pseb|haryana|hbse|"
    r"west\s*bengal|wbchse|gujarat|gseb|odisha|chse|assam|ahsec|jharkhand|jac|chhattisgarh|cgbse|"
    r"other\s*state\s*board)\s*(?:state\s*)?(?:board|inter(?:mediate)?|hsc|puc?|12th)?)\b",
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

_BOARD_LABEL = {
    "state_board": "Telangana / AP / State Board (All India)",
    "cbse": "CBSE / ICSE / NIOS",
    "ib": "International Baccalaureate (IB)",
}
_ENTRANCE_PROGRAMS = ("btech_", "bsc_agri")


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
        elif re.search(r"\b(?:robotics\s*(?:&|and)\s*automation)\b", low):
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
    elif _STATE_BOARD.search(message or ""):
        out["board"] = "state_board"
        if re.search(r"\b(?:ts|tg|telangana|tsbie|biets)\b", low):
            out["board_label"] = "Telangana Intermediate (TSBIE)"
            out["board_key"] = "ts_state_board"
        elif re.search(r"\b(?:ap|andhra|bieap)\b", low):
            out["board_label"] = "Andhra Pradesh Intermediate (BIEAP)"
            out["board_key"] = "ap_state_board"
        elif re.search(r"\b(?:other|maharashtra|karnataka|tamil|kerala|up|bihar|mp|rajasthan|delhi|punjab|haryana|bengal|gujarat)\b", low):
            out["board_label"] = "Other State Board"
            out["board_key"] = "other_state_board"
        else:
            out["board_label"] = "Telangana / AP State Board"
            out["board_key"] = "ts_state_board"

    # Stage detection
    if _STAGE_2ND.search(message or "") and not (re.search(r"\b(?:completed|passed)\s+1st\s+year\b", low) and not re.search(r"\b(?:in|studying|currently|in\s+the)\s*2nd\b", low)):
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
    frac = re.search(r"(?<![\d.])(\d{2,4})\s*(?:marks\s+)?(?:/|out\s+of)\s*(\d{2,4})", low)
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
    if _OTHER_FEE_TOPIC.search(message or ""):
        return False
    if bool(_FEE_WORDS.search(message or "")):
        return True
    if _COUNSELLOR_TRIGGER.search(message or ""):
        return True
    if _BARE_SCORE_OR_MARKS.match((message or "").strip()):
        return True
    num = _bare_number(message)
    if num is not None and (35 <= num <= 1000):
        return True
    return False


def decide(message: str, profile: dict, intake: dict | None) -> dict | None:
    """What to do with a fee enquiry. Multi-step intake with counsellor workflow and anti-repetition."""
    from . import intents
    if intents._ADMISSION_GUARANTEE_PATTERN.search(message or "") or intents._FUTURE_YEAR_FEE_PATTERN.search(message or ""):
        return None
    intake = dict(intake or {})
    said = parse_details(message)
    active = bool(intake) and int(intake.get("turns", 0)) < 10
    number = _bare_number(message)

    if not is_fee_enquiry(message):
        # Only a reply to our own question continues the intake (a number, a board, "no JEE"...).
        reply_like = bool(said.keys() - {"generic_btech"}) or number is not None
        if intake.get("waiting_for") == "marks_max" and re.search(
            r"\b(?:1000|thousand|yes|correct|right|inter|intermediate|600|out\s+of)\b", (message or "").lower()
        ):
            reply_like = True
        if not (active and reply_like):
            return None

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
            if number is not None:
                if max_m > 100:
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
        elif waiting == "marks_max":
            raw = intake.get("pending_raw_marks")
            if number is not None:
                if number >= (raw or 0) and (raw or 0) > 0:
                    known["percent"] = round((float(raw) / float(number)) * 100, 2)
                elif 35 <= number <= 100:
                    known["percent"] = float(number)
            elif re.search(r"\b(?:1000|thousand|yes|correct|right|inter|intermediate)\b", (message or "").lower()):
                if raw:
                    known["percent"] = round((float(raw) / 1000.0) * 100, 2)
            elif re.search(r"\b600\b", (message or "").lower()):
                if raw:
                    known["percent"] = round((float(raw) / 600.0) * 100, 2)
        elif number is not None:
            if 35 <= number <= 100:
                known.setdefault("percent", number)
            elif 100 < number <= 1000:
                if counsellor_mode:
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

    # =========================================================================
    # GUIDED ADMISSION COUNSELLOR WORKFLOW
    # =========================================================================
    if counsellor_mode:
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

        # Check if this is a re-query (all details were already known)
        is_all_known = has_board and has_stage and has_marks and has_route and has_prog
        is_re_query = is_all_known and (intake.get("waiting_for") == "done" or int(intake.get("turns", 0)) > 0)

        # Step 0: If course/degree is completely unknown (neither specific programme nor generic B.Tech)
        # Prompt user to choose or state their course first before board/marks questions.
        has_any_course = bool(has_prog or said.get("generic_btech") or known.get("generic_btech") or intake.get("generic_btech"))
        if not has_any_course and not intake.get("waiting_for"):
            state["waiting_for"] = "program"
            text = (
                "Sure! I can help you with fee and scholarship details at SR University.\n\n"
                "Which course or degree are you considering?"
            )
            chips = [
                "B.Tech CSE",
                "B.Tech (Other Branches)",
                "MBA",
                "BBA",
                "B.Sc Agriculture",
            ]
            card = build_counsellor_program_card(selected_program=known.get("program"), step_label="Step 1: Preferred Programme")
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        # Step 1: Board selection (if not already known)
        if not has_board:
            state["waiting_for"] = "board"
            text = (
                "Absolutely! I can help you understand your potential scholarship and the fee you may need to pay at SR University.\n\n"
                "To give you a relevant estimate, let me first understand your academic background. I'll guide you through a few quick questions.\n\n"
                "Where did you complete your schooling / Intermediate education?\n"
                "Select the board under which you studied so I can use the appropriate academic assessment criteria."
            )
            chips = [
                "Telangana Intermediate (TSBIE)",
                "AP Intermediate (BIEAP)",
                "CBSE",
                "ISC",
                "Other State Board",
                "IB",
            ]
            card = build_counsellor_board_card(selected_board=known.get("board_key"))
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        # Step 2: Academic stage selection (if not already known)
        if not has_stage:
            state["waiting_for"] = "stage"
            board_lbl = known.get("board_label") or _BOARD_LABEL.get(known.get("board") or "", "your board")
            text = (
                f"Great! You've selected {board_lbl}.\n\n"
                f"Next, let's understand your current academic stage so I can ask for the correct marks.\n\n"
                f"Which year are you currently studying in?"
            )
            chips = [
                "Intermediate 1st Year (11th)",
                "Intermediate 2nd Year (12th)",
                "Completed Intermediate (Passed out)",
            ]
            card = build_counsellor_stage_card(board_label=board_lbl, selected_stage=known.get("academic_stage"))
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        # Step 3: Marks input (if not already known)
        if not has_marks:
            state["waiting_for"] = "marks"
            b_key = known.get("board_key") or "ts_state_board"
            s_key = known.get("academic_stage") or "completed"
            board_lbl = known.get("board_label") or "your board"
            max_m = get_max_marks(b_key, s_key)

            if s_key == "1st_year":
                text = (
                    f"Got it! You're currently studying Intermediate 1st Year under {board_lbl}. "
                    f"Let's start with your academic performance. What marks have you scored in your Intermediate 1st Year examinations?"
                )
                chips = [f"{int(max_m * 0.9)} out of {max_m}", f"{int(max_m * 0.94)} out of {max_m}", f"{int(max_m * 0.98)} out of {max_m}"] if max_m > 100 else ["85%", "92%", "96%"]
            elif s_key == "2nd_year":
                text = (
                    f"Perfect! Since you're currently studying Intermediate 2nd Year, let's use your completed "
                    f"first-year academic performance for a preliminary assessment. What marks did you score in Intermediate 1st Year?"
                )
                chips = [f"{int(max_m * 0.9)} out of {max_m}", f"{int(max_m * 0.94)} out of {max_m}", f"{int(max_m * 0.98)} out of {max_m}"] if max_m > 100 else ["85%", "92%", "96%"]
            else:
                text = (
                    f"Great! Since you've already completed Intermediate, we'll use your actual final examination "
                    f"marks for the assessment. Let's get your final Intermediate score."
                )
                chips = [f"{int(max_m * 0.85)} out of {max_m}", f"{int(max_m * 0.92)} out of {max_m}", f"{int(max_m * 0.96)} out of {max_m}"] if max_m > 100 else ["85%", "92%", "96%"]

            card = build_counsellor_marks_card(
                board_key=b_key, stage_key=s_key, max_marks=max_m, board_label=board_lbl, default_val=known.get("raw_marks")
            )
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        # Step 4: Admission route selection (if not already known)
        if not has_route:
            state["waiting_for"] = "route"
            raw_m = known.get("raw_marks")
            max_m = known.get("max_marks") or get_max_marks(known.get("board_key"), known.get("academic_stage"))
            pct = known.get("percent")
            score_str = f"**{int(raw_m) if raw_m == int(raw_m) else raw_m}/{max_m} ({pct}%)**" if raw_m and max_m > 100 else f"**{pct}%**"
            proj_str = " (projected based on 1st-year performance)" if known.get("is_projected") else ""
            prog_title = "B.Tech" if (said.get("generic_btech") or known.get("generic_btech") or not prog_key) else fees.clean_program_name(prog_key, specialization=known.get("specialization"), user_text=known.get("program_raw"))

            text = (
                f"Thank you! Based on your academic score of {score_str}{proj_str}, you have a strong academic profile for SR University.\n\n"
                f"Which admission route are you planning to use for {prog_title}?\n"
                f"Select your admission pathway so we can factor in any entrance rank scholarships."
            )
            card = build_counsellor_route_card(selected_route=known.get("admission_route"))
            chips = ["TG EAPCET", "AP EAPCET", "JEE Main", "SR University SRSAT", "Other", "Not decided yet"]
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        # Step 4b: Entrance rank (skippable) if entrance route selected but score missing
        if (
            known.get("admission_route") in ("tg_eapcet", "ap_eapcet", "jee_main")
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

        # Step 5: Programme selection (if not already known)
        if not has_prog:
            state["waiting_for"] = "program"
            text = (
                "Which B.Tech programme are you interested in?\n"
                "Choose an engineering programme or branch to view your exact fee and scholarship breakdown."
            )
            card = build_counsellor_program_card(selected_program=known.get("program"), step_label="Step 5: Preferred Programme")
            chips = ["B.Tech CSE", "B.Tech AI & Robotics", "B.Tech ECE", "B.Tech EEE", "B.Tech Mechanical", "B.Tech Civil"]
            return {"action": "ask", "text": text, "chips": chips, "cards": [card], "state": state}

        # Step 6: All details known -> Calculate!
        state["waiting_for"] = "done"
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
        if known.get("eapcet_rank") is not None:
            args["eapcet_rank"] = known["eapcet_rank"]
        if known.get("jee_percentile") is not None:
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
                "route_label": known.get("route_label") or "Direct Merit / 10+2 Marks",
                "eapcet_rank": known.get("eapcet_rank"),
                "jee_percentile": known.get("jee_percentile"),
                "ib_score": known.get("ib_score"),
                "program": prog_key,
                "program_name": prog_name,
                "specialization": known.get("specialization"),
                "program_raw": known.get("program_raw"),
                "re_query": is_re_query,
            },
        }

    # =========================================================================
    # STANDARD FEE FORM INTAKE (for generic university fee structure queries)
    # =========================================================================
    if not prog_key:
        if "program" in asked:
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
            calc_pct = pct_val or round((raw_val / 1000.0) * 100, 1)
            state["percent"] = calc_pct
            if raw_val:
                state["pending_raw_marks"] = raw_val

            res = fees.calculate_fee("btech_cse", percent=calc_pct, board=known.get("board") or "state_board")
            waiver = res.get("scholarship_percent", 0)
            net_tuition = res.get("tuition_first_year_after_scholarship", "₹3,40,000")
            per_sem = res.get("per_semester_after_scholarship", "₹1,70,000")
            savings = res.get("saving_first_year", "₹0")

            marks_str = f"**{raw_val} marks** (~{calc_pct}% in TS/AP Intermediate out of 1000)" if raw_val else f"**{calc_pct}%**"
            if waiver > 0:
                text = (
                    f"With {marks_str}, you qualify for a **{waiver}% Merit Scholarship** on your tuition!\n\n"
                    f"For example, in our flagship **B.Tech Computer Science & Engineering (CSE)** (standard tuition ₹3,40,000/year):\n"
                    f"• **Net Tuition**: **{net_tuition} per year** ({per_sem} per semester)\n"
                    f"• **Scholarship Savings**: You save **{savings} per year**\n\n"
                    f"Which degree programme or engineering branch are you interested in exploring? "
                    f"You can choose a programme below or use the interactive assessment form."
                )
                if raw_val and not said.get("max_marks"):
                    text += f"\n\n*(Note: Calculated assuming {raw_val} out of 1000 in Intermediate State Board. If your score is out of 600 or CBSE, please let me know your board or maximum marks).*"
            else:
                text = (
                    f"With {marks_str}, you meet the official 50% minimum eligibility requirement for B.Tech admission at SR University!\n\n"
                    f"Standard tuition for **B.Tech CSE** is ₹3,40,000/year (₹1,70,000/semester). "
                    f"We also offer B.Tech Core branches (Mechanical, Civil, EEE) at ₹2,00,000/year, and BBA/BCA at ₹1,50,000/year.\n\n"
                    f"Which programme or branch would you like to explore?"
                )
            chips = ["B.Tech CSE", "B.Tech AI and Robotics", "B.Tech ECE", "B.Sc Agriculture", "BBA"]
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
        pct_1000 = round(raw_val / 10.0, 1)
        res = fees.calculate_fee(prog_key, percent=pct_1000, board=known.get("board") or "state_board")
        waiver = res.get("scholarship_percent", 0)
        net_tuition = res.get("tuition_first_year_after_scholarship", standard)
        per_sem = res.get("per_semester_after_scholarship", "")
        savings = res.get("saving_first_year", "₹0")
        waiver_msg = (
            f"qualify for a **{waiver}% Merit Scholarship** (Net tuition: **{net_tuition}/year** [{per_sem}/sem], saving {savings}/yr)"
            if waiver > 0
            else "meet the official 50% minimum eligibility criteria"
        )
        text = (
            f"Based on **{raw_val} marks** (assuming out of 1000 in Intermediate State Board = **{pct_1000}%**), you {waiver_msg} for **{name}**.\n\n"
            f"Please confirm your maximum/total marks (e.g., out of 1000 for Intermediate State Board, or out of 600) or select below to view your full fee structure:"
        )
        chips = [
            f"{raw_val} out of 1000 ({pct_1000}%)",
            f"{raw_val} out of 600",
            f"{pct_1000}%",
            "Hostel details",
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

