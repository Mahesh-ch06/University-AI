"""Events, campus life, clubs, sports, hostel life and food (v4.14.0).

Answers come only from facts the admissions team approved on 24 Nov 2026 (sru.edu.in Events / Campus Life / Clubs
pages, the admissions presentation of 30 Oct 2026, the hostel rules and fee documents, the official YouTube
channel). The events themselves are the admin panel's list (Admin -> Campus media -> Events), so an event added
or edited there is used in the very next answer. No source links are shown to students.

topic(message, waiting) -> the topic key, or None (not about these things, or an answer to a pending step).
answer(key, message)    -> Answer(text, chips, event_ids, video_ids): the verified text (the model may word it,
                           see agent._reply), the event cards to show (in order) and the official videos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from app.services import app_settings

# A message about one of these is not ours: fees, admissions, placements, rankings... (or several questions).
_OTHER_TOPIC = re.compile(
    r"\b(fee|fees|cost|price|pay|paid|tuition|scholar\w*|concession|discount|eligib\w*|cut-?off|marks?|percent\w*|"
    r"apply|application|admission|placement\w*|package|lpa|salary|recruit\w*|rank\w*|nirf|naac|accredit\w*|"
    r"syllab\w*|curricul\w*|faculty|professor|callback|call me|visit|bus|transport|refund|deadline|document\w*|"
    r"loan|hall ticket|exam|room types?|sharing|ac rooms?|non-?ac|curfew|in-?time|out-?pass|rules?|warden|"
    r"ragging|safety|security|laundry charge|deposit|quota|reservation|ncc|defence|disab\w*|orphan|single\s+parent)\b|"
    r"\d+\s*%", re.I)
# General-knowledge questions that only share a word with campus life ("who won the cricket world cup?").
_WORLD = re.compile(
    r"\b(who\s+won|world\s+cup|ipl|t20|odi|test\s+match|score|olympics?|fifa|premier\s+league|virat|dhoni|"
    r"sachin|cricketer|footballer|recipe|how\s+to\s+(?:cook|make)|movie|film|actor|actress|song\s+lyrics|"
    r"prime\s+minister|president|capital\s+of|weather|news|stock\s+price|bitcoin)\b", re.I)
_QUESTIONISH = re.compile(
    r"\?|^\s*(?:how|what|whats|what's|which|when|where|who|is|are|was|do|does|did|can|could|will|tell|show|any|"
    r"explain|describe|share|give|list|i want|i wanna|want to know|info|details?)\b", re.I)

_EVENTS = re.compile(
    r"\b(events?|fests?|festivals?|celebrat\w*|cultural\s+(?:activit\w*|programs?|programmes?|nights?)|"
    r"concerts?|dj\s+night|annual\s+day|culturals|extra-?curricular)\b", re.I)
_CLUBS = re.compile(r"\b(clubs?|societ(?:y|ies)|student\s+chapters?|chapters?|communit(?:y|ies)\s+for\s+students)\b",
                    re.I)
_SPORTS = re.compile(
    r"\b(sports?|gym|gymnasium|fitness|games|cricket|football|basketball|badminton|tennis|volleyball|kabaddi|"
    r"athletics?|playground|stadium|swimming|yoga|martial\s+arts?|workout)\b", re.I)
_FOOD = re.compile(
    r"\b(food|mess|meals?|canteen|cafeteria|cafe|dining|breakfast|lunch|dinner|snacks?|tiffin|veg|vegetarian|"
    r"non-?veg\w*|chicken|egg|eggs|menu|kitchen|eat|eating|hungry|kiosks?|food\s+court)\b", re.I)
_HOSTEL_LIFE = re.compile(
    r"\bhostel\s*(?:life|lyf|experience|culture|environment|atmosphere|vibes?|days)\b|"
    r"\b(?:life|living|staying|stay)\s+in\s+(?:the\s+)?hostels?\b|"
    r"\bhow\s+(?:is|are|was)\s+(?:the\s+)?hostels?\s*(?:here|at\s+sru|in\s+sru)?\s*[?!.]*$|"
    r"\b(?:is|are)\s+(?:the\s+)?hostels?\s+(?:good|nice|comfortable|clean|ok|okay|fun|bad)\b|"
    r"\bhostels?\s+(?:good|nice|ok|okay)\s*\?", re.I)
_CAMPUS_LIFE = re.compile(
    r"\b(?:campus|student|college|university|uni)\s*(?:life|lyf|experience|culture|environment|atmosphere|vibes?)\b|"
    r"\blife\s+(?:at|in)\s+(?:sru|sr\s+university|the\s+campus|campus|this\s+college|the\s+college|your\s+college)\b|"
    r"\bhow\s+(?:is|are|was)\s+(?:the\s+)?(?:campus|college|university|sru)\s*(?:here|life)?\s*[?!.]*$|"
    r"\bwhat\s+(?:do|can)\s+(?:students|we|i)\s+do\s+(?:after|beyond|outside)\s+(?:classes|class|college)\b|"
    r"\b(?:fun|enjoy\w*|activities)\s+(?:at|in|on)\s+(?:sru|the\s+campus|campus|college)\b|"
    r"\bstudent\s+activities\b|\bis\s+(?:sru|the\s+campus|campus)\s+(?:fun|boring|good\s+for\s+students)\b", re.I)
_WELLNESS = re.compile(
    r"\b(mental\s+health|stress|anxiety|depress\w*|wellness|well-?being|medical|doctor|hospital|health\s*(?:centre|"
    r"center|care|clinic)|clinic|ambulance|first\s+aid|sick|fever|emergency)\b", re.I)


# ---- the 39 clubs on sru.edu.in/clubs-organisations (official descriptions) ---------------------------------------
# (group, name, aliases students use, description)
CLUBS = [
    ("tech", "Google Developers Club", "google developers, gdsc, gdg, google", "Learn through Google technologies, developer tools and hands-on projects, and connect with fellow developers."),
    ("tech", "AWS Club", "aws, amazon web services", "Hands-on cloud computing with AWS technologies, building practical projects."),
    ("tech", "Azure Developer Club", "azure, microsoft azure", "Learn and build with Microsoft Azure through projects, workshops and activities."),
    ("tech", "Cloud Computing and DevOps Club", "cloud, devops", "How modern applications are built, deployed and managed, with practical cloud and DevOps exposure."),
    ("tech", "AI & ML Club", "ai, ml, ai & ml, artificial intelligence, machine learning", "Hands-on Artificial Intelligence and Machine Learning projects."),
    ("tech", "Data Science Club", "data science, data, analytics", "Work with data to solve real-world problems and build practical skills."),
    ("tech", "Coding Club", "coding, programming, competitive programming, cp", "Turn ideas into code: practise, build projects and take on coding challenges."),
    ("tech", "GeeksforGeeks Club", "geeksforgeeks, gfg, dsa, problem solving", "Practise coding, problem-solving and technical skills together."),
    ("tech", "GitHub Club", "github, open source, git", "Build and collaborate on real projects, with open-source contributions and team development."),
    ("tech", "Hackathon Club", "hackathon", "Team up and turn an idea into a working solution under real challenges."),
    ("tech", "Cyber Security Club", "cyber security, cybersecurity, ethical hacking, hacking, security", "Explore cybersecurity, ethical hacking and practical security concepts."),
    ("tech", "IEEE Club", "ieee, electronics, electrical", "Connect engineering concepts with practical applications and emerging technologies."),
    ("tech", "ACM Student Chapter", "acm", "Explore the wider world of computing through events, projects and discussions."),
    ("tech", "ACM-Women", "acm-women, acm women, women in tech, women in computing, girls in tech", "A supportive space for women interested in computing and technology."),
    ("tech", "Computer Society of India (CSI)", "csi, computer society", "Technical events, projects and activities beyond the classroom."),
    ("tech", "ACIS Club", "acis, information systems", "Learn about computing and information systems through ideas and projects."),
    ("culture", "Ashwavega Club", "ashwavega, cultural club, culture club", "Celebrates the energy, talent and creativity of student life: participate, perform and make campus memories."),
    ("culture", "Dance Club", "dance, dancing", "Learn, perform and enjoy dancing together, whether you're experienced or trying it for the first time."),
    ("culture", "Drama Club", "drama, theatre, theater, acting, skit", "Bring stories to life on stage, build confidence and express yourself."),
    ("culture", "Sangeetam Club", "sangeetam, music, singing, band, instrument", "For students who love music: sing, play and perform."),
    ("culture", "Photopedia Club", "photopedia, photography, photo, camera", "Capture people, places and moments while developing your photography skills."),
    ("culture", "Fashion Club", "fashion, styling, modelling, modeling, ramp", "Explore fashion, styling and trends, and develop your own style."),
    ("culture", "Designing and Branding Club", "designing, design, branding, graphic design", "Visual communication, branding and creative design."),
    ("culture", "Digital Design and Branding Club", "digital design", "Turn ideas into visuals that make an impact."),
    ("culture", "LMCC", "lmcc, literature, debate, debating, public speaking, communication, writing, poetry", "For students who love words and ideas: communication skills, literature and creative expression."),
    ("culture", "E-Gaming Club", "e-gaming, egaming, gaming, esports, games club", "Gaming enthusiasts connect and compete in friendly matches."),
    ("sports", "Sports Club", "sports club", "Play, compete and stay active, with teamwork and a healthy competitive spirit."),
    ("sports", "Yoga Club", "yoga, meditation", "Practise yoga, improve your focus and find balance."),
    ("sports", "Martial Arts Club", "martial arts, karate, taekwondo, self defence, self-defence, self defense, kung fu", "Strength, discipline, confidence and self-defence skills."),
    ("sports", "Adventure Club", "adventure, trekking, trek, hiking, camping", "Step outside your comfort zone, explore and make memories."),
    ("sports", "Gardening Club", "gardening, plants, nature, environment, green club", "Plant and nurture, and help make the campus greener."),
    ("business", "Startup & Innovation Club", "startup, startups, innovation, entrepreneurship, entrepreneur", "Take an idea further: learn, experiment, build and connect with an entrepreneurial community."),
    ("business", "Finance Club", "finance, investment, investing, stock market, stocks, trading", "Money and business in practice: finance, investments and budgeting."),
    ("business", "Marketing Club", "marketing, advertising, brands", "Brands, campaigns, consumer behaviour and the creative side of marketing."),
    ("business", "HR Club", "hr, human resources, people management", "HR, leadership, teamwork and people management."),
    ("business", "Business Analytics Club", "business analytics", "How businesses use data to make better decisions."),
    ("business", "Logistics & Supply Chain Club", "logistics, supply chain, operations", "Planning, operations, logistics and supply chain management."),
    ("business", "International Student Affairs Networking Club", "international student, international students, networking, foreign students", "Brings students from different backgrounds together to share cultures and experiences."),
]
CLUB_GROUPS = {"tech": "Tech clubs", "culture": "Culture & creativity clubs", "sports": "Sports & wellbeing clubs",
               "business": "Business & leadership clubs"}
_GROUP_WORDS = {"tech": r"tech\w*|technical|coding\s+clubs", "culture": r"cultur\w*|creativ\w*|arts?\b|fun\s+clubs",
                "sports": r"sports?\s+clubs|fitness\s+clubs|wellbeing|well-being",
                "business": r"business|management|leadership|non-?tech\w*"}


def find_club(message: str) -> tuple | None:
    low = " " + re.sub(r"[^a-z0-9&+\- ]+", " ", (message or "").lower()) + " "
    best, best_len = None, 0
    for club in CLUBS:
        for alias in [club[1].lower()] + [a.strip() for a in club[2].split(",")]:
            if alias and re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", low) and len(alias) > best_len:
                best, best_len = club, len(alias)
    return best


def club_group(message: str) -> str | None:
    for key, words in _GROUP_WORDS.items():
        if re.search(rf"\b(?:{words})", message or "", re.I) and re.search(r"\bclubs?\b", message or "", re.I):
            return key
    return None


def _unknown_club(message: str) -> str | None:
    """'robotics club' / 'club for chess' when no such club is on the list: the word the student used."""
    m = re.search(r"\b([a-z][a-z\- ]{2,24}?)\s+club\b", (message or "").lower()) or \
        re.search(r"\bclubs?\s+(?:for|of|on|about)\s+([a-z][a-z\- ]{2,24})", (message or "").lower())
    if not m:
        return None
    word = re.sub(r"^(?:is|are|there|a|an|the|any|do|does|you|have|sru|in|at|of|which|what|good|best|"
                  r"tell|me|about|join|some|\s)+", "", m.group(1)).strip()
    if not word or word in ("student", "students", "college", "university", "campus", "all", "many", "how",
                            "list", "other", "more", "different", "kind", "kinds", "type", "types"):
        return None
    return word


@dataclass
class Answer:
    text: str
    chips: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)
    video_ids: list[str] = field(default_factory=list)
    video_query: str = ""          # show official videos on this topic, picked at random (see video_service)
    options: bool = True           # the chips answer the question the reply asks


def events() -> list[dict]:
    """The enabled events, in the admin panel's order."""
    return [e for e in (app_settings.get("event_highlights") or []) if e.get("enabled", True)]


