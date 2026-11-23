"""Conversation manager: understands what the student is actually asking before anything is answered.

Runs before every other route in agent.run_agent, with no AI call. It handles four things:

1. BROAD TOPICS ("tell me about the hostel", "placements", "transport"): ask which aspect the student
   wants (one short question with chips). The reply ("Hostel fees.") is turned into a specific question
   ("What are the hostel fees?") that the normal routes answer, and nothing else about the hostel is added.
2. BROAD PROGRAMMES ("tell me about CSE", "B.Tech"): ask the branch if needed, then the aspect
   (eligibility, fees, curriculum, placements, faculty, labs, careers, admission process). The chosen aspect
   is asked about THAT programme only.
3. ADMISSION JOURNEY ("I want to join", "I'm interested", "I want to join B.Tech CSE", "am I eligible"):
   programme -> branch -> goal (eligibility / process / fees) -> marks -> subjects -> verdict from
   eligibility.py. Each step asks one question, never re-asks what the student already said, and keeps
   the programme for the rest of the conversation.
4. SHORT FOLLOW-UPS: "placements" / "fees" / "faculty" right after the student chose a programme are read
   as being about that programme.

Specific questions ("What are the hostel fees?", "CSE fees with 85%") are NOT touched: decide() returns
None and the existing routes answer directly.

State lives in conv_state["dialogue"]: {"step", "intent", "topic", "program", "degree", "goal"}.
"""
from __future__ import annotations

import re

from . import config, eligibility, fee_intake, fees

