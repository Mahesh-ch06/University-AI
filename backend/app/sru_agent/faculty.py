"""Faculty directory search (official profiles from https://sru.edu.in/faculty/).

The data file faculty_directory.json is built by scripts/build_faculty_directory.py. Search is
plain code (no AI call): by name, by role (dean, head of department), by department or school,
and by research topic or subject.
"""
import difflib
import json
import re
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).with_name("faculty_directory.json")
DIRECTORY_URL = "https://sru.edu.in/faculty/"

# Words students use -> the department or school names on the faculty pages.
_DEPARTMENTS = [
    (r"\b(?:cse|cs|computer\s*science|computers?|it|information\s*technology|ai\s*ml|aiml|ai|artificial\s*intelligence|"
     r"data\s*science|cyber\s*security|machine\s*learning|software)\b", "Computer Science & Artificial Intelligence"),
    (r"\b(?:ece|electronics(?:\s*and\s*communication)?|communication\s*engineering|vlsi)\b",
     "Electronics & Communication Engineering"),
    (r"\b(?:eee|electrical(?:\s*and\s*electronics)?)\b", "Electrical & Electronics Engineering"),
    (r"\b(?:mech|mechanical)\b", "Mechanical Engineering"),
    (r"\b(?:civil)\b", "Civil Engineering"),
    (r"\b(?:maths?|mathematics|statistics)\b", "Mathematics"),
    (r"\b(?:physics)\b", "Physics"),
    (r"\b(?:chemistry)\b", "Chemistry"),
    (r"\b(?:english|communication\s*skills)\b", "English"),
    (r"\b(?:biotech|biotechnology)\b", "Biotechnology"),
    (r"\b(?:mba|bba|b\.?com|business|management|commerce|astra)\b", "Astra School of Business"),
    (r"\b(?:agri|agriculture|agricultural|b\.?\s*sc\s*(?:\(?\s*hons\.?\s*\)?\s*)?ag\w*|horticulture)\b",
     "School of Agriculture"),
    (r"\b(?:engineering\s+school|school\s+of\s+engineering)\b", "School of Engineering"),
    (r"\b(?:sciences?\s*(?:and|&)\s*humanities)\b", "School of Sciences & Humanities"),
]
_FACULTY_WORDS = re.compile(
    r"\b(?:faculty|faculties|professors?|prof|lecturers?|teachers?|teaching\s+staff|staff|hod|h\.o\.d|"
    r"heads?\s+of\b|dean|deans|mentor|who\s+teach(?:es)?|research(?:ers?)?\s+(?:on|in)|"
    r"ph\.?\s?d\s+(?:holders?|faculty|guides?|supervisors?))\b", re.IGNORECASE)
_STOP = set("the a an of in on at for to and or is are who what which with about sru sr university faculty "
            "faculties professor professors teacher teachers teach teaches teaching staff department dept school "
            "me tell list show give any there do does have has their your our dr mr ms mrs please research "
            "researching doing work works working expert experts specialist specialists many how much best good "
            "senior name names head hod dean deans qualified qualification experience experienced areas area "
            "all list named called".split())
# Words that only name a department (not a research topic).
_UNIT_ONLY = set("cse cs it ece eee mech mechanical civil maths math mathematics physics chemistry english biotech "
                 "biotechnology mba bba bcom com business management commerce astra agri agriculture agricultural "
                 "computer computers science sciences electronics electrical communication engineering information "
                 "technology humanities btech tech".split())


@lru_cache(maxsize=1)
def _data() -> dict:
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"faculty": [], "count": 0, "collected_on": ""}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _name_key(name: str) -> str:
    """The person's name only: honorifics and any role written in brackets after the name
    ("Dr. Rupesh Mishra (Director of Centre for Experiential Learning)") are not part of it."""
    name = re.sub(r"\([^)]*\)", " ", name or "")
    return " ".join(w for w in _norm(name).split() if w not in ("dr", "prof", "mr", "ms", "mrs"))


