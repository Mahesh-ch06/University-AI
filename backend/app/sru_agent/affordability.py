"""Affordability and special concessions multi-step conversational engine.

When a student mentions financial difficulty or high fees (e.g. "i can't afford that much fee",
"too expensive", "financial problem"):
1. Reassures the student warmly by name ({user_name}).
2. Explains that SR University offers up to 40% merit scholarships, 20 special-category concessions,
   and semester-wise payment.
3. Promises: "I will be asking you some questions, answer them, and at last I will let you know your
   final net fee after all concessions and deductions."
4. Guides the student through:
   - Step 1: Course & Academic Score (10+2 marks % or entrance rank).
   - Step 2: Checking the official special-category concessions.
   - Step 3: Consolidated net fee calculation (merit + special concessions deduction),
     explaining semester-wise payment; loans are referred to the Admissions Office (not on the fee circular).
"""

from __future__ import annotations

import re
from app.services.card_service import build_counsellor_program_card
from typing import Any

from . import fees


def _concession_count() -> int:
    return len(fees.load_data().get("special_concessions", []))


def _concession_lines() -> str:
    """Every concession a student can claim, from the fee policy, grouped by yearly amount (never a partial list)."""
    groups: dict[int, list[str]] = {}
    for c in fees.load_data().get("special_concessions", []):
        if c.get("selectable", True):
            groups.setdefault(int(c["amount"]), []).append(c["label"])
    return "\n".join(f"• **{fees.inr(a)} a year:** " + "; ".join(labels)
                      for a, labels in sorted(groups.items(), reverse=True))


AFFORDABILITY_REGEX = re.compile(
    r"\b("
    r"can'?t\s+(?:afford|efford|effecot|affort|pay|manage)|"
    r"cannot\s+(?:afford|pay|manage)|"
    r"cant\s+(?:afford|efford|effecot|affort|pay|manage)|"
    r"unable\s+to\s+afford|hard\s+to\s+afford|not\s+able\s+to\s+afford|"
    r"fee\s+is\s+(?:too|very|quite|so)\s+high|fees\s+(?:are|is)\s+(?:too|very|quite|so)\s+high|"
    r"fee\s+too\s+high|fees\s+too\s+high|"
    r"too\s+expensive|very\s+expensive|costly|pricey|"
    r"financial\s+problem|financial\s+problems|financial\s+issue|financial\s+issues|"
    r"financial\s+crisis|financial\s+hardship|financial\s+constraint|financial\s+trouble|"
    r"poor\s+family|poor\s+background|middle\s+class\s+family|lower\s+middle\s+class|financially\s+weak|"
    r"can\s+i\s+get\s+(?:any\s+)?discount|fee\s+discount|reduce\s+(?:the\s+)?fee|less\s+fee|concession\s+for\s+poor|"
    r"any\s+fee\s+reduction|lower\s+the\s+fee|is\s+there\s+any\s+concession|need\s+financial\s+help|financial\s+aid"
    r")\b",
    re.IGNORECASE,
)


# How students describe each official category (keyword lists only). Labels and amounts always come
# from the fee policy (fees.load_data()["special_concessions"]), never from this file.
_CONCESSION_KEYWORDS = {
    'orphan': ['orphan', 'lost both parents', 'lost parents', 'no parents', 'both parents passed'],
    'sports_international': ['international sports', 'international player', 'sports international'],
    'staff_child': ['staff child', 'employee child', 'faculty child', 'sru employee'],
    'disability': ['disability', 'pwd', 'handicap', 'handicapped', 'differently abled', 'physical disability'],
    'single_parent': ['single parent', 'divorce', 'divorced', 'single mother', 'single father', 'only mother', 'only father'],
    'defence': ['defence', 'defense', 'crpf', 'martyr', 'army', 'navy', 'air force', 'paramilitary', 'soldier', 'armed forces'],
    'sibling': ['sibling', 'brother', 'sister', 'sibling at sru', 'studying at sru'],
    'andhra_pradesh': ['andhra', 'ap resident', 'andhra pradesh', 'from ap', 'from andhra'],
    'girl_child_outside_telangana': ['girl outside telangana', 'girl student outside', 'girl non ts', 'non-ts girl'],
    'only_girl_child_telangana': ['only girl child', 'girl child telangana', 'girl child ts', 'single girl child'],
    'sports_national': ['national sports', 'sports national', 'national level', 'state sports', 'athlete', 'sports'],
    'state_police': ['police', 'state police', 'police personnel', 'cop'],
    'sr_junior_college': ['sr junior college', 'sr college', 'sr junior'],
    'alumni': ['alumni', 'alumnus'],
    'ncc_c': ['ncc', 'ncc c', "ncc 'c'"],
    'padma_gallantry': ['padma', 'gallantry', 'j&k migrant', 'kashmiri migrant', 'migrant'],
    'non_local': ['other states', 'outside telangana and andhra', 'non local', 'north india', 'other state'],
    'lateral_entry': ['lateral entry', 'ecet', 'diploma'],
    'international': ['international student', 'foreign student', 'nri'],
}