# ----------------------------------------------------------------------------------------------- topics
# Each aspect: chip label, words that select it, and the specific question it becomes. Only aspects with
# answers in the verified sources (or that the AI answers from the handbook) are offered.
TOPICS = {
    "hostel": {
        "words": r"hostels?|hostals?|hostles?|accommodation|accomodation|residen(?:ce|tial)(?:\s+life)?",
        "question": "Sure! What would you like to know about the hostel?",
        "aspects": [
            ("Room facilities", r"room|facilit|amenit|\bac\b|non[\s-]?ac|wi-?fi|sharing", "What are the hostel room facilities?"),
            ("Hostel fees", r"fee|cost|price|charge|how\s+much", "What are the hostel fees?"),
            ("Food & mess", r"food|mess|meal|dining|menu", "Tell me about the hostel mess and food."),
            ("Rules & timings", r"rule|curfew|timing|in[\s-]?time|out[\s-]?pass|discipline", "What are the hostel rules and timings?"),
            ("Safety & wardens", r"safe|secur|warden|cctv", "How safe is the hostel? Tell me about the wardens and security."),
        ],
    },
    "placements": {
        "words": r"placements?|placments?|placemnts?|placement\s+(?:cell|record|details)",
        "question": "Sure! What would you like to know about placements at SR University?",
        "aspects": [
            ("Packages & record", r"package|record|salary|lpa|highest|average|stat", "What is SR University's placement record: highest and average packages?"),
            ("Top recruiters", r"recruit|compan|employer|hiring", "Which companies recruit at SR University?"),
            ("Placement training", r"train|support|prepar|assist|process|cell", "How does SR University prepare and support students for placements?"),
            ("Internships", r"intern", "Tell me about internships at SR University."),
        ],
    },
    "admissions": {
        "words": r"admissions?(?:\s+details)?",
        "question": "Sure! What would you like to know about admissions?",
        "aspects": [
            ("Check my eligibility", r"eligib|qualif|marks|check", "__journey_eligibility__"),
            ("Admission process", r"process|apply|application|procedure|steps", "__journey_process__"),
            ("Fees & scholarships", r"fee|scholar|cost|waiver", "What is the fee structure for 2027-28?"),
            ("Documents required", r"document|certificate|papers", "What documents are required for admission?"),
        ],
    },
    "scholarships": {
        "words": r"scholarships?|scholorships?|scolarships?|scholership?s?|merit\s+scholarships?",
        "question": "Sure! What would you like to know about scholarships?",
        "aspects": [
            ("Merit scholarship slabs", r"slab|merit|criteria|how\s+much|percent|table", "What are the merit scholarship slabs for 2027-28?"),
            ("Calculate my scholarship", r"calculat|my\s+scholar|estimate|check", "Calculate my scholarship"),
            ("Special category concessions", r"special|concession|category|sports|defen[cs]e|single\s+parent|orphan", "What are the special category concessions?"),
        ],
    },
    "transport": {
        "words": r"transport(?:ation)?|tranport|bus(?:es)?|college\s+bus",
        "question": "Sure! What would you like to know about transport?",
        "aspects": [
            ("Transport fee", r"fee|cost|price|charge|how\s+much", "What is the transport fee?"),
            ("Bus routes", r"route|area|cover|stop|pick", "Which areas do the SR University buses cover?"),
            ("Transport contact", r"contact|incharge|in-charge|phone|number", "Who do I contact about transport?"),
        ],
    },
    "campus": {
        "words": r"campus(?:\s+facilities)?|facilities|infrastructure",
        "question": "Sure! Which campus facilities would you like to know about?",
        "aspects": [
            ("Labs", r"lab", "What labs and research facilities does SR University have?"),
            ("Hostel", r"hostel|accommodation", "__topic_hostel__"),
            ("Dining & cafeteria", r"food|dining|canteen|cafe", "Tell me about the campus canteen and cafeteria."),
            ("Library", r"librar|books", "Tell me about the SR University library."),
            ("Sports", r"sport|gym|ground|play", "What sports facilities does SR University have?"),
        ],
    },
    "faculty": {
        "words": r"faculty|professors?|teachers?|lecturers?",
        "question": "Sure! Which department's faculty would you like to know about?",
        "aspects": [
            ("Computer Science & AI", r"\bcse\b|computer|\bai\b|data", "Who are the faculty in the CSE department?"),
            ("ECE / EEE", r"\bece\b|\beee\b|electronic|electrical", "Who are the faculty in the ECE department?"),
            ("Mechanical / Civil", r"mech|civil", "Who are the faculty in the Mechanical department?"),
            ("Management", r"manag|business|mba|bba", "Who are the faculty in the School of Business?"),
            ("Agriculture", r"agri", "Who are the faculty in the School of Agriculture?"),
        ],
    },
    "labs": {
        "words": r"labs?|laborator(?:y|ies)",
        "question": "Sure! Which area's labs would you like to know about?",
        "aspects": [
            ("AI & Computer Science", r"\bai\b|comput|\bcse\b|data|software", "What AI and computer science labs does SR University have?"),
            ("Robotics & IoT", r"robot|iot|drone|embedded", "What robotics and IoT labs does SR University have?"),
            ("Electronics", r"electron|\bece\b|vlsi", "What electronics and VLSI labs does SR University have?"),
            ("Agriculture", r"agri|farm", "What agriculture labs and farms does SR University have?"),
        ],
    },
    "internships": {
        "words": r"internships?",
        "question": "Sure! What would you like to know about internships?",
        "aspects": [
            ("Internship opportunities", r"opportunit|available|where|compan", "What internship opportunities do SR University students get?"),
            ("Stipends", r"stipend|paid|salary|money", "Do SR University students get paid internships?"),
            ("Startups & SRiX", r"startup|srix|incubat|entrepreneur", "Tell me about SRiX and startup opportunities at SR University."),
        ],
    },
    "research": {
        "words": r"research(?:\s+opportunities)?",
        "question": "Sure! What would you like to know about research at SR University?",
        "aspects": [
            ("Research centres", r"cent(?:re|er)|lab|facilit", "What research centres does SR University have?"),
            ("Ph.D. programmes", r"ph\.?\s?d|doctor", "Tell me about Ph.D. programmes at SR University."),
            ("Research rankings", r"rank|quality|the\b", "What are SR University's research rankings?"),
            ("Startups & SRiX", r"startup|srix|incubat|innovation", "Tell me about SRiX and startup opportunities at SR University."),
        ],
    },
    "student_life": {
        "words": r"student\s+life|campus\s+life|clubs?|college\s+life",
        "question": "Sure! What part of student life would you like to know about?",
        "aspects": [
            ("Clubs & activities", r"club|activit|societ", "What clubs and student activities are there at SR University?"),
            ("Events & fests", r"event|fest|cultural|technical", "What events and fests happen at SR University?"),
            ("Hostel life", r"hostel|residen", "__topic_hostel__"),
            ("Sports", r"sport|game|gym", "What sports facilities does SR University have?"),
        ],
    },
    "events": {
        "words": r"events?|fests?|festivals?",
        "question": "Sure! Which kind of events would you like to know about?",
        "aspects": [
            ("Technical fests & hackathons", r"tech|hackathon|coding", "What technical fests and hackathons happen at SR University?"),
            ("Cultural events", r"cultur|dance|music", "What cultural events happen at SR University?"),
            ("Sports events", r"sport|game|tournament", "What sports events happen at SR University?"),
        ],
    },
    "departments": {
        "words": r"departments?|schools?",
        "question": "Sure! Which school or department would you like to know about?",
        "aspects": [
            ("Computer Science & AI", r"comput|\bcse\b|\bai\b", "__program_btech_cse__"),
            ("Engineering", r"engineer|ece|eee|mech|civil", "__degree_btech__"),
            ("Business (BBA / MBA)", r"business|manag|bba|mba", "__program_bba__"),
            ("Agriculture", r"agri", "__program_bsc_agri__"),
            ("Design", r"design", "__program_bdes__"),
        ],
    },
}