# Words that name an office or a title, never a person: a question that shares "Director" or "Admissions" with a
# profile is not about that person (v4.17.1, entity resolution).
_ROLE_WORDS = set("director directors deputy associate assistant additional joint chief executive officer officers "
                  "registrar controller chancellor vice pro president chairman chairperson chair principal "
                  "coordinator coordinators manager incharge charge warden librarian secretary ceo cfo coo "
                  "admissions admission marketing placement placements training examinations exams exam evaluation "
                  "office centre center cell lead leads leader leaders role position designation holds hold serve "
                  "serves served post title officials official authority".split())
_ROLE_NOUN = re.compile(
    r"\b(?:director|registrar|controller|chancellor|officer|coordinator|principal|president|ceo|"
    r"chair(?:man|person)?|warden|librarian|secretary|in[\s-]?charge|manager)s?\b", re.IGNORECASE)


def _name_words(query: str) -> list[str]:
    """The words of a query that can be part of a person's name."""
    return [w for w in _name_key(query).split()
            if len(w) > 2 and w not in _STOP and w not in _ROLE_WORDS and w not in _UNIT_ONLY and not _units(w)]


def _is_person_name(words: list[str]) -> bool:
    """Do these words name someone in the directory (every word a name part, close spellings allowed)?"""
    words = [w for w in words if len(w) > 2]
    if not words:
        return False
    for p in _data()["faculty"]:
        parts = _name_key(p["name"]).split()
        if all(w in parts or any(difflib.SequenceMatcher(None, w, part).ratio() >= 0.84 for part in parts
                                 if len(part) > 2) for w in words):
            return True
    return False


def _stem(word: str) -> str:
    return word[:6]


def _office_words(query: str) -> list[str]:
    """What the asked role is about ("Director of Admissions and Marketing" -> admissions, marketing)."""
    generic = {"director", "directors", "deputy", "associate", "assistant", "additional", "joint", "chief",
               "officer", "officers", "role", "position", "designation", "holds", "hold", "serve", "serves",
               "lead", "leads", "leader", "leaders", "post", "title", "official", "officials", "authority"}
    return [w for w in _norm(query).split()
            if len(w) > 2 and w not in _STOP and w not in generic and not _ROLE_NOUN.fullmatch(w)]


def _holds_role(person: dict, query: str) -> bool:
    """Does this profile's own role / designation name the office asked about (every office word, and the title)?"""
    text = _norm(f"{person.get('name', '')} {person.get('role', '')} {person.get('designation', '')}")
    words = text.split()
    noun = _ROLE_NOUN.search(query or "")
    if noun and _stem(noun.group(0).lower()) not in {_stem(w) for w in words}:
        return False
    office = _office_words(query)
    return bool(office) and all(any(_stem(w) == _stem(o) for w in words) for o in office)


_TITLE_NAME = re.compile(r"\b(?:dr|prof|professor)\.?\s+[A-Za-z]{3,}|\bwho\s+heads?\b", re.IGNORECASE)


def is_faculty_question(message: str) -> bool:
    return bool(_FACULTY_WORDS.search(message or "") or _TITLE_NAME.search(message or ""))


def _units(text: str) -> list[str]:
    found = []
    for pattern, unit in _DEPARTMENTS:
        if re.search(pattern, text or "", re.IGNORECASE) and unit not in found:
            found.append(unit)
    return found


def _in_unit(person: dict, unit: str) -> bool:
    return unit in (person.get("department"), person.get("school"))


def _leads(person: dict, kind: str) -> bool:
    """Is this person a Dean / Head (not an Associate or Assistant Dean)? Uses the role line on the
    profile and the designation ('Professor, Dean, Astra School of Business')."""
    parts = [person.get("role") or ""] + (person.get("designation") or "").split(",")
    return any(re.match(rf"\s*{kind}\b", part, re.IGNORECASE) for part in parts)


def _topic_words(query: str) -> list[str]:
    return [w for w in _norm(query).split() if len(w) > 1 and w not in _STOP and w not in _UNIT_ONLY]


