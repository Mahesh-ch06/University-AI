"""Intelligent Course Selection & Fee Enquiry Flow for SRU Buddy.

Implements a structured multi-step conversational state machine:
  Fee Enquiry -> School Selection -> Programme Selection -> Specialization (if applicable) -> Detailed Fee Structure.
All figures are grounded in fee_policy_2027_28.json and the verified admissions handbook.
"""
import re
from typing import Any

from app.services.card_service import build_counsellor_board_card
from . import config, fees

FEE_PORTAL_URL = config.FEE_PORTAL_URL
DEFAULT_ACADEMIC_YEAR = config.ADMISSION_YEAR  # "2027-28"

# -----------------------------------------------------------------------------
# 1. Official SR University Schools Directory & Verified Program Mappings
# -----------------------------------------------------------------------------

SCHOOLS_DATA = [
    {
        "id": "school_cs_ai",
        "key": "cs_ai",
        "number": 1,
        "name": "School of Computer Science & Artificial Intelligence",
        "display_name": "School of Computer Science & Artificial Intelligence (CSE)",
        "short_name": "CS & AI (CSE)",
        "icon": "💻",
        "highlight": "Cutting-edge curriculum in AI, Quantum Computing & Advanced Cyber Systems",
        "keywords": ["cse", "computer science", "cs & ai", "cs and ai", "artificial intelligence", "ai", "aiml", "cyber", "data science"],
        "programs": {
            "ug": [
                {
                    "key": "btech_cse",
                    "name": "B.Tech Computer Science & Engineering (CSE)",
                    "degree": "B.Tech",

                    "has_specializations": True,
                    "specializations": [
                        "Artificial Intelligence & Machine Learning (AIML)",
                        "Data Science",
                        "Cyber Security",
                        "Robotics and Automation",
                        "Quantum AI",
                        "Core CSE",
                    ],
                },
                {
                    "key": "btech_ai_robotics",
                    "name": "B.Tech in Artificial Intelligence & Robotics",
                    "degree": "B.Tech",

                    "has_specializations": False,
                },
                {
                    "key": "bca",
                    "name": "BCA (Bachelor of Computer Applications)",
                    "degree": "BCA",

                    "has_specializations": False,
                },
                {
                    "key": "bsc_cs",
                    "name": "B.Sc Computer Science (Hons.)",
                    "degree": "B.Sc",

                    "has_specializations": False,
                },
                {
                    "key": "bsc_maths_ai",
                    "name": "B.Sc (Hons.) in Mathematics & AI",
                    "degree": "B.Sc",

                    "has_specializations": False,
                },
            ],
            "pg": [
                {
                    "key": "mtech",
                    "name": "M.Tech CSE (AIML, Data Science, Cyber Security)",
                    "degree": "M.Tech",

                    "has_specializations": True,
                },
                {
                    "key": "mca",
                    "name": "MCA (Master of Computer Applications)",
                    "degree": "MCA",

                    "has_specializations": False,
                },
                {
                    "key": "msc",
                    "name": "M.Sc Computer Science",
                    "degree": "M.Sc",

                    "has_specializations": False,
                },
            ],
        },
    },
    {
        "id": "school_engineering",
        "key": "engineering",
        "number": 2,
        "name": "School of Engineering",
        "display_name": "School of Engineering",
        "short_name": "School of Engineering",
        "icon": "⚙️",
        "highlight": "Tier-1 NBA Accredited B.Tech Programs with Smart Robotics & EV Labs",
        "keywords": ["engineering", "ece", "eee", "mech", "mechanical", "civil", "electronics", "electrical", "iep"],
        "programs": {
            "ug": [
                {
                    "key": "btech_ece",
                    "name": "B.Tech Electronics & Communication Engineering (ECE)",
                    "degree": "B.Tech",

                    "has_specializations": True,
                    "specializations": ["AIML", "VLSI System Design", "Robotics and Automation"],
                },
                {
                    "key": "btech_eee",
                    "name": "B.Tech Electrical & Electronics Engineering (EEE)",
                    "degree": "B.Tech",

                    "has_specializations": True,
                    "specializations": ["Electric Vehicles (EV)", "Renewable Energy"],
                },
                {
                    "key": "btech_mech",
                    "name": "B.Tech Mechanical Engineering",
                    "degree": "B.Tech",

                    "has_specializations": True,
                    "specializations": ["Robotics and Automation", "Smart Manufacturing"],
                },
                {
                    "key": "btech_civil",
                    "name": "B.Tech Civil Engineering",
                    "degree": "B.Tech",

                    "has_specializations": False,
                },
                {
                    "key": "btech_iep",
                    "name": "B.Tech International Engineering Programme (IEP)",
                    "degree": "B.Tech",

                    "has_specializations": False,
                },
            ],
            "pg": [
                {
                    "key": "mtech",
                    "name": "M.Tech Engineering (VLSI, Embedded Systems, EDT, AMS, Thermal, CTM)",
                    "degree": "M.Tech",

                    "has_specializations": True,
                },
            ],
        },
    },
    {
        "id": "school_agriculture",
        "key": "agriculture",
        "number": 3,
        "name": "School of Agriculture",
        "display_name": "School of Agriculture",
        "short_name": "School of Agriculture",
        "icon": "🌾",
        "highlight": "ICAR-Accredited — 1st Private University in Telugu States to earn ICAR accreditation",
        "keywords": ["agriculture", "agri", "icar", "bsc agri", "farming", "food tech", "food technology"],
        "programs": {
            "ug": [
                {
                    "key": "bsc_agri",
                    "name": "B.Sc. (Hons.) Agriculture (ICAR-Accredited)",
                    "degree": "B.Sc",

                    "has_specializations": False,
                },
                {
                    "key": "btech_food_tech",
                    "name": "B.Tech Food Technology",
                    "degree": "B.Tech",

                    "has_specializations": False,
                },
            ],
            "pg": [
                {
                    "key": "msc",
                    "name": "M.Sc. Agriculture (Agronomy, Genetics, Horticulture, Pathology, Soil Science)",
                    "degree": "M.Sc",

                    "has_specializations": True,
                },
            ],
        },
    },
    {
        "id": "school_business",
        "key": "business",
        "number": 4,
        "name": "Astra School of Business",
        "display_name": "Astra School of Business",
        "short_name": "Astra School of Business",
        "icon": "📊",
        "highlight": "Modern Case-Study & Business Analytics Pedagogy with Global Networking",
        "keywords": ["business", "astra", "management", "bba", "mba", "bcom", "commerce", "hospitality"],
        "programs": {
            "ug": [
                {
                    "key": "bba",
                    "name": "BBA (Bachelor of Business Administration)",
                    "degree": "BBA",

                    "has_specializations": False,
                },
                {
                    "key": "bba_specialised",
                    "name": "BBA Specialised (Finance, Operations, HR, Business Analytics, Marketing)",
                    "degree": "BBA",

                    "has_specializations": True,
                    "specializations": ["Finance", "Business Analytics", "Marketing", "HR", "Operations"],
                },
                {
                    "key": "bcom",
                    "name": "B.Com. (Bachelor of Commerce)",
                    "degree": "B.Com",

                    "has_specializations": False,
                },
                {
                    "key": "bsc_hospitality",
                    "name": "B.Sc in Hospitality and Event Management",
                    "degree": "B.Sc",

                    "has_specializations": False,
                },
            ],
            "pg": [
                {
                    "key": "mba",
                    "name": "MBA (Finance, Operations, HR, Business Analytics, Marketing)",
                    "degree": "MBA",

                    "has_specializations": True,
                    "specializations": ["Finance", "Business Analytics", "Marketing", "HR", "Operations"],
                },
                {
                    "key": "mba_agri",
                    "name": "MBA in Agri-Business Management",
                    "degree": "MBA",

                    "has_specializations": False,
                },
            ],
        },
    },
    {
        "id": "school_sciences_humanities",
        "key": "sciences",
        "number": 5,
        "name": "School of Sciences & Humanities",
        "display_name": "School of Sciences & Humanities",
        "short_name": "School of Sciences & Humanities",
        "icon": "🔬",
        "highlight": "Interdisciplinary Research in AI, Biotechnology & Space Engineering",
        "keywords": ["sciences", "humanities", "biotech", "physics", "chemistry", "biology", "maths"],
        "programs": {
            "ug": [
                {
                    "key": "btech_biotech",
                    "name": "B.Tech Biotechnology with AI",
                    "degree": "B.Tech",

                    "has_specializations": False,
                },
                {
                    "key": "btech_engg_physics",
                    "name": "B.Tech Engineering Physics in AI, Robotics & Space",
                    "degree": "B.Tech",

                    "has_specializations": False,
                },
                {
                    "key": "bsc_physics",
                    "name": "B.Sc Physics",
                    "degree": "B.Sc",

                    "has_specializations": False,
                },
                {
                    "key": "bsc_chemistry",
                    "name": "B.Sc Chemistry",
                    "degree": "B.Sc",

                    "has_specializations": False,
                },
            ],
            "pg": [
                {
                    "key": "msc",
                    "name": "M.Sc Sciences & Mathematics",
                    "degree": "M.Sc",

                    "has_specializations": False,
                },
            ],
        },
    },
    {
        "id": "school_design",
        "key": "design",
        "number": 6,
        "name": "School of Design",
        "display_name": "School of Design",
        "short_name": "School of Design",
        "icon": "🎨",
        "highlight": "Studio-Based Creative & Digital Prototyping Pathways with Industry Mentors",
        "keywords": ["design", "bdes", "fashion", "interior", "fashion design", "interior design"],
        "programs": {
            "ug": [
                {
                    "key": "bdes",
                    "name": "B.Des (Design: Interior Design, Fashion Design)",
                    "degree": "B.Des",

                    "has_specializations": True,
                    "specializations": ["Interior Design", "Fashion Design"],
                },
            ],
            "pg": [],
        },
    },
]

