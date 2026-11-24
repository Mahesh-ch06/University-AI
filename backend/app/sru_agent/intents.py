"""Deterministic intent classification and disambiguation for SRU Buddy."""

import re
from typing import Literal

AgentIntent = Literal[
    "DATE_QUERY",
    "CONFUSION_QUERY",
    "DATE_CONFIRMATION_YES",
    "DATE_CONFIRMATION_NO",
    "CAMPUS_TOUR_DISPATCH",
    "CAMPUS_TOUR_VIRTUAL",
    "CAMPUS_VISIT_BOOKING_WITH_DATE",
    "CAMPUS_VISIT_BOOKING",
    "CAMPUS_VISIT_INFO",
    "PLACEMENT_GUARANTEE_QUERY",
    "PLACEMENT_INFO_QUERY",
    "ADMISSION_GUARANTEE_QUERY",
    "FUTURE_YEAR_FEE_QUERY",
    "SPECIAL_CONCESSIONS_QUERY",
    "OTHER_FEES_QUERY",
    "NEXT_GEN_TECH_QUERY",
    "FEE_TREE_QUERY",
    "ALL_PROGRAMS_QUERY",
    "BTECH_TREE_QUERY",
    "BTECH_PROGRAMS_QUERY",
    "PROGRAM_AI_ROBOTICS_QUERY",
    "PROGRAM_CSE_QUERY",
    "PROGRAM_ECE_QUERY",
    "PROGRAM_CORE_QUERY",
    "PROGRAM_MANAGEMENT_QUERY",
    "PROGRAM_AGRICULTURE_QUERY",
    "PROGRAM_COMP_APP_QUERY",
    "PROGRAM_DESIGN_QUERY",
    "ELIGIBILITY_QUERY",
    "BTECH_CSE_FEE_QUERY",
    "BTECH_AI_ROBOTICS_FEE_QUERY",
    "BTECH_ECE_FEE_QUERY",
    "BTECH_CORE_FEE_QUERY",
    "MANAGEMENT_FEE_QUERY",
    "AGRICULTURE_FEE_QUERY",
    "COMP_APP_FEE_QUERY",
    "DESIGN_FEE_QUERY",
    "HOSTEL_FEE_QUERY",
    "HOSTEL_MESS_QUERY",
    "HOSTEL_CURFEW_RULES_QUERY",
    "HOSTEL_SAFETY_QUERY",
    "HOSTEL_INFO_QUERY",
    "CAMPUS_CANTEEN_QUERY",
    "ACADEMIC_EVALUATION_QUERY",
    "COMBINED_FEE_HOSTEL_QUERY",
    "LAB_FACILITIES_QUERY",
    "WHY_CHOOSE_SRU_QUERY",
    "ABOUT_SRU_QUERY",
    "JOIN_SRU_QUERY",
    "BRANCH_GUIDANCE_QUERY",
    "GENERAL",
]

_DATE_QUERY_PATTERN = re.compile(
    r"^\s*(what\s+is\s+today'?s\s+date|what'?s\s+today'?s\s+date|what\s+date\s+is\s+today|"
    r"today'?s\s+date|tell\s+me\s+today'?s\s+date|current\s+date|"
    r"what\s+is\s+the\s+date\s+today|what\s+date\s+is\s+it|what\s+day\s+is\s+it\s+today)[?!.,\s]*$",
    re.IGNORECASE,
)

_CONFUSION_PATTERN = re.compile(
    r"^\s*(what\s+are\s+you\s+talking\s+about|what\s+are\s+u\s+talking\s+about|"
    r"what\s+do\s+you\s+mean|what\s+does\s+that\s+mean|"
    r"i\s+didn'?t\s+(ask|say|mention)\s+that|i\s+never\s+(asked|said|mentioned)\s+that|"
    r"huh|what\s+is\s+this|what\s+are\s+you\s+saying)[?!.,\s]*$",
    re.IGNORECASE,
)

_JOIN_SRU_PATTERN = re.compile(
    r"^\s*(?:i\s+(?:want|would\s+like|wish|plan|hope)\s+to\s+join\s+(?:sru|sr\s*u(?:niversity)?)|"
    r"how\s+(?:can\s+i|to)\s+join\s+(?:sru|sr\s*u(?:niversity)?)|"
    r"i\s+(?:am\s+)?planning\s+to\s+join\s+(?:sru|sr\s*u(?:niversity)?)|"
    r"i\s+want\s+to\s+take\s+admission\s+in\s+(?:sru|sr\s*u(?:niversity)?)|"
    r"how\s+to\s+get\s+admission\s+in\s+(?:sru|sr\s*u(?:niversity)?)|"
    r"admission\s+in\s+(?:sru|sr\s*u(?:niversity)?)|"
    r"i\s+want\s+to\s+join)[?!.,\s]*$",
    re.IGNORECASE,
)

_BRANCH_GUIDANCE_PATTERN = re.compile(
    r"\b(?:confused\s+(?:about\s+)?(?:which\s+)?(?:branch|course|stream|speciali[sz]ation)|"
    r"which\s+(?:branch|course|stream|speciali[sz]ation)\s+(?:should\s+i|to)\s+(?:choose|take|pick|join|study|opt)|"
    r"which\s+(?:branch|course|stream)\s+is\s+(?:best|better|good)|"
    r"(?:help|guide)\s+me\s+(?:to\s+)?(?:choose|pick|select|decide)\s+(?:a\s+)?(?:branch|course)|"
    r"(?:not\s+sure|unsure)\s+(?:about\s+)?(?:which\s+)?(?:branch|course)|"
    r"suggest\s+(?:a\s+|me\s+a\s+)?(?:branch|course)|"
    r"which\s+engineering\s+branch)\b",
    re.IGNORECASE,
)

_YES_CONFIRM_PATTERN = re.compile(
    r"^\s*(yes|yeah|yep|yup|yes\s+please|correct|sure|right|that'?s\s+right|ok|okay|confirm)[.!?\s]*$",
    re.IGNORECASE,
)

_NO_CONFIRM_PATTERN = re.compile(
    r"^\s*(no|nope|nah|not\s+that|wrong|different\s+date|cancel|neither)[.!?\s]*$",
    re.IGNORECASE,
)

# Explicit booking phrases (actions to book, schedule, or reserve a visit)
_EXPLICIT_BOOKING_PHRASES = (
    "book campus tour", "schedule campus visit", "how can i book a campus tour",
    "book a campus tour", "schedule visit", "book a visit", "book a tour",
    "schedule a tour", "schedule tour", "tour booking", "campus visit booking",
    "how to book a visit", "i want to book a visit", "i want to schedule a visit",
    "register for campus visit", "reserve a slot", "book my visit",
)

# Date mention in the context of visiting
_VISIT_WITH_DATE_PATTERN = re.compile(
    r"\b(visit\s+(on|at|for)|visit\s+this|visit\s+next|visit\s+tomorrow|visit\s+today|"
    r"come\s+(on|at|for)|coming\s+(on|at|for)|plan\s+to\s+visit\s+on|"
    r"want\s+to\s+visit\s+on|would\s+like\s+to\s+visit\s+on)\s+([a-zA-Z0-9\s/-]+)",
    re.IGNORECASE,
)

# General campus visit information inquiries
_VISIT_INFO_PATTERNS = (
    "campus visit", "visit campus", "visit sru", "visit the campus",
    "can i visit", "can we visit", "can parents visit", "visiting hours",
    "visiting timings", "visit timings", "visiting rules", "visiting guidelines",
    "what to see on campus", "how to visit sru", "how to visit the campus", "directions to campus",
)

_VIRTUAL_TOUR_PATTERN = re.compile(
    r"\b(?:virtual(?:\s+tour)?|videos?|watch\s+video|youtube|online\s+tour|video\s+tour|campus\s+videos?)\b",
    re.IGNORECASE,
)

_IN_PERSON_TOUR_PATTERN = re.compile(
    r"\b(?:in[\s-]?person(?:\s+(?:campus\s+)?visit)?|physical(?:\s+campus)?\s+visit|visit\s+in\s+person|come\s+to\s+campus)\b",
    re.IGNORECASE,
)

