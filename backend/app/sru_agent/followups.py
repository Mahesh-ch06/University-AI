"""Follow-up suggestion chips for the agent: about what the student just asked, not generic.

The topic comes first from the tool that answered (a fee calculation, a faculty search ...), then
from whole words in the student's message. The answer text is NOT used to pick the topic: most
answers end with an offer such as "shall I calculate your fee?", which used to turn every chip
row into fee chips. Every chip is a question SRU Buddy can answer, and a chip that repeats what
the student just asked is dropped.
"""
import re

from . import fees

# (topic, pattern on the student's message), checked in order; the first match wins.
_TOPICS = [
    ("tour_choice", r"\b(?:campus\s+tour|college\s+tour|walkthrough|see\s+the\s+campus)\b"),
    ("visit", r"\b(?:visit|visiting|come\s+to\s+(?:the\s+)?campus)\b"),
    ("faculty", r"\b(?:faculty|faculties|professors?|lecturers?|teachers?|hod|dean|deans|head\s+of)\b"),
    ("next_gen", r"\b(?:next[\s-]?gen|ai\s+(?:&|and)\s+robotics|quantum\s+ai|precision\s+agric\w*|robotics\s+(?:&|and)\s+automation)\b"),
    ("concessions", r"\b(?:concessions?|sibling|defen[cs]e|single\s+parent|orphan|sports\s+quota|girl\s+child|"
                    r"special\s+category)\b"),
    ("transport", r"\b(?:bus|buses|transport|transportation|commute|route|routes)\b"),
    ("hostel", r"\b(?:hostels?|mess|warden|curfew|in-?time|room\s+(?:type|sharing)|ac\s+room|non-?ac)\b"),
    ("compare", r"\b(?:vs|versus|compare|comparison|difference\s+between|better\s+than)\b"),
    ("career_guidance", r"\b(?:confused|not\s+sure|don'?t\s+know|what\s+(?:to|should\s+i)\s+study|which\s+(?:course|branch|stream)|options?\s+after\s+(?:mpc|bipc|inter|12th)|career\s+options?|suggest\s+a\s+course|what\s+clicks)\b"),
    ("scholarship", r"\b(?:scholarships?|waiver|merit)\b"),
    ("fee", r"\b(?:fee|fees|fess|tuition|cost|how\s+much|per\s+sem\w*)\b"),
    ("eligibility", r"\b(?:eligib\w*|cut-?off|minimum\s+marks|can\s+i\s+(?:join|get|apply))\b"),
    ("apply", r"\b(?:apply|application|admission\s+process|how\s+to\s+join|last\s+date|deadline|counselling)\b"),
    ("documents", r"\b(?:documents?|certificates?|tc|marksheet)\b"),
    ("placements", r"\b(?:placements?|package|lpa|ctc|recruiters?|jobs?|internships?|salary|career)\b"),
    ("international", r"\b(?:international|abroad|foreign|2\s*\+\s*2|exchange|overseas)\b"),
    ("research", r"\b(?:research|patents?|startups?|srix|nest|incubat\w*|innovation)\b"),
    ("academics", r"\b(?:attendance|detention|exams?|grading|cgpa|gpa|credits?|minors?|honou?rs|syllabus|"
                  r"curriculum|subjects?)\b"),
    ("about", r"\b(?:rank|ranking|rankings|nirf|naac|nba|accredit\w*|ugc|why\s+sru|why\s+choose|about\s+sru|"
              r"reputation|good\s+university|is\s+sru\s+good|recogni[sz]ed|valid)\b"),
    ("campus", r"\b(?:campus|library|labs?|sports|gym|wifi|facilities|infrastructure|canteen)\b"),
    ("programs", r"\b(?:courses?|programmes?|programs?|branches?|speciali[sz]ations?|b\.?\s?tech|mba|bba|b\.?des|"
                 r"agriculture)\b"),
]
_TOOL_TOPIC = {"calculate_fee": "fee_personal", "share_fee_estimate": "fee_personal",
               "check_eligibility": "eligibility", "get_program_info": "programs", "compare_programs": "compare",
               "get_special_concessions": "concessions", "find_faculty": "faculty",
               "request_counsellor_callback": "after_request", "request_campus_visit_callback": "after_request",
               "get_university_videos": "virtual_tour"}