# -----------------------------------------------------------------------------
# 2. Helpers for Intent & Entity Detection
# -----------------------------------------------------------------------------

def _fill_from_policy() -> None:
    """Tuition and duration come from the fee policy (fee_policy_2027_28.json), never from this file."""
    progs = fees.load_data()["programs"]
    for school in SCHOOLS_DATA:
        for level in ("ug", "pg"):
            for prog in school["programs"].get(level, []):
                policy = progs.get(prog["key"], {})
                prog["tuition_per_year"] = policy.get("tuition_per_year")
                prog["duration_years"] = policy.get("duration_years")


_fill_from_policy()

_FEE_TRIGGER_WORDS = re.compile(
    r"\b(?:fee|fees|fess|feez|tuition|cost|costs|expense|expenses|hostel\s*fee|mess\s*fee|"
    r"bus\s*fee|transport\s*fee|admission\s*fee|fee\s*structure|total\s*cost|how\s*much\s*to\s*study|"
    r"tuition\s*and\s*accommodation|fee\s*for\s*cse|fees\s*for\s*agriculture)\b",
    re.IGNORECASE,
)

_BACK_NAVIGATION_WORDS = re.compile(
    r"\b(?:go\s*back|back|change\s*school|different\s*school|other\s*school|another\s*school|"
    r"change\s*course|different\s*programme|change\s*programme|previous\s*menu|restart\s*selection)\b",
    re.IGNORECASE,
)

_FEE_EXCLUSIONS = re.compile(
    r"\b(?:refund|refunds|cancellation\s*refund|cancel\s*my\s*admission|cancel\s*admission|admission\s*cancel|"
    r"calculate|calculation|how\s+to\s+pay|mode\s+of\s+payment|payment\s+mode|payment\s+method|due\s+date|last\s+date|deadline|"
    r"hostel\s*fee|hostel\s*fees|hostel\s*charges?|hostel\s*rent|mess\s*fee|mess\s*fees|mess\s*charges?)\b",
    re.IGNORECASE,
)