_CAMPUS_TOUR_DISPATCH_PATTERN = re.compile(
    r"^\s*(?:(?:campus?|college?|university)\s+(?:tour|walkthrough|info)|"
    r"(?:see|show\s+me|explore|view)\s+(?:the\s+)?(?:campus?|college?|university))[.!?\s]*$"
    r"|\b(?:(?:tell\s+me\s+about|details\s+(?:of|for|about))\s+(?:the\s+)?(?:campus?\s+)?tour)\b"
    r"|\b(?:(?:can|could)\s+(?:i|we)|how\s+(?:can\s+i|to))\s+(?:see|tour|explore|walkthrough)\s+(?:the\s+)?campus?\b"
    r"|\b(?:is\s+there\s+a\s+(?:campus?\s+)?tour|take\s+a\s+(?:campus?\s+)?tour)\b"
    r"|\b(?:want\s+to\s+see\s+(?:the\s+)?campus?|like\s+to\s+see\s+(?:the\s+)?campus?|want\s+a\s+campus?\s+tour)\b"
    r"|\b(?:see|explore|tour|view)\s+(?:the\s+)?campus?\b"
    r"|\b(?:campus?\s+(?:chudali|dekhna\s+hai))\b",
    re.IGNORECASE,
)

_PLACEMENT_GUARANTEE_PATTERN = re.compile(
    r"(?:"
    r"\b(?:guarantee|guaranteed|assure|assured|assurance|promise|promised)\b.*?\b(?:placements?|jobs?)\b|"
    r"\b(?:placements?|jobs?)\b.*?\b(?:guarantee|guaranteed|assured?|assurance|promise|promised)\b|"
    r"(?:\b100\s*%|\b100\s*percent\b).*?\b(?:placements?|jobs?)\b|"
    r"\b(?:placements?|jobs?)\b.*?(?:\b100\s*%|\b100\s*percent\b)|"
    r"\b(?:placement|job)\s+guarantee\b|"
    r"\b(?:placement|job)\s+assurance\b|"
    r"\bwill\s+i\s+(?:definitely\s+|surely\s+|for\s+sure\s+)?get\s+(?:a\s+)?(?:job|placement|placed)\b|"
    r"\bcan\s+(?:you|sru)\s+(?:promise|guarantee)\s+(?:a\s+)?(?:job|placement)\b|"
    r"\bjob\s+confirm\b"
    r")",
    re.IGNORECASE,
)

_ADMISSION_GUARANTEE_PATTERN = re.compile(
    r"(?:"
    r"\b(?:guarantee|guaranteed|promise|promised|assure|assured)\b.*?\b(?:admissions?|seats?|getting\s+in|seat\s+allotment)\b|"
    r"\b(?:admissions?|seats?)\b.*?\b(?:guarantee|guaranteed|confirm|confirmed|promise|promised|assured?)\b|"
    r"\b(?:is\s+admission\s+guaranteed|can\s+you\s+guarantee\s+admission|seat\s+confirm\s+ga\s+vastunda|"
    r"will\s+i\s+(?:definitely|surely|guaranteed)\s+get\s+(?:a\s+)?seat|confirmed\s+seat|seat\s+guaranteed|"
    r"seat\s+vastunda|seat\s+vasthunda|seat\s+pakka|pakka\s+seat|guarantee\s+seat)\b"
    r")",
    re.IGNORECASE,
)

_FUTURE_YEAR_FEE_PATTERN = re.compile(
    r"\b(?:fees?|tuition|cost|fee\s+structure)\b.*?\b(?:2028-?29|2029-?30|2029|2030|2031|future\s+years?)\b|"
    r"\b(?:2028-?29|2029-?30|2029|2030|2031)\b.*?\b(?:fees?|tuition|cost|fee\s+structure)\b",
    re.IGNORECASE,
)

_SPECIAL_CONCESSIONS_PATTERN = re.compile(
    r"\b(?:special\s+category\s+(?:fee\s+)?concessions?|special\s+concessions?|"
    r"category\s+concessions?|concession\s+table|fee\s+concession\s+table|"
    r"concessions?\s+table|special\s+category\s+discounts?)\b",
    re.IGNORECASE,
)

_OTHER_FEES_PATTERN = re.compile(
    r"\b(?:other\s+fees?|other\s+academic(?:\s*/\s*university|\s+university)?\s+charges?|other\s+charges?|annual\s+charges?|"
    r"university\s+charges?|additional\s+fees?|additional\s+charges?|enrolment\s+fee|enrollment\s+fee|application\s+form\s+fee|"
    r"specialisation\s+fee|specialization\s+fee|phd\s+fee|"
    r"fees?\s+(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee)|"
    r"(?:other\s+than|apart\s+from|besides|excluding|except)\s+(?:sem(?:ester)?\s+fee|tuition(?:\s+fee)?|course\s+fee))\b",
    re.IGNORECASE,
)



_NEXT_GEN_TECH_PATTERN = re.compile(
    r"\b(?:next[\s-]?gen(?:eration)?\s+technology\s+programs?|"
    r"next[\s-]?gen(?:eration)?\s+tech\s+programs?|"
    r"next[\s-]?gen(?:eration)?\s+programs?|"
    r"ai\s*(?:&|and)\s*robotics.*(?:precision\s+agric\w*|quantum\s+ai)|"
    r"quantum\s+ai.*(?:precision\s+agric\w*|ai\s*(?:&|and)\s*robotics)|"
    r"precision\s+agric\w*.*(?:quantum\s+ai|ai\s*(?:&|and)\s*robotics))\b",
    re.IGNORECASE,
)

_FEE_TREE_PATTERN = re.compile(
    r"^\s*(?:what\s+is\s+(?:the\s+)?fee\s+structure\s+for\s+2027[-–]28\s+across\s+different\s+programs|"
    r"fee\s+structure\s+2027[-–]28|fee\s+structure\s+for\s+2027[-–]28|"
    r"fee\s+tree|show\s+fee\s+tree|fee\s+structure\s+tree|"
    r"fee\s+structure\s+across\s+(?:all\s+)?programs?|"
    r"fee\s+structure\s+directory|what\s+is\s+the\s+fee\s+structure\s+for\s+all\s+programs)[?!.,\s]*$",
    re.IGNORECASE,
)

_ALL_PROGRAMS_PATTERN = re.compile(
    r"\b(?:what\s+are\s+all\s+(?:the\s+)?programs\s+(?:and\s+courses\s+)?available|"
    r"programs\s+available\s+at\s+sru|courses\s+available\s+at\s+sru|"
    r"all\s+programs\s+available|all\s+courses\s+available|"
    r"all\s+programs\s+at\s+sru|all\s+courses\s+at\s+sru|"
    r"list\s+all\s+programs|list\s+all\s+courses|"
    r"what\s+programs\s+are\s+offered|what\s+courses\s+are\s+offered|"
    r"degrees\s+offered\s+at\s+sru|schools\s+and\s+programs)\b",
    re.IGNORECASE,
)

_BTECH_ENGINEERING_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?tech\s+program(?:me)?s?(?:\s+offered)?|b\.?\s?tech\s+branches?|"
    r"b\.?\s?tech\s+courses?|engineering\s+program(?:me)?s?|engineering\s+branches?|"
    r"b\.?\s?tech\s+engineering|b\.?\s?tech)\s*$",
    re.IGNORECASE,
)

_BTECH_CSE_ALLIED_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?tech\s+cse\s*(?:&|and)\s*allied|cse\s*(?:&|and)\s*allied|b\.?\s?tech\s+cse\s+branch)\s*$",
    re.IGNORECASE,
)

_BTECH_CSE_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?tech\s+(?:in\s+)?cse|b\.?\s?tech\s+(?:in\s+)?computer\s+science(?:(?:\s+and|&)\s*engineering)?|"
    r"cse\s+branch|computer\s+science\s+branch|b\.?\s?tech\s+cse)\s*$",
    re.IGNORECASE,
)

_BTECH_AI_ROBOTICS_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?tech\s+(?:in\s+)?(?:ai|artificial\s+intelligence)\s*(?:&|and)\s*robotics|"
    r"ai\s*(?:&|and)\s*robotics\s+branch|b\.?\s?tech\s+ai\s*(?:&|and)\s*robotics|"
    r"(?:ai|artificial\s+intelligence)\s*(?:&|and)\s*robotics)\s*$",
    re.IGNORECASE,
)

