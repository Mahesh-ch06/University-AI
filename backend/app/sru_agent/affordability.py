"""Affordability and special concessions multi-step conversational engine.

When a student mentions financial difficulty or high fees (e.g. "i can't afford that much fee",
"too expensive", "financial problem"):
1. Reassures the student warmly by name ({user_name}).
2. Explains that SR University offers up to 40% merit scholarships, 19 special-category concessions,
   and on-campus bank education loan support.
3. Promises: "I will be asking you some questions, answer them, and at last I will let you know your
   final net fee after all concessions and deductions."
4. Guides the student through:
   - Step 1: Course & Academic Score (10+2 marks % or entrance rank).
   - Step 2: Checking official 19 special-category concessions.
   - Step 3: Consolidated net fee calculation (merit + special concessions deduction),
     explaining semester installment options and on-campus SBI / Union Bank loan support.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.card_service import build_fee_scholarship_form_card
from . import fees


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


SPECIAL_CONCESSION_CATEGORIES = [
    {
        "key": "orphan",
        "label": "Lost both parents (Orphan)",
        "amount": 50000,
        "keywords": ["orphan", "lost both parents", "lost parents", "no parents", "both parents passed"],
    },
    {
        "key": "sports_international",
        "label": "International-level sports achiever",
        "amount": 50000,
        "keywords": ["international sports", "international player", "sports international"],
    },
    {
        "key": "staff_child",
        "label": "Child of regular SR University employee",
        "amount": 50000,
        "keywords": ["staff child", "employee child", "faculty child", "sru employee"],
    },
    {
        "key": "disability",
        "label": "Students with 50% or above disability (PwD)",
        "amount": 20000,
        "keywords": ["disability", "pwd", "handicap", "handicapped", "differently abled", "physical disability"],
    },
    {
        "key": "single_parent",
        "label": "Single living parent / Divorced mother",
        "amount": 15000,
        "keywords": ["single parent", "divorce", "divorced", "single mother", "single father", "only mother", "only father"],
    },
    {
        "key": "defence",
        "label": "Child of Defence / CRPF personnel & martyrs",
        "amount": 15000,
        "keywords": ["defence", "defense", "crpf", "martyr", "army", "navy", "air force", "paramilitary", "soldier", "armed forces"],
    },
    {
        "key": "sibling",
        "label": "Sibling currently enrolled at SR University",
        "amount": 15000,
        "keywords": ["sibling", "brother", "sister", "sibling at sru", "studying at sru"],
    },
    {
        "key": "andhra_pradesh",
        "label": "Students from Andhra Pradesh",
        "amount": 15000,
        "keywords": ["andhra", "ap resident", "andhra pradesh", "from ap", "from andhra"],
    },
    {
        "key": "girl_child_outside_telangana",
        "label": "Girl student from outside Telangana",
        "amount": 15000,
        "keywords": ["girl outside telangana", "girl student outside", "girl non ts", "non-ts girl"],
    },
    {
        "key": "only_girl_child_telangana",
        "label": "Only girl child from Telangana",
        "amount": 15000,
        "keywords": ["only girl child", "girl child telangana", "girl child ts", "single girl child"],
    },
    {
        "key": "sports_national",
        "label": "National-level sports achiever",
        "amount": 15000,
        "keywords": ["national sports", "sports national", "national level", "state sports", "athlete", "sports"],
    },
    {
        "key": "state_police",
        "label": "Child of State Police personnel",
        "amount": 15000,
        "keywords": ["police", "state police", "police personnel", "cop"],
    },
    {
        "key": "sr_junior_college",
        "label": "Student of SR Junior College",
        "amount": 15000,
        "keywords": ["sr junior college", "sr college", "sr junior"],
    },
    {
        "key": "alumni",
        "label": "SRU alumni, their children or siblings",
        "amount": 15000,
        "keywords": ["alumni", "alumnus"],
    },
    {
        "key": "ncc_c",
        "label": "NCC 'C' certificate holder",
        "amount": 15000,
        "keywords": ["ncc", "ncc c", "ncc 'c'"],
    },
    {
        "key": "padma_gallantry",
        "label": "Child of Padma / Gallantry awardee or J&K migrant",
        "amount": 15000,
        "keywords": ["padma", "gallantry", "j&k migrant", "kashmiri migrant", "migrant"],
    },
    {
        "key": "non_local",
        "label": "Student from outside TS & AP",
        "amount": 15000,
        "keywords": ["other states", "outside telangana and andhra", "non local", "north india", "other state"],
    },
    {
        "key": "lateral_entry",
        "label": "Lateral entry student",
        "amount": 15000,
        "keywords": ["lateral entry", "ecet", "diploma"],
    },
    {
        "key": "international",
        "label": "International student",
        "amount": 15000,
        "keywords": ["international student", "foreign student", "nri"],
    },
]


def is_affordability_query(message: str) -> bool:
    """Returns True if message mentions fee affordability or financial constraints."""
    if not message:
        return False
    return bool(AFFORDABILITY_REGEX.search(message))


def match_all_special_concessions(message: str) -> list[dict]:
    """Matches a user message against all applicable categories from SR University's 19 official special concessions."""
    low = (message or "").lower()
    if re.search(r"\b(?:none|no|neither|na|n/?a|not\s+applicable|none\s+of\s+these|nothing)\b", low):
        return []

    matched = []
    seen_keys = set()
    for cat in SPECIAL_CONCESSION_CATEGORIES:
        if cat["key"] in seen_keys:
            continue
        for kw in cat["keywords"]:
            if re.search(rf"\b{re.escape(kw)}\b" if len(kw) <= 5 else re.escape(kw), low):
                matched.append(cat)
                seen_keys.add(cat["key"])
                break
    return matched