def _short_program(profile: dict) -> str | None:
    key = fees.find_program(str((profile or {}).get("program_interest") or ""))
    if not key:
        return None
    return fees.load_data()["programs"][key]["name"].split(" (")[0]


def _short_dept(name: str) -> str:
    return (name.replace("Computer Science & Artificial Intelligence", "CSE & AI")
            .replace("Electronics & Communication Engineering", "ECE")
            .replace("Electrical & Electronics Engineering", "EEE").replace(" Engineering", "")
            .replace("Astra School of Business", "the business school").replace("School of ", ""))


def _chips(topic: str, program: str | None, department: str | None, message: str = "") -> list[str]:
    p = program or "B.Tech CSE"
    mine = program or "my course"
    low = (message or "").lower()

    if topic == "hostel":
        if re.search(r"\b(?:fee|fees|cost|price|how\s+much|rent|pay)\b", low):
            return ["AC vs Non-AC room fees", "Mess charges", "Double-sharing availability", "Hostel fee payment details"]
        if re.search(r"\b(?:mess|food|dining|meal|canteen|eating)\b", low):
            return ["Does fee include mess?", "Mess timings & food", "AC vs Non-AC room fees", "Hostel in-time rules"]
        return ["AC vs Non-AC room fees", "Mess & dining facilities", "Hostel in-time rules", "Hostel room sharing options"]

    if topic == "placements":
        if re.search(r"\b(?:guarantee|guaranteed|98%|100%|sure)\b", low):
            return ["Placement assistance policy", "Top recruiters & packages", "Average package by branch", "Internship training"]
        return ["Top recruiters & packages", "Average package by branch", "Placement training and internships", "Placement assistance policy"]

    table = {
        "fee_personal": ["Special category concessions", f"Add hostel to my {mine} fee",
                         f"Eligibility for {p}", "How do I apply for 2027-28?", "How is the fee paid each semester?"],
        "fee": ["Scholarship for my marks", "Special category concessions", "Hostel fees", "How do I apply for 2027-28?"],
        "scholarship": ["Scholarship for my marks", "Special category concessions",
                        "Do I keep my scholarship every year?", f"{p} fee after scholarship"],
        "concessions": ["Calculate my fee with scholarship", "Documents for a concession", "How do I apply for 2027-28?",
                        "Talk to a counsellor"],
        "next_gen": ["Fee for AI & Robotics", "B.Tech CSE fee structure", "Calculate my scholarship", "How do I apply for 2027-28?"],
        "eligibility": [f"{p} fee with my marks", "How do I apply for 2027-28?", "Documents needed for admission",
                        f"Placements for {p}"],
        "programs": [f"{p} fee and scholarship", f"Eligibility for {p}", "Who are the faculty?", f"Placements for {p}"],
        "compare": ["Scholarship for my marks", "Placement record by branch", "Faculty in each department",
                    "How do I apply for 2027-28?"],
        "career_guidance": ["I like computers", "I like building things", "People and numbers", "Still not sure"],
        "faculty": ([f"Faculty research areas in {_short_dept(department)}", f"Placements for {p}",
                     "Heads of all departments",
                     "Deans of all schools"] if department else
                    ["Heads of all departments", "Deans of all schools", "Faculty working on AI",
                     "Research centres at SRU"]),
        "placements": ["Top recruiters & packages", "Average package by branch", "Placement training and internships",
                       "Placement assistance policy"],
        "hostel": ["AC vs Non-AC room fees", "Mess & dining facilities", "Hostel in-time rules", "Hostel room sharing options"],
        "transport": ["Bus routes and stops", "Transport fee", "Hostel options", "How to reach the campus"],
        "tour_choice": ["🎥 Virtual Tour (Videos & Info)", "🏛️ In-Person Campus Visit"],
        "virtual_tour": ["🏛️ In-Person Campus Visit", "Hostel details", "Why choose SRU?"],
        "visit": ["Ask counsellor to call me", "How to reach the campus", "🎥 Virtual Tour (Videos & Info)", "Hostel details"],
        "apply": ["Documents needed for admission", "Application fee", "Scholarship for my marks", "Talk to a counsellor"],
        "documents": ["How do I apply for 2027-28?", "Scholarship for my marks", "Talk to a counsellor"],
        "about": ["Placement record", "Faculty and research", "International partnerships", "Scholarship for my marks"],
        "international": ["2+2 study abroad programme", "Scholarships for international students", "Placement record",
                          "How do I apply for 2027-28?"],
        "research": ["SRiX startup incubator", "Research centres at SRU", "Faculty research areas", "Placement record"],
        "academics": ["Attendance rule", "Exams and grading", "Minors and honours", "Placement record"],
        "campus": ["🎥 Virtual Tour (Videos & Info)", "🏛️ In-Person Campus Visit", "Sports facilities", "Hostel details"],
        "after_request": ["Scholarship for my marks", "Documents needed for admission", "How to reach the campus",
                          "Hostel details"],
        "default": ["Fee and scholarship for my marks", "Placement record", "Why choose SRU?", "Plan a campus visit"],
    }
    return table.get(topic, table["default"])