_BTECH_ECE_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?tech\s+(?:in\s+)?ece|b\.?\s?tech\s+(?:in\s+)?electronics(?:(?:\s+and|&)\s*communication)?|ece\s+branch)\s*$",
    re.IGNORECASE,
)

_BTECH_CORE_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?tech\s+core(?:\s+engineering)?|core\s+engineering(?:\s+branch|\s+branches)?|"
    r"mechanical\s+branch|civil\s+branch|eee\s+branch)\s*$",
    re.IGNORECASE,
)

_MANAGEMENT_PATTERN = re.compile(
    r"^\s*(?:management\s*(?:\(\s*bba\s*/\s*mba\s*\))?|bba\s*(?:&|and)\s*mba(?:\s+management)?)\s*$",
    re.IGNORECASE,
)

_AGRICULTURE_PATTERN = re.compile(
    r"^\s*(?:b\.?\s?sc\.?\s*(?:\(hons\)\s*)?agriculture|agriculture\s+program)\s*$",
    re.IGNORECASE,
)

_COMP_APP_PATTERN = re.compile(
    r"^\s*(?:computer\s+applications\s*(?:\(\s*bca\s*/\s*mca\s*\))?|bca\s*(?:&|and)\s*mca)\s*$",
    re.IGNORECASE,
)

_DESIGN_PATTERN = re.compile(
    r"^\s*(?:design\s*(?:\(\s*b\.?\s?des\s*\))?|b\.?\s?des)\s*$",
    re.IGNORECASE,
)

_BTECH_FEE_CHIP_PATTERN = re.compile(
    r"^\s*b\.?\s?tech\s+engineering\s*$",
    re.IGNORECASE,
)

_MGMT_FEE_CHIP_PATTERN = re.compile(
    r"^\s*management\s*\(\s*bba\s*/\s*mba\s*\)\s*$",
    re.IGNORECASE,
)

_AGRI_FEE_CHIP_PATTERN = re.compile(
    r"^\s*b\.?\s?sc\.?\s*\(hons\)\s*agriculture\s*$",
    re.IGNORECASE,
)

_COMP_APP_FEE_CHIP_PATTERN = re.compile(
    r"^\s*computer\s+applications\s*\(\s*bca\s*/\s*mca\s*\)\s*$",
    re.IGNORECASE,
)

_DESIGN_FEE_CHIP_PATTERN = re.compile(
    r"^\s*design\s*\(\s*b\.?\s?des\s*\)\s*$",
    re.IGNORECASE,
)

_ELIGIBILITY_PATTERN = re.compile(
    r"^\s*(?:eligibility\s+criteria|eligibility|admission\s+eligibility|"
    r"eligibility\s+requirements?|what\s+is\s+the\s+eligibility|"
    r"who\s+is\s+eligible|eligibility\s+for\s+b\.?tech|eligibility\s+cutoffs?|"
    r"minimum\s+eligibility)\s*$",
    re.IGNORECASE,
)

_PLACEMENT_QUERY_PATTERN = re.compile(
    r"\b(?:placements?\s+for\s+this\s+branch|campus\s+placements?|"
    r"placement\s+records?|highest\s+packages?|average\s+packages?|"
    r"top\s+recruiters|placement\s+statistics|placement\s+details?|placement\s+training|"
    r"which\s+companies\s+(?:recruit|visit|hire|come)|companies\s+(?:that\s+)?(?:recruit|visit|hire)|"
    r"internships?\s+(?:at|in)\s+(?:sr|sru)|prepare\s+and\s+support\s+students\s+for\s+placements)\b",
    re.IGNORECASE,
)

_FEE_KEYWORD_PATTERN = re.compile(
    r"\b(?:fees?|tuition|cost|costs|pricing|charges?|how\s+much)\b",
    re.IGNORECASE,
)

_FEE_OR_SCHOLARSHIP_SHORT_PATTERN = re.compile(
    r"^\s*(?:fees?|fee\s+structure|fee\s*&\s*scholarships?|fees?\s*(?:and|&)\s*scholarships?|"
    r"tuition\s*fees?|what\s+is\s+the\s+fee|fee\s+details?|check\s+fees?|fee\s+and\s+scholarship)\s*$",
    re.IGNORECASE,
)

_HOSTEL_FEE_PATTERN = re.compile(
    r"\b(?:hostel|mess|boarding)\b.*?\b(?:fee|fees|cost|costs|charge|charges|price|prices|how\s+much|rate|rates|rent|package|deposit|deposits)\b|"
    r"\b(?:fee|fees|cost|costs|charge|charges|price|prices|how\s+much|rate|rates|rent|package)\b.*?\b(?:hostel|mess|boarding)\b|"
    r"^\s*(?:hostel\s*fee|hostel\s*fees|mess\s*fee|hostel\s*cost|hostel\s*charges|hostel\s*rent|hostel\s*pricing|hostel\s*room\s*fees?)\s*$",
    re.IGNORECASE,
)

_HOSTEL_MESS_PATTERN = re.compile(
    r"\b(?:mess\s+food|hostel\s+food|food\s+in\s+hostel|food\s+in\s+mess|mess\s+menu|dining\s+hall|mega\s+dining|"
    r"food\s+timings?|mess\s+timings?|dining\s+timings?|dining\s+hours?|breakfast|lunch|dinner|evening\s+snacks?|canteen\s+food|"
    r"veg\s+and\s+non[\s-]*veg|non[\s-]*veg|veg[\s-]*food|food\s+quality|how\s+is\s+(?:the\s+)?food|"
    r"what\s+food\s+is\s+served|food\s+menu|mess\s+facility|mess\s+facilities|dining\s+facility|dining\s+facilities)\b",
    re.IGNORECASE,
)

_HOSTEL_CURFEW_RULES_PATTERN = re.compile(
    r"\b(?:curfew|in[- ]?time|out[- ]?pass|outing\s+rules?|hostel\s+rules?|rules\s+in\s+hostel|"
    r"biometric\s+attendance|roll\s+call|silence\s+hours?|gate\s+timings?|night\s+timings?|"
    r"can\s+we\s+go\s+out|permission\s+to\s+leave|late\s+permission|curfew\s+timings?|"
    r"in[- ]?time\s+for\s+(?:first\s+years?|girls|boys|students?)|hostel\s+discipline|"
    r"prohibited\s+items?|cross[- ]?gender)\b",
    re.IGNORECASE,
)

_HOSTEL_SAFETY_PATTERN = re.compile(
    r"\b(?:hostels?\s+safety|is\s+hostels?\s+safe|security\s+in\s+(?:campus\s+)?hostels?|cctv\s+in\s+(?:campus\s+)?hostels?|"
    r"ragging\s+in\s+(?:campus\s+)?hostels?|wardens?|hostels?\s+in[- ]?charge|girls\s+hostels?\s+warden|"
    r"boys\s+hostels?\s+warden|counsellors?\s+in\s+hostels?|anti[- ]?ragging\s+in\s+hostels?|"
    r"medical\s+support\s+in\s+hostels?|ambulance\s+in\s+hostels?)\b",
    re.IGNORECASE,
)

_HOSTEL_INFO_PATTERN = re.compile(
    r"\b(?:hostels?|hostel\s+facilities|hostel\s+life|hostel\s+accommodation|campus\s+hostels?|"
    r"hostel\s+details|tell\s+me\s+about\s+(?:the\s+)?hostels?|living\s+on\s+campus|stay\s+in\s+hostel|"
    r"hostel\s+rooms?|ac\s+rooms?\s+in\s+hostel|room\s+sharing\s+in\s+hostel|boys\s+hostels?|"
    r"girls\s+hostels?|wifi\s+in\s+hostel|hot\s+water\s+in\s+hostel|gym\s+in\s+hostel|laundry\s+in\s+hostel|"
    r"hostel\s+options?|explore\s+hostels?|hostel\s+amenities|residential\s+(?:campus\s+)?living|campus\s+accommodation)\b|^\s*(?:hostel|hostels|hostel\s+details|hostel\s+info)\s*$",
    re.IGNORECASE,
)


