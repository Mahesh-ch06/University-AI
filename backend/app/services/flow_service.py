"""Flow service — manages guided conversation state machines like the Admission Wizard."""

import re

WIZARD_TRIGGERS = [
    "admission wizard",
    "guided admission",
    "admission journey",
    "start wizard",
    "start the wizard",
]


def detect_flow_trigger(user_message: str) -> str | None:
    """Detect if the user is triggering a guided conversation flow."""
    msg = user_message.lower().strip()
    if any(t in msg for t in WIZARD_TRIGGERS):
        return "admission_wizard"
    return None


def get_wizard_step_from_history(history: list[dict[str, str]], current_message: str) -> dict | None:
    """Analyze conversation history and current message to determine Admission Wizard step."""
    clean_msg = current_message.lower().strip()

    # User cancellation check
    if any(clean_msg == cmd or clean_msg.startswith(cmd + " ") for cmd in ("cancel", "stop", "exit", "quit", "nevermind", "restart")):
        return None

    # Determine if a wizard is explicitly requested in current message
    is_explicit_trigger = any(t in clean_msg for t in WIZARD_TRIGGERS)

    # Check whether the wizard was already completed in history (Step 4 rendered)
    last_step4_idx = -1
    last_trigger_idx = -1

    for i, m in enumerate(history):
        content = m.get("content", "").lower()
        if (
            "step 4 of 4" in content
            or "instant admission verdict" in content
            or "admission assessment: additional guidance" in content
        ):
            last_step4_idx = i
        if (
            any(t in content for t in WIZARD_TRIGGERS)
            or "step 1 of 4" in content
            or "welcome to the sr university admission wizard" in content
        ):
            last_trigger_idx = i

    # If Step 4 has already been displayed after the most recent wizard trigger,
    # and the user did NOT explicitly start a new wizard in this message,
    # then the flow is done. Return None so normal RAG / chat handles the query.
    if last_step4_idx != -1 and last_step4_idx >= last_trigger_idx and not is_explicit_trigger:
        return None

    # If no wizard has been started in history and this message isn't an explicit trigger, return None
    if last_trigger_idx == -1 and not is_explicit_trigger:
        return None

    # Limit history inspection to messages starting from the most recent wizard trigger
    wizard_start_idx = max(last_trigger_idx, 0) if last_trigger_idx != -1 else len(history)
    wizard_history = history[wizard_start_idx:] + [{"role": "user", "content": current_message}]

    # If this is a fresh wizard trigger and nothing else is selected yet, start at Step 1
    if is_explicit_trigger and len(wizard_history) <= 1:
        return {
            "flow_name": "admission_wizard",
            "step": 1,
            "total_steps": 4,
            "step_title": "Choose Degree Program",
            "completed": False,
            "options": ["🎓 B.Tech", "📘 M.Tech", "💼 MBA", "🔬 Ph.D."],
        }

    extracted_degree = None
    extracted_branch = None
    extracted_score = None

    for m in wizard_history:
        text = m.get("content", "").lower()

        if any(d in text for d in ("b.tech", "btech", "m.tech", "mtech", "mba", "ph.d", "phd")):
            if "b.tech" in text or "btech" in text:
                extracted_degree = "B.Tech"
            elif "m.tech" in text or "mtech" in text:
                extracted_degree = "M.Tech"
            elif "mba" in text:
                extracted_degree = "MBA"
            elif "ph.d" in text or "phd" in text:
                extracted_degree = "Ph.D."

        if any(b in text for b in ("cse", "computer science", "ai & ml", "aiml", "ece", "data science", "electronics")):
            if "ai" in text or "aiml" in text:
                extracted_branch = "CSE (AI & ML)"
            elif "cse" in text or "computer science" in text:
                extracted_branch = "CSE (Core)"
            elif "ece" in text or "electronics" in text:
                extracted_branch = "ECE"
            elif "data science" in text:
                extracted_branch = "Data Science"

        # Check for percentages
        match = re.search(r"\b(\d{1,2}(?:\.\d+)?)\s*%", text)
        if match:
            extracted_score = match.group(0)
        elif "90%+" in text or "90% +" in text:
            extracted_score = "92%"
        elif "80%" in text:
            extracted_score = "85%"
        elif "60%" in text or "70%" in text:
            extracted_score = "68%"
        elif "50%" in text:
            extracted_score = "55%"
        elif "below 50%" in text:
            extracted_score = "45%"
        elif "below 60%" in text:
            extracted_score = "55%"

    # Step 4: All info collected -> Verdict
    if extracted_degree and extracted_branch and extracted_score:
        score_val = 0.0
        try:
            score_val = float(re.sub(r"[^\d.]", "", extracted_score))
        except ValueError:
            score_val = None

        is_eligible = None  # decided in execute_wizard_step by eligibility.py
        return {
            "flow_name": "admission_wizard",
            "step": 4,
            "total_steps": 4,
            "step_title": "Eligibility Verdict & Next Steps",
            "degree": extracted_degree,
            "branch": extracted_branch,
            "score": extracted_score,
            "is_eligible": is_eligible,
            "completed": True,
            "options": [
                "📋 How to Apply",
                "💰 Fee Structure",
                "🏠 Hostel Details",
                "🔬 Lab Facilities",
            ],
        }

    # Step 3: Degree & Branch known -> Ask Score
    if extracted_degree and extracted_branch:
        return {
            "flow_name": "admission_wizard",
            "step": 3,
            "total_steps": 4,
            "step_title": "Qualifying Marks",
            "degree": extracted_degree,
            "branch": extracted_branch,
            "completed": False,
            "options": ["90%+ Marks", "80% - 89%", "60% - 79%", "50% - 59%", "Below 50%"],
        }

    # Step 2: Degree known -> Ask Branch
    if extracted_degree:
        return {
            "flow_name": "admission_wizard",
            "step": 2,
            "total_steps": 4,
            "step_title": "Choose Branch",
            "degree": extracted_degree,
            "completed": False,
            "options": [
                "💻 CSE (Core)",
                "🤖 CSE (AI & ML)",
                "📡 Electronics (ECE)",
                "📊 Data Science",
            ],
        }

    # Step 1: Initial step -> Ask Degree
    return {
        "flow_name": "admission_wizard",
        "step": 1,
        "total_steps": 4,
        "step_title": "Choose Degree Program",
        "completed": False,
        "options": ["🎓 B.Tech", "📘 M.Tech", "💼 MBA", "🔬 Ph.D."],
    }