def _names(event: dict) -> list[str]:
    words = [w.strip().lower() for w in (event.get("keywords") or "").split(",") if len(w.strip()) > 2]
    head = re.split(r"\s+[–—-]\s+", event.get("title") or "")[0].strip().lower()
    return [n for n in [head, *words] if n]


def find_event(message: str) -> dict | None:
    """The event named in the message (by its title or other names), or None."""
    low = " " + re.sub(r"[^a-z0-9' ]+", " ", (message or "").lower()) + " "
    best, best_len = None, 0
    for e in events():
        for name in _names(e):
            if re.search(rf"(?<![a-z]){re.escape(name)}(?![a-z])", low) and len(name) > best_len:
                best, best_len = e, len(name)
    return best


def topic(message: str, waiting: bool = False) -> str | None:
    """What the message asks about, or None. `waiting`: a step of a workflow waits for an answer, so a bare
    word ("sports", "yes") is that answer, not a question about campus life."""
    text = (message or "").strip()
    if not text or len(text) > 300:
        return None
    if waiting and not _QUESTIONISH.search(text) and len(text.split()) <= 2 and not find_event(text):
        return None                       # a bare word ("sports", "yes") answers the step that is waiting
    if _OTHER_TOPIC.search(text) or _WORLD.search(text):
        return None
    event = find_event(text)
    if event:
        return "event:" + event["id"]
    if _HOSTEL_LIFE.search(text):
        return "hostel_life"
    if _FOOD.search(text):
        return "food"
    if _CLUBS.search(text) or (find_club(text) and re.search(r"\bclub", text, re.I)):
        return "clubs"
    if _EVENTS.search(text):
        return "events"
    if _SPORTS.search(text):
        return "sports"
    if _CAMPUS_LIFE.search(text):
        return "campus_life"
    if _WELLNESS.search(text) and not re.search(r"\b(counsell?or|talk|connect|speak|call)\b", text, re.I):
        return "wellness"
    return None