_COMBINED_HOSTEL_FEE_PATTERN = re.compile(
    r"\b(?:add\s+hostel|include\s+hostel|combine\s+.*hostel|hostel\s+.*(?:add|included?)|"
    r"(?:total\s+)?(?:fee|cost|tuition)\s+including\s+hostel|"
    r"total\s+fee\s+including\s+hostel|fee\s+with\s+hostel|tuition\s+and\s+hostel|"
    r"college\s+and\s+hostel|fee\s*\+\s*hostel|hostel\s*\+\s*fee|hostel\s*\+\s*tuition|"
    r"total\s+cost\s+with\s+hostel|both\s+hostel\s+and\s+(?:college|tuition))\b",
    re.IGNORECASE,
)

_CAMPUS_CANTEEN_PATTERN = re.compile(
    r"\b(?:food\s+stalls?|food\s+options?|cafeteria|central\s+cafeteria|canteen|canteens|"
    r"food\s+kiosks?|kiosks?\s+in\s+campus|tasty\s+treat|meet\s+and\s+eat|bharat\s+foods|"
    r"campus\s+canteen|campus\s+cafeteria|snacks?\s+(?:on|in)\s+campus|coffee\s+shop|tea\s+stalls?|"
    r"eating\s+options?|places?\s+to\s+eat)\b",
    re.IGNORECASE,
)

_ACADEMIC_EVALUATION_PATTERN = re.compile(
    r"\b(?:(?:exam|exams|semester)\s+total\s+marks|passmarks|pass\s+marks|passing\s+marks|"
    r"cie\s+and\s+ese|cie\s+marks|ese\s+marks|continuous\s+internal\s+evaluation|"
    r"end\s+semester\s+exams?|grading\s+system|grading\s+scale|10[- ]point\s+scale|"
    r"minimum\s+pass\s+grade|grade\s+points?|how\s+are\s+marks\s+evaluated|"
    r"academic\s+progression|promotion\s+rules?|condonation\s+rules?|"
    r"cgpa\s+calculation|sgpa\s+calculation|percentage\s+conversion)\b",
    re.IGNORECASE,
)

_LAB_FACILITIES_PATTERN = re.compile(
    r"\b(?:"
    r"how\s+many\s+labs(?:\s+are\s+there)?|"
    r"how\s+many\s+laboratories(?:\s+are\s+there)?|"
    r"number\s+of\s+labs|number\s+of\s+laboratories|"
    r"count\s+of\s+labs|count\s+of\s+laboratories|"
    r"total\s+labs|total\s+laboratories|"
    r"what\s+labs(?:\s+are\s+there|\s+do\s+you\s+have|\s+available)?|"
    r"which\s+labs(?:\s+are\s+there|\s+do\s+you\s+have|\s+available)?|"
    r"what\s+laboratories(?:\s+are\s+there|\s+do\s+you\s+have|\s+available)?|"
    r"which\s+laboratories(?:\s+are\s+there|\s+do\s+you\s+have|\s+available)?|"
    r"laborator(?:y|ies)\s*(?:&|and)\s*facilities|labs?\s*(?:&|and)\s*facilities|"
    r"lab\s+facilities|laboratory\s+facilities|research\s+centres?|research\s+centers?|"
    r"list\s+of\s+labs|list\s+of\s+laboratories|"
    r"tell\s+me\s+about\s+(?:the\s+)?labs?|tell\s+me\s+about\s+(?:the\s+)?laboratories|"
    r"university\s+labs|campus\s+labs|sru\s+labs|modern\s+labs"
    r")\b",
    re.IGNORECASE,
)

_WHY_CHOOSE_SRU_PATTERN = re.compile(
    r"\b(?:why\s+choose\s+(?:sr\s*u(?:niversity)?|sru)|why\s+sru|why\s+sr\s*university|"
    r"why\s+should\s+i\s+(?:join|choose|pick)\s+(?:sr\s*u(?:niversity)?|sru)|"
    r"what\s+makes\s+(?:sr\s*u(?:niversity)?|sru)\s+(?:special|unique|better)|"
    r"advantages\s+of\s+(?:sr\s*u(?:niversity)?|sru)|benefits\s+of\s+(?:sr\s*u(?:niversity)?|sru)|"
    r"is\s+sru\s+good|how\s+is\s+sru)\b",
    re.IGNORECASE,
)

_ABOUT_SRU_PATTERN = re.compile(
    r"\b(?:about\s+(?:sr\s*u(?:niversity)?|sru)|tell\s+me\s+about\s+(?:sr\s*u(?:niversity)?|sru)|"
    r"overview\s+of\s+(?:sr\s*u(?:niversity)?|sru)|"
    r"describe\s+(?:sr\s*u(?:niversity)?|sru)|know\s+about\s+(?:sr\s*u(?:niversity)?|sru))\b|"
    r"^\s*(?:what\s+is\s+(?:sr\s*u(?:niversity)?|sru))[?!.,\s]*$",
    re.IGNORECASE,
)


def _has_score_or_rank(msg: str) -> bool:
    return bool(re.search(r"\d{2,3}\s*%|\brank\b|\bpercent\b|\bpercentile\b|\bmarks\b|\beapcet\b|\beamcet\b|\bjee\b", msg, re.IGNORECASE))