# Aspects of a programme, with the specific question each becomes ({p} = programme name).
PROGRAM_ASPECTS = [
    ("Eligibility", r"eligib|qualif|criteria|minimum|cut-?off|can\s+i\s+(?:join|get)", "__journey_eligibility__"),
    ("Fees", r"\bfees?\b|cost|tuition|how\s+much|price|scholar", "{p} fees"),
    ("Curriculum", r"curricul|syllab|subject|course\s+structure|what\s+will\s+i\s+(?:study|learn)", "What is the curriculum of {p}?"),
    ("Placements", r"placement|package|recruit|job", "What are the placements for {p}?"),
    ("Faculty", r"faculty|professor|teacher", "Who are the faculty for {p}?"),
    ("Labs", r"\blabs?\b|laborator|facilit", "What labs and facilities are there for {p}?"),
    ("Career opportunities", r"career|scope|future|opportunit", "What are the career opportunities after {p}?"),
    ("Admission process", r"process|apply|application|procedure|admission", "__journey_process__"),
]

_FILLER = re.compile(
    r"\b(?:tell|me|about|abt|what|whats|what's|wat|is|are|the|a|an|on|of|for|at|in|sru|sr|university|your|ur|"
    r"you|guys|please|pls|plz|can|could|would|give|share|some|any|info|information|details?|detail|overview|"
    r"know|want|wanna|to|i|explain|describe|more|regarding|related|all|show|let|us|do|have|how|hi|hello|"
    r"okay|ok|so|and|like|this|college|program|programme|course|branch)\b",
    re.IGNORECASE)
_DEGREE_WORDS = re.compile(r"\b(?:b\.?\s?tech|btech|engineering|bachelor\s+of\s+technology)\b", re.IGNORECASE)

_JOIN = re.compile(
    r"\b(?:(?:i\s+)?(?:want|wanna|would\s+like|wish|am\s+planning|planning|plan|looking|hope)\s+(?:to\s+)?"
    r"(?:join|apply|take\s+(?:an\s+)?admission|get\s+(?:an\s+)?admission|get\s+(?:a\s+)?seat|study)"
    r"|how\s+(?:can|do)\s+i\s+(?:join|get\s+(?:an\s+)?admission|get\s+(?:a\s+)?seat)"
    r"|can\s+i\s+(?:join|get\s+(?:an\s+)?admission|get\s+(?:a\s+)?seat)"
    r"|i\s+need\s+(?:an\s+)?admission|interested\s+in\s+joining|admission\s+(?:in|into|for)\b)",
    re.IGNORECASE)
_INTEREST_ONLY = re.compile(
    r"^\s*(?:hi|hello|hey)?[,\s]*(?:i\s*(?:am|'m|m)\s+|me\s+)?(?:very\s+|really\s+|so\s+)?interested"
    r"(?:\s+in\s+(?:sru|sr\s+university|this\s+university|your\s+university|it|this))?\s*[.!]*\s*$",
    re.IGNORECASE)
_ELIGIBILITY_Q = re.compile(r"\b(?:am\s+i\s+eligible|eligib\w*|can\s+i\s+get\s+(?:a\s+)?seat|minimum\s+marks|"
                            r"cut-?off|qualify\s+for\s+admission)\b", re.IGNORECASE)
_PROCESS_Q = re.compile(r"\b(?:how\s+(?:do|can)\s+i\s+apply|how\s+to\s+apply|application\s+process|"
                        r"admission\s+process|admission\s+procedure|steps\s+to\s+apply|apply\s+online)\b", re.IGNORECASE)
