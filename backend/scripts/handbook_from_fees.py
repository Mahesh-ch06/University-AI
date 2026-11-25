"""Build the fee and scholarship pages of the handbook from the fee file.

The handbook used to carry hand-typed fee facts that had drifted away from the official fee card
(wrong PG fees and slabs, special concessions that do not exist). These pages are now GENERATED
from backend/app/sru_agent/fee_policy_2027_28.json, so the knowledge base, the chat and the calculator
all say the same thing. Run through `python scripts/export_fee_config.py`.
"""
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.sru_agent import fees  # noqa: E402

HANDBOOK_DIRS = [BACKEND / "data" / "handbook", BACKEND.parent / "data" / "handbook"]
FEE_PAGE = "08_admissions_fees_scholarships_and_eligibility.md"
FACTS_PAGE = "09_verified_sru_facts.md"
BEGIN, END = "<!-- FEES:BEGIN (generated from fee_policy_2027_28.json, do not edit by hand) -->", "<!-- FEES:END -->"
_EXAMS = (("state_board", "Intermediate / State Board %"), ("cbse", "CBSE / ICSE %"),
          ("jee_percentile", "JEE Main percentile"), ("eapcet_rank", "TG / AP EAPCET rank"),
          ("ib", "IB Diploma score (out of 45)"))


def _rng(kind, slab):
    return fees._range_text(kind, slab)


def _slab_rows(data, set_name):
    slab_set = data["slab_sets"][set_name]
    percents = sorted({s["percent"] for table in slab_set.values() for s in table})
    rows = []
    for pct in percents:
        cells = []
        for kind, _label in _EXAMS:
            hit = [s for s in slab_set.get(kind, []) if s["percent"] == pct]
            cells.append(_rng(kind, hit[0]) if hit else "not applicable")
        rows.append((pct, cells))
    return percents, rows


def _program_table(data, level):
    programs = [(k, p) for k, p in data["programs"].items() if p.get("level", "ug") == level]
    percents = sorted({s["percent"] for t in data["slab_sets"][level].values() for s in t})
    head = ("| Program | Standard fee per year | " + " | ".join(f"With {p}% scholarship" for p in percents)
            + " | Increase every year (same for all students) | Duration |")
    lines = [head, "|---|---:|" + "---:|" * len(percents) + "---:|---|"]
    for _key, p in programs:
        fee = p["tuition_per_year"]
        cells = " | ".join(fees.inr(round(fee * (100 - pct) / 100)) for pct in percents)
        years = f"{p['duration_years']} years" if p.get("duration_years") else "ask Admissions"
        lines.append(f"| **{p['name']}** | **{fees.inr(fee)}** | {cells} | {fees.inr(p['yearly_increase'])} | {years} |")
    return "\n".join(lines)


def _slab_table(data, level):
    _percents, rows = _slab_rows(data, level)
    used = [(i, label) for i, (kind, label) in enumerate(_EXAMS) if data["slab_sets"][level].get(kind)]
    if level == "pg":
        used = [(0, "Qualifying degree %")]
    lines = ["| Scholarship on tuition | " + " | ".join(label for _i, label in used) + " |",
             "|---:|" + "---|" * len(used)]
    for pct, cells in rows:
        lines.append(f"| **{pct}%** | " + " | ".join(cells[i] for i, _l in used) + " |")
    return "\n".join(lines)


def _concessions(data):
    lines = ["| No. | Category | Concession per year |", "|---:|---|---:|"]
    for i, c in enumerate(data["special_concessions"], 1):
        lines.append(f"| {i} | {c['label']} | {fees.inr(c['amount'])} |")
    return "\n".join(lines)