def classify_agent_intent(message: str, state: dict | None = None) -> AgentIntent:
    """Classify user intent before triggering LLM or rich cards."""
    msg = (message or "").strip().lower()
    if not msg:
        return "GENERAL"
    # Common misspellings of the words the topics below look for (v4.13.0: "placment record", "scolarship").
    msg = re.sub(r"\bplac(?:e)?m(?:e|a)?nt(s)?\b", r"placement\1", msg)
    msg = re.sub(r"\bs[ck]?h?o[lr]+[ae]?r?s+h?i*p+(s)?\b", r"scholarship\1", msg)

    state = state or {}

    # 1. Date query
    if _DATE_QUERY_PATTERN.match(msg):
        return "DATE_QUERY"

    # 2. Confusion query
    if _CONFUSION_PATTERN.match(msg):
        return "CONFUSION_QUERY"

    # 2b. General join query without course
    if _JOIN_SRU_PATTERN.match(msg):
        from . import fees as _fees
        if not _fees.find_program(msg):
            return "JOIN_SRU_QUERY"

    # 3. Active date confirmation in progress
    if state.get("awaiting_date_confirmation"):
        if _YES_CONFIRM_PATTERN.match(msg):
            return "DATE_CONFIRMATION_YES"
        if _NO_CONFIRM_PATTERN.match(msg):
            return "DATE_CONFIRMATION_NO"

    # 3b. Academic evaluation & exam criteria
    if _ACADEMIC_EVALUATION_PATTERN.search(msg):
        return "ACADEMIC_EVALUATION_QUERY"

    # 3c. Combined fee (Hostel + College/Tuition)
    if _COMBINED_HOSTEL_FEE_PATTERN.search(msg):
        return "COMBINED_FEE_HOSTEL_QUERY"

    # 3d. Campus canteen & food stalls (before hostel mess)
    if _CAMPUS_CANTEEN_PATTERN.search(msg):
        return "CAMPUS_CANTEEN_QUERY"

    # 3e. Laboratory & research facilities query
    if _LAB_FACILITIES_PATTERN.search(msg) and not bool(re.search(r"\b(?:fees?|tuition|cost|price|scholarship|manual|exam|timetable)\b", msg)):
        return "LAB_FACILITIES_QUERY"

    # 4. Check if message is asking to visit on a specific date
    if _VISIT_WITH_DATE_PATTERN.search(msg) or any(k in msg for k in ("visit on", "visit tomorrow", "visit today")):
        return "CAMPUS_VISIT_BOOKING_WITH_DATE"

    if state.get("active_topic") == "campus_visit":
        # Guard: If user asks an academic, fee, scholarship, canteen, or general question, do not hijack into campus visit!
        has_off_topic_context = bool(re.search(
            r"\b(?:scholarship|marks?|rank|fee|fees|tuition|canteen|cafeteria|food|stalls?|exam|passmarks|"
            r"faculty|dean|hod|hostel|placements?|package|vc|vice\s+chancellor|chancellor|sports|library|labs?|laborator(?:y|ies)|research)\b",
            msg
        ))
        if not has_off_topic_context:
            from .tools import resolve_campus_visit_date
            res = resolve_campus_visit_date(msg)
            if res.get("date"):
                return "CAMPUS_VISIT_BOOKING_WITH_DATE"

    if re.search(r"\b(?:visit|come|tour)\b", msg) and not re.search(r"\b(?:timings?|hours?|rules?|allowed|can\s+parents)\b", msg):
        from .tools import resolve_campus_visit_date
        if resolve_campus_visit_date(msg).get("date"):
            return "CAMPUS_VISIT_BOOKING_WITH_DATE"

    # 5. Explicit booking request (without a specific date yet)
    if any(phrase in msg for phrase in _EXPLICIT_BOOKING_PHRASES):
        return "CAMPUS_VISIT_BOOKING"

    # 5b. Explicit Virtual Tour / Video inquiry
    if _VIRTUAL_TOUR_PATTERN.search(msg) and any(k in msg for k in ("tour", "campus", "walkthrough", "info", "sru")):
        return "CAMPUS_TOUR_VIRTUAL"

    # 5c. Explicit In-Person Campus Visit inquiry
    if _IN_PERSON_TOUR_PATTERN.search(msg):
        return "CAMPUS_VISIT_INFO"

    # 5d. General Campus Tour inquiry (presents both Virtual and In-Person options)
    if _CAMPUS_TOUR_DISPATCH_PATTERN.search(msg):
        return "CAMPUS_TOUR_DISPATCH"

    # 6. General campus visit inquiry
    if any(pattern in msg for pattern in _VISIT_INFO_PATTERNS):
        return "CAMPUS_VISIT_INFO"

    # 6b. Placement guarantee / 100% placement assistance inquiry
    if _PLACEMENT_GUARANTEE_PATTERN.search(msg):
        return "PLACEMENT_GUARANTEE_QUERY"
    if _PLACEMENT_QUERY_PATTERN.search(msg):
        return "PLACEMENT_INFO_QUERY"   # packages, recruiters, training, internships: a short factual answer

    # 6bb. Admission / Seat guarantee inquiry (evaluated before fee / score checks)
    if _ADMISSION_GUARANTEE_PATTERN.search(msg):
        return "ADMISSION_GUARANTEE_QUERY"

    # 6bc. Future academic year fee inquiry
    if _FUTURE_YEAR_FEE_PATTERN.search(msg):
        return "FUTURE_YEAR_FEE_QUERY"

    # 6c. Dedicated Hostel Inquiries (Categorized before fee calculations)
    if _HOSTEL_FEE_PATTERN.search(msg) and not _COMBINED_HOSTEL_FEE_PATTERN.search(msg):
        return "HOSTEL_FEE_QUERY"
    if _HOSTEL_MESS_PATTERN.search(msg):
        return "HOSTEL_MESS_QUERY"
    if _HOSTEL_CURFEW_RULES_PATTERN.search(msg):
        return "HOSTEL_CURFEW_RULES_QUERY"
    if _HOSTEL_SAFETY_PATTERN.search(msg):
        return "HOSTEL_SAFETY_QUERY"
    if _HOSTEL_INFO_PATTERN.search(msg):
        return "HOSTEL_INFO_QUERY"

    # 6d. Eligibility criteria inquiry
    if _ELIGIBILITY_PATTERN.match(msg):
        return "ELIGIBILITY_QUERY"

    # 7. Deterministic quick responses (when user hasn't provided a specific score/rank to calculate)
    if not _has_score_or_rank(msg):
        if _OTHER_FEES_PATTERN.search(msg):
            return "OTHER_FEES_QUERY"
        if _SPECIAL_CONCESSIONS_PATTERN.search(msg):
            return "SPECIAL_CONCESSIONS_QUERY"
        if _NEXT_GEN_TECH_PATTERN.search(msg):
            return "NEXT_GEN_TECH_QUERY"
        if _FEE_TREE_PATTERN.search(msg):
            return "FEE_TREE_QUERY"
        if _ALL_PROGRAMS_PATTERN.search(msg):
            return "ALL_PROGRAMS_QUERY"

        in_tree = bool(state.get("fee_tree_step"))
        active_prog = state.get("active_program") or state.get("fee_flow_prog") or state.get("program_interest")
        has_fee_word = bool(_FEE_KEYWORD_PATTERN.search(msg))

        # Contextual fee query: user asks "Fee & scholarships" or "Fee structure" while an active program is selected
        if _FEE_OR_SCHOLARSHIP_SHORT_PATTERN.match(msg) and active_prog:
            if active_prog in ("btech_ai_robotics", "ai_robotics"):
                return "BTECH_AI_ROBOTICS_FEE_QUERY"
            if active_prog in ("btech_cse", "cse"):
                return "BTECH_CSE_FEE_QUERY"
            if active_prog in ("btech_ece", "ece"):
                return "BTECH_ECE_FEE_QUERY"
            if active_prog in ("btech_mech", "btech_core", "core"):
                return "BTECH_CORE_FEE_QUERY"
            if active_prog in ("mba", "bba", "management"):
                return "MANAGEMENT_FEE_QUERY"
            if active_prog in ("bsc_agri", "agri"):
                return "AGRICULTURE_FEE_QUERY"
            if active_prog in ("bca", "mca", "comp_app"):
                return "COMP_APP_FEE_QUERY"
            if active_prog in ("design", "bdes"):
                return "DESIGN_FEE_QUERY"


        # Active fee tree sub-selections
        if in_tree:
            if _BTECH_CSE_ALLIED_PATTERN.match(msg) or re.search(r"\b(?:cse|computer\s+science)\b", msg):
                return "BTECH_CSE_FEE_QUERY"
            if _BTECH_AI_ROBOTICS_PATTERN.match(msg) or re.search(r"\b(?:ai\s*&?\s*robotics|artificial\s+intelligence\s*&?\s*robotics)\b", msg):
                return "BTECH_AI_ROBOTICS_FEE_QUERY"
            if _BTECH_ECE_PATTERN.match(msg) or re.search(r"\b(?:ece|electronics)\b", msg):
                return "BTECH_ECE_FEE_QUERY"
            if _BTECH_CORE_PATTERN.match(msg) or re.search(r"\b(?:core|mech|civil|eee|biotech)\b", msg):
                return "BTECH_CORE_FEE_QUERY"
            if _BTECH_ENGINEERING_PATTERN.match(msg) or re.search(r"\b(?:b\.?\s?tech|engineering)\b", msg):
                return "BTECH_TREE_QUERY"
            if _MANAGEMENT_PATTERN.match(msg) or re.search(r"\b(?:bba|mba|management)\b", msg):
                return "MANAGEMENT_FEE_QUERY"
            if _AGRICULTURE_PATTERN.match(msg) or re.search(r"\b(?:agri|agriculture)\b", msg):
                return "AGRICULTURE_FEE_QUERY"
            if _COMP_APP_PATTERN.match(msg) or re.search(r"\b(?:bca|mca)\b", msg):
                return "COMP_APP_FEE_QUERY"
            if _DESIGN_PATTERN.match(msg) or re.search(r"\b(?:design|b\.?\s?des)\b", msg):
                return "DESIGN_FEE_QUERY"

        # Explicit fee tree chip clicks outside in_tree
        if _BTECH_FEE_CHIP_PATTERN.match(msg):
            return "BTECH_TREE_QUERY"
        if _BTECH_CSE_ALLIED_PATTERN.match(msg):
            return "BTECH_CSE_FEE_QUERY"
        if _MGMT_FEE_CHIP_PATTERN.match(msg):
            return "MANAGEMENT_FEE_QUERY"
        if _AGRI_FEE_CHIP_PATTERN.match(msg):
            return "AGRICULTURE_FEE_QUERY"
        if _COMP_APP_FEE_CHIP_PATTERN.match(msg):
            return "COMP_APP_FEE_QUERY"
        if _DESIGN_FEE_CHIP_PATTERN.match(msg):
            return "DESIGN_FEE_QUERY"

        # Program exploration queries (without fee intent)
        if _BTECH_AI_ROBOTICS_PATTERN.match(msg):
            return "PROGRAM_AI_ROBOTICS_QUERY"
        if _BTECH_CSE_PATTERN.match(msg):
            return "PROGRAM_CSE_QUERY"
        if _BTECH_ECE_PATTERN.match(msg):
            return "PROGRAM_ECE_QUERY"
        if _BTECH_CORE_PATTERN.match(msg):
            return "PROGRAM_CORE_QUERY"
        if _BTECH_ENGINEERING_PATTERN.match(msg):
            return "BTECH_PROGRAMS_QUERY"
        if _MANAGEMENT_PATTERN.match(msg):
            return "PROGRAM_MANAGEMENT_QUERY"
        if _AGRICULTURE_PATTERN.match(msg):
            return "PROGRAM_AGRICULTURE_QUERY"
        if _COMP_APP_PATTERN.match(msg):
            return "PROGRAM_COMP_APP_QUERY"
        if _DESIGN_PATTERN.match(msg):
            return "PROGRAM_DESIGN_QUERY"

    # 8. Branch & Career Guidance
    if _BRANCH_GUIDANCE_PATTERN.search(msg):
        return "BRANCH_GUIDANCE_QUERY"

    # 9. University overview & "Why choose SRU" queries (only if not a multi-topic comparison)
    is_comparison_query = bool(re.search(r"\b(?:vs|versus|compare|comparison|better\s+than|difference\s+between)\b", msg, re.I))
    if not is_comparison_query:
        if _WHY_CHOOSE_SRU_PATTERN.search(msg):
            return "WHY_CHOOSE_SRU_QUERY"
        if _ABOUT_SRU_PATTERN.search(msg):
            return "ABOUT_SRU_QUERY"

    return "GENERAL"