_STOP = set("the a an of for to and or my is are what how do i me in on at with about sru tell can".split())


def _overlaps(chip: str, message: str) -> bool:
    """Would this chip just repeat the student's own question?"""
    words = [w for w in re.findall(r"[a-z0-9+]+", chip.lower()) if w not in _STOP and len(w) > 2]
    if not words:
        return False
    msg = set(re.findall(r"[a-z0-9+]+", message.lower()))
    return sum(1 for w in words if w in msg) / len(words) >= 0.5


def topic_of(message: str, tools_used: list | None = None, active_topic: str | None = None) -> str:
    for t in tools_used or []:
        name = t.get("name") if isinstance(t, dict) else t
        if name in _TOOL_TOPIC and (not isinstance(t, dict) or t.get("status") in ("ok", "saved", "calculated")):
            return _TOOL_TOPIC[name]
    low = (message or "").lower()
    if active_topic == "hostel" and re.search(r"\b(?:fee|fees|cost|how\s+much|charge|charges|rent|annual\s+fee)\b", low):
        if not re.search(r"\b(?:b\.?tech|m\.?tech|bba|mba|bca|mca|b\.?sc|course|branch|engineering|tuition)\b", low):
            return "hostel"
    for topic, pattern in _TOPICS:
        if re.search(pattern, message or "", re.IGNORECASE):
            return topic
    if active_topic and active_topic in (
        "hostel", "placements", "fee", "scholarship", "programs", "faculty", "campus_visit", "transport", "concessions"
    ):
        return active_topic
    return "default"


FIXED_ADMISSION_CHIP = "💰 Fee & Scholarship Info"
FIXED_ADMISSION_ALT = "How do I apply for 2027-28?"
FIXED_UNIVERSITY_CHIP = "🏫 Why Choose SRU?"
FIXED_UNIVERSITY_ALT = "Plan a campus visit"