_GOALS = [
    ("eligibility", r"eligib|qualif|check|marks|criteria|can\s+i\s+(?:join|get)"),
    ("process", r"process|apply|application|procedure|steps|how\s+to\s+join"),
    ("fees", r"\bfees?\b|cost|scholar|tuition|how\s+much"),
]
# A whole message that is only an aspect word ("fees", "placements?", "syllabus") is a follow-up about the
# programme being discussed. Anything longer ("calculate my scholarship") is a question of its own.
_ASPECT_ONLY = re.compile(
    r"(?:fees?|fee\s+structure|cost|tuition|placements?|packages?|curriculum|syllabus|subjects|faculty|"
    r"professors|labs?|eligibility|careers?|career\s+opportunities|scope|admission\s+process)", re.IGNORECASE)
_SKIP_WORDS = re.compile(r"^\s*(?:skip|no|nope|not\s+now|later|never\s*mind|cancel|stop)\b", re.IGNORECASE)

_SHORT = {"btech_cse": "B.Tech CSE", "btech_ece": "B.Tech ECE", "btech_eee": "B.Tech EEE",
          "btech_mech": "B.Tech Mechanical", "btech_civil": "B.Tech Civil", "btech_ai_robotics": "B.Tech AI & Robotics",
          "bsc_agri": "B.Sc Agriculture", "bba": "BBA", "mba": "MBA", "bca": "BCA", "mca": "MCA", "bcom": "B.Com",
          "bdes": "B.Des", "mtech": "M.Tech", "msc": "M.Sc"}


def short_name(key: str) -> str:
    return _SHORT.get(key) or fees.clean_program_name(key)


def _norm(message: str) -> str:
    low = (message or "").lower()
    low = re.sub(r"[?!.,;:'\"()]+", " ", low)
    return re.sub(r"\s+", " ", low).strip()


def _strip_filler(text: str) -> str:
    return re.sub(r"\s+", " ", _FILLER.sub(" ", text)).strip()


def _program_in(message: str) -> str | None:
    """Programme key named in the message (not a generic 'B.Tech')."""
    return fees.find_program(message or "")


def _generic_btech(message: str) -> bool:
    return bool(_DEGREE_WORDS.search(message or "")) and not _program_in(message)


def _broad_topic(message: str) -> str | None:
    """Topic name when the whole message is just that topic ("tell me about the hostel", "placements?")."""
    rest = _strip_filler(_norm(message))
    if not rest:
        return None
    for name, topic in TOPICS.items():
        if re.fullmatch(rf"(?:{topic['words']})", rest):
            return name
    return None


def _broad_program(message: str) -> tuple[str | None, bool]:
    """(program_key, generic_btech) when the whole message only names a programme ("CSE", "tell me about B.Tech")."""
    low = _norm(message)
    key = _program_in(low)
    rest = low
    if key:
        aliases = sorted(fees.load_data()["programs"][key]["aliases"] + [short_name(key).lower()], key=len, reverse=True)
        for alias in aliases:
            rest = re.sub(rf"(?<![a-z]){re.escape(alias.lower())}(?![a-z])", " ", rest)
    rest = _DEGREE_WORDS.sub(" ", rest)
    rest = re.sub(r"\b(?:b\s?sc|bsc|hons|bachelor|degree|engineering|school|department|dept)\b", " ", rest)
    rest = _strip_filler(rest)
    if rest:
        return None, False
    if key:
        return key, False
    if _DEGREE_WORDS.search(low):
        return None, True
    return None, False


def _pick(message: str, options: list[tuple]) -> tuple | None:
    """The option a reply selects: exact chip label first, then the option's words."""
    low = _norm(message)
    for opt in options:
        if low == _norm(opt[0]):
            return opt
    for opt in options:
        if re.search(opt[1], low, re.IGNORECASE):
            return opt
    return None


def _ask(text: str, chips: list[str], state: dict) -> dict:
    return {"kind": "reply", "text": text, "chips": chips[:4], "state": state}


def _rewrite(message: str, state: dict | None, profile_updates: dict | None = None) -> dict:
    return {"kind": "rewrite", "message": message, "state": state, "profile_updates": profile_updates or {}}


# ------------------------------------------------------------------------------------------ the journey
def _ask_program(intent: str, state: dict) -> dict:
    state.update(step="program", intent=intent)
    if intent == "join":
        text = "That's great! Which programme or course are you interested in joining at SR University?"
    else:
        text = "Sure! Which programme would you like to explore?"
    return _ask(text, ["B.Tech", "BBA", "MBA", "B.Sc Agriculture"], state)


def _ask_branch(intent: str, state: dict) -> dict:
    state.update(step="branch", intent=intent, degree="btech")
    text = ("Great! Which B.Tech branch are you interested in, such as CSE (with AI & ML, Data Science or Cyber "
            "Security specialisations), AI & Robotics, ECE, EEE, Mechanical or Civil?")
    return _ask(text, ["CSE", "AI & Robotics", "ECE", "Mechanical"], state)