_ACADEMIC_YEAR_REGEX = re.compile(r"\b(202\d[-–]\d{2,4})\b")


def extract_academic_year(message: str, fallback: str = DEFAULT_ACADEMIC_YEAR) -> str:
    m = _ACADEMIC_YEAR_REGEX.search(message or "")
    if m:
        raw = m.group(1).replace("–", "-")
        # Normalize 2027-2028 -> 2027-28
        parts = raw.split("-")
        if len(parts) == 2 and len(parts[1]) == 4:
            return f"{parts[0]}-{parts[1][-2:]}"
        return raw
    return fallback


def is_broad_fee_query(message: str) -> bool:
    """Matches broad fee queries that initiate the structured academic flow."""
    if _FEE_EXCLUSIONS.search(message or ""):
        return False
    return bool(_FEE_TRIGGER_WORDS.search(message or ""))


def detect_back_navigation(message: str) -> bool:
    return bool(_BACK_NAVIGATION_WORDS.search(message or ""))


def detect_school(message: str) -> dict | None:
    """Matches free text or number selection to one of the 6 schools."""
    low = (message or "").lower().strip()
    # Number matching: "1", "option 1", "school 1"
    num_match = re.search(r"\b(?:option\s*|school\s*)?([1-6])\b", low)
    if num_match:
        idx = int(num_match.group(1)) - 1
        if 0 <= idx < len(SCHOOLS_DATA):
            return SCHOOLS_DATA[idx]

    # Keyword / Name matching
    for school in SCHOOLS_DATA:
        if school["name"].lower() in low or school["display_name"].lower() in low:
            return school
        if any(re.search(rf"\b{re.escape(kw)}\b", low) for kw in school["keywords"]):
            return school
    return None


def detect_program_under_school(message: str, school: dict | None) -> dict | None:
    """Matches message to a program under the given school or any school."""
    low = (message or "").lower().strip()
    schools_to_search = [school] if school else SCHOOLS_DATA

    for sch in schools_to_search:
        all_progs = sch["programs"].get("ug", []) + sch["programs"].get("pg", [])
        for prog in all_progs:
            # Check program name, degree, or key
            if prog["name"].lower() in low or prog["key"] in low:
                return prog
            # Check degree words (e.g. "btech cse", "bca", "mtech", "bdes")
            if re.search(rf"\b{re.escape(prog['degree'].lower())}\b", low):
                # If specific words match
                if "cse" in low and "cse" in prog["key"]:
                    return prog
                if "robotics" in low and "robotics" in prog["key"]:
                    return prog
                if "ece" in low and "ece" in prog["key"]:
                    return prog
                if "eee" in low and "eee" in prog["key"]:
                    return prog
                if "mech" in low and "mech" in prog["key"]:
                    return prog
                if "civil" in low and "civil" in prog["key"]:
                    return prog
                if "food" in low and "food" in prog["key"]:
                    return prog
                if "agri" in low and "agri" in prog["key"]:
                    return prog
                if "bba" in low and "bba" in prog["key"]:
                    return prog
                if "mba" in low and "mba" in prog["key"]:
                    return prog
                if "bdes" in low or "design" in low and "bdes" in prog["key"]:
                    return prog
                if "bca" in low and "bca" in prog["key"]:
                    return prog
                if "mca" in low and "mca" in prog["key"]:
                    return prog

    # Fallback to general find_program
    found_key = fees.find_program(message)
    if found_key:
        for sch in SCHOOLS_DATA:
            all_progs = sch["programs"].get("ug", []) + sch["programs"].get("pg", [])
            for prog in all_progs:
                if prog["key"] == found_key:
                    return prog
    return None


def detect_specialization(message: str, prog: dict) -> str | None:
    low = (message or "").lower()
    if not prog.get("has_specializations"):
        return None

    # Precise keyword mappings (avoids false positive substring hits like 'and')
    if re.search(r"\b(?:aiml|ai\s*&?\s*ml|ai\s*and\s*ml|ai/ml|aml|machine\s+learning)\b", low):
        return "Artificial Intelligence & Machine Learning (AIML)"
    if re.search(r"\b(?:data\s+science|datascience|ds)\b", low):
        return "Data Science"
    if re.search(r"\b(?:cyber\s*security|cybersecurity|cyber|infosec)\b", low):
        return "Cyber Security"
    if re.search(r"\b(?:quantum\s*ai|quantum)\b", low):
        return "Quantum AI"
    if re.search(r"\b(?:robotics\s*(?:&|and)\s*automation)\b", low):
        return "Robotics and Automation"
    if re.search(r"\b(?:core\s*cse|core)\b", low):
        return "Core CSE"

    return None


# -----------------------------------------------------------------------------
# 3. Card Generators for Frontend
# -----------------------------------------------------------------------------

def build_school_selection_card() -> dict:
    return {
        "type": "school_selection",
        "title": "Select Academic School",
        "subtitle": "Choose your preferred school or academic area to explore programmes & fee structures",
        "schools": [
            {
                "id": s["id"],
                "number": s["number"],
                "name": s["display_name"],
                "short_name": s["short_name"],
                "icon": s["icon"],
                "highlight": s["highlight"],
            }
            for s in SCHOOLS_DATA
        ],
        "allow_custom": True,
    }


def _detect_level(msg: str, conv_state: dict | None = None, profile: dict | None = None) -> str | None:
    low = (msg or "").lower()
    if re.search(r"\b(?:ug|undergrad|undergraduate|bachelor|b\.?tech|bba|bca|bdes|b\.?com|b\.?sc)\b", low):
        return "ug"
    if re.search(r"\b(?:pg|postgrad|postgraduate|master|mba|mca|m\.?tech|m\.?sc)\b", low):
        return "pg"
    if conv_state and conv_state.get("degree_level") in ("ug", "pg"):
        return conv_state.get("degree_level")
    if profile and profile.get("degree_level") in ("ug", "pg"):
        return profile.get("degree_level")
    return None


