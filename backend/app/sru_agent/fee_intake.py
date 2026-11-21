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
    r"comparison|difference|cheaper|cheapest|last\s+date|due\s+date|deadline|exam\s+fee|caution|deposit|"
    r"other\s+fees?|other\s+academic(?:\s*/\s*university|\s+university)?\s+charges?|other\s+charges?|annual\s+charges?|"
    r"university\s+charges?|additional\s+fees?|additional\s+charges?|enrolment\s+fee|enrollment\s+fee|application\s+form\s+fee|"
    r"specialisation\s+fee|specialization\s+fee|phd\s+fee|"
    r"fees?\s+(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee)|"
    r"(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee))\b",
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

    # CGPA parsing (e.g. "9.2 CGPA", "CGPA 8.8")
    cgpa_m = re.search(r"\b(?:cgpa\s*[:=]?\s*(\d{1,2}(?:\.\d+)?)|(\d{1,2}(?:\.\d+)?)\s*cgpa)\b", low)
    if cgpa_m:
        cgpa_val = float(cgpa_m.group(1) or cgpa_m.group(2))
        if 0 < cgpa_val <= 10.0:
            out["cgpa"] = cgpa_val
            out["percent"] = round(cgpa_val * 9.5, 2)

    # Explicit fraction parsing (e.g. "890/1000", "890 out of 1000", "450/600", "920 marks out of 1000")
    frac = re.search(r"(?<![\d.])(\d{2,4})\s*(?:marks\s+)?(?:/|out\s+of)\s*(\d{3,4})", low)
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

    # Raw 3-digit marks without maximum marks specified (e.g. "890 marks", "scored 890")
    if not out.get("percent"):
        raw_marks_m = re.search(r"\b(?:scored|got|secured|obtained|have)?\s*(\d{3,4})\s*marks\b", low)
        if raw_marks_m and 100 < int(raw_marks_m.group(1)) <= 1000:
            out["needs_marks_confirmation"] = int(raw_marks_m.group(1))

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


_SCORE_OR_MARKS_QUERY = re.compile(
    r"\b(?:\d{2,4}\s*marks?|scored\s+\d{2,4}|got\s+\d{2,4}|secured\s+\d{2,4}|obtained\s+\d{2,4}|"
    r"\d{2,4}\s*(?:/|out\s+of)\s*\d{3,4}|\d{1,2}(?:\.\d+)?\s*%|cgpa\s*[:=]?\s*\d|\d\s*cgpa)\b",
    re.IGNORECASE,
)


def is_fee_enquiry(message: str) -> bool:
    if _OTHER_FEE_TOPIC.search(message or ""):
        return False
    if bool(_FEE_WORDS.search(message or "")):
        return True
    if _SCORE_OR_MARKS_QUERY.search(message or ""):
        return True
    num = _bare_number(message)
    if num is not None and (35 <= num <= 1000):
        return True
    return False


def decide(message: str, profile: dict, intake: dict | None) -> dict | None:
    """What to do with a fee enquiry. Multi-step intake with All India 10+2 boards and FeeScholarshipForm card."""
    intake = dict(intake or {})
    said = parse_details(message)
    active = bool(intake) and int(intake.get("turns", 0)) < 5
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

    if active:
        waiting = intake.get("waiting_for")
        if waiting == "marks_max":
            raw = intake.get("pending_raw_marks")
            if number is not None:
                if number >= (raw or 0) and (raw or 0) > 0:
                    said["percent"] = round((float(raw) / float(number)) * 100, 2)
                elif 35 <= number <= 100:
                    said["percent"] = float(number)
            elif re.search(r"\b(?:1000|thousand|yes|correct|right|inter|intermediate)\b", (message or "").lower()):
                if raw:
                    said["percent"] = round((float(raw) / 1000.0) * 100, 2)
            elif re.search(r"\b600\b", (message or "").lower()):
                if raw:
                    said["percent"] = round((float(raw) / 600.0) * 100, 2)
        elif number is not None:
            # A bare number answers the question we asked last.
            if waiting == "rank":
                said.setdefault("eapcet_rank" if number > 100 else "jee_percentile",
                                int(number) if number > 100 else number)
            elif waiting == "ib" and number <= 45:
                said.setdefault("ib_score", int(number))
            elif 35 <= number <= 100:
                said.setdefault("percent", number)
            elif 100 < number <= 1000:
                # Raw 3-digit score needs confirmation of maximum marks per user requirement
                said["needs_marks_confirmation"] = int(number)
            elif number > 1000:
                said.setdefault("eapcet_rank", int(number))

    # Known facts aggregation
    known = {k: profile.get(k) for k in ("percent", "board", "board_label", "eapcet_rank", "jee_percentile", "ib_score")
             if profile.get(k) not in (None, "")}
    known.update({k: v for k, v in intake.items() if k in (
        "program", "percent", "board", "board_label", "eapcet_rank", "jee_percentile", "ib_score", "no_entrance", "pending_raw_marks")})
    known.update({k: v for k, v in said.items() if k not in ("generic_btech", "needs_marks_confirmation")})

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
                for k_clr in ("percent", "board", "board_label", "eapcet_rank", "jee_percentile", "ib_score", "pending_raw_marks"):
                    known.pop(k_clr, None)
                intake.pop("waiting_for", None)
                intake.pop("pending_raw_marks", None)
                asked = set()
            else:
                asked = set(intake.get("asked", [])) - {"entrance", "program"}
        else:
            asked = set(intake.get("asked", []))
    else:
        if said.get("program"):
            known["program"] = said["program"]
        elif not known.get("program") and profile.get("program_interest") and not said.get("generic_btech"):
            known["program"] = profile["program_interest"]
        asked = set(intake.get("asked", []))

    if intake.get("board"):
        asked |= {"board", "entrance"}
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

    # -------------------------------------------------------------------------
    # CONFIRMATION: Raw 3-digit marks without maximum marks (e.g. "890")
    # -------------------------------------------------------------------------
    if said.get("needs_marks_confirmation") and not known.get("percent") and not has_score:
        raw_val = said["needs_marks_confirmation"]
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

    # -------------------------------------------------------------------------
    # STEP 2 / 3: No marks or scores yet
    # -------------------------------------------------------------------------
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

        # UG: ask for 10+2 board first if not known
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

        # UG: board is known, but marks/rank are not known
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

    # -------------------------------------------------------------------------
    # STEP 4: Only an entrance score given: board marks may give a higher scholarship
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # STEP 5: The board changes the scholarship only for some percentages: ask only then
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # STEP 6: B.Tech / B.Sc Agriculture: an entrance score may give more; ask once
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # STEP 7: All necessary details are known -> Calculate!
    # -------------------------------------------------------------------------
    return calculate()