# ---- the verified texts ------------------------------------------------------------------------------------
_CLUBS_TEXT = (
    "SR University has **39 student clubs**, technical and cultural:\n\n"
    "• **Tech:** Google Developers, AWS, Azure Developer, AI & ML, Data Science, Cloud & DevOps, Coding, Cyber "
    "Security, GitHub, GeeksforGeeks, Hackathon, IEEE, ACM and CSI\n"
    "• **Culture & creativity:** Dance, Drama, Sangeetam (music), Fashion, Photopedia, Designing & Branding and "
    "E-Gaming\n"
    "• **Sports & wellbeing:** Sports, Yoga, Martial Arts, Adventure and Gardening\n"
    "• **Business & leadership:** Startup & Innovation, Finance, Marketing, HR, Business Analytics, LMCC "
    "(communication) and International Student Affairs\n\n"
    "Which kind of club interests you?")
_SPORTS_TEXT = (
    "Sports at SR University:\n\n"
    "• **Sports complex:** indoor and outdoor courts and grounds for basketball, cricket, football, badminton, "
    "tennis and more\n"
    "• **Fitness:** an Olympic-standard gym and fitness centres\n"
    "• **Competitions:** the Annual Sports Day and annual inter-university tournaments\n"
    "• **Clubs:** the Sports, Yoga, Martial Arts and Adventure clubs\n\n"
    "Would you like to know about the clubs or the other events on campus?")