def build_course_selection_card(school: dict, level: str | None = None) -> dict:
    ug = school["programs"].get("ug", []) if level != "pg" else []
    pg = school["programs"].get("pg", []) if level != "ug" else []
    return {
        "type": "course_selection",
        "title": f"Programmes in {school['short_name']}",
        "subtitle": "Select your intended degree or programme",
        "school_id": school["id"],
        "school_name": school["display_name"],
        "icon": school["icon"],
        "level": level,
        "programs_ug": ug,
        "programs_pg": pg,
    }


def build_detailed_fee_card(prog: dict, school: dict, year: str, spec: str | None = None, user_text: str | None = None) -> dict:
    """The programme's standard fee (no scholarship yet), semester by semester, from the ONE fee engine."""
    key = prog.get("key", "")
    data = fees.load_data()
    ch = data["charges"]
    spec_on = bool(spec) and key in data.get("schedule", {}).get("specialization_fee_programs", [])
    plan = fees.fee_schedule(key, 0, specialization=spec_on)
    y1 = plan["years"][0]
    tuition = y1["annual_tuition"]

    def rows(sem):
        return [{"label": i["label"], "amount": i["amount"], "formatted": fees.inr(i["amount"]), "kind": i["kind"]}
                for i in sem["items"]]

    semesters = [{"semester": s["semester"], "items": rows(s), "total": s["total"], "formatted_total": fees.inr(s["total"])}
                 for s in y1["semesters"]]
    hostel = fees.hostel_per_year()
    clean_p_name = fees.clean_program_name(key, specialization=spec, user_text=user_text)
    return {
        "type": "fee_structure_detailed",
        "title": f"Fee Structure — {clean_p_name}",
        "academic_year": year,
        "school_name": school["display_name"],
        "program_name": clean_p_name,
        "specialization": spec,
        "degree": prog.get("degree", "Degree"),
        "duration_years": prog.get("duration_years"),
        "tuition": {
            "annual": tuition,
            "semester": semesters[0]["items"][0]["amount"],
            "formatted_annual": fees.inr(tuition),
            "formatted_semester": fees.inr(semesters[0]["items"][0]["amount"]),
            "yearly_increase": fees.inr(data["programs"][key]["yearly_increase"]),
        },
        "semesters": semesters,
        "first_year_total": y1["total"],
        "formatted_first_year_total": fees.inr(y1["total"]),
        "course_total": plan["course_total"],
        "formatted_course_total": fees.inr(plan["course_total"]) if plan["course_total"] else None,
        "application_fee": fees.inr(plan["application_fee"]),
        "specialization_fee": fees.inr(ch["specialization_fee"]["amount"]) if key in data.get("schedule", {}).get("specialization_fee_programs", []) else None,
        "formatted_transport": fees.inr(ch["bus"]["amount"]),
        "hostel_options": [
            {"type": fees.HOSTEL_LABELS[k], "fee": v, "formatted": fees.inr(v)} for k, v in hostel.items()
        ],
        "hostel_note": "Hostel fees are not on the 2027-28 fee circular; the Admissions Office confirms them.",
        "hostel_deposits": [
            {"label": "Electricity deposit, AC (one-time)", "amount": ch["electricity_deposit"]["ac"],
             "formatted": fees.inr(ch["electricity_deposit"]["ac"])},
            {"label": "Electricity deposit, Non-AC (one-time)", "amount": ch["electricity_deposit"]["non_ac"],
             "formatted": fees.inr(ch["electricity_deposit"]["non_ac"])},
        ],
        "dining_info": "Meals are included in the hostel fee, served in SRU's 4,000-seat central dining facility.",
        "verified": True,
        "source": data["source"],
    }


def fee_summary_text(fee_card: dict, lead: str, closing: str) -> str:
    """The chat text for a programme's standard fee, written only from the engine's numbers on the card."""
    s1, s2 = fee_card["semesters"][0], fee_card["semesters"][1]
    extras = [i for i in s1["items"] if i["kind"] != "tuition"]
    extra_text = ", ".join(f"{i['label'].lower()} {i['formatted']}" for i in extras)
    lines = [lead, "",
             f"• **Tuition:** {fee_card['tuition']['formatted_annual']} a year, split equally: "
             f"{fee_card['tuition']['formatted_semester']} per semester "
             f"(rises by {fee_card['tuition']['yearly_increase']} each year)",
             f"• **Semester 1:** {s1['formatted_total']} (tuition + {extra_text})",
             f"• **Semester 2:** {s2['formatted_total']} (tuition only)",
             f"• **First year:** {fee_card['formatted_first_year_total']}"]
    if fee_card.get("formatted_course_total"):
        lines.append(f"• **Full course ({fee_card['duration_years']} years):** {fee_card['formatted_course_total']}")
    lines += [f"• **Application form:** {fee_card['application_fee']}, paid separately when you apply",
              f"• **Optional:** bus {fee_card['formatted_transport']} a year; hostel by room type", "",
              "This is the standard fee before any merit scholarship. " + closing]
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 4. State Machine Execution & Transition Engine
# -----------------------------------------------------------------------------

def _is_fee_exit_or_offtopic(low: str) -> bool:
    return any(k in low for k in (
        "cancel", "stop", "exit", "no need", "nevermind", "later", "quit", "close", "back",
        "vc", "vice chancellor", "chancellor", "who is", "tell about", "about sru", "about sr",
        "faculty", "dean", "hod", "canteen", "cafeteria", "sports", "library", "exam", "passmarks",
        "pass marks", "marks", "placement", "placements", "highest package", "average package",
        "founder", "location", "address", "how to reach", "bus", "transport", "cie", "ese"
    )) or len(low.split()) > 5