def execute_wizard_step(step_info: dict) -> tuple[str, dict]:
    """Generate assistant answer and flow metadata for the current wizard step."""
    step = step_info["step"]

    if step == 1:
        text = (
            "🧭 **Welcome to the SR University Admission Wizard!** (Step 1 of 4)\n\n"
            "I'm here to guide you step-by-step through admissions, branch selection, and instant eligibility check.\n\n"
            "To begin, **what degree level are you looking for?**"
        )
    elif step == 2:
        degree = step_info.get("degree", "B.Tech")
        text = (
            f"🧭 **Step 2 of 4: Select Your Branch** ({degree})\n\n"
            f"Great choice aiming for {degree}! Which engineering or specialization track interests you the most?"
        )
    elif step == 3:
        branch = step_info.get("branch", "CSE")
        text = (
            f"🧭 **Step 3 of 4: Qualifying Percentage** ({branch})\n\n"
            f"Almost there! What was your 10+2 / Intermediate PCM aggregate percentage (or expected score)?"
        )
    else:  # step == 4: the verdict comes from eligibility.py and fees.py, never from fixed numbers here
        from app.sru_agent import eligibility, fees

        degree = step_info.get("degree", "B.Tech")
        branch = step_info.get("branch", "")
        score = str(step_info.get("score", ""))
        try:
            score_num = float(re.sub(r"[^\d.]", "", score))
        except ValueError:
            score_num = None
        program_key = fees.find_program(f"{degree} {branch}") or fees.find_program(degree)
        verdict = eligibility.assess(program_key, score_num) if score_num is not None else {"status": "need_marks"}
        step_info["is_eligible"] = verdict.get("eligible")

        if score_num is None:
            text = ("📋 **Step 3 of 4: Qualifying Percentage**\n\n"
                    "I couldn't read your percentage. Please type it as a number, for example 78%.")
        elif verdict.get("status") in ("unknown_program", "need_marks"):
            text = (f"📋 **Admission Assessment** (Step 4 of 4)\n\n"
                    f"I can't verify the eligibility rules for **{degree} {branch}** from the official fee card. "
                    f"Please check with {eligibility.ADMISSIONS_CONTACT}.")
        else:
            text = f"📋 **Admission Assessment** (Step 4 of 4)\n\n{eligibility.explain(verdict)}"
            if verdict["status"] != eligibility.BELOW:
                sch = fees.scholarship_for(program_key, percent=score_num)
                if sch["percent"]:
                    text += (f"\n\n🌟 **Merit scholarship:** {sch['basis_text']} falls in the **{sch['percent']}%** "
                             f"slab of the 2027-28 fee card (State Board slabs; CBSE slabs differ slightly).")
                text += ("\n\n**How to apply** (from sru.edu.in/admission): register on https://apply.sru.edu.in, "
                         "complete the application and upload documents, submit your scores, then accept the offer "
                         "and pay the fee.")

        return text, step_info