def _semester_table(data) -> str:
    lines = ["| Programme | Min. marks | Tuition / semester | Semester 1 | Semester 2 | Year 1 | Full course |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for key, p in data["programs"].items():
        r = fees.calculate_fee(key)
        minimum = f"{p['min_percent']:g}%" + ("" if p.get("min_percent_confirmed", True) else " (to be confirmed)")
        lines.append(f"| {p['name']} | {minimum} | {r['per_semester_after_scholarship']} | {r['sem1_total_payable']} | "
                     f"{r['sem2_total_payable']} | {r['first_year_total_payable']} | {r.get('full_course_total') or 'n/a'} |")
    return "\n".join(lines)


def _worked_example() -> str:
    r = fees.calculate_fee("btech_cse", percent=95)
    rows = ["| Component | Semester 1 | Semester 2 |", "|---|---:|---:|"]
    s1 = {i["key"]: i["amount"] for i in r["semester_1"]["items"]}
    s2 = {i["key"]: i["amount"] for i in r["semester_2"]["items"]}
    for i in r["semester_1"]["items"]:
        rows.append(f"| {i['item']} | {i['amount']} | {s2.get(i['key'], '—')} |")
    rows.append(f"| **Total** | **{r['sem1_total_payable']}** | **{r['sem2_total_payable']}** |")
    return ("\n".join(rows) + f"\n\nFirst year: **{r['first_year_total_payable']}**. The application fee "
            f"({r['application_fee']}) and optional charges (hostel, bus) are not included.")


def render_fee_page() -> str:
    d = fees.load_data()
    year, hostel, ch = d["academic_year"], fees.hostel_per_year(), d["charges"]
    elec = ch["electricity_deposit"]
    return f"""# SR University: Admissions, Fees & Scholarships ({year})

> **Source:** {d['source']} (official fee circular).
> **This page is generated** from `backend/app/sru_agent/fee_policy_2027_28.json`. Do not edit it by hand:
> change the fee file and run `python scripts/export_fee_config.py`.
> **Currency:** Indian Rupees (₹). Tuition is per year and is the only amount split equally between the two
> semesters; the other charges are placed in the semester the policy names (see section 3).

---

## 1. Undergraduate (UG) programs: tuition fee per year, {year}

The scholarship percentage is applied to the standard fee. The yearly increase is the same amount
for every student, with or without a scholarship.

{_program_table(d, 'ug')}

### Who gets which UG merit scholarship ({year})

Only ONE scholarship applies: the best one among the student's scores. Scholarships are not added together.
The standard fee (no scholarship) is for Intermediate 55 to 59.9% in B.Tech CSE and ECE, and 50 to 59.9% in other programs.

{_slab_table(d, 'ug')}

- An EAPCET rank above 20,000 does not earn a rank-based scholarship. The student's Intermediate, CBSE/ICSE, JEE or IB score may still earn one.
- {d.get('ib_overlap_note', '')}

---

## 2. Postgraduate (PG) programs: tuition fee per year, {year}

{_program_table(d, 'pg')}

### Who gets which PG merit scholarship ({year})

PG scholarships depend only on the percentage in the qualifying degree. The standard fee is for 50 to 59.9%.

{_slab_table(d, 'pg')}

---

## 3. Other fees and charges ({year})

| Fee | Amount | When it is paid |
|---|---:|---|
| Enrollment fee | {fees.inr(ch['enrollment_fee']['amount'])} | One-time, Semester 1 of Year 1 |
| Other fee | {fees.inr(ch['other_fee']['amount'])} | Every year, whole in Semester 1 (not split) |
| Exam fee (Year 1) | {fees.inr(ch['exam_fee']['amount'])} | Year 1 only, Semester 1 |
| Application form fee | {fees.inr(ch['application_fee']['amount'])} | Once, with the application; never part of a semester payable |
| Specialisation fee | {fees.inr(ch['specialization_fee']['amount'])} | Every year from Year 2 where a specialisation applies; never in Year 1 |
| University bus | {fees.inr(ch['bus']['amount'])} | Optional, per year; only if chosen |
| Ph.D. fee | {fees.inr(ch['phd_fee']['amount'])} | Per year |
| Electricity deposit, Non-AC hostel | {fees.inr(elec['non_ac'])} | One-time, first hostel semester |
| Electricity deposit, AC hostel | {fees.inr(elec['ac'])} | One-time, first hostel semester |

Merit scholarships reduce tuition only; they never apply to these charges. There is no separate "admission fee".

### Semester-wise fee, Year 1 (standard fee, day scholar)

Calculation order: base tuition → merit scholarship → yearly increase (from Year 2) → special concessions → tuition
split equally between the semesters → charges placed by the policy → semester payables → first-year and course totals.
The application fee is shown separately.

{_semester_table(d)}

**Worked example (from the fee circular): B.Tech CSE with 95% in Intermediate → 30% scholarship.**

{_worked_example()}

---

## 4. Special category concessions (all courses, per year, {year})

The fee circular lists exactly {len(d['special_concessions'])} categories. Each applies per academic year, subject to verification of credentials.

{_concessions(d)}

- State-level sports is **not** on the list. Only national-level (₹15,000) and international-level (₹50,000) sports achievers are.
- There is no general concession for "all girl students": the two girl-student categories are "Only girl child from Telangana" and "Girl Child from Outside Telangana".
- The Chancellor / Pro Chancellor Recommendation concession is granted only on that recommendation.

### Administrative terms printed on the fee circular
{chr(10).join('- ' + t for t in d['terms'])}

---

## 5. Hostel accommodation and dining (per year)

Hostel room fees are **not** printed on the {year} fee circular, so the Admissions Office confirms them. These amounts are
from the university's hostel fee table and include room and mess. The circular's only hostel charge is the one-time
electricity deposit.

| Room type | Fee per year | Electricity deposit (one-time) |
|---|---:|---:|
| 4-sharing, Non-AC | {fees.inr(hostel['non_ac_4'])} | {fees.inr(elec['non_ac'])} |
| 3-sharing, Non-AC | {fees.inr(hostel['non_ac_3'])} | {fees.inr(elec['non_ac'])} |
| 4-sharing, AC | {fees.inr(hostel['ac_4'])} | {fees.inr(elec['ac'])} |
| 3-sharing, AC | {fees.inr(hostel['ac_3'])} | {fees.inr(elec['ac'])} |

- **Dining**: 4 meals a day (breakfast, lunch, evening snacks, dinner), vegetarian and non-vegetarian.
- **Facilities**: 24/7 Wi-Fi, 4,000-seat dining hall, study areas, ambulance on campus, power backup.
- Hostel is optional and is added to a fee only when the student chooses it.

---

## 6. Rankings and accreditations

{chr(10).join(f"- **{r['body']}**: {r['claim']}." for r in d['rankings'])}

---

## 7. Official admissions contacts

- **Admissions Helpline**: 833 100 3030 (+91 833 100 3030)
- **Campus Visit Number**: 833 100 4040 (+91 833 100 4040)
- **Email**: `admissions@sru.edu.in` / `info@sru.edu.in`
- **Application Portal**: [https://apply.sru.edu.in](https://apply.sru.edu.in)
- **Official Website**: [https://www.sru.edu.in](https://www.sru.edu.in)
- **Campus Address**: SR University, Ananthasagar, Hasanparthy, Warangal, Telangana 506371.

---

## 8. Not on the fee circular (ask the Admissions Office)

The list of documents required at admission, the fee refund policy, payment dates and instalment
rules, and scholarship continuation rules are not printed on the {year} fee circular. The agent must
say these are confirmed by the Admissions Office rather than state them.
"""


def render_facts_sections() -> str:
    """Sections 3 and 4 of the verified-facts page."""
    d = fees.load_data()
    year = d["academic_year"]
    ug = [(k, p) for k, p in d["programs"].items() if p.get("level", "ug") == "ug"]
    pg = [(k, p) for k, p in d["programs"].items() if p.get("level") == "pg"]
    line = lambda p: (f"  - **{p['name']}**: **{fees.inr(p['tuition_per_year'])} per year** "
                      f"({fees.inr(p['tuition_per_year'] / 2)} per semester); increases by "
                      f"{fees.inr(p['yearly_increase'])} every year for every student.")
    ch = d["charges"]
    groups = {}
    for c in d["special_concessions"]:
        groups.setdefault(c["amount"], []).append(c["label"])
    conc = "\n".join(f"    - **{fees.inr(a)} per year**: " + "; ".join(labels) + "."
                     for a, labels in sorted(groups.items(), reverse=True))
    slabs = lambda level: "\n".join(
        f"    - **{pct}% scholarship**: " + " | ".join(
            f"{label}: {cells[i]}" for i, (kind, label) in enumerate(_EXAMS)
            if d["slab_sets"][level].get(kind)) for pct, cells in _slab_rows(d, level)[1])
    return f"""{BEGIN}
## 3. Tuition Fee Structure ({year})

- **[FACT-ID: FEE-001] [STATUS: VERIFIED] [SOURCE: official {year} fee circular, via fee_policy_2027_28.json]**
  - **Scoping rule**: when asked about a fee, state only the fee for the program or item asked about.
  - **Undergraduate programs (tuition per year)**:
{chr(10).join(line(p) for _k, p in ug)}
  - **Postgraduate programs (tuition per year)**:
{chr(10).join(line(p) for _k, p in pg)}
  - **Other fees**: enrollment fee {fees.inr(ch['enrollment_fee']['amount'])} (one-time, Semester 1 of Year 1); other fee {fees.inr(ch['other_fee']['amount'])} per year (Semester 1); exam fee {fees.inr(ch['exam_fee']['amount'])} (Year 1 only, Semester 1); application form fee {fees.inr(ch['application_fee']['amount'])} (paid separately); university bus {fees.inr(ch['bus']['amount'])} per year (optional); specialisation fee {fees.inr(ch['specialization_fee']['amount'])} per year from Year 2 where applicable; Ph.D. fee {fees.inr(ch['phd_fee']['amount'])} per year; hostel electricity deposit {fees.inr(ch['electricity_deposit']['non_ac'])} (Non-AC) / {fees.inr(ch['electricity_deposit']['ac'])} (AC), one-time.
  - Only tuition is split equally between the two semesters; merit scholarships reduce tuition only. Example: B.Tech CSE standard fee is Semester 1 {fees.calculate_fee('btech_cse')['sem1_total_payable']}, Semester 2 {fees.calculate_fee('btech_cse')['sem2_total_payable']}, Year 1 {fees.calculate_fee('btech_cse')['first_year_total_payable']}.
  - There is no separate admission fee on the {year} fee circular.

---

## 4. Merit Scholarships & Special Category Concessions ({year})

- **[FACT-ID: FEE-002] [STATUS: VERIFIED] [SOURCE: official {year} fee circular, via fee_policy_2027_28.json]**
  - Only the best single scholarship applies; scholarships are never added together. The scholarship is applied to the standard fee and is subject to marksheet verification.
  - **Undergraduate merit scholarship slabs**:
{slabs('ug')}
  - An EAPCET rank above 20,000 earns no rank-based scholarship (the student's board %, JEE or IB score may still earn one).
  - **Postgraduate merit scholarship slabs (percentage in the qualifying degree)**:
{chr(10).join(f"    - **{pct}% scholarship**: {cells[0]}" for pct, cells in _slab_rows(d, 'pg')[1])}
  - **{len(d['special_concessions'])} special category concessions (per year, all courses, subject to document verification)**:
{conc}
  - State-level sports is NOT on the list. There is no concession for "all girl students", North-East domicile, teachers' children, COVID-affected students or partner organisations: those are not on the fee circular.
{END}"""


def write_all() -> list:
    """Write both handbook copies. Returns the paths written."""
    written = []
    for directory in HANDBOOK_DIRS:
        if not directory.is_dir():
            continue
        (directory / FEE_PAGE).write_text(render_fee_page(), encoding="utf-8")
        written.append(directory / FEE_PAGE)
        facts = directory / FACTS_PAGE
        if facts.exists():
            text = facts.read_text(encoding="utf-8")
            facts.write_text(replace_facts_sections(text), encoding="utf-8")
            written.append(facts)
    return written


def replace_facts_sections(text: str) -> str:
    block = render_facts_sections()
    if "<!-- FEES:BEGIN" in text:
        return re.sub(r"<!-- FEES:BEGIN[^>]*-->.*?" + re.escape(END), lambda _m: block, text, flags=re.S)
    # first run: replace the old hand-typed sections 3 and 4
    start = text.index("## 3. Tuition Fee Structure")
    end = text.index("## 5. Campus Placements")
    return text[:start] + block + "\n\n---\n\n" + text[end:]