def _build_combined_hostel_payload(
    prog_dict: dict,
    saved_year: str,
    user_name: str | None,
    conv_state: dict,
) -> dict:
    from app.services.card_service import BTECH_CSE_WITH_HOSTEL_FEE_CARD
    key = prog_dict.get("key", "btech_cse")
    prog_name = fees.clean_program_name(key)
    r = fees.calculate_fee(key, hostel="ac_4")
    name_str = f", {user_name}" if user_name else ""
    lines = "\n".join(f"• {i['item']}: {i['amount']}" for i in r["semester_1"]["items"])
    reply_text = (
        f"Here's the combined fee breakdown for **{prog_name}** with an **AC 4-sharing hostel** room for "
        f"**{saved_year}**{name_str} (standard fee; tuition {r['tuition_first_year']} a year, split equally):\n\n"
        f"**Semester 1**\n{lines}\n👉 **Semester 1 payable: {r['sem1_total_payable']}**\n\n"
        f"**Semester 2**: tuition {r['per_semester_after_scholarship']} → **{r['sem2_total_payable']}**\n\n"
        f"**First year: {r['first_year_total_payable']}** (application form fee {r['application_fee']} is paid separately).\n\n"
        f"*Hostel fees are not on the fee circular and are confirmed by the Admissions Office. Merit scholarships "
        f"reduce tuition only.*"
    )
    return {
        "text": reply_text,
        "cards": [BTECH_CSE_WITH_HOSTEL_FEE_CARD],
        "suggestions": [
            "Calculate scholarship for my marks",
            "Hostel room options",
            "Placement records for this course",
            "Change school / programme",
        ],
        "new_state": {
            **conv_state,
            "fee_flow_state": "completed",
            "fee_flow_prog": prog_dict.get("key", "btech_cse"),
            "fee_flow_year": saved_year,
        },
    }