def match_special_concession(message: str) -> dict | None:
    """Matches a user message against SR University's 19 official special concessions, returning the highest concession."""
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
    promise_statement = (
        "I will be asking you some questions, answer them, and at last I will let you know "
        "your final net fee after all concessions and deductions."
    )

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
                f"We offer extensive merit scholarships (up to 40% tuition waiver) as well as 19 special-category "
                f"concessions and on-campus bank education loan support.\n\n"
                f"{promise_statement}\n\n"
                f"Great news! Based on your academic score, you qualify for a **{sch_pct}% Merit Scholarship** on **{prog_name}**, "
                f"saving **{saving}/year** on tuition!\n\n"
                f"**Step 2: Special-Category Concessions**\n"
                f"Do you or your family qualify under any of SR University's official concession categories below?\n"
                f"• **Single living parent / Divorced mother**: ₹15,000 concession\n"
                f"• **Orphan (Lost both parents)**: ₹50,000 concession\n"
                f"• **Child of Defence / CRPF personnel & martyrs**: ₹15,000 concession\n"
                f"• **Sibling currently studying at SR University**: ₹15,000 concession\n"
                f"• **Girl student from outside Telangana**: ₹15,000 concession\n"
                f"• **Only girl child from Telangana**: ₹15,000 concession\n"
                f"• **Resident of Andhra Pradesh**: ₹15,000 concession\n"
                f"• **Differently Abled / 50%+ Disability**: ₹20,000 concession\n"
                f"• **National/International Sports achievers**: ₹15,000 – ₹50,000 concession\n"
                f"• **Child of State Police / NCC 'C' / SR Junior College**: ₹15,000 concession"
            )
            chips = [
                "Single parent / Divorced",
                "Lost both parents (Orphan)",
                "Child of Defence / CRPF",
                "Sibling at SR University",
                "Girl student (non-TS)",
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
            f"We offer generous merit scholarships (up to 40% tuition fee waiver) along with 19 special-category "
            f"concessions and full on-campus bank education loan support.\n\n"
            f"{promise_statement}\n\n"
            f"**Step 1 of 2: Academic Programme & Marks**\n"
            f"Please select or tell me:\n"
            f"1. Which **course / programme** are you planning to study (e.g. B.Tech CSE, BBA, BCA, MBA)?\n"
            f"2. What are your **10+2 marks (%)** or entrance rank (JEE / EAPCET)?"
        )
        chips = ["B.Tech CSE", "B.Tech AI & Robotics", "B.Tech ECE", "BBA", "B.Sc Agriculture"] if level != "pg" else ["MBA", "MCA", "M.Tech CSE"]
        form_card = build_fee_scholarship_form_card(selected_program=prog_key, level=level, only_selected=bool(prog_key))

        new_affordability = {
            "step": "awaiting_academics",
            "program": prog_key,
            "level": level,
        }
        return {
            "text": reply_text,
            "cards": [form_card],
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
            form_card = build_fee_scholarship_form_card(selected_program=detected_prog, level=level, only_selected=True)
            new_affordability = {
                "step": "awaiting_academics",
                "program": detected_prog,
                "level": level,
            }
            return {
                "text": text,
                "cards": [form_card],
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
            f"**Step 2 of 2: Special-Category Concessions**\n"
            f"SR University provides an additional 19 special-category annual concessions. Do any of these apply to you or your family?\n\n"
            f"• **Single living parent / Divorced mother**: ₹15,000 concession\n"
            f"• **Orphan (Lost both parents)**: ₹50,000 concession\n"
            f"• **Child of Defence / CRPF personnel & martyrs**: ₹15,000 concession\n"
            f"• **Sibling currently enrolled at SR University**: ₹15,000 concession\n"
            f"• **Girl student from outside Telangana**: ₹15,000 concession\n"
            f"• **Only girl child from Telangana**: ₹15,000 concession\n"
            f"• **Resident of Andhra Pradesh**: ₹15,000 concession\n"
            f"• **Differently Abled / 50%+ Disability**: ₹20,000 concession\n"
            f"• **National/International Sports achievers**: ₹15,000 – ₹50,000 concession\n"
            f"• **Child of State Police / NCC 'C' / SR Junior College**: ₹15,000 concession"
        )
        chips = [
            "Single parent / Divorced",
            "Lost both parents (Orphan)",
            "Child of Defence / CRPF",
            "Sibling at SR University",
            "Girl student (non-TS)",
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

        final_net_annual_int = max(0, tuition_after_merit_int - concession_amount)
        final_net_sem_int = final_net_annual_int // 2
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
            f"• **Final Net Annual Tuition Payable**: **{fees.inr(final_net_annual_int)}**\n"
            f"• **Payable Per Semester**: **{fees.inr(final_net_sem_int)}** *(in 2 manageable semester instalments)*\n"
            f"• **Total Annual Savings**: **{fees.inr(total_savings_int)}**\n\n"
            f"---\n\n"
            f"### 💡 Flexible Payment & On-Campus Financial Aid Options\n"
            f"1. **Semester-wise Instalment Plan**: You do not have to pay the entire year's tuition upfront. Fees are collected per semester ({fees.inr(final_net_sem_int)}/sem).\n"
            f"2. **On-Campus Bank Education Loans**: SR University has full-fledged on-campus branches and counters of **State Bank of India (SBI)** and **Union Bank of India**. They provide priority education loans covering tuition, hostel, and laptops under Central Government schemes (such as Vidya Lakshmi) with repayment starting after graduation.\n"
            f"3. **Admissions Financial Aid Desk**: Our team assists you with immediate provisional admission and loan estimate letters required by banks for swift sanction.\n\n"
            f"Would you like assistance connecting with our admissions financial aid desk or booking a campus visit?"
        )

        fee_card_data = dict(calc)
        fee_card_data["net_tuition_per_sem"] = fees.inr(final_net_sem_int)
        fee_card_data["per_semester_after_scholarship"] = fees.inr(final_net_sem_int)
        other_sem = 10000
        fee_card_data["total_per_semester"] = fees.inr(final_net_sem_int + other_sem)
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