def is_branch_guidance_query(message: str) -> bool:
    """True if message is asking for branch or career guidance / confused about branch."""
    return bool(_BRANCH_GUIDANCE_PATTERN.search(message or ""))


# ----------------------------------------------------------------------------
# Contact requests: "ask someone to call me", "don't call me", and the name a
# student gives along with a phone number. Used by the agent to run the callback /
# cancel tools itself, so a request is never "noted" without being saved.
# ----------------------------------------------------------------------------
_CONTACT_VERB = r"(?:call|contact|phone|ring|disturb|message|whatsapp|text)(?:ing)?"
_NOT_NOW = r"(?!\s+(?:me\s+|us\s+)?(?:before|until|till|at|on|in\s+the|during|now|today|tomorrow|after|between)\b)"

_CANCEL_CONTACT_PATTERN = re.compile(
    rf"\b(?:do\s*n[o']?t|dont|never|stop|no\s+need\s+to|need\s+not|not\s+to|please\s+don'?t)\s+{_CONTACT_VERB}\b{_NOT_NOW}"
    r"|\bcancel\b.{0,30}\b(?:call\s*-?\s*back|callback|call|request|visit|booking|appointment|tour)\b"
    r"|\b(?:call\s*-?\s*back|callback|visit|booking|appointment)\b.{0,20}\bcancel\b"
    r"|\b(?:remove|delete)\s+my\s+(?:number|details|phone|contact|request|data)\b"
    r"|\b(?:i\s+)?(?:do\s*n[o']?t|dont)\s+want\s+(?:a\s+|any\s+|the\s+)?(?:call|callback|call\s*back|calls)\b"
    r"|\bcall\s+(?:cheyakandi|cheyyakandi|cheyoddu|cheyyoddu|cheyakudadhu|vaddu|oddu|mat\s+kar\w*|nahi\s+kar\w*|na\s+kar\w*)\b",
    re.IGNORECASE,
)
_CANCEL_IT_PATTERN = re.compile(r"^\s*(?:please\s+|pls\s+)?cancel(?:\s+(?:it|that|this|please|pls))?[.!\s]*$",
                                re.IGNORECASE)

_CALLBACK_REQUEST_PATTERN = re.compile(
    r"\bcall\s*-?\s*back\b"
    r"|\b(?:call|ring|phone|contact)\s+(?:me|us|him|her|my\s+(?:son|daughter|father|mother|dad|mom|"
    r"parents?|husband|wife|brother|sister|ward))\b"
    r"|\b(?:someone|somebody|anyone|counsell?or|admissions?\s+(?:team|office|officer|people)|team)\b"
    r".{0,25}\b(?:call|contact|phone|ring)\b(?!\s+(?:number|no\b|details|cent(?:re|er)|letter|it\b))"
    r"|\b(?:talk|speak)\s+(?:to|with)\s+(?:a\s+|an\s+|the\s+|your\s+|some\s+)?(?:counsell?or|admissions?|"
    r"someone|somebody|human|person|representative|agent|staff)\b"
    r"|\b(?:call|phone)\s+(?:cheyandi|cheyyandi|cheyamani|cheyinchandi|cheyagalara|cheyyagalara|"
    r"karo|kijiye|karna|kardo|kar\s+do|kar\s+dijiye)\b",
    re.IGNORECASE,
)
# "Will someone call me after I apply?" is a question about the process, not a request.
_PROCESS_QUESTION = re.compile(r"^\s*(?:will|would|does|do|did|is|are|when|why|how\s+(?:long|soon|many))\b",
                               re.IGNORECASE)

_VISIT_REQUEST_PATTERN = re.compile(
    r"\b(?:book|schedule|arrange|plan|register|reserve|fix)\b.{0,30}\b(?:visit|tour|slot)\b"
    r"|\b(?:want|wish|like|planning|plan|coming|come)\b.{0,25}\b(?:visit(?:\s+the\s+campus)?|come\s+to\s+(?:the\s+)?campus|visit\s+in\s+person)\b"
    r"|\bvisit\b.{0,20}\b(?:book|schedule|arrange)\b",
    re.IGNORECASE,
)


_NUMBER_UPDATE_PATTERN = re.compile(
    r"\b(?:change|update|replace|correct|edit|modify)\b.{0,40}\b(?:number|mobile|phone|contact)\b"
    r"|\b(?:number|mobile|phone)\b.{0,25}\b(?:changed|is\s+wrong|was\s+wrong|incorrect)\b"
    r"|\b(?:my\s+)?new\s+(?:mobile\s+|phone\s+|contact\s+)?(?:number|no\b)"
    r"|\b(?:update|change|edit)\b.{0,25}\b(?:settings?|profile|my\s+details)\b",
    re.IGNORECASE,
)
_NUMBER_STATEMENT_PATTERN = re.compile(
    r"\b(?:my|this\s+is\s+my|here\s+is\s+my)\s+(?:new\s+)?(?:mobile|phone|contact|whatsapp|cell)?\s*"
    r"(?:number|no\.?|num)\b", re.IGNORECASE)


def is_number_update(message: str) -> bool:
    """'change my number', 'my new number is ...', 'update it in the settings'."""
    if re.search(r"\b(?:marks?|board|academic|percentage|group|stream|scores?)\b", message or "", re.I) \
            and not re.search(r"\b(?:number|mobile|phone|contact)\b", message or "", re.I):
        return False  # "change my academic details / marks": the admission details, not the phone number
    return bool(_NUMBER_UPDATE_PATTERN.search(message or ""))


def is_number_statement(message: str) -> bool:
    """'my mobile number is 98...' (the student is telling us their number)."""
    return bool(_NUMBER_STATEMENT_PATTERN.search(message or ""))


def is_cancel_contact(message: str, has_open_request: bool = False) -> bool:
    """True for 'don't call me', 'cancel the callback', 'cancel my visit' (and bare 'cancel' when a
    request is open or being arranged)."""
    msg = message or ""
    if _CANCEL_CONTACT_PATTERN.search(msg):
        return True
    return bool(has_open_request and _CANCEL_IT_PATTERN.match(msg))