def process_fee_flow(
    message: str,
    session_id: str,
    profile: dict,
    conv_state: dict,
) -> dict | None:
    """Executes the fee enquiry state machine.

    Returns dict with keys:
      - text: str
      - cards: list[dict]
      - suggestions: list[str]
      - new_state: dict
    or None if this message is not part of the fee flow.
    """
    msg = message.strip()
    low = msg.lower()
    current_state = conv_state.get("fee_flow_state")
    saved_school_id = conv_state.get("fee_flow_school")
    saved_prog_key = conv_state.get("fee_flow_prog") or conv_state.get("active_program") or (profile.get("program_interest") if profile else None)
    saved_year = conv_state.get("fee_flow_year") or extract_academic_year(msg, DEFAULT_ACADEMIC_YEAR)
    is_fee_query = is_broad_fee_query(msg)
    user_name = profile.get("name")
    name_part = f", {user_name}" if user_name else ""

    # Check for back navigation
    if detect_back_navigation(msg) and current_state:
        # Step back to school selection
        return {
            "text": f"No problem{', ' + user_name if user_name else ''}! Let's select your preferred school or academic area:",
            "cards": [build_school_selection_card()],
            "suggestions": [s["display_name"] for s in SCHOOLS_DATA],
            "new_state": {
                "fee_flow_state": "awaiting_school_selection",
                "fee_flow_school": None,
                "fee_flow_prog": None,
                "fee_flow_year": saved_year,
            },
        }

    # -------------------------------------------------------------------------
    # Initial Trigger: Not in flow yet
    # -------------------------------------------------------------------------
    if not current_state:
        # If user is asking about exam evaluation, passing marks, or CIE/ESE,
        # pass through to the dedicated academic evaluation handler.
        is_exam_q = any(k in low for k in (
            "marks and passmarks", "passmarks", "pass marks", "cie and ese",
            "cie marks", "ese marks", "grading scale", "10-point scale", "continuous internal evaluation"
        ))
        if is_exam_q:
            return None

        # If user provides personal entrance/board scores (e.g. 85%, EAPCET rank),
        # pass through to the dedicated scholarship calculation tools/model.
        has_scores = bool(
            re.search(r"(?<![\d.])(\d{2}(?:\.\d+)?)\s*(?:%|percent|percentage)", low)
            or re.search(r"\b(?:eapcet|eamcet|jee|rank|percentile)\s*[\d,]+", low)
            or re.search(r"\b\d{1,6}\s*(?:rank|percentile)\b", low)
            or "inter (" in low
            or "no entrance" in low
        )
        if has_scores:
            return None

        if not is_fee_query and not any(kw in low for kw in ("school of", "astra school")):
            return None

        if conv_state.get("active_topic") == "hostel" and not any(kw in low for kw in ("school of", "astra school", "btech", "b.tech", "mtech", "bba", "mba", "tuition")):
            return None

        # Check if user mentioned an unverified year (e.g. 2028-29, 2030)
        mentioned_year = extract_academic_year(msg, "")
        year_unverified_notice = ""
        if mentioned_year and mentioned_year not in ("2027-28", "2026-27"):
            year_unverified_notice = (
                f"Note: The official fee structure for Academic Year **{mentioned_year}** has not yet been finalized "
                f"by the university. I am displaying the latest verified fee structure for **{DEFAULT_ACADEMIC_YEAR}**.\n\n"
            )
            saved_year = DEFAULT_ACADEMIC_YEAR
        elif mentioned_year:
            saved_year = mentioned_year

        # Check if user ALREADY specified a School directly (e.g. "fees for Agriculture", "Astra School of Business")
        matched_school = detect_school(msg)
        has_specific_prog_word = bool(re.search(
            r"\b(?:b\.?\s?tech|m\.?\s?tech|b\.?\s?sc|m\.?\s?sc|bba|mba|bca|mca|b\.?\s?com|b\.?\s?des|"
            r"cse|aiml|ai\s*&?\s*ml|ai\s*and\s*ml|ai/ml|aml|data\s*science|cyber\s*security|quantum\s*ai|robotics|"
            r"ece|eee|mech|civil|food\s*tech|biotech|physics|chemistry|design)\b",
            low,
        ))
        matched_prog = detect_program_under_school(msg, matched_school) if (has_specific_prog_word or not matched_school) else None

        if matched_prog:
            is_combined_hostel_q = any(k in low for k in (
                "add hostel", "include hostel", "including hostel", "with hostel", "hostel fee too",
                "hostel also", "hostel and college", "both hostel and", "fee + hostel", "hostel + fee",
                "combine my entire", "total fee including hostel", "total cost with hostel"
            )) or ("hostel" in low and any(k in low for k in ("combine", "both", "include", "together", "plus", "along with", "with college", "with tuition")))
            if is_combined_hostel_q:
                return _build_combined_hostel_payload(matched_prog, saved_year, user_name, conv_state)
            # User named a specific program (e.g. "B.Tech CSE fee for 2027-28" or "hostel fee for B.Tech")
            # Find the school of this program
            sch = matched_school
            if not sch:
                for s in SCHOOLS_DATA:
                    all_p = s["programs"].get("ug", []) + s["programs"].get("pg", [])
                    if any(p["key"] == matched_prog["key"] for p in all_p):
                        sch = s
                        break
            sch = sch or SCHOOLS_DATA[0]
            spec = detect_specialization(msg, matched_prog)
            fee_card = build_detailed_fee_card(matched_prog, sch, saved_year, spec, user_text=msg)
            clean_p_name = fees.clean_program_name(matched_prog["key"], specialization=spec, user_text=msg)

            reply_text = year_unverified_notice + fee_summary_text(
                fee_card, f"Sure{name_part}! Here's the fee for **{clean_p_name}** ({sch['short_name']}), {saved_year}:",
                "Want me to work out your scholarship from your marks, or add a hostel room?")

            follow_up_chips = [
                "Calculate scholarship for my marks",
                "Hostel room options",
                "Placement records for this course",
                "Change school / programme",
            ]

            return {
                "text": reply_text,
                "cards": [fee_card],
                "suggestions": follow_up_chips,
                "new_state": {
                    "fee_flow_state": "completed",
                    "fee_flow_school": sch["id"],
                    "fee_flow_prog": matched_prog["key"],
                    "fee_flow_year": saved_year,
                    "fee_intake": {
                        "program": matched_prog["key"],
                        "asked": ["program"],
                        "waiting_for": "board",
                        "turns": 1,
                    },
                },
            }

        elif matched_school:
            # User named the School directly (e.g. "fees for Agriculture", "interested in Astra School of Business")
            level = _detect_level(msg, conv_state, profile)
            prog_card = build_course_selection_card(matched_school, level=level)
            all_progs = prog_card["programs_ug"] + prog_card["programs_pg"]

            chips = [p["name"] for p in all_progs[:5]] + ["Change School"]

            return {
                "text": (
                    f"{year_unverified_notice}Got it{', ' + user_name if user_name else ''}. "
                    f"Here are the verified programmes offered under the **{matched_school['display_name']}**.\n\n"
                    f"Which degree or programme would you like to explore for Academic Year **{saved_year}**?"
                ),
                "cards": [prog_card],
                "suggestions": chips,
                "new_state": {
                    "fee_flow_state": "awaiting_course_selection",
                    "fee_flow_school": matched_school["id"],
                    "fee_flow_prog": None,
                    "fee_flow_year": saved_year,
                },
            }

        else:
            # General fee query: "What is the complete fee structure?", "What is the hostel fee?", "total cost"
            # Initiate Step 1: School selection
            school_card = build_school_selection_card()
            chips = [
                "1. CS & AI (CSE)",
                "2. School of Engineering",
                "3. School of Agriculture",
                "4. Astra School of Business",
                "5. Sciences & Humanities",
                "6. School of Design",
            ]

            return {
                "text": (
                    f"{year_unverified_notice}Sure{', ' + user_name if user_name else ''}! "
                    f"I can help you explore the tuition fees, hostel charges, and other applicable expenses at SR University for Academic Year **{saved_year}**.\n\n"
                    f"First, which academic area or school interests you?"
                ),
                "cards": [school_card],
                "suggestions": chips,
                "new_state": {
                    "fee_flow_state": "awaiting_school_selection",
                    "fee_flow_school": None,
                    "fee_flow_prog": None,
                    "fee_flow_year": saved_year,
                },
            }

    # -------------------------------------------------------------------------
    # State: awaiting_school_selection
    # -------------------------------------------------------------------------
    if current_state == "awaiting_school_selection":
        matched_school = detect_school(msg)
        # Check if user typed a programme manually directly
        matched_prog = detect_program_under_school(msg, matched_school)

        if matched_prog:
            sch = matched_school
            if not sch:
                for s in SCHOOLS_DATA:
                    all_p = s["programs"].get("ug", []) + s["programs"].get("pg", [])
                    if any(p["key"] == matched_prog["key"] for p in all_p):
                        sch = s
                        break
            sch = sch or SCHOOLS_DATA[0]
            spec = detect_specialization(msg, matched_prog)
            fee_card = build_detailed_fee_card(matched_prog, sch, saved_year, spec, user_text=msg)
            clean_p_name = fees.clean_program_name(matched_prog["key"], specialization=spec, user_text=msg)
            reply_text = fee_summary_text(
                fee_card, f"Great choice{name_part}! Here's the fee for **{clean_p_name}** ({sch['short_name']}), {saved_year}:",
                "Want me to work out your scholarship from your marks, or add a hostel room?")
            return {
                "text": reply_text,
                "cards": [fee_card],
                "suggestions": ["Calculate scholarship for my marks", "Hostel room options", "Change school / programme"],
                "new_state": {
                    "fee_flow_state": "completed",
                    "fee_flow_school": sch["id"],
                    "fee_flow_prog": matched_prog["key"],
                    "fee_flow_year": saved_year,
                    "fee_intake": {
                        "program": matched_prog["key"],
                        "asked": ["program"],
                        "waiting_for": "board",
                        "turns": 1,
                    },
                },
            }

        if matched_school:
            level = _detect_level(msg, conv_state, profile)
            prog_card = build_course_selection_card(matched_school, level=level)
            all_progs = prog_card["programs_ug"] + prog_card["programs_pg"]
            chips = [p["name"] for p in all_progs[:5]] + ["Change School"]

            return {
                "text": (
                    f"Got it{', ' + user_name if user_name else ''}. "
                    f"Here are the verified programmes offered under the **{matched_school['display_name']}**.\n\n"
                    f"Which degree or programme would you like to explore for Academic Year **{saved_year}**?"
                ),
                "cards": [prog_card],
                "suggestions": chips,
                "new_state": {
                    "fee_flow_state": "awaiting_course_selection",
                    "fee_flow_school": matched_school["id"],
                    "fee_flow_prog": None,
                    "fee_flow_year": saved_year,
                },
            }

        # If user typed something not matching any school or course:
        # Check if user wants to exit/cancel or is asking an off-topic question
        if _is_fee_exit_or_offtopic(low):
            conv_state["fee_flow_state"] = None
            return None

        return {
            "text": (
                f"I'd love to help you find the exact fee details{', ' + user_name if user_name else ''}. "
                f"Please select one of our 6 schools below or type the name of the programme you're interested in:"
            ),
            "cards": [build_school_selection_card()],
            "suggestions": [s["display_name"] for s in SCHOOLS_DATA],
            "new_state": conv_state,
        }

    # -------------------------------------------------------------------------
    # State: awaiting_course_selection
    # -------------------------------------------------------------------------
    if current_state == "awaiting_course_selection":
        school = next((s for s in SCHOOLS_DATA if s["id"] == saved_school_id), None)
        matched_prog = detect_program_under_school(msg, school)

        if matched_prog:
            sch = school or SCHOOLS_DATA[0]
            spec = detect_specialization(msg, matched_prog)
            fee_card = build_detailed_fee_card(matched_prog, sch, saved_year, spec, user_text=msg)
            clean_p_name = fees.clean_program_name(matched_prog["key"], specialization=spec, user_text=msg)

            reply_text = fee_summary_text(
                fee_card, f"Here's the fee for **{clean_p_name}** ({sch['short_name']}), {saved_year}:",
                "Want me to work out your scholarship from your marks, or add a hostel room?")

            follow_up_chips = [
                "Calculate scholarship for my marks",
                "Hostel room options",
                "Placement records for this course",
                "Change school / programme",
            ]

            return {
                "text": reply_text,
                "cards": [fee_card],
                "suggestions": follow_up_chips,
                "new_state": {
                    "fee_flow_state": "completed",
                    "fee_flow_school": sch["id"],
                    "fee_flow_prog": matched_prog["key"],
                    "fee_flow_year": saved_year,
                    "fee_intake": {
                        "program": matched_prog["key"],
                        "asked": ["program"],
                        "waiting_for": "board",
                        "turns": 1,
                    },
                },
            }

        # User might have typed another school
        new_school = detect_school(msg)
        if new_school and new_school["id"] != saved_school_id:
            level = _detect_level(msg, conv_state, profile)
            prog_card = build_course_selection_card(new_school, level=level)
            all_p = prog_card["programs_ug"] + prog_card["programs_pg"]
            chips = [p["name"] for p in all_p[:5]] + ["Change School"]
            return {
                "text": (
                    f"Switched to **{new_school['display_name']}**! "
                    f"Here are the available programmes for Academic Year **{saved_year}**:"
                ),
                "cards": [prog_card],
                "suggestions": chips,
                "new_state": {
                    "fee_flow_state": "awaiting_course_selection",
                    "fee_flow_school": new_school["id"],
                    "fee_flow_prog": None,
                    "fee_flow_year": saved_year,
                },
            }

        # Otherwise check if user is asking an off-topic question or wants to exit
        if _is_fee_exit_or_offtopic(low):
            conv_state["fee_flow_state"] = None
            return None

        # Re-prompt with the current school's course card
        if school:
            level = _detect_level(msg, conv_state, profile)
            prog_card = build_course_selection_card(school, level=level)
            all_p = prog_card["programs_ug"] + prog_card["programs_pg"]
            return {
                "text": f"Please select one of the programmes offered under **{school['display_name']}** below, or type your preferred degree:",
                "cards": [prog_card],
                "suggestions": [p["name"] for p in all_p[:5]],
                "new_state": conv_state,
            }

    # -------------------------------------------------------------------------
    # State: completed (Handling follow-ups on the same course)
    # -------------------------------------------------------------------------
    if current_state == "completed":
        # Follow-up: Calculate scholarship for my marks on the active programme
        if any(k in low for k in ("calculate scholarship", "scholarship for my marks", "check scholarship", "my marks", "my scholarship")):
            fee_data = fees.load_data()
            prog_key = saved_prog_key or conv_state.get("active_program") or (profile.get("program_interest") if profile else None)
            if not prog_key:
                return {
                    "text": "Sure! Which course or degree are you considering pursuing at SR University?",
                    "cards": [build_school_selection_card()],
                    "suggestions": ["B.Tech Engineering", "MBA", "BBA", "B.Sc Agriculture"],
                    "new_state": {
                        **conv_state,
                        "fee_flow_state": "awaiting_school_selection",
                    },
                }
            prog_dict = fee_data["programs"].get(prog_key, {})
            prog_name = prog_dict.get("name", "B.Tech Computer Science & Engineering")
            return {
                "text": (
                    f"To calculate your merit scholarship and exact net tuition for **{prog_name}**, "
                    f"which **10+2 / Intermediate Board** did you complete?\n\n"
                    f"• **Telangana State Board (TS BIE)**\n"
                    f"• **AP State Board (BIEAP)**\n"
                    f"• **CBSE / ICSE / NIOS**\n"
                    f"• **Other State Boards across India** (Maharashtra, Karnataka, Tamil Nadu, UP, Bihar, etc.)\n"
                    f"• **IB (International Baccalaureate)**\n\n"
                    f"In the next step, I'll ask for your marks or entrance rank to determine your exact fee."
                ),
                "cards": [{**build_counsellor_board_card(), "program": prog_key}],
                "suggestions": [
                    "Telangana State Board",
                    "AP State Board",
                    "CBSE / ICSE",
                    "Other State Board across India",
                    "IB",
                ],
                "new_state": {
                    **conv_state,
                    "fee_flow_state": "completed",
                    "fee_flow_prog": prog_key,
                    "fee_flow_year": saved_year,
                    "fee_intake": {
                        "program": prog_key,
                        "asked": ["program", "board"],
                        "waiting_for": "board",
                        "turns": 1,
                    },
                },
            }

        # Follow-up: Combined Hostel + College / Tuition / Total fee including hostel
        is_combined_hostel_q = any(k in low for k in (
            "add hostel", "include hostel", "including hostel", "with hostel", "hostel fee too",
            "hostel also", "hostel and college", "both hostel and", "fee + hostel", "hostel + fee",
            "combine my entire", "total fee including hostel", "total cost with hostel"
        )) or ("hostel" in low and any(k in low for k in ("combine", "both", "include", "together", "plus", "along with", "with college", "with tuition")))

        if is_combined_hostel_q:
            fee_data = fees.load_data()
            active_p = saved_prog_key or conv_state.get("active_program") or (profile.get("program_interest") if profile else None) or "btech_cse"
            prog_dict = fee_data["programs"].get(active_p, {})
            return _build_combined_hostel_payload(prog_dict, saved_year, user_name, conv_state)

        # Follow-up: Hostel specific fee/cost query only (strictly standalone)
        is_hostel_cost_q = any(k in low for k in ("hostel", "accommodation", "room", "mess", "boarding")) and (
            any(k in low for k in ("fee", "fees", "cost", "costs", "charge", "charges", "price", "how much", "rate", "rent", "package", "deposit"))
            or low.strip("?. ") in ("what about hostel", "what about the hostel", "hostel")
        ) and not any(k in low for k in ("facility", "facilities", "curfew", "food", "mess food", "menu", "timing", "timings", "rule", "rules", "warden", "gym", "wifi", "internet"))
        if is_hostel_cost_q:
            school = next((s for s in SCHOOLS_DATA if s["id"] == saved_school_id), SCHOOLS_DATA[0])
            active_p = saved_prog_key or conv_state.get("active_program") or (profile.get("program_interest") if profile else None) or "btech_cse"
            prog_dict = fees.load_data()["programs"].get(active_p, {})
            prog_name = prog_dict.get("name", "B.Tech CSE")

            return {
                "text": (
                    "Here are the residential hostel charges at SR University (room with meals, per year):\n\n"
                    + "".join(f"• **{fees.HOSTEL_LABELS[k]}**: {fees.inr(v)}/year\n" for k, v in fees.hostel_per_year().items())
                    + f"\n• Electricity deposit (one-time): {fees.inr(fees.charge_amount('electricity_deposit', 'ac'))} AC / "
                    f"{fees.inr(fees.charge_amount('electricity_deposit', 'non_ac'))} Non-AC\n\n"
                    "Meals are served in the 4,000-seat central dining complex, with 24/7 security and wardens. "
                    "Hostel room fees aren't on the 2027-28 fee circular, so the Admissions Office confirms them."
                ),
                "cards": [],
                "suggestions": [
                    "Calculate scholarship for my marks",
                    "Total fee including hostel",
                    "Change school / programme",
                ],
                "new_state": conv_state,
            }

        # Follow-up: Total fee query (strict, excluding exam evaluation & marks questions)
        is_exam_evaluation_q = any(k in low for k in (
            "marks", "passmarks", "pass marks", "passing marks", "grade", "grades",
            "grading", "credit", "credits", "evaluation", "cie", "ese", "exam", "exams"
        ))
        is_total_fee_q = not is_exam_evaluation_q and (
            any(k in low for k in ("total fee", "total cost", "overall fee", "total expense", "total tuition"))
            or ("total" in low and any(k in low for k in ("fee", "fees", "cost", "costs", "tuition", "package", "payable", "expense")))
        )
        if is_total_fee_q:
            fee_data = fees.load_data()
            active_p = saved_prog_key or conv_state.get("active_program") or (profile.get("program_interest") if profile else None) or "btech_cse"
            active_p = active_p if active_p in fee_data["programs"] else "btech_cse"
            day = fees.calculate_fee(active_p)
            stay = fees.calculate_fee(active_p, hostel="non_ac_4")
            course = (f"• **Full course ({day['duration_years']} years, day scholar):** **{day['full_course_total']}**\n"
                      if day.get("full_course_total") else "")
            return {
                "text": (
                    f"Here's the total cost breakdown for **{fees.clean_program_name(active_p)}** (standard fee, before "
                    f"any scholarship):\n\n"
                    f"• **Year 1, day scholar:** **{day['first_year_total_payable']}** "
                    f"(Semester 1 {day['sem1_total_payable']} + Semester 2 {day['sem2_total_payable']})\n"
                    f"• **Year 1 with a Non-AC 4-sharing hostel:** **{stay['first_year_total_payable']}** "
                    f"(includes the hostel fee and the one-time electricity deposit)\n"
                    f"{course}"
                    f"• Application form {day['application_fee']} is paid separately.\n\n"
                    f"Shall I work out your scholarship from your 10+2 marks or entrance rank?"
                ),
                "cards": [],
                "suggestions": [
                    "Calculate scholarship for my marks",
                    "Explore hostel facilities",
                    "Change school / programme",
                ],
                "new_state": conv_state,
            }

        # If user wants to change school / course
        if any(k in low for k in ("change", "another", "different", "other course", "other program")):
            return {
                "text": f"Sure{', ' + user_name if user_name else ''}! Which school or programme would you like to explore next?",
                "cards": [build_school_selection_card()],
                "suggestions": [s["display_name"] for s in SCHOOLS_DATA],
                "new_state": {
                    "fee_flow_state": "awaiting_school_selection",
                    "fee_flow_school": None,
                    "fee_flow_prog": None,
                    "fee_flow_year": saved_year,
                },
            }

    return None