def needs_yes_no(answer: str | None) -> bool:
    """Detect if the answer ends with a binary / confirmation question that invites Yes or No."""
    if not answer:
        return False
    text = answer.strip()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if not lines:
        return False
    last_line = lines[-1]
    
    if not last_line.endswith("?"):
        return False
        
    low = last_line.lower()
    
    # Exclude open-ended questions starting with question words
    if re.match(r"^(?:what|which|who|where|how|why|when)\b", low):
        return False
    # "Would you like to explore courses or check the fees?" offers a choice, not a yes / no: a "Yes" chip
    # would be meaningless there.
    question = re.split(r"(?<=[.!])\s+", last_line)[-1].lower()
    if re.search(r"\bor\b", question):
        return False
        
    # Check if it starts with or contains binary question stems
    binary_stems = [
        r"\b(?:would you like|would you want|do you want|shall i|should i|can i|may i)\b",
        r"\b(?:want me to|like me to|interested in|wish to)\b",
        r"\b(?:are you interested|do you have|have you)\b",
        r"\b(?:could i|shall we|can we)\b",
    ]
    for pattern in binary_stems:
        if re.search(pattern, low):
            return True
            
    return False


def ensure_fixed_chips(chips: list[str] | None = None, answer: str | None = None, message: str = "") -> list[str]:
    """Ensure exactly 4 chips: 2 contextual + 2 fixed (admission + university),
    or Yes/No + 2 fixed if the assistant response ends with a binary question."""
    if needs_yes_no(answer):
        return ["Yes", "No"]   # the answer to the question just asked; nothing else to pick from
        
    contextual = [c for c in (chips or []) if c not in (FIXED_ADMISSION_CHIP, FIXED_UNIVERSITY_CHIP)]
    
    # Take top 2 contextual chips
    top_contextual = contextual[:2] if len(contextual) >= 2 else (contextual + [c for c in _chips("default", None, None) if c not in contextual])[:2]
    
    # Check for overlaps with fixed chips
    low_ctx = " ".join(top_contextual).lower()
    
    adm_chip = FIXED_ADMISSION_ALT if ("fee" in low_ctx or "scholarship" in low_ctx) else FIXED_ADMISSION_CHIP
    if adm_chip.lower() in low_ctx:
        adm_chip = "How do I apply for 2027-28?"
        
    uni_chip = FIXED_UNIVERSITY_ALT if ("why choose" in low_ctx or "about" in low_ctx or "ranking" in low_ctx) else FIXED_UNIVERSITY_CHIP
    if uni_chip.lower() in low_ctx:
        uni_chip = "Plan a campus visit"
        
    result = []
    for c in top_contextual:
        if c not in result:
            result.append(c)
    if adm_chip not in result and len(result) < 3:
        result.append(adm_chip)
    if uni_chip not in result and len(result) < 4:
        result.append(uni_chip)
        
    # If still less than 4, fill with fallbacks
    fallbacks = [FIXED_ADMISSION_CHIP, FIXED_UNIVERSITY_CHIP, "Plan a campus visit", "How do I apply for 2027-28?"]
    for fb in fallbacks:
        if len(result) >= 4:
            break
        if fb not in result:
            result.append(fb)
            
    return result[:4]


def suggest(message: str, tools_used: list | None = None, profile: dict | None = None,
            department: str | None = None, limit: int = 4, history: list | None = None,
            active_topic: str | None = None, answer: str | None = None) -> list[str]:
    if needs_yes_no(answer):
        return ["Yes", "No"]   # the answer to the question just asked; nothing else to pick from

    topic = topic_of(message, tools_used, active_topic=active_topic)
    chips = _chips(topic, _short_program(profile or {}), department, message=message)
    if topic == "career_guidance":
        candidates = chips[:2]
        return ensure_fixed_chips(candidates, answer=answer, message=message)

    # Collect past questions from history to avoid repeating recent queries
    past_queries = set()
    for h in (history or [])[-4:]:
        if h.get("role") == "user":
            past_queries.add(h.get("text", "").lower())

    picked = []
    for c in chips:
        if _overlaps(c, message or ""):
            continue
        if any(_overlaps(c, pq) for pq in past_queries):
            continue
        picked.append(c)

    candidates = picked if len(picked) >= 2 else chips
    return ensure_fixed_chips(candidates, answer=answer, message=message)