def _ask_goal(key: str, state: dict, name_first: str = "Great! ") -> dict:
    state.update(step="goal", intent="join", program=key)
    p = short_name(key)
    text = f"{name_first}Are you looking to check your {p} eligibility, understand the admission process, or know the fees?"
    return _ask(text, ["Check my eligibility", "Admission process", f"{p} fees"], state)


def _ask_aspect(key: str, state: dict, lead: str = "Sure! ") -> dict:
    state.update(step="program_aspect", intent="explore", program=key)
    p = short_name(key)
    text = (f"{lead}What would you like to explore about {p}: admission eligibility, fees, curriculum, placements, "
            f"faculty, labs or career opportunities?")
    return _ask(text, ["Eligibility", "Fees", "Placements", "Curriculum"], state)


def _process_text(key: str | None) -> str:
    """How to apply, from sru.edu.in/admission (handbook 11, section 5). Nothing beyond what it states."""
    for_p = f" for **{short_name(key)}**" if key else ""
    return (f"Here is how to apply{for_p} (from the official admission page, sru.edu.in/admission):\n\n"
            f"1. **Register online** on the admission portal: {config.APPLY_URL}\n"
            "2. **Complete the application**: enter your details, choose the programme and upload your documents.\n"
            "3. **Submit your scores**: JEE Main or EAPCET result where available; your Intermediate / 10+2 marks "
            "are used for merit scholarships.\n"
            "4. **Confirm your seat**: accept the offer and pay the fee.\n\n"
            "The official page does not list the documents to upload, the important dates or the refund policy; "
            f"the Admissions Office confirms these ({config.ADMISSIONS_PHONE}, info@sru.edu.in).")


def _marks_question(key: str) -> str:
    if fees.load_data()["programs"][key].get("level") == "pg":
        return (f"Sure! To check your {short_name(key)} eligibility, what percentage did you score (or expect) in your "
                f"bachelor's degree?")
    return (f"Sure! To check your {short_name(key)} eligibility, please share your 10+2 / Intermediate marks: a "
            f"percentage (for example 78%), or your marks with the total (for example 850 out of 1000).")


def _read_marks(message: str, state: dict) -> dict:
    """{'percent', 'raw', 'max'} from the reply, or {'raw_only': n} when the total is missing."""
    said = fee_intake.parse_details(message)
    if said.get("raw_marks") is not None and said.get("max_marks"):
        exact = eligibility.percent_from_marks(said["raw_marks"], said["max_marks"])
        if exact is not None:
            return {"percent": exact, "raw": float(said["raw_marks"]), "max": float(said["max_marks"])}
    if said.get("percent") is not None and said.get("cgpa") is None:
        return {"percent": float(said["percent"])}
    number = fee_intake._bare_number(message)
    if state.get("pending_raw") is not None and number is not None and number >= state["pending_raw"]:
        exact = eligibility.percent_from_marks(state["pending_raw"], number)
        if exact is not None:
            return {"percent": exact, "raw": float(state["pending_raw"]), "max": float(number)}
    raw = said.get("raw_marks") or (number if number is not None and number > 100 else None)
    if raw is not None:
        return {"raw_only": float(raw)}
    if number is not None and 0 <= number <= 100:
        return {"percent": float(number)}
    return {}


def _verdict_reply(key: str, marks: dict, stream: str | None, state: dict) -> dict:
    verdict = eligibility.assess(key, marks["percent"], stream)
    score_text = (f"{fee_intake._num(marks['raw'])} marks out of {fee_intake._num(marks['max'])}"
                  if marks.get("max") and marks["max"] > 100 else None)
    updates = {"percent": round(marks["percent"], 2), "program_interest": key}
    if marks.get("raw") is not None:
        updates.update(raw_marks=marks["raw"], max_marks=marks["max"])
    if verdict["needs_stream"] and verdict["status"] != eligibility.BELOW:
        state.update(step="stream", program=key, marks=marks)
        return {**_ask(eligibility.stream_question(verdict), eligibility.stream_chips(verdict), state),
                "profile_updates": updates}
    p = short_name(key)
    if verdict["status"] == eligibility.BELOW or verdict.get("stream_ok") is False:
        chips = ["Talk to an admissions counsellor"]
    elif verdict["status"] == eligibility.CONFIRM:
        chips = ["Talk to an admissions counsellor", f"{p} fees"]
    else:
        chips = [f"{p} fees & scholarship", f"{p} admission process", f"{p} placements"]
    if stream:
        updates["stream"] = stream
    state.update(step=None, goal=None, marks=None, pending_raw=None, program=key)
    return {"kind": "reply", "text": eligibility.explain(verdict, score_text), "chips": chips, "state": state,
            "profile_updates": updates, "eligible": verdict["eligible"]}