def _official_categories() -> list[dict]:
    """The circular's concessions a student can claim, with the keywords students use for them."""
    out = []
    for c in fees.load_data().get("special_concessions", []):
        if c.get("selectable", True):
            out.append({"key": c["key"], "label": c["label"], "amount": int(c["amount"]),
                        "keywords": _CONCESSION_KEYWORDS.get(c["key"], [c["label"].lower()])})
    return out


def is_affordability_query(message: str) -> bool:
    """Returns True if message mentions fee affordability or financial constraints."""
    if not message:
        return False
    return bool(AFFORDABILITY_REGEX.search(message))


def match_all_special_concessions(message: str) -> list[dict]:
    """Matches a user message against all applicable categories from SR University's official special concessions."""
    low = (message or "").lower()
    if re.search(r"\b(?:none|no|neither|na|n/?a|not\s+applicable|none\s+of\s+these|nothing)\b", low):
        return []

    matched = []
    seen_keys = set()
    cats = {c["key"]: c for c in _official_categories()}
    # where the student lives: "I'm from Delhi" -> students from outside TG and AP; "from AP" -> Andhra Pradesh
    from . import compound
    if re.search(r"\b(?:from|in|live\s+in)\s+(?:ap|a\.p\.?|andhra(?:\s+pradesh)?)\b", low) and "andhra_pradesh" in cats:
        matched.append(cats["andhra_pradesh"]); seen_keys.add("andhra_pradesh")
    elif (compound.from_other_state(message) or re.search(r"\banother\s+state\b|\bother\s+state\b", low)) \
            and "non_local" in cats:
        matched.append(cats["non_local"]); seen_keys.add("non_local")
    for cat in _official_categories():
        if cat["key"] in seen_keys:
            continue
        for kw in cat["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b" if len(kw) <= 5 else re.escape(kw), low):
                matched.append(cat)
                seen_keys.add(cat["key"])
                break
    return matched


def match_special_concession(message: str) -> dict | None:
    """Matches a user message against SR University's official special concessions, returning the highest concession."""
    all_matched = match_all_special_concessions(message)
    if not all_matched:
        return None
    # Pick the highest benefit category
    best = max(all_matched, key=lambda c: c["amount"])
    if len(all_matched) > 1:
        best = dict(best)
        best["all_eligible"] = all_matched
    return best


def _extract_percent(message: str) -> float | None:
    """Extracts a percentage or score out of 1000 from message."""
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:%|percent|marks|\/1000)?", message.lower())
    if m:
        val = float(m.group(1))
        if 100 < val <= 1000:
            return val / 10.0
        if 35 <= val <= 100:
            return val
    return None


def _extract_board(message: str) -> str:
    """Maps board mention to fee board key."""
    low = (message or "").lower()
    if "cbse" in low or "icse" in low or "isc" in low or "nios" in low:
        return "cbse"
    if "ib" in low or "international baccalaureate" in low:
        return "ib"
    return "state_board"