# "Talk to a counsellor / a person" (v4.12.0): the student wants a human now. Handled by the counsellor connect
# flow (services/live_connect.py): a short real attempt, then a callback. "Call me" stays a callback request.
_CONNECT_PATTERN = re.compile(
    r"\b(?:talk|speak|chat|connect|transfer|put)\s+(?:me\s+)?(?:to|with|through\s+to)\s+"
    r"(?:(?:a|an|the|your|some|real|live)\s+)*"
    r"(?:counsell?or|admissions?(?:\s+(?:team|officer|counsell?or|office))?|someone|somebody|human|person|"
    r"representative|agent|staff|executive|customer\s+(?:care|support|service)|support(?:\s+team)?|"
    r"help\s*desk|helpline|call\s*cent(?:er|re))\b"
    r"|\breal\s+(?:person|human)\b|\blive\s+(?:agent|counsell?or|person|support|chat)\b|\bconnect\s+me\b"
    # v4.13.0: "customer care", "human please", "I need help from a person"
    r"|(?<!the\s)\bcustomer\s+(?:care|support|service)\b(?!\s+(?:of|at|in|for)\b)"
    r"|\b(?:human|person|agent|counsell?or)\s+please\b"
    r"|\b(?:help|assistance)\s+from\s+(?:a\s+)?(?:person|human|someone|counsell?or)\b"
    r"|\b(?:need|want)\s+(?:to\s+talk\s+to\s+)?(?:a\s+)?(?:human|real\s+person)\b",
    re.IGNORECASE)


def is_connect_request(message: str) -> bool:
    """True when the student asks to talk to a person now ("talk to a counsellor", "connect me")."""
    msg = message or ""
    if _CANCEL_CONTACT_PATTERN.search(msg) or re.search(r"\b(?:don'?t|do\s+not|no\s+need)\b", msg, re.IGNORECASE):
        return False
    return bool(_CONNECT_PATTERN.search(msg))


def is_callback_request(message: str) -> bool:
    """True when the student asks to be phoned by the admissions team."""
    msg = message or ""
    if _CANCEL_CONTACT_PATTERN.search(msg) or not _CALLBACK_REQUEST_PATTERN.search(msg):
        return False
    has_digits = bool(re.search(r"\d{5,}", msg))
    return has_digits or not _PROCESS_QUESTION.match(msg)


def is_visit_request(message: str) -> bool:
    """True when the student asks to book / plan a campus visit (not just asks about visiting)."""
    return bool(_VISIT_REQUEST_PATTERN.search(message or ""))


_NOT_A_NAME = frozenset("""
a an the i im am is are was me my mine we us you your u he she they this that it its here there
yes yeah yep ok okay no not sure please pls plz thanks thank hi hello hey sir madam mam
name names number numbers phone mobile contact call calls callback back whatsapp no num ph
and or but so for of on in at to from with by as if then also too very just now still about
interested looking planning studying student parent father mother son daughter brother sister
going coming visiting calling asking thinking confused worried eligible ready waiting getting
done fine good happy want wants need needs like would will can could should may have has had
visit campus tour book booking schedule date today tomorrow morning afternoon evening night
monday tuesday wednesday thursday friday saturday sunday
january february march april june july august september october november december
cse ece eee mech civil btech mtech mba bba bca mca bsc msc engineering course fee fees hostel
scholarship admission admissions counsellor counselor team sru university inter intermediate
rank marks percent percentage eapcet eamcet jee cbse people persons members friends
bus buses route routes transport placement placements library timings timing faculty professor professors
hod dean details detail information info location address directions food mess sports ragging refund
documents document apply application loan lab labs wifi college ranking rankings nirf reach how what where
when why which who fee structure syllabus curriculum seats seat cutoff exam exams result results
tell know give check calculate find share help speak chat medium telugu hindi english hyderabad
""".split())
_NAME_INTRO = re.compile(
    r"(?:\bmy\s+name\s+is|\bname\s*(?:is|:|-)|\bname\s+(?=[A-Za-z])|\bmyself\b|\bnaa\s+peru\b|"
    r"\bmera\s+naam\b|\bcall\s+me\s+(?!on\b)|\b(?:it's|its)\b)\s*([A-Za-z][A-Za-z .']{0,45})", re.IGNORECASE)
# "I am ..." or "This is ..."
_WEAK_NAME_INTRO = re.compile(r"(?:\bi\s+am\b|\bi'm\b|\bim\b|\bthis\s+is\b)\s+([A-Za-z][A-Za-z .']{0,45})",
                              re.IGNORECASE)
_HERE_NAME_INTRO = re.compile(r"^([A-Za-z][A-Za-z .']{1,45})\s+here\b", re.IGNORECASE)
_NAME_WORD = re.compile(r"[A-Za-z][A-Za-z.']*")


def _clean_name(fragment: str):
    """Leading words of `fragment` that can be a person's name (1-4 words), else None."""
    words = []
    for raw in (fragment or "").replace(",", " , ").split():
        word = raw.strip(".'")
        if not _NAME_WORD.fullmatch(raw) or word.lower() in _NOT_A_NAME or len(words) == 4:
            break
        words.append(word)
    while words and len(words[-1]) == 1 and len(words) > 3:
        words.pop()
    name = " ".join(words).strip()
    if len(name.replace(" ", "")) < 2:
        return None
    return " ".join(w if w.isupper() and len(w) <= 3 else w.capitalize() for w in name.split())


def extract_name(message: str, bare_ok: bool = False):
    """The student's name if the message states one.

    Understands 'my name is Mahesh', 'I am Mahesh, 98...', 'Mahesh Reddy',
    'Hello, I'm Mahesh', 'call me Mahesh', 'its Mahesh', 'Mahesh here'.
    With bare_ok=True (the agent has just asked for the name) a message
    that is only a name ('Mahesh', 'Mahesh Reddy') also counts.
    """
    msg = (message or "").strip()
    if not msg:
        return None

    # 1. Explicit name introduction ("my name is ...", "call me ...", "its ...", "myself ...")
    for m in _NAME_INTRO.finditer(msg):
        name = _clean_name(m.group(1))
        if name:
            return name

    # 2. "[Name] here"
    m_here = _HERE_NAME_INTRO.match(msg)
    if m_here:
        name = _clean_name(m_here.group(1))
        if name:
            return name

    phone = re.search(r"(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)", msg)

    # 3. Weak introductions ("I am Mahesh", "I'm Mahesh", "this is Mahesh")
    for m in _WEAK_NAME_INTRO.finditer(msg):
        name = _clean_name(m.group(1))
        if name:
            typed = m.group(1).split()[:len(name.split())]
            if phone or bare_ok or all(w[:1].isupper() for w in typed):
                return name

    # 4. Phone adjacent names
    if phone:
        before = re.sub(r"[\s,\-(:]+$", "", msg[:phone.start()])
        before = re.split(r"[.;:!?\n,]", before)[-1].strip()
        if before and all(_NAME_WORD.fullmatch(w) for w in before.split()) and len(before.split()) <= 4:
            name = _clean_name(before)
            if name and len(name.split()) == len(before.split()):
                return name
        after = re.sub(r"^[\s,\-).]+", "", msg[phone.end():])
        after = re.split(r"[.;:!?\n,]", after)[0].strip()
        if after and all(_NAME_WORD.fullmatch(w) for w in after.split()) and len(after.split()) <= 4:
            name = _clean_name(after)
            if name and len(name.split()) == len(after.split()):
                return name

    # 5. Bare name (when awaiting name from previous turn)
    if bare_ok:
        # Check if user said "I am / I'm / it's [Name]"
        cleaned_msg = re.sub(r"^(?:hello|hi|hey|i\s+am|i'm|im|this\s+is|it's|its)\s+", "", msg, flags=re.IGNORECASE).strip()
        if 1 <= len(cleaned_msg.split()) <= 4 and all(_NAME_WORD.fullmatch(w) for w in cleaned_msg.split()):
            name = _clean_name(cleaned_msg)
            if name and len(name.split()) == len(cleaned_msg.split()):
                return name

    return None


_REFUSAL_PATTERN = re.compile(
    r"^\s*(?:no|nope|nah|skip|pass|not\s+now|dont\s+want\s+to\s+say|don'?t\s+want\s+to\s+say|"
    r"prefer\s+not\s+to\s+say|why\s+do\s+you\s+need|why\s+name|just\s+tell\s+me|"
    r"leave\s+it|just\s+answer|answer\s+my\s+question)[!.,?\s]*$",
    re.IGNORECASE,
)