def _eligibility_step(key: str, message: str, state: dict, profile: dict, first_time: bool) -> dict:
    """Ask for marks, or decide with the marks the student already gave (in this message or earlier)."""
    marks = _read_marks(message, state)
    if not marks and first_time and profile.get("percent") is not None and \
            fees.load_data()["programs"][key].get("level") != "pg":
        marks = {"percent": float(profile["percent"])}
        if profile.get("raw_marks") and profile.get("max_marks"):
            marks.update(raw=float(profile["raw_marks"]), max=float(profile["max_marks"]))
            exact = eligibility.percent_from_marks(marks["raw"], marks["max"])
            marks["percent"] = exact if exact is not None else marks["percent"]
    if marks.get("raw_only") is not None:
        raw = fee_intake._num(marks["raw_only"])
        state.update(step="total", program=key, goal="eligibility", pending_raw=marks["raw_only"])
        return _ask(f"Thanks! Out of how many total marks is **{raw}**? For example, 1000 for TS / AP Intermediate, "
                    f"or 500 / 600 for some other boards.", [f"{raw} out of 1000", f"{raw} out of 600", f"{raw} out of 500"],
                    state)
    if marks.get("percent") is None:
        state.update(step="marks", program=key, goal="eligibility")
        return _ask(_marks_question(key), [], state)
    stream = eligibility.parse_stream(message) if re.search(r"\b(?:mpc|pcm|bipc|pcb)\b", message.lower()) else None
    return _verdict_reply(key, marks, stream or profile.get("stream"), state)


def _goal_reply(goal: str, key: str, message: str, state: dict, profile: dict) -> dict:
    if goal == "eligibility":
        return _eligibility_step(key, message, state, profile, first_time=True)
    if goal == "process":
        state.update(step=None, goal=None, program=key)
        p = short_name(key)
        return {"kind": "reply", "text": _process_text(key), "chips": ["Check my eligibility", f"{p} fees", "Talk to an admissions counsellor"],
                "state": state, "profile_updates": {"program_interest": key}}
    state.update(step=None, goal=None, program=key)
    return _rewrite(f"{fees.clean_program_name(key)} fees", state, {"program_interest": key})


def _resolve_special(target: str, state: dict, profile: dict, message: str) -> dict | None:
    """Aspect targets that continue the dialogue instead of becoming a question."""
    if target == "__journey_eligibility__":
        key = state.get("program")
        if key:
            return _eligibility_step(key, "", state, profile, first_time=True)
        state.update(goal="eligibility")
        return _ask_program("join", state) | {"state": {**state, "step": "program", "goal": "eligibility"}}
    if target == "__journey_process__":
        key = state.get("program")
        state.update(step=None)
        chips = ["Check my eligibility", "Fees & scholarships", "Talk to an admissions counsellor"]
        if not key:
            text = _process_text(None) + "\n\nWhich programme are you considering? I can check your eligibility for it."
            state.update(step="program", intent="join", goal=None)
            return _ask(text, ["B.Tech", "BBA", "MBA", "B.Sc Agriculture"], state)
        return {"kind": "reply", "text": _process_text(key), "chips": chips, "state": state, "profile_updates": {}}
    if target.startswith("__topic_"):
        topic = target[len("__topic_"):-2]
        return _ask_topic(topic, state)
    if target == "__degree_btech__":
        return _ask_branch("explore", state)
    if target.startswith("__program_"):
        return _ask_aspect(target[len("__program_"):-2], state)
    return None


def _ask_topic(topic: str, state: dict, program: str | None = None) -> dict:
    t = TOPICS[topic]
    state.update(step="topic_aspect", topic=topic, intent="explore")
    chips = [a[0] for a in t["aspects"]]
    labels = [a[0].lower() for a in t["aspects"]]
    text = f"{t['question']} For example: {', '.join(labels[:-1])} or {labels[-1]}."
    return _ask(text, chips, state)