def process_affordability_flow(
    message: str,
    profile: dict[str, Any],
    conv_state: dict[str, Any],
) -> dict[str, Any] | None:
    """Processes the multi-step affordability and concession workflow.

    Returns response dictionary with text, cards, suggestions, and updated new_state,
    or None if this flow does not handle the message.
    """
    user_name = profile.get("name") or conv_state.get("user_name") or ""
    greeting_lead = f"I understand your concern, {user_name}!" if user_name else "I completely understand your concern!"

    flow_state = conv_state.get("affordability_flow")

    # -------------------------------------------------------------------------
    # Entry Point: User expressed affordability concern
    # -------------------------------------------------------------------------
    if not flow_state and is_affordability_query(message):
        # Check what we already know from state or profile
        existing_prog = conv_state.get("fee_flow_prog") or conv_state.get("program") or profile.get("program_interest")
        intake_dict = conv_state.get("fee_intake") or {}
        existing_percent = intake_dict.get("percent") or profile.get("twelfth_percent")
        existing_board = intake_dict.get("board") or "state_board"

        # If we already know their course AND marks, jump straight to Step 2!
        if existing_prog and existing_percent:
            calc = fees.calculate_fee(program=existing_prog, percent=existing_percent, board=existing_board)
            sch_pct = calc.get("scholarship_percent", 0)
            saving = calc.get("saving_first_year", "₹0")
            prog_name = calc.get("program", "your course")

            reply_text = (
                f"{greeting_lead} At SR University, no deserving student is held back by financial constraints. "
                f"We offer extensive merit scholarships (up to 40% tuition waiver) as well as {_concession_count()} special-category "
                f"concessions, and fees are paid semester by semester.\n\n"
                f"Based on your academic score, you qualify for a **{sch_pct}% Merit Scholarship** on **{prog_name}**, "
                f"saving **{saving}/year** on tuition!\n\n"
                f"**Could a special concession lower it further?** Tell me if any of these applies to you "
                f"(each is approved once your proof is verified):\n"
                + _concession_lines()
            )
            chips = [
                "Single parent / Divorced",
                "Lost both parents (Orphan)",
                "Child of Defence / CRPF",
                "Sibling at SR University",
                "From another state",
                "From Andhra Pradesh",
                "None of these",
            ]
            new_affordability = {
                "step": "awaiting_concession",
                "program": existing_prog,
                "percent": existing_percent,
                "board": existing_board,
            }
            return {
                "text": reply_text,
                "cards": [],
                "suggestions": chips,
                "new_state": {**conv_state, "affordability_flow": new_affordability},
            }

        # Otherwise, initiate Step 1 (Academics: Course + Marks)
        prog_key = fees.find_program(message) or existing_prog
        level = "ug"
        if prog_key:
            p_dict = fees.load_data()["programs"].get(prog_key, {})
            level = p_dict.get("level", "ug")

        reply_text = (
            f"{greeting_lead} At SR University, no deserving student is held back by financial constraints. "
            f"We offer generous merit scholarships (up to 40% tuition fee waiver) along with {_concession_count()} special-category "
            f"concessions, and fees are paid semester by semester.\n\n"
            f"**Step 1 of 2: Academic Programme & Marks**\n"
            f"Please select or tell me:\n"
            f"1. Which **course / programme** are you planning to study (e.g. B.Tech CSE, BBA, BCA, MBA)?\n"
            f"2. What are your **10+2 marks (%)** or entrance rank (JEE / EAPCET)?"
        )
        chips = ["B.Tech CSE", "B.Tech AI & Robotics", "B.Tech ECE", "BBA", "B.Sc Agriculture"] if level != "pg" else ["MBA", "MCA", "M.Tech CSE"]

        new_affordability = {
            "step": "awaiting_academics",
            "program": prog_key,
            "level": level,
        }
        return {
            "text": reply_text,
            # v4.13.0: the programme's step card (the older consolidated form is no longer shown)
            "cards": [] if prog_key else [build_counsellor_program_card(step_label="Preferred Programme")],
            "suggestions": chips,
            "new_state": {**conv_state, "affordability_flow": new_affordability},
        }

    # -------------------------------------------------------------------------
    # Active State: awaiting_academics
    # -------------------------------------------------------------------------
    if flow_state and flow_state.get("step") == "awaiting_academics":
        detected_prog = fees.find_program(message) or flow_state.get("program") or "btech_cse"
        detected_percent = _extract_percent(message)
        detected_board = _extract_board(message)

        p_dict = fees.load_data()["programs"].get(detected_prog, {})
        level = p_dict.get("level", "ug")

        if not detected_percent:
            # Re-prompt for marks
            prog_name = p_dict.get("name", detected_prog)
            text = (
                f"Got it for **{prog_name}**! What are your Intermediate / 10+2 marks (%) or entrance rank?\n\n"
                f"This will allow me to apply your merit scholarship (up to 40% waiver) before we check special concessions."
            )
            chips = ["90% marks", "85% marks", "80% marks", "75% marks", "EAPCET rank 15000"]
            new_affordability = {
                "step": "awaiting_academics",
                "program": detected_prog,
                "level": level,
            }
            return {
                "text": text,
                "cards": [],
                "suggestions": chips,
                "new_state": {**conv_state, "affordability_flow": new_affordability},
            }

        # Marks are now known -> Calculate merit waiver and proceed to Step 2 (Concessions)
        calc = fees.calculate_fee(program=detected_prog, percent=detected_percent, board=detected_board)
        sch_pct = calc.get("scholarship_percent", 0)
        saving = calc.get("saving_first_year", "₹0")
        prog_name = calc.get("program", "your course")

        text = (
            f"Great news{', ' + user_name if user_name else ''}! Based on your {detected_percent}% score, "
            f"you qualify for a **{sch_pct}% Merit Scholarship** on **{prog_name}**, saving **{saving}/year** on tuition!\n\n"
            f"**Could a special concession lower it further?** Tell me if any of these applies to you "
            f"(each is approved once your proof is verified):\n\n"
            + _concession_lines()
        )
        chips = [
            "Single parent / Divorced",
            "Lost both parents (Orphan)",
            "Child of Defence / CRPF",
            "Sibling at SR University",
            "From another state",
            "From Andhra Pradesh",
            "None of these",
        ]
        new_affordability = {
            "step": "awaiting_concession",
            "program": detected_prog,
            "percent": detected_percent,
            "board": detected_board,
        }
        return {
            "text": text,
            "cards": [],
            "suggestions": chips,
            "new_state": {**conv_state, "affordability_flow": new_affordability},
        }

    # -------------------------------------------------------------------------
    # Active State: awaiting_concession
    # -------------------------------------------------------------------------
    if flow_state and flow_state.get("step") == "awaiting_concession":
        matched_concession = match_special_concession(message)
        prog_key = flow_state.get("program") or "btech_cse"
        percent = flow_state.get("percent")
        board = flow_state.get("board") or "state_board"

        calc = fees.calculate_fee(program=prog_key, percent=percent, board=board)
        base_str = calc.get("tuition_first_year", "₹3,40,000")
        base_int = int(re.sub(r"[^\d]", "", base_str)) if base_str else 340000
        sch_pct = calc.get("scholarship_percent", 0)
        tuition_after_merit_str = calc.get("tuition_first_year_after_scholarship", "0")
        tuition_after_merit_int = int(re.sub(r"[^\d]", "", tuition_after_merit_str)) if tuition_after_merit_str else base_int
        merit_saving_int = base_int - tuition_after_merit_int

        concession_amount = matched_concession["amount"] if matched_concession else 0
        concession_label = matched_concession["label"] if matched_concession else "None"

        # One engine: the concession is deducted by fees.calculate_fee, never by maths here.
        with_conc = (fees.calculate_fee(program=prog_key, percent=percent, board=board,
                                        concessions=[matched_concession.get("key") or concession_label])
                     if matched_concession else calc)
        final_net_annual_int = max(0, tuition_after_merit_int - concession_amount)
        total_savings_int = merit_saving_int + concession_amount
        prog_name = calc.get("program", prog_key)

        if matched_concession:
            all_elig = matched_concession.get("all_eligible")
            if all_elig and len(all_elig) > 1:
                labels = ", ".join(c["label"] for c in all_elig)
                concession_bullet = (
                    f"• **Special Concession ({concession_label})**: -{fees.inr(concession_amount)} "
                    f"*(applied highest benefit category among your eligible categories: {labels})*\n"
                )
            else:
                concession_bullet = f"• **Special Concession ({concession_label})**: -{fees.inr(concession_amount)}\n"
        else:
            concession_bullet = "• **Special Concession**: Standard merit deduction applied (no additional special category claimed)\n"

        final_text = (
            f"Here is your final net fee breakdown after all considered deductions{', ' + user_name if user_name else ''}:\n\n"
            f"### 🎓 {prog_name} (Academic Year 2027-28)\n"
            f"• **Standard Annual Tuition**: {fees.inr(base_int)}\n"
            f"• **Merit Scholarship ({sch_pct}%)**: -{fees.inr(merit_saving_int)} ({calc.get('scholarship_basis_text')})\n"
            f"{concession_bullet}"
            f"• **Net Annual Tuition**: **{fees.inr(final_net_annual_int)}**\n"
            f"• **Semester 1 payable**: **{with_conc['sem1_total_payable']}** *(tuition + enrollment, other and Year-1 exam fees)*\n"
            f"• **Semester 2 payable**: **{with_conc['sem2_total_payable']}** *(tuition only)*\n"
            f"• **First-year total**: **{with_conc['first_year_total_payable']}** *(application form {with_conc['application_fee']} paid separately)*\n"
            f"• **Total Annual Savings**: **{fees.inr(total_savings_int)}**\n\n"
            f"---\n\n"
            f"**Paying it:** fees are paid semester by semester, so you never pay the whole year at once "
            f"(Semester 1 {with_conc['sem1_total_payable']}, Semester 2 {with_conc['sem2_total_payable']}). Education "
            f"loans and any other instalment arrangement aren't on the fee circular, so the Admissions Office "
            f"(833 100 3030) can guide you on them.\n\n"
            f"Would you like me to connect you with an admissions counsellor?"
        )

        fee_card_data = dict(with_conc)
        fee_card_data["special_concession_applied"] = concession_label if matched_concession else None
        fee_card_data["special_concession_amount"] = fees.inr(concession_amount) if concession_amount else None

        cards = [{"type": "calculate_fee", "data": fee_card_data}]
        chips = [
            "Talk to Admissions Counselor",
            "Hostel room & mess fees",
            "Campus visit",
            "Change programme",
        ]

        return {
            "text": final_text,
            "cards": cards,
            "suggestions": chips,
            "new_state": {
                **conv_state,
                "affordability_flow": None,
                "fee_flow_prog": prog_key,
                "fee_flow_state": "completed",
            },
        }

    return None
