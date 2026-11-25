"""Fee, scholarship and eligibility maths. Pure Python, no AI.

The agent is NOT allowed to state a fee from memory. It must call these
functions, which read fee_policy_2027_28.json (the 2027-28 fee circular), so every
number is traceable. calculate_fee / fee_schedule is the ONLY fee calculator.
The Fee & Scholarship Calculator reads the same file through
/api/v1/agent/fee-config and /api/v1/agent/calculate.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).with_name("fee_policy_2027_28.json")
HOSTEL_LABELS = {
    "non_ac_4": "Non-AC, 4-sharing", "non_ac_3": "Non-AC, 3-sharing",
    "ac_4": "AC, 4-sharing", "ac_3": "AC, 3-sharing",
}
# score kind -> label shown to students
EXAM_LABELS = {
    "state_board": "State Board (10+2 / Inter) %",
    "cbse": "CBSE / ICSE %",
    "jee_percentile": "JEE Main percentile",
    "eapcet_rank": "TG/AP EAPCET rank",
    "ib": "IB Diploma score",
}
# A degree word in the question limits which programs may match, so that
# "mtech data science" is M.Tech and not B.Tech CSE.
_DEGREE_PREFIXES = {
    "mtech": ("mtech",), "mba": ("mba",), "mca": ("mca",), "msc": ("msc",),
    "bba": ("bba",), "bca": ("bca",), "bsc": ("bsc",), "bcom": ("bcom",),
    "bdes": ("bdes",), "btech": ("btech",),
}
_DEGREE_SPELLINGS = (
    (r"\bb\s?tech\b", "btech"), (r"\bm\s?tech\b", "mtech"), (r"\bb\s?sc\b", "bsc"),
    (r"\bm\s?sc\b", "msc"), (r"\bb\s?com\b", "bcom"), (r"\bb\s?des\b", "bdes"),
)


@lru_cache(maxsize=1)
def load_data() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def inr(amount) -> str:
    """Format rupees the Indian way: 340000 -> '₹3,40,000'."""
    n = int(round(amount))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + "₹" + s


def _normalise(text: str) -> str:
    t = (text or "").lower().replace(".", "")
    t = re.sub(r"[^a-z0-9&+ ]", " ", t)
    for pattern, word in _DEGREE_SPELLINGS:
        t = re.sub(pattern, word, t)
    return " " + re.sub(r"\s+", " ", t).strip() + " "


def find_program(text: str):
    """Match free text like 'cse', 'mech', 'B.Tech AI & ML' to a program key."""
    if not text:
        return None
    programs = load_data()["programs"]
    if text in programs:
        return text
    t = _normalise(text)
    if t.strip() in programs:
        return t.strip()

    degree = next((d for d in _DEGREE_PREFIXES if f" {d} " in t), None)
    allowed = [k for k in programs if not degree or k.startswith(_DEGREE_PREFIXES[degree])]

    best = None
    for key in allowed:
        for alias in programs[key]["aliases"]:
            if f" {alias} " in t and (best is None or len(alias) > best[0]):
                best = (len(alias), key)
    if best:
        return best[1]
    # "mca", "mtech", "bcom" on their own name exactly one program
    if degree and degree in programs:
        return degree
    return None


_SHORT_NAMES = {"btech_cse": "B.Tech CSE", "btech_ece": "B.Tech ECE", "btech_eee": "B.Tech EEE",
                "btech_mech": "B.Tech Mechanical", "btech_civil": "B.Tech Civil",
                "btech_ai_robotics": "B.Tech AI & Robotics", "bsc_agri": "B.Sc Agriculture", "bba": "BBA",
                "mba": "MBA", "bca": "BCA", "mca": "MCA", "bcom": "B.Com", "bdes": "B.Des", "mtech": "M.Tech",
                "msc": "M.Sc"}


def short_name(key: str) -> str:
    """'B.Tech CSE' for chips and short sentences (clean_program_name gives the full official name)."""
    return _SHORT_NAMES.get(key) or clean_program_name(key)


def _is_generic_btech(text: str) -> bool:
    t = _normalise(text)
    return " btech " in t or " engineering " in t


def clean_program_name(key: str, specialization: str | bool | None = None, user_text: str | None = None) -> str:
    """Returns the exact, clean program name based on user selection without dumping all specializations."""
    low_text = (user_text or "").lower()
    spec = specialization.lower() if isinstance(specialization, str) else ""

    if key in ("btech_cse", "btech_cse_core", "cse"):
        # Check for specific specializations
        if any(k in spec for k in ("aiml", "ai & ml", "ai and ml", "ai/ml", "aml", "machine learning")) or re.search(r"\b(?:aiml|ai\s*&?\s*ml|ai\s*and\s*ml|ai/ml|aml|machine\s+learning)\b", low_text):
            return "B.Tech CSE (Artificial Intelligence & Machine Learning)"
        if any(k in spec for k in ("data science", "datascience", "ds")) or re.search(r"\b(?:data\s+science|datascience|ds)\b", low_text):
            return "B.Tech CSE (Data Science)"
        if any(k in spec for k in ("cyber security", "cybersecurity", "cyber", "infosec")) or re.search(r"\b(?:cyber\s*security|cybersecurity|cyber|infosec)\b", low_text):
            return "B.Tech CSE (Cyber Security)"
        if any(k in spec for k in ("quantum ai", "quantum")) or re.search(r"\b(?:quantum\s*ai|quantum)\b", low_text):
            return "B.Tech CSE (Quantum AI)"
        if any(k in spec for k in ("robotics & automation", "robotics and automation", "robotics")) or re.search(r"\b(?:robotics(?:\s*(?:&|and)\s*automation)?)\b", low_text):
            return "B.Tech CSE (Robotics & Automation)"
        return "B.Tech Computer Science & Engineering (CSE)"

    if key == "btech_ai_robotics":
        return "B.Tech in Artificial Intelligence & Robotics"

    if key == "btech_ece":
        return "B.Tech Electronics & Communication Engineering (ECE)"

    if key == "btech_eee":
        return "B.Tech Electrical & Electronics Engineering (EEE)"

    if key == "btech_mech":
        return "B.Tech Mechanical Engineering"

    if key == "btech_civil":
        return "B.Tech Civil Engineering"

    if key == "btech_biotech":
        return "B.Tech Biotechnology"

    if key == "btech_food_tech":
        return "B.Tech Food Technology"

    if key == "btech_iep":
        return "B.Tech International Engineering Program (IEP)"

    if key == "bsc_agri":
        return "B.Sc (Hons.) Agriculture"

    if key == "mba":
        return "Master of Business Administration (MBA)"

    if key == "bba":
        return "Bachelor of Business Administration (BBA)"

    if key == "bca":
        return "BCA (Bachelor of Computer Applications)"

    if key == "mca":
        return "MCA (Master of Computer Applications)"

    if key == "mtech":
        return "M.Tech Computer Science & Engineering"

    try:
        data = load_data()
        prog = data.get("programs", {}).get(key, {})
        raw_name = prog.get("name", key)
        if "(AIML," in raw_name or "(Core," in raw_name:
            return "B.Tech Computer Science & Engineering (CSE)"
        return raw_name
    except Exception:
        return key



def _match_slab(slabs, value):
    val = round(value, 2)
    for slab in slabs:
        if slab["min"] <= val <= slab["max"]:
            return slab["percent"]
    return 0


def _scores(percent=None, board="state_board", eapcet_rank=None, jee_percentile=None, ib_score=None,
            level="ug"):
    scores = []
    if percent is not None:
        # PG scholarships use the percentage in the qualifying degree, whatever the school board was.
        is_cbse = level != "pg" and str(board or "").lower() in ("cbse", "icse")
        scores.append(("cbse" if is_cbse else "state_board", float(percent)))
    if eapcet_rank is not None:
        scores.append(("eapcet_rank", int(eapcet_rank)))
    if jee_percentile is not None:
        scores.append(("jee_percentile", float(jee_percentile)))
    if ib_score is not None:
        scores.append(("ib", float(ib_score)))
    return scores


def _score_text(kind: str, value, level: str = "ug") -> str:
    """'Intermediate 85%', 'EAPCET rank 40,000' ... for showing a score back to the student."""
    if kind == "eapcet_rank":
        return f"EAPCET rank {int(value):,}"
    if kind == "jee_percentile":
        return f"JEE Main {value:g} percentile"
    if kind == "ib":
        return f"IB score {value:g}/45"
    if level == "pg":
        return f"qualifying degree {value:g}%"
    return f"{'CBSE/ICSE' if kind == 'cbse' else 'Intermediate'} {value:g}%"


def _no_slab_reason(kind: str, table: list) -> str:
    """Why a score earned no scholarship, in words a student understands."""
    if kind == "eapcet_rank":
        worst = max(s["max"] for s in table)
        return f"rank-based scholarships cover EAPCET ranks 1 to {int(worst):,} only"
    lowest = min(s["min"] for s in table)
    unit = {"jee_percentile": " percentile", "ib": " (IB score)"}.get(kind, "%")
    return f"merit scholarship starts at {lowest:g}{unit}"


def scholarship_for(program_key, percent=None, board="state_board",
                    eapcet_rank=None, jee_percentile=None, ib_score=None) -> dict:
    """Best scholarship across the scores given, plus what EACH score earns by itself.
    Never guesses a missing table."""
    data = load_data()
    prog = data["programs"][program_key]
    level = prog.get("level", "ug")
    slab_set = data["slab_sets"].get(prog["slab_set"], {})
    best, basis, basis_text, missing, considered = 0, None, None, [], []
    for kind, value in _scores(percent, board, eapcet_rank, jee_percentile, ib_score, level):
        table = slab_set.get(kind) or []
        label = _score_text(kind, value, level)
        if not table:
            missing.append(kind)
            considered.append({"score": label, "scholarship_percent": 0,
                               "note": "this score is not used for scholarships in this program"})
            continue
        pct = _match_slab(table, value)
        entry = {"score": label, "scholarship_percent": pct}
        if not pct:
            entry["note"] = _no_slab_reason(kind, table)
        considered.append(entry)
        if pct > best:
            best, basis, basis_text = pct, f"{kind.replace('_', ' ')} {value:g}", label
    return {"percent": best, "basis": basis, "basis_text": basis_text, "not_configured": missing,
            "considered": considered}


def _exam_label(kind: str, prog: dict) -> str:
    if prog.get("level") == "pg" and kind == "state_board":
        return "Qualifying degree %"
    return EXAM_LABELS[kind]


def _range_text(kind: str, slab: dict) -> str:
    lo, hi = slab["min"], slab["max"]
    if kind == "eapcet_rank":
        return f"{lo:,} – {hi:,}"
    if kind == "ib":
        return f"{lo:g} and above" if hi >= 45 else f"{lo:g} – {hi:g}"
    unit = " %ile" if kind == "jee_percentile" else "%"
    if hi >= 100:
        return f"{lo:g}{unit} and above"
    return f"{lo:g} – {int(hi * 10) / 10:g}{unit}"


def _next_slab(program_key, pct_now, percent=None, board="state_board",
               eapcet_rank=None, jee_percentile=None, ib_score=None):
    """The next higher slab for the score the student gave: what it needs and what it saves."""
    data = load_data()
    prog = data["programs"][program_key]
    slab_set = data["slab_sets"].get(prog["slab_set"], {})
    scores = _scores(percent, board, eapcet_rank, jee_percentile, ib_score, prog.get("level", "ug"))
    if not scores:
        return None
    kind, _value = scores[0]
    higher = sorted((s for s in slab_set.get(kind) or [] if s["percent"] > pct_now),
                    key=lambda s: s["percent"])
    if not higher:
        return None
    nxt = higher[0]
    extra = round(prog["tuition_per_year"] * (nxt["percent"] - pct_now) / 100)
    return {"scholarship_percent": nxt["percent"],
            "requires": f"{_exam_label(kind, prog)}: {_range_text(kind, nxt)}",
            "extra_saving_first_year": inr(extra)}


def check_eligibility(program: str, percent=None, stream: str | None = None) -> dict:
    """Admission eligibility on marks, from the single eligibility module (never a threshold written here).
    Admission eligibility is NOT scholarship eligibility: scholarships are calculate_fee / scholarship_for."""
    from . import eligibility
    key = find_program(program)
    if not key and _is_generic_btech(program):
        # "btech" with no branch: the minimums differ by branch (CSE / ECE fee band), so ask the branch.
        return {"status": "need_branch",
                "ask_student": "Ask which B.Tech branch they want; minimums differ between branches."}
    if not key:
        return {"status": "unknown_program", "known_programs": list_programs()["programs"]}
    if percent in (None, "") :
        return {"status": "need_marks", "program": clean_program_name(key),
                "ask_student": "Ask for their 10+2 / Intermediate marks (percentage, or marks with the total), "
                               "or the degree percentage for a PG programme. Do not assume any marks."}
    result = eligibility.assess(key, float(percent), stream)
    return {
        "status": "ok",
        "program": result["program"],
        "your_percent": result["percent"],
        "eligibility_status": result["status"],
        "eligible": result["eligible"],
        "lowest_listed_minimum": result["floor"],
        "highest_listed_minimum": result["ceiling"],
        "sources_disagree": result["conflict"],
        "requirement": (result.get("stream_requirement") or {}).get("label") or load_data()["programs"][key]["eligibility_note"],
        "explanation": eligibility.explain(result),
        "instruction": ("Give the student the 'explanation' text in your own words without changing any figure. "
                        "below_minimum: say clearly they do not meet the minimum on these marks; never say they "
                        "qualify. needs_confirmation: the official sources disagree, so do not say eligible or "
                        "not eligible; ask them to confirm with the Admissions Office. Never invent alternative "
                        "pathways or exceptions."),
    }


def list_programs() -> dict:
    data = load_data()
    return {"status": "ok", "academic_year": data["academic_year"], "programs": [
        {"key": k, "name": p["name"], "level": p.get("level", "ug"),
         "tuition_per_year": inr(p["tuition_per_year"]),
         "minimum_percent": p["min_percent"]} for k, p in data["programs"].items()]}


def program_info(program: str) -> dict:
    """Eligibility, duration, tuition and scholarship slabs for one program (no student marks needed)."""
    data = load_data()
    key = find_program(program)
    if not key:
        return {"status": "unknown_program", "known_programs": list_programs()["programs"]}
    prog = data["programs"][key]
    slab_set = data["slab_sets"].get(prog["slab_set"], {})
    slabs = {}
    for kind, table in slab_set.items():
        if table:
            slabs[_exam_label(kind, prog)] = [
                f"{_range_text(kind, s)} -> {s['percent']}% scholarship"
                for s in sorted(table, key=lambda s: s["percent"])]
    info = {
        "status": "ok", "academic_year": data["academic_year"], "source": data["source"],
        "program": prog["name"], "level": prog.get("level", "ug"),
        "duration_years": prog.get("duration_years"),
        "minimum_percent": prog["min_percent"],
        "eligibility": prog["eligibility_note"],
        "tuition_per_year": inr(prog["tuition_per_year"]),
        "tuition_per_semester": inr(prog["tuition_per_year"] / 2),
        "tuition_split": "Only tuition is split equally between the two semesters; other charges are added by the calculator.",
        "yearly_tuition_increase": inr(prog["yearly_increase"]),
        "merit_scholarship_slabs": slabs,
        "reminder": "Admission depends on seat availability and document verification.",
    }
    if prog.get("min_percent_confirmed") is False:
        info["note"] = f"The {prog['min_percent']:g}% PG minimum is subject to confirmation by the Admissions Office."
    if prog.get("duration_years") is None:
        info["duration_note"] = "Course duration is not in the fee policy. Do not state one."
    return info


def special_concessions(category: str = "") -> dict:
    """Annual special-category concessions from the circular, optionally filtered by a keyword."""
    data = load_data()
    items = data.get("special_concessions", [])
    ignore = {"state", "level", "student", "students", "from", "any", "the", "and", "for", "child",
              "children", "scholarship", "concession", "discount", "fee", "there"}
    words = [w for w in re.findall(r"[a-z]+", (category or "").lower()) if len(w) > 2 and w not in ignore]
    matched = [c for c in items
               if any(w in c["label"].lower() or w in c["key"] for w in words)] if words else []
    return {
        "status": "ok", "academic_year": data["academic_year"],
        "matching": [{"category": c["label"], "per_year": inr(c["amount"])} for c in matched],
        "all_categories": [{"category": c["label"], "per_year": inr(c["amount"]),
                            **({"selectable": False, "note": c.get("note", "")} if not c.get("selectable", True) else {})}
                           for c in items],
        "note": data.get("special_concession_note", ""),
        "instruction": "If 'matching' is empty, say plainly that the category asked about is not in the "
                       "official list, then mention the closest listed categories. Do not ask the student "
                       "for personal hardship details; documents go to the Admissions Office.",
    }


def charge_amount(key: str, variant: str | None = None) -> int:
    """One fee head from the circular, e.g. charge_amount('other_fee') -> 15000."""
    c = load_data()["charges"][key]
    return int(c[variant] if variant else c.get("amount", 0))


def hostel_per_year() -> dict:
    """Hostel room fees (with meals). NOT on the fee circular: pending confirmation, see policy['hostel']."""
    return dict(load_data().get("hostel", {}).get("per_year", {}))


def _allocate(amount: int, where, semesters: int = 2) -> list[int]:
    """Place an annual amount in one semester (1, 2) or split it ('split')."""
    out = [0] * semesters
    if where == "split":
        first = round(amount / semesters)
        out[0] = first
        for i in range(1, semesters):
            out[i] = (amount - first) // (semesters - 1)
        out[-1] += amount - sum(out)
    else:
        out[max(0, min(semesters, int(where or 1)) - 1)] = amount
    return out


def _concession_items(concessions) -> list[dict]:
    """Selected special-category concessions (keys or labels) that the circular lists and a student may claim."""
    items = {c["key"]: c for c in load_data().get("special_concessions", [])}
    by_label = {c["label"].lower(): c for c in items.values()}
    chosen = []
    for c in concessions or ():
        key = c.get("key") if isinstance(c, dict) else c
        item = items.get(key) or by_label.get(str(key or "").lower())
        if item and item.get("selectable", True) and item not in chosen:
            chosen.append(item)
    return chosen


def fee_schedule(program_key: str, scholarship_percent: float = 0, *, hostel: str | None = None,
                 transport: bool = False, specialization: bool = False, concessions=()) -> dict:
    """THE semester-wise fee engine (steps 3-14 of the fee policy). Deterministic, component based.

    Tuition is the only amount split between the two semesters. Every other head is placed where the
    policy (or its configurable ``schedule``) says: one-time charges once, annual charges whole in one
    semester, optional charges only when chosen, and no merit scholarship on any charge.
    """
    data = load_data()
    prog = data["programs"][program_key]
    rules = data.get("schedule", {})
    n_sem = int(rules.get("semesters_per_year", 2))
    years = prog.get("duration_years") or 1
    base = int(prog["tuition_per_year"])
    inc = int(prog["yearly_increase"])
    scholarship = round(base * float(scholarship_percent) / 100)                       # step 4-5
    continues = rules.get("scholarship_continues_every_year", True)
    charges = data["charges"]
    hostel_fee = hostel_per_year().get(hostel, 0) if hostel and hostel != "none" else 0
    deposit = charges["electricity_deposit"]["ac" if str(hostel).startswith("ac") else "non_ac"] if hostel_fee else 0
    spec_on = bool(specialization) and program_key in rules.get("specialization_fee_programs", [])
    chosen = _concession_items(concessions)
    concession_total = sum(int(c["amount"]) for c in chosen)

    out_years, course_total = [], 0
    for y in range(1, years + 1):
        sch_y = scholarship if (y == 1 or continues) else 0
        annual = base - sch_y + (y - 1) * inc                                            # step 6
        sem_tuition = _allocate(annual, "split", n_sem)                                   # step 8
        sems = [{"semester": s + 1, "items": [{"key": "tuition", "label": "Tuition", "amount": sem_tuition[s],
                                                "kind": "tuition"}]} for s in range(n_sem)]

        def put(key, label, amount, where, kind="charge"):
            for s, amt in enumerate(_allocate(int(amount), where, n_sem)):
                if amt:
                    sems[s]["items"].append({"key": key, "label": label, "amount": amt, "kind": kind})

        # step 9: concessions, an annual deduction from tuition (never more than the year's tuition)
        if concession_total:
            ded = min(concession_total, annual)
            first = int(rules.get("concession_semester", 1)) - 1 if rules.get("concession_semester") != "split" else None
            parts = _allocate(ded, "split" if first is None else first + 1, n_sem)
            for s in range(n_sem):                     # a deduction never exceeds that semester's tuition
                over = parts[s] - sem_tuition[s]
                if over > 0:
                    parts[s] -= over
                    parts[(s + 1) % n_sem] += over
            for s, amt in enumerate(parts):
                if amt:
                    sems[s]["items"].append({"key": "concession", "label": "Special concession",
                                             "amount": -amt, "kind": "concession"})
        # steps 10-11: charges, placed by the policy
        if y == 1:
            c = charges["enrollment_fee"]
            put("enrollment_fee", c["label"], c["amount"], c.get("semester", 1))
        if y == 1 or rules.get("other_fee_every_year", True):
            put("other_fee", charges["other_fee"]["label"], charges["other_fee"]["amount"],
                charges["other_fee"].get("semester", 1))
        if y == 1:
            c = charges["exam_fee"]
            put("exam_fee", c["label"], c["amount"], c.get("semester", 1))
        if spec_on and y >= charges["specialization_fee"].get("from_year", 2):
            put("specialization_fee", charges["specialization_fee"]["label"], charges["specialization_fee"]["amount"],
                charges["specialization_fee"].get("semester", 1))
        if transport:
            put("bus", charges["bus"]["label"], charges["bus"]["amount"], rules.get("bus_semester", 1), "optional")
        if hostel_fee:
            put("hostel", f"Hostel ({HOSTEL_LABELS.get(hostel, hostel)})", hostel_fee, rules.get("hostel_semester", 1),
                "optional")
            if y == 1:
                put("electricity_deposit", charges["electricity_deposit"]["label"], deposit, 1, "optional")
        for s in sems:                                                                    # step 12
            s["total"] = sum(i["amount"] for i in s["items"])
        year_total = sum(s["total"] for s in sems)                                        # step 13
        course_total += year_total
        out_years.append({"year": y, "tuition_before_scholarship": base + (y - 1) * inc, "scholarship": sch_y,
                          "annual_tuition": annual, "concession": min(concession_total, annual),
                          "semesters": sems, "total": year_total})
    return {"years": out_years, "duration_known": bool(prog.get("duration_years")),
            "course_total": course_total if prog.get("duration_years") else None,           # step 14
            "application_fee": charge_amount("application_fee"),                              # step 15
            "concessions": [{"key": c["key"], "label": c["label"], "amount": c["amount"]} for c in chosen]}


def verification_flags(program_key: str, percent=None, jee_percentile=None, ib_score=None,
                       eapcet_rank=None) -> list[str]:
    """Things the Admissions Office must verify before the estimate is final (never hidden from the student)."""
    data = load_data()
    prog = data["programs"][program_key]
    flags = []
    if percent is not None and float(percent) < float(prog["min_percent"]):
        flags.append(f"Your marks are below the {prog['min_percent']:g}% minimum listed for this programme; "
                     f"admission needs verification by the Admissions Office.")
    if prog.get("min_percent_confirmed") is False:
        flags.append(f"The {prog['min_percent']:g}% minimum for postgraduate programmes is subject to confirmation.")
    if jee_percentile is not None and 94.5 < float(jee_percentile) < 95:
        flags.append(data.get("jee_gap_note", ""))
    if ib_score is not None and 30 <= float(ib_score) <= 37 and data.get("ib_overlap_note"):
        flags.append(data["ib_overlap_note"])
    return [f for f in flags if f]


def calculate_fee(program: str, percent=None, board="state_board", eapcet_rank=None,
                  jee_percentile=None, hostel="none", specialization=False,
                  ib_score=None, transport=False, concessions=()) -> dict:
    """The ONE fee calculator (chatbot, admission flow and frontend all call it).

    Order: resolve programme -> check minimum -> base tuition -> scholarship -> increment -> concessions ->
    split tuition -> place charges -> semester payables -> annual payable -> course total; the application
    fee is shown separately and never added to a semester.
    """
    data = load_data()
    key = find_program(program)                                                          # step 1
    if not key:
        return {"status": "unknown_program",
                "ask_student": "Ask which course or branch they mean.",
                "known_programs": list_programs()["programs"]}
    prog = data["programs"][key]
    sch = scholarship_for(key, percent, board, eapcet_rank, jee_percentile, ib_score)
    pct = sch["percent"]
    base = prog["tuition_per_year"]                                                       # step 3
    plan = fee_schedule(key, pct, hostel=hostel, transport=transport, specialization=specialization,
                        concessions=concessions)
    y1 = plan["years"][0]
    s1, s2 = y1["semesters"][0], y1["semesters"][1]
    has_hostel = any(i["key"] == "hostel" for i in s1["items"] + s2["items"])
    hostel_fee = hostel_per_year().get(hostel, 0) if has_hostel else 0
    transport_fee = charge_amount("bus") if transport else 0
    spec_applies = bool(specialization) and key in data.get("schedule", {}).get("specialization_fee_programs", [])

    def money_rows(sem):
        return [{"key": i["key"], "item": i["label"], "amount": inr(i["amount"]), "kind": i["kind"]}
                for i in sem["items"]]

    result = {
        "status": "ok",
        "academic_year": data["academic_year"],
        "source": data["source"],
        "policy_id": data.get("policy_id"),
        "data_status": "verified" if data.get("verified") else
        "UNVERIFIED: tell the student the final fee will be confirmed by the Admissions Office",
        "program_key": key,
        "program": clean_program_name(key, specialization=specialization, user_text=program),
        "raw_program_name": prog["name"],
        "scholarship_percent": pct,
        "scholarship_basis": sch["basis"],
        "scholarship_basis_text": sch["basis_text"],
        # What each score earns by itself. The best one is applied; scholarships are not added together.
        "scores_considered": sch["considered"],
        "tuition_first_year": inr(base),
        "scholarship_amount_per_year": inr(y1["scholarship"]),
        "tuition_first_year_after_scholarship": inr(y1["annual_tuition"]),
        "per_semester_after_scholarship": inr(s1["items"][0]["amount"]),
        "saving_first_year": inr(y1["scholarship"]),
        "one_time_enrollment_fee": inr(charge_amount("enrollment_fee")),
        "exam_fee_first_year": inr(charge_amount("exam_fee")),
        "other_fee_per_year": inr(charge_amount("other_fee")),
        "application_fee": inr(plan["application_fee"]),
        "application_fee_note": "Paid once with the application form; not part of any semester payable.",
        "has_hostel": has_hostel,
        "hostel": {
            "type": HOSTEL_LABELS.get(hostel),
            "per_year": inr(hostel_fee),
            "electricity_deposit": inr(charge_amount("electricity_deposit", "ac" if str(hostel).startswith("ac") else "non_ac")),
            "status": "Hostel fees are not on the 2027-28 fee circular; the Admissions Office confirms them.",
        } if has_hostel else None,
        "transport_per_year": inr(transport_fee) if transport_fee else None,
        "specialization_fee_per_year": inr(charge_amount("specialization_fee")) if spec_applies else None,
        "concessions_applied": [{"category": c["label"], "per_year": inr(c["amount"])} for c in plan["concessions"]],
        "semester_1": {"items": money_rows(s1), "total": inr(s1["total"])},
        "semester_2": {"items": money_rows(s2), "total": inr(s2["total"])},
        "sem1_total_payable": inr(s1["total"]),
        "sem2_total_payable": inr(s2["total"]),
        # A semester with no one-time or annual charges (Year 1, Semester 2).
        "total_per_semester": inr(s2["total"]),
        "first_year_total_payable": inr(y1["total"]),
        "yearly_increase": inr(prog["yearly_increase"]),
        "schedule": [{"year": y["year"], "annual_tuition": inr(y["annual_tuition"]),
                      "semesters": [{"semester": s["semester"], "items": money_rows(s), "total": inr(s["total"])}
                                    for s in y["semesters"]],
                      "total": inr(y["total"])} for y in plan["years"]],
        "not_included": ["application form fee (paid separately)", "books and personal expenses"]
        + ([] if transport_fee else ["bus (optional)"]) + ([] if has_hostel else ["hostel (optional)"]),
        "notes": [],
        "flags": verification_flags(key, percent, jee_percentile, ib_score, eapcet_rank)
        + (["More than one special concession was selected; whether they can be combined is decided by the "
            "Admissions Office on verification."] if len(plan["concessions"]) > 1 else []),
    }
    if plan["course_total"] is not None:
        result["duration_years"] = prog["duration_years"]
        result["year_by_year"] = [{"year": y["year"], "tuition": inr(y["tuition_before_scholarship"]),
                                   "after_scholarship": inr(y["annual_tuition"]),
                                   "per_semester": inr(y["semesters"][0]["items"][0]["amount"]),
                                   "total_payable": inr(y["total"])} for y in plan["years"]]
        result["full_course_total"] = inr(plan["course_total"])
    else:
        result["notes"].append("Course duration is not set in the fee policy, so no full-course total.")

    nxt = _next_slab(key, pct, percent, board, eapcet_rank, jee_percentile, ib_score)
    if nxt:
        result["next_scholarship_slab"] = nxt
    if has_hostel:
        result["hostel_options_per_year"] = {HOSTEL_LABELS[k]: inr(v) for k, v in hostel_per_year().items()}
    if sch["not_configured"]:
        result["notes"].append(
            "No scholarship table is configured for: " + ", ".join(sch["not_configured"]) +
            ". Do NOT state a scholarship for that score; say the Admissions Office will confirm it.")
    given = _scores(percent, board, eapcet_rank, jee_percentile, ib_score)
    if not given:
        result["notes"].append("No marks or rank given, so no scholarship applied. Ask for marks to personalise.")
    elif pct == 0 and not sch["not_configured"]:
        result["notes"].append("This score is outside the merit scholarship slabs, so the standard fee applies. "
                               "Another score (board %, JEE, EAPCET) may still qualify.")
    result["notes"].append("Merit scholarship applies to tuition only, subject to marksheet verification.")
    if percent is not None:
        # Admission eligibility is separate from the scholarship: a 23% student gets no "you qualify".
        from . import eligibility                                                         # step 2
        verdict = eligibility.assess(key, float(percent))
        result["admission_eligibility"] = {
            "status": verdict["status"], "eligible": verdict["eligible"],
            "lowest_listed_minimum": verdict["floor"], "highest_listed_minimum": verdict["ceiling"],
            "explanation": eligibility.explain(verdict),
        }
        if verdict["status"] == eligibility.BELOW:
            result["instruction"] = ("The student's marks are BELOW the programme minimum. Lead with the "
                                     "admission_eligibility explanation: they do not meet the minimum on these "
                                     "marks. Do not present this fee as a fee they can pay or say they qualify.")
    return result


def rankings() -> dict:
    """Rankings and accreditations exactly as printed on the official fee card."""
    data = load_data()
    return {"status": "ok", "source": data["source"], "rankings": data.get("rankings", [])}


def compare_programs(program_a: str, program_b: str, **score) -> dict:
    """Side-by-side fee summary of two programs for the same student."""
    rows = []
    for name in (program_a, program_b):
        r = calculate_fee(name, **score)
        if r.get("status") != "ok":
            return {"status": "unknown_program", "unknown": name,
                    "known_programs": list_programs()["programs"]}
        rows.append({k: r.get(k) for k in (
            "program", "scholarship_percent", "tuition_first_year",
            "tuition_first_year_after_scholarship", "per_semester_after_scholarship",
            "first_year_total_payable", "yearly_increase", "duration_years", "full_course_total")})
    data = load_data()
    return {"status": "ok", "academic_year": data["academic_year"], "source": data["source"],
            "comparison": rows,
            "instruction": "Compare on fees only. Do not say which branch has better jobs unless a "
                           "search result supports it."}


def fee_config() -> dict:
    """Everything the Fee & Scholarship Calculator needs to draw itself. Every payable in here is produced
    by fee_schedule (the one engine); the frontend shows these numbers and never does fee maths itself."""
    data = load_data()
    programs = []
    for key, prog in data["programs"].items():
        slab_set = data["slab_sets"].get(prog["slab_set"], {})
        exams = [{"key": k, "label": _exam_label(k, prog)} for k in EXAM_LABELS if slab_set.get(k)]
        percents = sorted({0} | {s["percent"] for table in slab_set.values() for s in table})
        slabs = []
        for pct in percents:
            ranges, bounds = {}, {}
            for kind, table in slab_set.items():
                hit = [s for s in table if s["percent"] == pct]
                if hit:
                    ranges[kind] = _range_text(kind, hit[0])       # text to show
                    bounds[kind] = [hit[0]["min"], hit[0]["max"]]  # numbers to match a score against
            plan = fee_schedule(key, pct)
            y1 = plan["years"][0]
            slabs.append({"scholarship_percent": pct, "ranges": ranges, "bounds": bounds,
                          "annual_tuition": y1["annual_tuition"], "saving_per_year": y1["scholarship"],
                          "tuition_per_semester": y1["semesters"][0]["items"][0]["amount"],
                          "semesters": [{"semester": s["semester"], "total": s["total"],
                                         "items": [{"label": i["label"], "amount": i["amount"], "kind": i["kind"]}
                                                   for i in s["items"]]} for s in y1["semesters"]],
                          "first_year_total": y1["total"], "course_total": plan["course_total"],
                          "years": [{"year": y["year"], "annual_tuition": y["annual_tuition"], "total": y["total"]}
                                    for y in plan["years"]] if plan["course_total"] else []})
        programs.append({
            "id": key, "name": prog["name"], "level": prog.get("level", "ug"),
            "tuition_per_year": prog["tuition_per_year"],
            "yearly_increase": prog["yearly_increase"],
            "duration_years": prog.get("duration_years"),
            "minimum_percent": prog["min_percent"],
            "minimum_confirmed": prog.get("min_percent_confirmed", True),
            "eligibility": prog.get("eligibility_note", ""),
            "specialization_fee_applies": key in data.get("schedule", {}).get("specialization_fee_programs", []),
            "exams": exams, "slabs": slabs,
        })
    return {
        "status": "ok", "academic_year": data["academic_year"], "source": data["source"],
        "policy_id": data.get("policy_id"),
        "charges": {k: {kk: vv for kk, vv in v.items()} for k, v in data["charges"].items()},
        "schedule": {k: v for k, v in data.get("schedule", {}).items() if not k.startswith("_")},
        "hostel_per_year": hostel_per_year(), "hostel_labels": HOSTEL_LABELS,
        "hostel_status": data.get("hostel", {}).get("source", ""),
        "special_concessions": [c for c in data.get("special_concessions", []) if c.get("selectable", True)],
        "terms": data.get("terms", []),
        "programs": programs,
    }