# ------------------------------------------------------------------------------------------- decide()
def decide(message: str, conv_state: dict, profile: dict) -> dict | None:
    """What to do with this message before any other route. None = not handled (state unchanged).
    Otherwise a dict with kind 'reply' (send text + chips), 'rewrite' (continue with a more specific
    message) or 'pass' (continue as is), plus the new dialogue state."""
    original = dict(conv_state.get("dialogue") or {})
    state = dict(original)
    step = state.get("step")
    low = _norm(message)
    program_now = _program_in(message)

    # ---- 1. An answer to our own last question -------------------------------------------------------
    if step:
        if _SKIP_WORDS.match(low) and len(low.split()) <= 3:
            return {"kind": "reply", "text": "No problem! What else would you like to know about SR University?",
                    "chips": ["Explore programmes", "Hostel", "Placements", "Scholarships"], "state": {}}
        if step == "topic_aspect":
            topic = TOPICS.get(state.get("topic") or "")
            opt = _pick(message, topic["aspects"]) if topic else None
            if opt:
                special = _resolve_special(opt[2], state, profile, message)
                if special:
                    return special
                return _rewrite(opt[2], {"program": state.get("program")} if state.get("program") else {})
        elif step == "program_aspect":
            key = state.get("program")
            opt = _pick(message, PROGRAM_ASPECTS)
            if key and opt:
                special = _resolve_special(opt[2], state, profile, message)
                if special:
                    return special
                return _rewrite(opt[2].format(p=fees.clean_program_name(key)), {"program": key},
                                {"program_interest": key})
        elif step == "program":
            if program_now:
                if state.get("goal"):
                    return _goal_reply(state["goal"], program_now, message, state, profile)
                if state.get("intent") == "join":
                    return _ask_goal(program_now, state)
                return _ask_aspect(program_now, state, lead="Great choice! ")
            if _generic_btech(message):
                return _ask_branch(state.get("intent") or "join", state)
        elif step == "branch":
            if program_now:
                if state.get("goal"):
                    return _goal_reply(state["goal"], program_now, message, state, profile)
                if state.get("intent") == "join":
                    return _ask_goal(program_now, state)
                return _ask_aspect(program_now, state, lead="Great choice! ")
        elif step == "goal":
            key = state.get("program")
            goal = next((g for g, pat in _GOALS if re.search(pat, low)), None)
            if key and goal:
                return _goal_reply(goal, key, message, state, profile)
        elif step in ("marks", "total"):
            key = state.get("program")
            marks = _read_marks(message, state)
            if key and (marks.get("percent") is not None or marks.get("raw_only") is not None):
                return _eligibility_step(key, message, state, profile, first_time=False)
        elif step == "stream":
            key, marks = state.get("program"), state.get("marks")
            stream = eligibility.parse_stream(message)
            if key and marks and stream:
                return _verdict_reply(key, marks, stream, state)
        elif step == "interest":
            if program_now:
                return _ask_aspect(program_now, state)
            if _generic_btech(message):
                return _ask_branch("explore", state)
            if re.fullmatch(r"admissions?", _strip_filler(low)):
                return _ask_topic("admissions", state)
            if re.fullmatch(r"(?:a\s+)?(?:particular\s+)?(?:programmes?|programs?|courses?|degrees?)", low):
                return _ask_program("explore", state)
            if re.search(r"admission|join|apply|eligib", low):
                return _ask_program("join", state)
            topic = _broad_topic(message) or next((n for n, t in TOPICS.items() if re.search(rf"\b(?:{t['words']})\b", low)), None)
            if topic:
                return _ask_topic(topic, state)

        # Not an answer to our question: drop the question (keep the programme being discussed) and treat
        # the message as a new question below.
        state = {"program": state.get("program")} if state.get("program") else {}

    # ---- 2. Admission intent and vague interest ------------------------------------------------------
    from . import intents
    if re.match(r"\s*(?:school\s+of|astra\s+school)\b", low):
        # A tap on the school card ("School of Engineering"): the course browser continues it.
        return {"kind": "pass", "state": state} if state != original else None
    if intents.is_branch_guidance_query(message):
        # "850 marks, planning to join B.Tech, which branch?" is a specific request: branch guidance answers it.
        return {"kind": "pass", "state": state} if state != original else None

    if _INTEREST_ONLY.match(message or ""):
        state.update(step="interest", intent="explore")
        return _ask("That's great! What are you interested in exploring at SR University: admissions, a particular "
                    "programme, scholarships, campus life, or something else?",
                    ["Admissions", "Programmes", "Scholarships", "Campus life"], state)

    wants_join = bool(_JOIN.search(message or ""))
    asks_eligibility = bool(_ELIGIBILITY_Q.search(message or ""))
    asks_process = bool(_PROCESS_Q.search(message or ""))
    if asks_process:
        key = program_now or state.get("program")
        return _resolve_special("__journey_process__", {**state, "program": key} if key else state, profile, message)

    if wants_join or asks_eligibility:
        key = program_now or (state.get("program") if asks_eligibility else None)
        marks = _read_marks(message, state)
        if key:
            if asks_eligibility or marks:
                state.update(intent="join", goal="eligibility")
                return _eligibility_step(key, message, state, profile, first_time=True)
            return _ask_goal(key, state)
        if _generic_btech(message):
            state.update(goal="eligibility" if (asks_eligibility or marks) else None)
            return _ask_branch("join", state)
        if marks.get("percent") is not None and marks["percent"] < eligibility.lowest_minimum_any_program("ug"):
            # Below the lowest minimum of every programme: say so now, whatever the programme.
            known = {"percent": marks["percent"], "raw_marks": marks.get("raw"), "max_marks": marks.get("max")}
            out = fee_intake.format_ineligible_response(known, {})
            return {"kind": "reply", "text": out["text"], "chips": ["Talk to an admissions counsellor"],
                    "state": {}, "eligible": False}
        state.update(goal="eligibility" if asks_eligibility else None)
        if asks_eligibility and not wants_join:
            # "What is the eligibility criteria?": the overview from the data, then which programme.
            state.update(step="program", intent="join", goal="eligibility")
            if profile.get("percent") is not None:
                # Marks already given: do not ask again, only the programme is missing.
                pct = eligibility.show_percent(float(profile["percent"]))
                return _ask(f"I have your marks (**{pct}**). Admission eligibility depends on the programme, because "
                            f"the minimum marks differ between programmes. Which programme are you interested in?",
                            ["B.Tech CSE", "BBA", "MBA", "B.Sc Agriculture"], state)
            return _ask(eligibility.overview_text() + "\n\nWhich programme are you interested in? Share your marks and "
                        "I'll check your eligibility for it.", ["B.Tech CSE", "BBA", "MBA", "B.Sc Agriculture"], state)
        return _ask_program("join", state)

    # ---- 3. Broad topic / programme ------------------------------------------------------------------
    this_ref = re.search(r"\bthis\s+(?:branch|course|programme|program)\b", low)
    topic = _broad_topic(re.sub(r"\bthis\s+(?:branch|course|programme|program)\b", " ", low)) if this_ref else _broad_topic(message)
    if this_ref and not state.get("program") and topic in ("placements", "faculty", "labs"):
        return _ask_program("explore", state)
    # Right after a fee answer, "what about hostel?" / "and transport?" means that topic's fee.
    if topic and conv_state.get("active_topic") in ("fee", "scholarship", "hostel_fee", "fees"):
        fee_aspect = next((a for a in TOPICS[topic]["aspects"] if "fee" in a[0].lower()), None)
        if fee_aspect:
            return _rewrite(fee_aspect[2], state)
    if topic == "placements" and state.get("program"):
        key = state["program"]
        return _rewrite(f"What are the placements for {fees.clean_program_name(key)}?", {"program": key})
    if topic in ("faculty", "labs") and state.get("program"):
        key = state["program"]
        aspect = "Faculty" if topic == "faculty" else "Labs"
        target = next(a[2] for a in PROGRAM_ASPECTS if a[0] == aspect)
        return _rewrite(target.format(p=fees.clean_program_name(key)), {"program": key})
    if topic:
        return _ask_topic(topic, state)

    key, generic = _broad_program(message)
    if key:
        return _ask_aspect(key, state)
    if generic:
        return _ask_branch("explore", state)

    # ---- 4. Short follow-up about the programme already being discussed ("fees", "curriculum") -------
    if state.get("program") and not program_now and _ASPECT_ONLY.fullmatch(_strip_filler(low) or "-"):
        opt = _pick(message, PROGRAM_ASPECTS)
        if opt and not opt[2].startswith("__"):
            key = state["program"]
            return _rewrite(opt[2].format(p=fees.clean_program_name(key)), {"program": key})
        if opt:
            special = _resolve_special(opt[2], dict(state), profile, message)
            if special:
                return special

    if program_now and program_now != state.get("program"):
        # A specific question about a programme: remember it as the conversation's programme.
        return {"kind": "pass", "state": {"program": program_now}}
    if state != original:
        return {"kind": "pass", "state": state}
    return None