def is_refusal_or_skip(message: str) -> bool:
    """True if user refuses or skips providing their name."""
    msg = (message or "").strip()
    return bool(_REFUSAL_PATTERN.search(msg))


def detect_user_persona(message: str, history: list | None = None, profile: dict | None = None) -> str:
    """Classify user persona and communication style from message and history."""
    msg = (message or "").lower()
    profile = profile or {}

    # 1. Parent or guardian
    if profile.get("is_parent") or re.search(r"\b(?:my\s+(?:son|daughter|child|ward|kid)|as\s+a\s+parent|we\s+are\s+parents)\b", msg):
        return "parent"

    # 2. In a hurry / direct
    if re.search(r"\b(?:quick|urgently?|fast|in\s+short|briefly?|summarize|summary|just\s+tell\s+me)\b", msg) or (len(msg.split()) <= 3 and re.search(r"\b(?:fee|fees|cost|cutoff|package)\b", msg)):
        return "in_a_hurry"

    # 3. Confused
    if re.search(r"\b(?:confused|not\s+sure|dont\s+know|don't\s+know|help\s+me\s+choose|which\s+is\s+better|explain\s+simply|dont\s+understand|don't\s+understand)\b", msg):
        return "confused"

    # 4. Current student
    if re.search(r"\b(?:my\s+roll\s+no|hall\s+ticket|my\s+attendance|semester\s+exam|re-?evaluation|faculty\s+cabin|id\s+card|current\s+student|second\s+year|third\s+year)\b", msg):
        return "current_student"

    # 5. Casual user
    if re.search(r"\b(?:bro|buddy|dude|wassup|sup|cool|chill|hey\s+man)\b", msg) or any(c in msg for c in ("😎", "🔥", "🙌", "😂")):
        return "casual"

    # 6. Interested prospective student
    if re.search(r"\b(?:intermediate|inter\s+marks|12th|eapcet|eamcet|jee|join\s+sru|apply|admission|scholarship|eligibility)\b", msg):
        return "prospective_student"

    return "information_seeking"


def extract_preferred_time(message: str):
    """'tomorrow evening', 'after 5 pm' ... as typed, or None."""
    m = re.search(r"\b((?:today|tomorrow|tonight)\s+)?(morning|afternoon|evening|night)\b"
                  r"|\b(?:after|before|at|around|by)\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b"
                  r"|\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b(?:today|tomorrow)\b", message or "", re.IGNORECASE)
    return m.group(0).strip().lower() if m else None


def extract_visitors(message: str):
    m = re.search(r"\b(\d{1,2})\s*(?:people|persons?|members?|of\s+us|visitors?|guests?)\b", message or "",
                  re.IGNORECASE)
    return int(m.group(1)) if m else None


_BUDDY = r"(?:\s+(?:sru\s*_?\s*buddy|buddy|sru|there|bro|sir|mam|madam|team|dear|man|anna|akka))*"
_SMALL_TALK_PATTERNS = (
    ("greeting", re.compile(r"^(?:hi+|hello+|hey+|hlo+|helo|namaste|namaskaram|vanakkam|"
                            r"good\s+(?:morning|afternoon|evening))" + _BUDDY + r"[\s!.]*$", re.IGNORECASE)),
    ("how_are_you", re.compile(r"^(?:(?:hi+|hello+|hey+)[\s,]+)?(?:how\s+(?:are|r)\s+(?:you|u)(?:\s+doing)?|"
                               r"how\s+is\s+it\s+going|what'?s\s+up|wass?up)" + _BUDDY + r"[\s?!.]*$", re.IGNORECASE)),
    ("thanks", re.compile(r"^(?:ok(?:ay)?[\s,]+)?(?:thanks?(?:\s+a\s+lot)?|thank\s*(?:you|u)(?:\s+so\s+much|\s+very\s+much)?|"
                          r"thx|tq|ty)" + _BUDDY + r"[\s!.]*$", re.IGNORECASE)),
    ("bye", re.compile(r"^(?:ok(?:ay)?[\s,]+)?(?:bye+|good\s*bye|see\s+(?:you|u)|good\s+night)" + _BUDDY + r"[\s!.]*$",
                       re.IGNORECASE)),
    ("who_are_you", re.compile(r"^(?:who\s+(?:are|r)\s+(?:you|u)|what\s+(?:are|r)\s+(?:you|u)|"
                               r"what\s+can\s+(?:you|u)\s+do|what\s+is\s+sru\s*_?\s*buddy|"
                               r"are\s+(?:you|u)\s+(?:a\s+|an\s+)?(?:bot|human|ai|real|robot))" + r"[\s?!.]*$", re.IGNORECASE)),
)


def small_talk(message: str):
    """'greeting', 'how_are_you', 'thanks', 'bye' or 'who_are_you' when the message is ONLY that."""
    msg = (message or "").strip()
    if len(msg) > 60:
        return None
    for kind, pattern in _SMALL_TALK_PATTERNS:
        if pattern.match(msg):
            return kind
    return None


# ------------------------------------------------ OWASP LLM Guardrails ----
_ADVERSARIAL_PROMPT_PATTERN = re.compile(
    r"\b("
    # Instruction bypass / override / jailbreak
    r"ignore\s+(all\s+)?(previous|above|prior|system)\s+(instructions|prompts|rules|commands)|"
    r"disregard\s+(all\s+)?(previous|above|prior|system)\s+(instructions|prompts|rules)|"
    r"forget\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)|"
    r"you\s+are\s+now\s+(DAN|GPT|unrestricted|in\s+developer\s+mode|jailbroken|a\s+different\s+ai)|"
    r"act\s+as\s+(DAN|an\s+unrestricted|a\s+jailbroken|developer\s+mode|an\s+ai\s+without)|"
    r"enter\s+(developer\s+mode|DAN\s+mode|god\s+mode|unrestricted\s+mode)|"
    r"enable\s+(developer\s+mode|DAN\s+mode|jailbreak)|"
    r"jailbreak|"
    # System prompt extraction / leaking
    r"(reveal|tell\s+me|show\s+me|print|output|repeat|display|dump)\s+(your|the)\s+(?:system\s+prompt|context|hidden\s+prompt|raw\s+prompt|rules|(?:initial\s+|secret\s+|internal\s+)+(?:instructions?|prompt))|"
    r"(what\s+(?:is|are)\s+your|what\s+were\s+your)\s+(?:system\s+prompt|(?:initial\s+|secret\s+|internal\s+)+(?:instructions?|prompt)|rules|context)|"
    r"(repeat|output)\s+the\s+words\s+above|"
    # Malicious cyber & exploit generation
    r"write\s+(me\s+a?\s+)?.*?(code|script|program|exploit|tool)\s+(to|that|for)\s+(hack|crack|break|exploit|bypass|steal|ddos|phish)|"
    r"\b(how\s+to\s+(?:create|make|write|build|develop|code|generate)|write\s+(?:me\s+)?(?:a\s+)?)\b.*?\b(malware|virus|ransomware|trojan|keylogger|exploit|payload|phishing|spyware)\b|"
    r"\b(hack|crack|break\s+into|exploit|bypass|steal|ddos|phish)\b.*?\b(website|account|password|database|wifi|server|system)\b|"
    r"\b(hacking|phishing|ddos|malware|ransomware|keylogger|exploit)\b.*?\b(tutorial|guide|how\s+to|script|code)\b"
    r")\b",
    re.IGNORECASE,
)

ADVERSARIAL_REFUSAL_RESPONSE = (
    "I am SRU Buddy, the official AI assistant for SR University admissions and campus information. "
    "I cannot alter my core instructions, disclose system prompts, or assist with unauthorized or malicious requests. "
    "I would be glad to help you with SR University programs, admissions, merit scholarships, fee structures, or campus facilities!"
)


def check_adversarial_guardrail(message: str) -> str | None:
    """Pre-execution guardrail check against prompt injections, system prompt extraction, and malicious queries.

    Returns a deterministic refusal message if an adversarial pattern is detected, otherwise None.
    """
    if not message:
        return None
    if _ADVERSARIAL_PROMPT_PATTERN.search(message):
        return ADVERSARIAL_REFUSAL_RESPONSE
    return None