def _brief(p: dict, detail: bool = False) -> dict:
    out = {"name": p["name"], "position": p["role"] or p["designation"], "department": p["department"],
           "school": p["school"], "qualification": p["qualification"],
           "experience_years": p["experience_years"], "research_areas": p["research_areas"][:160],
           "profile_url": p["profile_url"]}
    if p["role"] and p["designation"] and p["designation"] not in p["role"]:
        out["designation"] = p["designation"]
    if detail:
        out.update({"subjects": p["subjects"], "education": p["education"], "supervision": p["supervision"],
                    "about": p["about"]})
    return {k: v for k, v in out.items() if v not in (None, "")}


def _by_name(query: str):
    """People whose name matches the query well (exact words, or a close spelling)."""
    q = _name_key(query)
    words = [w for w in q.split() if len(w) > 2 and w not in _STOP]
    if not words:
        return []
    scored = []
    for p in _data()["faculty"]:
        key = _name_key(p["name"])
        parts = key.split()
        hits = sum(1 for w in words if w in parts or any(
            difflib.SequenceMatcher(None, w, part).ratio() >= 0.84 for part in parts if len(part) > 2))
        if hits:
            scored.append((hits / max(len(parts), 1) + hits, p))
    scored.sort(key=lambda t: -t[0])
    if not scored:
        return []
    best = scored[0][0]
    return [p for s, p in scored if s >= best - 0.01][:5]


def _school_of(unit: str) -> str:
    """The school a department belongs to (from the directory itself)."""
    for p in _data()["faculty"]:
        if p["department"] == unit:
            return p["school"]
    return unit


def _by_topic(query: str, people: list, limit: int = 6):
    words = [w for w in _norm(query).split() if (len(w) > 2 or w in ("ai", "ml", "iot")) and w not in _STOP]
    if not words:
        return []
    scored = []
    for p in people:
        hay = " " + _norm(" ".join([p["research_areas"], p["interests"], p["subjects"]])) + " "
        score = sum(hay.count(f" {w}") for w in words)
        if len(words) > 1 and " ".join(words) in hay:
            score += 3  # the whole phrase ("machine learning"), not just one of its words
        if score:
            scored.append((score, p["experience_years"] or 0, p))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    return [p for _s, _e, p in scored[:limit]]