_FOOD_TEXT = (
    "Food at SR University:\n\n"
    "• **Dining hall:** a 4,000-seat dining hall serving **4 meals a day**, healthy, hygienic and nutritious, with "
    "vegetarian and non-vegetarian food\n"
    "• **Mess timings:** Breakfast 7:30–8:30 AM · Lunch 12:00–2:00 PM · Snacks 5:00–6:00 PM · Dinner "
    "7:30–8:30 PM\n"
    "• **Beyond the mess:** the Central Cafeteria (8:30 AM–6:00 PM) and the Tasty Treat, Meet and Eat and Bharat "
    "Foods kiosks (9:00 AM–7:00 PM)\n"
    "• Meals are included in the hostel fee.\n\n"
    "Would you like to know about hostel life or the hostel fees?")
_HOSTEL_LIFE_TEXT = (
    "Hostel life at SR University:\n\n"
    "• **Rooms:** AC and non-AC, 3- or 4-sharing, with modern furniture, study desks and high-speed internet; "
    "separate hostels for boys and girls\n"
    "• **Food:** 4 meals a day in the 4,000-seat dining hall\n"
    "• **Everyday comforts:** laundry and housekeeping, RO drinking water on every floor, hot water 7–9 AM and "
    "7–9 PM, 24x7 Wi-Fi and power backup\n"
    "• **Safety:** 24/7 surveillance and wardens; first-year students are back in the hostel by 8:30 PM\n"
    "• **Fun:** recreational spaces and **Lumina – Hostel Night**, the hostellers' own annual celebration\n\n"
    "Would you like the hostel fees or the mess timings?")
