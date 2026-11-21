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

from app.services.card_service import build_fee_scholarship_form_card
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
    r"comparison|difference|cheaper|cheapest|last\s+date|due\s+date|deadline|exam\s+fee|caution|deposit)\b",
    re.IGNORECASE,
)

_STATE_BOARD = re.compile(
    r"\b(?:state\s*board|bie(?:ap|ts)?|board\s+of\s+intermediate|intermediate\s+board|inter\s+board|"
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
    if fees.find_program(message or ""):
        out["program"] = message
    elif fees._is_generic_btech(low) or re.search(r"\b(?:b\.?\s?tech|btech|engineering)\b", low):
        out["generic_btech"] = True

    if _IB.search(message or ""):
        out["board"] = "ib"
        out["board_label"] = "IB"
    elif _CBSE.search(message or "") or _ICSE.search(message or "") or _NIOS.search(message or ""):
        out["board"] = "cbse"
        if _ICSE.search(message or "") and not _CBSE.search(message or ""):
            out["board_label"] = "ICSE"
        elif _NIOS.search(message or "") and not _CBSE.search(message or ""):
            out["board_label"] = "NIOS"
        else:
            out["board_label"] = "CBSE"
    elif _STATE_BOARD.search(message or ""):
        out["board"] = "state_board"
        if re.search(r"\b(?:ts|tg|telangana)\b", low):
            out["board_label"] = "Telangana State Board"
        elif re.search(r"\b(?:ap|andhra)\b", low):
            out["board_label"] = "AP State Board"
        elif re.search(r"\b(?:other|maharashtra|karnataka|tamil|kerala|up|bihar|mp|rajasthan|delhi|punjab|haryana|bengal|gujarat)\b", low):
            out["board_label"] = "Other State Board across India"
        else:
            out["board_label"] = "Telangana / AP State Board"

    # Percentage parsing
    m = re.search(r"(?<![\d.])(\d{2}(?:\.\d+)?)\s*(?:%|percent|per\s*cent|percentage)", low)
    marks = re.search(r"(?<!\d)(\d{3,4})\s*(?:marks|/\s*1000|out\s+of\s+1000)", low)
    if m and float(m.group(1)) <= 100:
        out["percent"] = float(m.group(1))
    elif marks and int(marks.group(1)) <= 1000:
        out["percent"] = round(int(marks.group(1)) / 10, 2)

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

    # JEE Main percentile
    m = re.search(r"\bjee(?:\s+main)?\D{0,25}(\d{1,2}(?:\.\d+)?)\b|(\d{1,2}(?:\.\d+)?)\s*(?:percentile|%ile)", low)
    if m:
        out["jee_percentile"] = float(m.group(1) or m.group(2))

    # IB score
    m = re.search(r"\bib\D{0,15}(\d{2})\b|(?<!\d)(\d{2})\s*(?:/\s*45|points|out\s+of\s+45)", low)
    if m and 0 < int(m.group(1) or m.group(2)) <= 45:
        out["ib_score"] = int(m.group(1) or m.group(2))
        out["board"] = "ib"

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
    return out


def _bare_number(message: str):
    m = re.fullmatch(r"\s*(\d{1,6}(?:\.\d+)?)\s*%?\s*", message or "")
    return float(m.group(1)) if m else None


def is_fee_enquiry(message: str) -> bool:
    return bool(_FEE_WORDS.search(message or "")) and not _OTHER_FEE_TOPIC.search(message or "")


def decide(message: str, profile: dict, intake: dict | None) -> dict | None:
    """What to do with a fee enquiry. Multi-step intake with All India 10+2 boards and FeeScholarshipForm card."""
    intake = dict(intake or {})
    said = parse_details(message)
    active = bool(intake) and int(intake.get("turns", 0)) < 5
    number = _bare_number(message)

    if not is_fee_enquiry(message):
        # Only a reply to our own question continues the intake (a number, a board, "no JEE"...).
        reply_like = bool(said.keys() - {"generic_btech"}) or number is not None
        if not (active and reply_like):
            return None

    if active and number is not None:
        # A bare number answers the question we asked last.
        waiting = intake.get("waiting_for")
        if waiting == "rank":
            said.setdefault("eapcet_rank" if number > 100 else "jee_percentile",
                            int(number) if number > 100 else number)
        elif waiting == "ib" and number <= 45:
            said.setdefault("ib_score", int(number))
        elif 35 <= number <= 100:
            said.setdefault("percent", number)
        elif 100 < number <= 1000:
            said.setdefault("percent", round(number / 10, 2))
        elif number > 1000:
            said.setdefault("eapcet_rank", int(number))

    # Known facts aggregation
    known = {k: profile.get(k) for k in ("percent", "board", "eapcet_rank", "jee_percentile", "ib_score")
             if profile.get(k) not in (None, "")}
    known.update({k: v for k, v in intake.items() if k in (
        "program", "percent", "board", "board_label", "eapcet_rank", "jee_percentile", "ib_score", "no_entrance")})
    known.update({k: v for k, v in said.items() if k != "generic_btech"})

    if said.get("program"):
        known["program"] = said["program"]
    elif not known.get("program") and profile.get("program_interest") and not said.get("generic_btech"):
        known["program"] = profile["program_interest"]

    asked = set(intake.get("asked", []))
    state = {**{k: v for k, v in known.items() if k != "standard_only"}, "asked": sorted(asked),
             "turns": int(intake.get("turns", 0)) + 1}

    prog_key = fees.find_program(str(known.get("program") or ""))

    # -------------------------------------------------------------------------
    # STEP 1: If Course is not known, ask for Course and Board first
    # -------------------------------------------------------------------------
    if not prog_key:
        if "program" in asked:
            return None  # Asked once already; let general agent assist
        state["asked"] = sorted(asked | {"program"})
        state["waiting_for"] = "program"
        text = (
            "To calculate your fee and check your eligible scholarship (up to 40% waiver), "
            "please select or tell me your **course** and your **10+2 / Intermediate Board** "
            "(Telangana, AP, CBSE, ICSE, Other State Boards across India, NIOS, or IB).\n\n"
            "In the next step, you can enter your 10+2 marks or entrance rank. "
            "You can also use the interactive assessment form below."
        )
        chips = ["B.Tech CSE", "B.Tech AI & Robotics", "B.Tech ECE", "BBA", "B.Sc Agriculture"]
        form_card = build_fee_scholarship_form_card()
        return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    known["program"] = prog_key
    state["program"] = prog_key
    prog = fees.load_data()["programs"][prog_key]
    level = prog.get("level", "ug")
    name = prog["name"]

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
            "state": None,
            "details": {
                "board": _BOARD_LABEL.get(known.get("board") or "", ""),
                "board_label": known.get("board_label"),
                "no_entrance": known.get("no_entrance"),
            },
        }

    # "Just the standard fee" / "skip"
    if (said.get("standard_only") and not has_score) or said.get("skip"):
        return calculate()

    # -------------------------------------------------------------------------
    # STEP 2: Course is known, but 10+2 Board is NOT known (for UG courses)
    # -------------------------------------------------------------------------
    if level != "pg" and not known.get("board"):
        if "board" in asked:
            return calculate()  # Asked once already, don't trap student
        state["asked"] = sorted(asked | {"board"})
        state["waiting_for"] = "board"
        text = (
            f"For **{name}**, scholarships are calculated based on your 10+2 board and marks/rank.\n\n"
            f"Which **10+2 / Intermediate Board** did you study under?\n"
            f"• **Telangana State Board (TS BIE)**\n"
            f"• **AP State Board (BIEAP)**\n"
            f"• **CBSE / ICSE / NIOS**\n"
            f"• **Other State Boards across India** (Maharashtra, Karnataka, Tamil Nadu, UP, Bihar, etc.)\n"
            f"• **IB (International Baccalaureate)**\n\n"
            f"In the next step, I'll ask for your marks or entrance rank to calculate your exact scholarship and fee. "
            f"You can also use the assessment form below."
        )
        chips = [
            "Telangana State Board",
            "AP State Board",
            "CBSE / ICSE",
            "Other State Board across India",
            "IB",
        ]
        form_card = build_fee_scholarship_form_card(selected_program=prog_key)
        return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    # -------------------------------------------------------------------------
    # STEP 3: Course and Board are known, but Marks / Rank are NOT known
    # -------------------------------------------------------------------------
    if not has_score:
        if "marks" in asked:
            return calculate()  # Asked once; proceed with standard fee
        state["asked"] = sorted(asked | {"marks"})
        board_disp = known.get("board_label") or _BOARD_LABEL.get(known.get("board"), "your board")
        board_card_key = _board_card_key(known.get("board"), known.get("board_label"))

        if level == "pg":
            state["waiting_for"] = "percent"
            text = (
                f"For **{name}**, please provide your qualifying degree percentage "
                f"(e.g. B.Tech / B.Sc / BBA percentage) to calculate your fee and scholarship."
            )
            chips = ["Degree 75%", "Degree 85%", "Just the standard fee"]
        elif known.get("board") == "ib":
            state["waiting_for"] = "ib"
            text = (
                f"Got it! For **{name}** under **International Baccalaureate (IB)**:\n"
                f"What is your IB Diploma score (points out of 45)? The IB scholarship slabs use points out of 45."
            )
            chips = ["30 points", "34 points", "38 points", "Just the standard fee"]
        else:
            state["waiting_for"] = "percent"
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

        form_card = build_fee_scholarship_form_card(selected_program=prog_key, selected_board=board_card_key)
        return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    # -------------------------------------------------------------------------
    # STEP 4: Only an entrance score given: board marks may give a higher scholarship
    # -------------------------------------------------------------------------
    if (level != "pg" and known.get("percent") is None and not known.get("ib_score")
            and "marks" not in asked and not known.get("skip")):
        state["asked"] = sorted(asked | {"marks"})
        state["waiting_for"] = "percent"
        board_disp = known.get("board_label") or _BOARD_LABEL.get(known.get("board"), "your board")
        text = (
            f"Thanks! What are your Intermediate / 12th marks for **{name}** under **{board_disp}**? "
            f"Board marks can also qualify for scholarships up to 40%, and the highest scholarship is always applied."
        )
        chips = ["85% in 10+2", "92% in 10+2", "Skip, use my entrance score"]
        form_card = build_fee_scholarship_form_card(
            selected_program=prog_key,
            selected_board=_board_card_key(known.get("board"), known.get("board_label")),
        )
        return {"action": "ask", "text": text, "chips": chips, "cards": [form_card], "state": state}

    # -------------------------------------------------------------------------
    # STEP 5: All necessary details are known -> Calculate!
    # -------------------------------------------------------------------------
    return calculate()