def search(query: str = "", department: str = "", role: str = "") -> dict:
    """Find faculty. Returns {"status": "ok", ...} with matching people, or "no_results"."""
    data = _data()
    people = data["faculty"]
    if not people:
        return {"status": "not_available", "note": f"The faculty list is not loaded. Point to {DIRECTORY_URL}."}
    text = " ".join(x for x in (query, department, role) if x)
    low = text.lower()
    base = {"source": DIRECTORY_URL, "as_of": data.get("collected_on"),
            "note": "From the official SRU faculty pages. Give the profile link for full details."}

    units = _units(department or query)
    if not units and re.search(r"\b(?:engineering|b\.?\s?tech)\b", department or query or "", re.IGNORECASE):
        units = ["School of Engineering"]
    wants_dean = bool(re.search(r"\bdeans?\b", role or low))
    wants_head = bool(re.search(r"\b(?:hods?|h\.o\.d|heads?)\b", role or low))

    # 1. Dean / head of a department or school
    if wants_dean or wants_head:
        leaders = [p for p in people if (wants_dean and _leads(p, "dean")) or (wants_head and _leads(p, "head"))]
        if units:
            # the Dean of a school leads every department in it
            leaders = [p for p in leaders if any(_in_unit(p, u) or u in p["role"] or u in p["designation"]
                                                 for u in units)
                       or (_leads(p, "dean") and any(_in_unit({"school": p["school"]}, u) or
                                                     _school_of(u) == p["school"] for u in units))]
        # Deans of a school (or Heads of a department) first; deans of a portfolio (Student Welfare,
        # Publications ...) only when no school / department leader matches.
        def _is_unit_leader(p):
            text = f"{p['role']}, {p['designation']}"
            return bool(re.search(r"\b(?:Dean|Head)\s*,\s*(?:School of|Astra|Department of)", text))
        primary = [p for p in leaders if _is_unit_leader(p)]
        portfolio_words = [w for w in _topic_words(query or "") if w not in ("hods", "heads")]
        portfolio = [p for p in leaders if not _is_unit_leader(p) and portfolio_words and
                     all(w in _norm(p["designation"]) for w in portfolio_words)]
        if portfolio and not units:
            primary = portfolio  # "dean of student welfare"
        elif portfolio_words and not units and not _is_person_name(portfolio_words):
            # "Associate Dean PDF" / "dean of students": the profile whose own designation is that title, or none
            title = portfolio_words + (["dean"] if wants_dean else ["head"])
            titled = [p for p in people if all(any(_stem(w) == _stem(x) for x in
                                                   _norm(f"{p['role']} {p['designation']}").split()) for w in title)]
            if titled:
                main = [p for p in titled if not re.search(r"\b(?:associate|assistant|deputy|additional)\s+(?:dean|head)",
                                                         f"{p['role']} {p['designation']}", re.IGNORECASE)]
                out = {**base, "status": "ok", "kind": "role_holder",
                       "note": "Quote each designation exactly as written.",
                       "faculty": [_brief(p, detail=len(titled) == 1) for p in (main or titled)[:6]]}
                if not main:
                    out["exact_title_held"] = False
                    out["note"] = ("No profile holds the exact title asked; these hold related associate / assistant "
                                   "titles. Say that, quote their titles exactly, and do not call any of them the "
                                   "holder of the title asked.")
                return out
            # an office no profile here holds; the school deans are different people (they are not returned for it)
            return {**base, "status": "no_results", "kind": "role_not_in_directory", "asked_role": query or role,
                    "note": "No faculty profile holds this office. Answer only from the approved university "
                            "documents; do not name a school dean for it."}
        if primary:
            leaders = primary
        if leaders:
            return {**base, "status": "ok", "kind": "leaders",
                    "faculty": [_brief(p, detail=len(leaders) == 1) for p in leaders[:12]]}

    # 2. A role or office ("Director of Admissions", "registrar"): only a profile whose own designation names
    #    that office answers it. The directory lists teaching faculty and academic leaders; other offices are in
    #    the approved university documents (the tool searches them when this says role_not_in_directory).
    asked_names = _name_words(query) if query else []
    role_query = bool(_ROLE_NOUN.search(text)) and not (wants_dean or wants_head)
    holders = [p for p in people if _holds_role(p, text)] if role_query else []
    if holders:
            return {**base, "status": "ok", "kind": "role_holder",
                    "note": "These profiles' own designation names the office asked about. Quote the designation "
                            "exactly as written.",
                    "faculty": [_brief(p, detail=len(holders) == 1) for p in holders[:6]]}
    if role_query and not asked_names:
        return {**base, "status": "no_results", "kind": "role_not_in_directory",
                "asked_role": query or role,
                "note": "No faculty profile holds this office. Do not name a faculty member for it because a title "
                        "word (e.g. 'Director') is shared; answer only from the approved university documents."}

    # 3. A person by name: every name word must match (a close spelling counts); a partial match is reported as
    #    such, never as the same person.
    named = _by_name(" ".join(asked_names)) if asked_names else []
    if named and not units:
        def _missing(p):
            parts = _name_key(p["name"]).split()
            # a close spelling counts as the same name word ("seshikala" ~ "sheshikala", 0.95); "randeep" is
            # not "sandeep" (0.86) and "mitra" is not "mishra" (0.73)
            return [w for w in asked_names if w not in parts and not any(
                difflib.SequenceMatcher(None, w, part).ratio() >= 0.88 for part in parts if len(part) > 2)]
        # everyone whose name has every asked word (not just the best-scored: "Babu" names three people)
        exact = [p for p in people if not _missing(p)]
        if len(exact) > 3:
            return {**base, "status": "ok", "kind": "person", "match": "ambiguous", "matches": len(exact),
                    "faculty": [_brief(p) for p in exact[:5]],
                    "note": f"{len(exact)} profiles match this name: ask the student for the full name or "
                            "department; do not pick one."}
        if exact:
            out = {**base, "status": "ok", "kind": "person", "match": "exact",
                   "faculty": [_brief(p, detail=True) for p in exact]}
            if len(exact) > 1:
                out["note"] = ("Several profiles match this name: say they are different people and ask which one "
                               "the student means.")
            if role_query:
                out["role_check"] = {p["name"]: _holds_role(p, text) for p in exact}
                if not all(out["role_check"].values()):
                    out["note"] = ("The profile does not list the role asked about. Say so; do not confirm a role "
                                   "the designation does not show.")
            return out
        if not exact and len(named) <= 3:
            return {**base, "status": "ok", "kind": "person", "match": "partial",
                    "asked_name": " ".join(asked_names),
                    "unmatched_name_words": sorted({w for p in named for w in _missing(p)}),
                    "faculty": [_brief(p) for p in named],
                    "note": "No profile matches the full name asked. These are only similar names: they may be "
                            "different people. Do not say they are the same person; ask the student to confirm "
                            "the name, and do not attribute any role to them from the question."}

    # 4. A topic, optionally inside a department ("who teaches machine learning in CSE")
    pool = [p for p in people if any(_in_unit(p, u) for u in units)] if units else people
    topical = _by_topic(" ".join(_topic_words(query or "")), pool)
    if topical:
        return {**base, "status": "ok", "kind": "topic", "faculty": [_brief(p) for p in topical]}

    # 5. A whole department or school: numbers, leaders and a few senior names
    if units:
        unit = units[0]
        members = [p for p in people if _in_unit(p, unit)]
        if members:
            leaders = [p for p in members if p["role"]]
            senior = sorted([p for p in members if not p["role"]],
                            key=lambda p: (0 if p["designation"].startswith("Professor") else
                                           1 if p["designation"].startswith("Associate") else 2,
                                           -(p["experience_years"] or 0)))
            phd = sum(1 for p in members if p["qualification"].startswith("Ph.D."))
            return {**base, "status": "ok", "kind": "department", "department": unit,
                    "faculty_listed": len(members), "with_phd_listed": phd,
                    "professors": sum(1 for p in members if p["designation"].startswith("Professor")),
                    "associate_professors": sum(1 for p in members if p["designation"].startswith("Associate")),
                    "assistant_professors": sum(1 for p in members if p["designation"].startswith("Assistant")),
                    "leaders": [_brief(p) for p in leaders],
                    "some_senior_faculty": [_brief(p) for p in senior[:6]]}

    if named:
        return {**base, "status": "ok", "kind": "person", "match": "partial",
                "note": "Similar names only; confirm the person with the student before attributing anything.",
                "faculty": [_brief(p) for p in named]}
    if not _topic_words(query or ""):
        return {**base, "status": "ok", "kind": "overview", **overview()}  # "tell me about the faculty"
    return {**base, "status": "no_results",
            "note": f"No matching faculty profile. Suggest the official directory {DIRECTORY_URL}."}


def overview() -> dict:
    """Numbers for 'tell me about the faculty' (all schools)."""
    people = _data()["faculty"]
    by_school: dict = {}
    for p in people:
        by_school[p["school"]] = by_school.get(p["school"], 0) + 1
    return {"faculty_listed": len(people), "by_school": by_school,
            "with_phd_listed": sum(1 for p in people if p["qualification"].startswith("Ph.D.")),
            "deans": [_brief(p) for p in people if re.search(r"\bDean\s*,\s*(?:School of|Astra)",
                                                              f"{p['role']}, {p['designation']}")],
            "source": DIRECTORY_URL, "as_of": _data().get("collected_on")}