_WELLNESS_TEXT = (
    "Health and support at SR University:\n\n"
    "• **Medical:** 24/7 medical and emergency support, with hospital tie-ups\n"
    "• **Counselling:** professional counsellors for stress and anxiety, peer support and student helplines\n"
    "• **Career guidance:** resume workshops and mock interviews\n\n"
    "Would you like to know about hostel life or campus life?")


def _when(e: dict, today: date | None = None) -> str:
    """The event's date as the admin wrote it; 'last held' when that date (e.g. '9 October 2026') has passed."""
    when = (e.get("when") or "").strip()
    m = re.match(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", when)
    if m:
        try:
            day = datetime.strptime(m.group(1), "%d %B %Y").date()
            if day < (today or date.today()):
                return "last held " + when
        except ValueError:
            pass
    return when


def _event_line(e: dict) -> str:
    when = _when(e)
    return f"• **{e['title']}**" + (f" · {when}" if when else "")


def _events_text() -> tuple[str, list[str]]:
    evs = events()
    if not evs:
        return ("SR University holds **50+ events every year**, cultural, technical and sports. Would you like to "
                "know about campus life or the clubs?", [])
    top = evs[:7]
    lines = [_event_line(e) for e in top]
    rest = [_short(e) for e in evs[7:]]
    more = f"\n\nAlso: {', '.join(rest)}." if rest else ""
    return ("SR University holds **50+ events every year**. The highlights:\n\n" + "\n".join(lines) + more
            + "\n\nWhich event would you like to know more about?", [e["id"] for e in evs])


def _short(e: dict) -> str:
    return re.split(r"\s+[–—-]\s+", e["title"])[0]


_EVALUATIVE = re.compile(r"\b(good|bad|nice|great|ok|okay|fine|quality|tasty|hygien\w*|clean|worth|boring|fun|"
                         r"enjoy\w*|like|best|worst|decent|safe)\b|\bhow\s+(?:is|are|was)\b", re.I)
_LEADS = {
    "food": "Students eat well at SRU: the food is healthy, hygienic and nutritious, with plenty of choice.\n\n",
    "hostel_life": "SRU's hostels are comfortable, safe and lively, a real home away from home.\n\n",
    "campus_life": "Not boring at all! ",
}


def answer(key: str, message: str = "") -> Answer:
    ans = _answer(key, message)
    lead = _LEADS.get(key) if _EVALUATIVE.search(message or "") else None
    if lead and key == "campus_life" and not re.search(r"\bboring\b", message or "", re.I):
        lead = None
    if lead:
        if key != "campus_life" and re.match(r"\s*(?:is|are|does|do|will|can|was)\b", message or "", re.I):
            lead = "Yes! " + lead
        ans.text = lead + ans.text
    return ans


def _answer(key: str, message: str = "") -> Answer:
    evs = {e["id"]: e for e in events()}
    if key.startswith("event:"):
        e = evs.get(key[6:])
        if not e:
            text, ids = _events_text()
            return Answer(text, [_short(x) for x in events()[:3]], ids)
        w = _when(e)
        when = f"\n\n**{'Last held' if w.startswith('last held') else 'When'}:** {w.removeprefix('last held ')}" \
            if w else ""
        text = (f"**{e['title']}**\n\n{e.get('summary') or ''}{when}\n\n"
                "Would you like to see the other events at SRU?")
        # the event's photo card carries its "Watch video" link: no second video card
        return Answer(text, ["Yes, show other events", "Hostel life", "Clubs at SRU"], [e["id"]], options=True)
    if key == "events":
        text, ids = _events_text()
        return Answer(text, [_short(x) for x in events()[:3]], ids)
    if key == "clubs":
        club = find_club(message)
        if club and not club_group(message):
            same = [c[1] for c in CLUBS if c[0] == club[0] and c[1] != club[1]][:4]
            text = (f"Yes, SR University has the **{club[1]}**. {club[3]}\n\n"
                    f"Other {CLUB_GROUPS[club[0]].lower()}: {', '.join(same)}.\n\n"
                    "Would you like to see all 39 clubs?")
            return Answer(text, ["Yes, show all clubs", "Events at SRU"], [], options=True)
        group = club_group(message)
        if group:
            rows = "\n".join(f"• **{c[1]}:** {c[3]}" for c in CLUBS if c[0] == group)
            others = [v for k, v in CLUB_GROUPS.items() if k != group]
            return Answer(f"{CLUB_GROUPS[group]} at SR University:\n\n{rows}\n\nWould you like to see the "
                          f"{others[0].lower()} or the {others[1].lower()}?", others[:2], [])
        unknown = _unknown_club(message)
        lead = (f"A **{unknown.title()}** club isn't on SR University's official list of clubs. " if unknown else "")
        return Answer(lead + _CLUBS_TEXT, ["Tech clubs", "Culture & creativity clubs", "Sports & wellbeing clubs"], [],
                      video_query="")
    if key == "sports":
        ids = [i for i in ("sports_day",) if i in evs]
        low = (message or "").lower()
        listed = [x for x in ("basketball", "cricket", "football", "badminton", "tennis") if x in low]
        unlisted = [x for x in ("swimming", "volleyball", "kabaddi", "hockey", "chess", "squash", "table tennis",
                                "athletics", "skating", "archery") if x in low and not (x == "tennis" and listed)]
        if re.search(r"\bgym|gymnasium|fitness|workout", low):
            return Answer("Yes. SR University has an **Olympic-standard gym** and fitness centres, alongside the indoor and "
                          "outdoor sports complex (basketball, cricket, football, badminton, tennis and more).\n\n"
                          "Would you like to know about the Sports or Yoga clubs?", ["Sports clubs", "Events at SRU"], [])
        if listed:
            names = " and ".join(listed)
            return Answer(f"Yes. **{names.title()}** is part of SR University's sports complex, which has indoor and "
                          "outdoor facilities for basketball, cricket, football, badminton, tennis and more, plus an "
                          "Olympic-standard gym. Students also play in the annual inter-university tournaments.\n\n"
                          "Would you like to know about the Annual Sports Day or the sports clubs?",
                          ["Annual Sports Day", "Sports clubs"], ids)
        if unlisted:
            names = " / ".join(unlisted)
            return Answer(f"**{names.title()}** isn't among the facilities SR University lists for its sports complex "
                          "(basketball, cricket, football, badminton, tennis and more, plus an Olympic-standard gym). "
                          "The Admissions team can confirm it for you.\n\nWould you like to know about the sports clubs?",
                          ["Sports clubs", "Talk to a counsellor"], [])
        return Answer(_SPORTS_TEXT, ["Clubs at SRU", "Events at SRU"], ids)
    if key == "food":
        low = (message or "").lower()
        if re.search(r"timing|\btime\b|when\s+is|what\s+time|breakfast|lunch|dinner|snacks", low) \
                and not re.search(r"\b(?:good|quality|tasty|how\s+is)\b", low):
            return Answer("Mess timings at SR University:\n\n• **Breakfast:** 7:30–8:30 AM\n• **Lunch:** 12:00–2:00 PM\n"
                          "• **Snacks:** 5:00–6:00 PM\n• **Dinner:** 7:30–8:30 PM\n\nBetween meals, the Central Cafeteria "
                          "is open 8:30 AM–6:00 PM and the food kiosks 9:00 AM–7:00 PM. Would you like to know about hostel "
                          "life?", ["Hostel life", "Hostel fees"], [])
        if re.search(r"non-?\s?veg|chicken|egg|vegetarian|\bveg\b", low):
            return Answer("Yes. The dining hall serves **vegetarian and non-vegetarian** food, with 4 meals a day "
                          "(healthy, hygienic and nutritious), and the cafeteria and kiosks for snacks.\n\nWould you like "
                          "the mess timings?", ["Mess timings", "Hostel life"], [], ["rpRekBrnGYs"])
        if re.search(r"canteen|cafeteria|cafe|kiosk|food\s+court|snack", low):
            return Answer("Yes. Besides the 4,000-seat dining hall, SR University has the **Central Cafeteria** (8:30 AM–"
                          "6:00 PM) and the **Tasty Treat, Meet and Eat and Bharat Foods** kiosks (9:00 AM–7:00 PM).\n\n"
                          "Would you like the mess timings?", ["Mess timings", "Hostel life"], [])
        return Answer(_FOOD_TEXT, ["Hostel life", "Hostel fees"], [], ["rpRekBrnGYs"], video_query="hostel food")
    if key == "hostel_life":
        ids = [i for i in ("lumina",) if i in evs]
        return Answer(_HOSTEL_LIFE_TEXT, ["Hostel fees", "Mess timings"], ids, video_query="hostel life")
    if key == "wellness":
        return Answer(_WELLNESS_TEXT, ["Hostel life", "Campus life"], [], [], video_query="")
    # campus life
    ev_names = ", ".join(_short(e) for e in events()[:4]) or "cultural, technical and sports events"
    text = ("Campus life at SR University is full and friendly:\n\n"
            f"• **Events:** 50+ a year, like {ev_names}\n"
            "• **Clubs:** 39, from Google Developers and AI & ML to Dance, Drama and music\n"
            "• **Sports:** an indoor and outdoor sports complex and an Olympic-standard gym\n"
            "• **Innovation:** the SRiX incubator, with 171+ startups and maker spaces\n"
            "• **Living:** a 170+ acre green campus and hostels with a 4,000-seat dining hall\n"
            "• **Support:** 24/7 medical help and counsellors\n\n"
            "What would you like to explore: events, clubs, hostel life or sports?")
    return Answer(text, ["Events", "Clubs", "Hostel life", "Sports"], list(evs)[:6])


_RECAPS = {
    "food": ("In short: 4 meals a day in the 4,000-seat dining hall, vegetarian and non-vegetarian, plus the "
             "cafeteria and food kiosks for snacks. Would you like the mess timings or the hostel fees?",
             ["Mess timings", "Hostel fees"]),
    "hostel_life": ("In short: comfortable AC / non-AC rooms, 4 meals a day, laundry, Wi-Fi, 24/7 security and "
                    "Lumina, the hostellers' own Hostel Night. Would you like the hostel fees or the room options?",
                    ["Hostel fees", "Room options"]),
    "events": ("SRU has 50+ events a year; the highlights are in the cards above. Which one would you like to know "
               "about?", []),
    "clubs": ("There are 39 clubs, tech, cultural, sports and business. Tell me what you enjoy and I'll point you to "
              "the right club.", ["Tech clubs", "Culture & creativity clubs", "Sports & wellbeing clubs"]),
    "sports": ("In short: an indoor and outdoor sports complex, an Olympic-standard gym, the Annual Sports Day and "
               "sports clubs. Would you like to know about the clubs or the events?", ["Clubs at SRU", "Events at SRU"]),
    "campus_life": ("In short: 50+ events, 39 clubs, sports, the SRiX incubator and a green 170+ acre campus. What "
                    "would you like to explore: events, clubs, hostel life or sports?",
                    ["Events", "Clubs", "Hostel life", "Sports"]),
    "wellness": ("In short: 24/7 medical help with hospital tie-ups, counsellors and career guidance. Would you like "
                 "to know about hostel life?", ["Hostel life"]),
}


def recap(key: str, full: "Answer", message: str = "") -> "Answer":
    """The same topic asked again in one conversation: a short recap instead of the same block (a specific question,
    e.g. the mess timings or a cricket ground, keeps its own answer)."""
    if key in ("food", "sports") and full.text not in (_FOOD_TEXT, _SPORTS_TEXT):
        return full
    if key == "clubs" and (find_club(message) or club_group(message) or _unknown_club(message)):
        return full                                      # a specific club or group is a new question
    text, chips = _RECAPS.get(key, (None, None))
    if not text:
        return full
    if key == "events":
        names = ", ".join(_short(e) for e in events()[:4])
        text = f"SRU has 50+ events a year, like {names}. Which one would you like to know about?"
        chips = [_short(e) for e in events()[:3]]
    return Answer(text, chips or full.chips, [], [], "", options=True)


def event_cards(ids: list[str]) -> dict | None:
    """The photo-card carousel for these events (in this order), or None."""
    evs = {e["id"]: e for e in events()}
    items = []
    for i in ids:
        e = evs.get(i)
        if not e:
            continue
        vid = e.get("video_id") or ""
        items.append({"id": e["id"], "title": e["title"], "when": e.get("when") or "",
                      "summary": e.get("summary") or "", "image_url": e.get("image_url") or "",
                      "video_url": f"https://www.youtube.com/watch?v={vid}" if vid else ""})
    if not items:
        return None
    return {"type": "event_highlights", "title": "Events at SRU", "items": items[:10]}
