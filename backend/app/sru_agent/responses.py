"""Static response templates and quick reply catalogues for SRU Buddy.

Decouples agent.py from large multi-line markdown texts.
"""
from __future__ import annotations
import hashlib
import re

_SMALL_TALK_CHIPS = ["B.Tech CSE fees", "Scholarship for my marks", "Placements at SRU", "Plan a campus visit"]

_PLACEMENT_ASSISTANCE_CHIPS = ["Top Recruiters & Packages", "Startup Incubator (SRiX)", "Placement Eligibility Rules", "Book a Campus Visit"]

_PLACEMENT_ASSISTANCE_RESPONSES = [
    """At **SR University**, we provide **100% placement assistance** to all eligible students.

While final job offers depend on student interview performance, SRU delivers full career preparation:

• 💼 **Top Recruiters**: 150+ companies visit campus (Microsoft, Amazon, ServiceNow) with 1,300+ offers.
• 📊 **Packages**: **6 to 6.5 LPA** average, with top offers reaching **₹51 LPA**, **₹49.30 LPA**, and **₹46.38 LPA**.
• 🚀 **Startup Incubator (SRiX)**: DST-supported on-campus incubator with ₹76+ Cr funding.

Would you like placement stats for a specific branch?""",

    """**SR University assures 100% placement assistance** and structured training for every eligible graduate.

Because final selection depends on student interview performance, placements are actively supported:

• 🎯 **150+ Hiring Partners**: 1,300+ campus offers from top MNCs (Amazon, Microsoft, ServiceNow) with coding prep.
• 📈 **Proven Outcomes**: **6 to 6.5 LPA** average salary, with highest offers of **₹51 LPA**, **₹49.30 LPA**, and **₹46.38 LPA**.
• 💡 **Innovation at SRiX**: Maker spaces and seed funding to launch your own startup.

Which engineering stream are you most interested in?""",

    """At **SR University**, we deliver **100% placement assistance** for all eligible students.

Hiring depends on student interview success, and SRU equips you with end-to-end readiness:

• 💼 **Corporate Drives**: 150+ marquee companies (Microsoft, Amazon, ServiceNow) with 1,300+ offers and internships.
• 📊 **Verified Salaries**: **6 to 6.5 LPA** average package, with top offers of **₹51 LPA**, **₹49.30 LPA**, and **₹46.38 LPA**.
• 🚀 **Startup Hub (SRiX)**: Access to our ₹76+ Cr DST-backed incubator.

Would you like to know more about internships or branch placements?""",

    """**SR University provides 100% placement assistance** and structured guidance to every eligible student.

Offers reflect individual student interview clearance, backed by our extensive recruitment ecosystem:

• 🎯 **Corporate Drives**: Direct recruitment by **150+ marquee companies** (Microsoft, Amazon, ServiceNow) with 1,300+ offers.
• 📈 **Verified Packages**: **6 to 6.5 LPA** average CTC, with peak packages of **₹51 LPA**, **₹49.30 LPA**, and **₹46.38 LPA**.
• 🛠️ **Startup Hub (SRiX)**: Incubation with prototyping labs and mentorship for founders.

Can I share details for a specific department or recruiter?""",
]

# ---------------------------------------------------------------------------------------------------------------
# Fee texts: GENERATED from the fee policy by the ONE fee engine (app/sru_agent/fees.py). No amount is typed here.
# ---------------------------------------------------------------------------------------------------------------
from . import fees as _fees


def _sem_table(key: str, **options) -> str:
    """Year-1 semester table: only tuition is split; other charges sit where the policy places them."""
    r = _fees.calculate_fee(key, **options)
    rows = ["| Component | Semester 1 | Semester 2 |", "| :--- | ---: | ---: |"]
    s1 = {i["key"]: i["amount"] for i in r["semester_1"]["items"]}
    s2 = {i["key"]: i["amount"] for i in r["semester_2"]["items"]}
    labels = {i["key"]: i["item"] for i in r["semester_1"]["items"] + r["semester_2"]["items"]}
    for k, label in labels.items():
        rows.append(f"| {label} | {s1.get(k, '—')} | {s2.get(k, '—')} |")
    rows.append(f"| **Semester payable** | **{r['sem1_total_payable']}** | **{r['sem2_total_payable']}** |")
    tail = f"**First year: {r['first_year_total_payable']}**"
    if r.get("full_course_total"):
        tail += f" · **Full course ({r['duration_years']} years): {r['full_course_total']}**"
    tail += f" · Application form {r['application_fee']} is paid separately."
    return "\n".join(rows) + "\n\n" + tail


def _slab_lines(key: str) -> str:
    p = _fees.load_data()["programs"][key]
    base = p["tuition_per_year"]
    ug = _fees.load_data()["slab_sets"][p["slab_set"]]
    names = {"state_board": "Inter", "cbse": "CBSE/ICSE", "jee_percentile": "JEE", "eapcet_rank": "EAPCET", "ib": "IB"}
    out = []
    for pct in (40, 30, 25, 20, 15, 10):
        parts = [f"{names[k]} {_fees._range_text(k, t[0])}" for k, t in
                 ((k, [x for x in table if x["percent"] == pct]) for k, table in ug.items()) if t]
        if parts:
            out.append(f"- **{pct}%**: {' / '.join(parts)} → tuition **{_fees.inr(base * (100 - pct) / 100)} / yr** "
                       f"(save {_fees.inr(base * pct / 100)})")
    return "\n".join(out)


def _programme_fee_text(key: str, heading: str, intro: str) -> str:
    p = _fees.load_data()["programs"][key]
    return (f"### {heading} — Fee Structure (2027–28)\n\n{intro}\n\n"
            f"Annual tuition **{_fees.inr(p['tuition_per_year'])}** (standard fee, minimum {p['min_percent']:g}% in "
            f"Intermediate), rising by {_fees.inr(p['yearly_increase'])} each year.\n\n"
            f"{_sem_table(key)}\n\n#### 🎓 Merit scholarships (tuition only)\n{_slab_lines(key)}\n\n"
            "Scholarships never reduce the other charges. Hostel and bus are optional and added only if you choose them.")


def _group_fee_text(heading: str, intro: str, rows: list[tuple[str, str]], extra: str = "") -> str:
    data = _fees.load_data()
    lines = ["| Programme | Annual tuition | Tuition / semester | Yearly increase |", "| :--- | ---: | ---: | ---: |"]
    for label, key in rows:
        p = data["programs"][key]
        lines.append(f"| **{label}** | **{_fees.inr(p['tuition_per_year'])}** | {_fees.inr(p['tuition_per_year'] / 2)} | "
                     f"+{_fees.inr(p['yearly_increase'])} |")
    ch = data["charges"]
    return (f"### {heading} — Fee Structure (2027–28)\n\n{intro}\n\n" + "\n".join(lines) + "\n\n"
            f"- **Semester 1 of Year 1** also has the enrollment fee {_fees.inr(ch['enrollment_fee']['amount'])}, "
            f"the other fee {_fees.inr(ch['other_fee']['amount'])} and the Year-1 exam fee "
            f"{_fees.inr(ch['exam_fee']['amount'])}; later years pay the other fee in Semester 1.\n"
            f"- Application form {_fees.inr(ch['application_fee']['amount'])}, paid separately.\n"
            + (f"- {extra}\n" if extra else "")
            + "- **Scholarships**: 10% to 40% of tuition on your qualifying marks (2027-28 fee circular).")


def _tuition_line(key: str) -> str:
    p = _fees.load_data()["programs"][key]
    return (f"- **Tuition**: {_fees.inr(p['tuition_per_year'])} / year ({_fees.inr(p['tuition_per_year'] / 2)} tuition "
            f"per semester) | Merit scholarships up to 40% available.")


def _concessions_text() -> str:
    items = [c for c in _fees.load_data()["special_concessions"]]
    rows = "\n".join(f"| **{c['label']}** | **{_fees.inr(c['amount'])} / year** |"
                     for c in sorted(items, key=lambda c: -int(c["amount"])))
    return ("### 🎖️ Special Category Fee Concessions (2027–28)\n\n"
            f"SR University offers annual special-category concessions in **{len(items)} categories**, deducted from "
            "tuition each academic year once your credentials are verified by the Admissions Office:\n\n"
            "| Category / Eligibility | Annual Concession |\n| :--- | :--- |\n" + rows + "\n\n"
            "Concessions apply per academic year, subject to verification of credentials. Submit certificates to the "
            "Admissions Office (833 100 3030 / info@sru.edu.in) during admission counselling.")


def _btech_tree_text() -> str:
    d = _fees.load_data()["programs"]
    def line(n, label, key):
        t = d[key]["tuition_per_year"]
        return f"• **{n}. {label}** — **{_fees.inr(t)} / yr** ({_fees.inr(t / 2)} tuition / sem)"
    return ("### 📘 B.Tech Fee Structure (2027–28)\n\nFor **B.Tech (Bachelor of Technology)**, SR University offers "
            "several engineering streams. Which branch would you like to view the detailed fee structure for?\n\n"
            + "\n".join([line(1, "B.Tech CSE & Allied** (AIML, Data Science, Cyber Security, Robotics, Quantum AI)**", "btech_cse"),
                         line(2, "B.Tech AI & Robotics", "btech_ai_robotics"),
                         line(3, "B.Tech ECE** (AIML, VLSI, Robotics & Automation)**", "btech_ece"),
                         line(4, "B.Tech Core** (Biotech, Civil, EEE, Mech, Food Tech, Engg Physics)**", "btech_mech")])
            + "\n\n*All B.Tech programmes offer **10% to 40% merit scholarships** on tuition, based on your 10+2 marks, "
              "JEE Main percentile or EAPCET rank. Minimum 55% for CSE and ECE, 50% for other branches.*\n\n"
              "👉 **Select a branch below to see the semester-wise breakdown:**")


def _hostel_fee_text() -> str:
    h = _fees.hostel_per_year()
    e = _fees.load_data()["charges"]["electricity_deposit"]
    return ("### 💰 SR University Residential Hostel Fees (2027–28)\n\nHostel accommodation is optional. Annual fees "
            "cover **room and all 4 daily meals** in the 4,000-seat mega dining hall:\n\n"
            "| Room Type | Annual Fee (Room + Mess) |\n| :--- | ---: |\n"
            + "\n".join(f"| **{_fees.HOSTEL_LABELS[k]}** | **{_fees.inr(v)} / year** |" for k, v in h.items())
            + f"\n\n• **Electricity deposit (one-time):** {_fees.inr(e['non_ac'])} Non-AC / {_fees.inr(e['ac'])} AC "
              "(2027-28 fee circular)\n\nHostel room fees are not on the 2027-28 fee circular, so the Admissions Office "
              "confirms them. Separate hostel blocks are provided for boys and girls on campus.")


def _combined_hostel_text() -> str:
    r = _fees.calculate_fee("btech_cse", hostel="ac_4")
    return ("### 🎓 B.Tech CSE Fee + Hostel (AC 4-Sharing), Year 1 (2027–28)\n\nStandard fee before any scholarship, "
            "semester by semester:\n\n" + _sem_table("btech_cse", hostel="ac_4") + "\n\n"
            f"Hostel room fees ({r['hostel']['per_year']} a year for AC 4-sharing) are not on the fee circular and are "
            "confirmed by the Admissions Office. Merit scholarships (up to 40%) reduce the tuition only.")


def _other_fees_text() -> str:
    ch = _fees.load_data()["charges"]
    e = ch["electricity_deposit"]
    i = _fees.inr
    return ("As per the official 2027-28 fee circular, the charges other than tuition are:\n\n"
            "| Fee Component | Amount | When |\n| :--- | ---: | :--- |\n"
            f"| **Enrollment Fee** | **{i(ch['enrollment_fee']['amount'])}** | One-time, Semester 1 of Year 1 |\n"
            f"| **Other Fee** | **{i(ch['other_fee']['amount'])}** | Every year, paid in Semester 1 (not split) |\n"
            f"| **Exam Fee (Year 1)** | **{i(ch['exam_fee']['amount'])}** | Year 1 only, Semester 1 |\n"
            f"| **Application Form** | **{i(ch['application_fee']['amount'])}** | Once, with the application (not in any semester) |\n"
            f"| **Specialisation Fee** | **{i(ch['specialization_fee']['amount'])}** | Per year from Year 2, where it applies |\n"
            f"| **PhD Fee** | **{i(ch['phd_fee']['amount'])}** | Per year (doctoral scholars) |\n\n"
            f"• **Optional:** university bus {i(ch['bus']['amount'])} a year; hostel by room type with a one-time "
            f"electricity deposit of {i(e['non_ac'])} (Non-AC) or {i(e['ac'])} (AC).\n\n"
            "Merit scholarships reduce tuition only, never these charges.")


_SPECIAL_CONCESSIONS_TEXT = _concessions_text()

_NEXT_GEN_TECH_TEXT = """### 🚀 Next-Gen Technology Programs at SR University

SR University has pioneered futuristic, multidisciplinary undergraduate engineering programs designed to prepare students for the next industrial revolution:

---

#### 1. 🤖 B.Tech in Artificial Intelligence & Robotics
- **Focus**: Autonomous mobile robotics, ROS (Robot Operating System), computer vision, sensor fusion, cyber-physical systems, and robotic manipulation.
- **Key Labs**: Advanced Robotics Arena, Makerspace, and Embedded Systems Lab.
@@AIR@@

---

#### 2. 🌾 B.Tech CSE — AI & Precision Agriculture
- **Focus**: Integrating machine learning, computer vision, IoT sensing, and drone analytics with modern agricultural science to create high-yield, climate-smart farming solutions.
- **Unique Advantage**: Jointly offered with SRU’s **ICAR-accredited School of Agriculture** with hands-on learning on experiential research farms.
@@CSE@@

---

#### 3. 🦾 B.Tech CSE — Robotics & Automation
- **Focus**: Industrial automation, PLC/SCADA programming, kinematics, machine kinematics, robotic arm control, and smart Industry 4.0 manufacturing.
- **Career Pathways**: Automation engineer, robotics software engineer, mechatronics specialist in automotive, aerospace, and defense sectors.
@@CSE@@

---

#### 4. ⚛️ B.Tech CSE — Quantum AI
- **Focus**: Quantum computing algorithms, Qiskit framework, quantum neural networks, quantum annealing, and post-quantum cryptography.
- **Cutting Edge**: Equips students for future high-performance computing, drug discovery simulations, and next-generation cybersecurity.
@@CSE@@

---

*Would you like to see the fee breakdown, eligibility cutoffs, or calculate your scholarship for any of these programs?*""".replace("@@AIR@@", _tuition_line("btech_ai_robotics")).replace("@@CSE@@", _tuition_line("btech_cse"))

_FEE_TREE_TEXT = """### 💰 SR University Fee Structure (2027–28)

Here is the **Program Category Directory**. Select an academic school below or tap a category to explore its branch fees and scholarship slabs:

• **📘 B.Tech Engineering** — CSE & Allied, AI & Robotics, ECE, Core Engineering
• **🏢 Management & Commerce** — BBA (General & Analytics), MBA (Finance, Marketing, HR, Analytics)
• **🌾 Agriculture (ICAR-Accredited)** — B.Sc. (Hons) Agriculture
• **💻 Computer Applications & IT** — BCA (Hons), B.Sc Computer Science, MCA
• **🎨 Design** — B.Des (Interior & Fashion Design)
• **🔬 Postgraduate & Sciences** — M.Tech, M.Sc (Computer Science / Agriculture)

👉 **Which program category would you like to see the fee structure for?** Tap an option below or type your branch:"""

_BTECH_TREE_TEXT = _btech_tree_text()

def get_btech_cse_fee_text(specialization: str | None = None, user_msg: str | None = None) -> str:
    clean_name = _fees.clean_program_name("btech_cse", specialization=specialization, user_text=user_msg)
    if user_msg and "allied" in user_msg.lower():
        title, intro = ("B.Tech CSE & Allied Streams", "Official fee schedule for **B.Tech Computer Science & "
                                                       "Engineering** and its specialised streams:")
    else:
        title, intro = clean_name, f"Official fee schedule for **{clean_name}**:"
    return _programme_fee_text("btech_cse", f"💻 {title}", intro)


_BTECH_CSE_FEE_TEXT = get_btech_cse_fee_text()

_BTECH_AI_ROBOTICS_FEE_TEXT = _programme_fee_text(
    "btech_ai_robotics", "🤖 B.Tech in Artificial Intelligence & Robotics",
    "Official fee schedule for the specialised **B.Tech in Artificial Intelligence & Robotics**:")

_BTECH_ECE_FEE_TEXT = _programme_fee_text(
    "btech_ece", "⚡ B.Tech Electronics & Communication (ECE)",
    "Official fee schedule for **B.Tech ECE** (specialisations in AIML, VLSI, and Robotics & Automation):")

_BTECH_CORE_FEE_TEXT = _programme_fee_text(
    "btech_mech", "⚙️ B.Tech Core Engineering",
    "Official fee schedule for **B.Tech Core Programs** (Mechanical, Civil, Electrical & Electronics, "
    "Biotechnology with AI, Food Technology, Engineering Physics, Applied Chemistry):")

_MANAGEMENT_FEE_TEXT = _group_fee_text(
    "🏢 Astra School of Business", "Official fee schedule for Management & Commerce programs:",
    [("BBA", "bba"), ("BBA (Finance, Operations, HR, Business Analytics, Marketing)", "bba_specialised"),
     ("B.Com", "bcom"), ("MBA", "mba"), ("MBA in Agri Business Management", "mba_agri")])

_AGRICULTURE_FEE_TEXT = _group_fee_text(
    "🌾 School of Agriculture", "Official fee schedule for the **ICAR-Accredited** agricultural programs:",
    [("B.Sc Agriculture", "bsc_agri"), ("B.Tech Food Technology", "btech_food_tech"),
     ("M.Sc (Agriculture disciplines)", "msc")],
    "**Accreditation**: first private university in the Telugu States with ICAR accreditation.")

_COMP_APP_FEE_TEXT = _group_fee_text(
    "💻 Computer Applications & IT", "Official fee schedule for Computer Applications:",
    [("BCA (Hons)", "bca"), ("B.Sc Computer Science (Hons)", "bsc_cs"), ("MCA", "mca"),
     ("M.Sc Computer Science", "msc")])

_DESIGN_FEE_TEXT = _group_fee_text(
    "🎨 School of Design", "Official fee schedule for Design programs:", [("B.Des (Design)", "bdes")])

_ALL_PROGRAMS_TEXT = """### 🎓 Programs Offered at SR University (2027–28)

SR University offers multidisciplinary UG, PG, and Ph.D. programs across **6 specialized schools**:

1. **School of Computer Science & Artificial Intelligence**: B.Tech CSE (Core, AIML, Data Science, Cyber Security, Quantum AI, Robotics), BCA, MCA, M.Tech, Ph.D.
2. **School of Engineering**: B.Tech in ECE, EEE, Mechanical, Civil & 2+2 International Engineering Program (IEP); M.Tech, Ph.D.
3. **Astra School of Business**: BBA (General & Specializations in Analytics, Finance, Marketing, HR), B.Com, MBA, Ph.D.
4. **School of Agriculture (ICAR-Accredited)**: B.Sc. (Hons) Agriculture, B.Tech Food Technology, M.Sc. Agriculture, Ph.D.
5. **School of Design**: B.Des in Interior Design & Fashion Design.
6. **School of Sciences & Humanities**: B.Tech Biotechnology (with AI), B.Sc, M.Sc, M.A. English.
7. **Doctoral Studies & Research (Ph.D.)**: Full-Time & Part-Time Ph.D. across all disciplines.

👉 **Which school or program would you like details on (eligibility, fees, or syllabus)?**"""

_HOSTEL_INFO_VARIANTS = [
    """### 🏢 Residential Living & Campus Hostels

SR University offers safe, vibrant residential living with separate facilities for Boys and Girls on campus:

• 🛏️ **Room Options**: AC and Non-AC 3-sharing and 4-sharing rooms with study desks, personal wardrobes, and Wi-Fi.
• 🍽️ **Mega Dining Hall**: 4,000-seat mess serving 4 wholesome meals daily (Breakfast, Lunch, Snacks, Dinner).
• 🛡️ **Safety & Wellness**: Round-the-clock security, biometric roll call, and an on-campus clinic with ambulance.

Would you like room fees, mess timings, or curfew rules?""",

    """### 🛏️ Hostel Room Options & Living Comfort

Residential living at SR University provides dedicated, fully-furnished spaces designed for comfortable studying:

• ❄️ **AC Comfort (3 & 4-Sharing)**: Fully air-conditioned rooms, ergonomic study desks, personal wardrobes, and power backup.
• 🌿 **Non-AC (3 & 4-Sharing)**: Spacious, well-ventilated rooms with dedicated study furniture, storage, and 24/7 campus fiber Wi-Fi.
• 💧 **Daily Essentials**: Commercial RO drinking water stations on every floor and scheduled solar hot water supply.

Would you like to know the annual room fees or check dining facilities?""" ,

    """### 🌿 Campus Amenities & Residential Community

Hostel life at SR University combines complete convenience, student wellness, and rigorous campus safety:

• 🍽️ **Dining & Nutrition**: 4,000-seat dining facility serving 4 hygienic meals daily with unlimited vegetarian and non-vegetarian menus.
• 🏃 **Sports & Fitness**: Modern indoor gymnasium with trainers, badminton, table tennis, and recreation lounges.
• 🔒 **Security & Discipline**: 100% CCTV surveillance, nightly biometric roll call, digital out-passes via Sruniv portal, and 24/7 medical support.

Can I help you with hostel fees, curfew guidelines, or mess schedules?""",
]

_HOSTEL_INFO_TEXT = _HOSTEL_INFO_VARIANTS[0]

def get_hostel_info_text(session_id: str | None = None, query: str = "") -> str:
    """Return a contextual or session-stable hostel information variant."""
    q = (query or "").lower()
    if any(k in q for k in ("room", "sharing", "ac", "non-ac", "bed", "furniture", "desk")):
        return _HOSTEL_INFO_VARIANTS[1]
    if any(k in q for k in ("amenit", "facilit", "gym", "water", "wifi", "medical", "clinic", "sports")):
        return _HOSTEL_INFO_VARIANTS[2]
    seed = (session_id or "default_hostel").encode("utf-8")
    idx = int(hashlib.md5(seed).hexdigest(), 16) % len(_HOSTEL_INFO_VARIANTS)
    return _HOSTEL_INFO_VARIANTS[idx]

_HOSTEL_MESS_TEXT = """### 🍽️ Dining & Mess Facilities at SR University

The university features a state-of-the-art **4,000-seat Mega Dining Hall** providing nutritious, wholesome meals in an ultra-hygienic environment:

• **4 Wholesome Meals Daily Schedule**:
  - 🍳 **Breakfast (7:30 AM – 8:30 AM)**: Nutritious South & North Indian breakfast items (idli, dosa, puri, upma, poha), boiled eggs/sprouts, tea, coffee, and fresh milk.
  - 🍛 **Lunch (12:00 PM – 2:00 PM)**: Complete balanced meal — steamed rice, roti/chapati, seasonal vegetable curries, dal/sambar, rasam, fresh curd/buttermilk, and papad.
  - ☕ **Evening Snacks (5:00 PM – 6:00 PM)**: Freshly made evening refreshments (samosas, cutlets, pakoras, or bajji) with hot tea and coffee.
  - 🍲 **Dinner (7:30 PM – 8:30 PM)**: Wholesome dinner with vegetarian dishes and non-vegetarian curries served on designated days, followed by desserts or seasonal fruits.
• **Dining Features**:
  - **Unlimited Self-Service**: Students enjoy unlimited servings during meal timings.
  - **Hygiene & Safety**: Steam-cooking boilers, commercial RO water for cooking and drinking, and regular health checkups of catering staff.
  - **Sick Diet**: Special light diet (khichdi, clear soup, boiled milk/eggs) provided upon resident doctor or hostel nurse recommendation.
  - **Festive Dinners**: Special grand feasts organized on major festivals and institutional celebrations.

*Would you like to know more about hostel room options, rules, or fees?*"""

_HOSTEL_CURFEW_RULES_TEXT = """### ⏰ Hostel Curfew & Timings

SR University maintains a secure residential campus with clear guidelines:

• ⏰ **In-Time**: first-year students by **8:30 PM**; senior students by **9:00 PM** on weekdays and **9:30 PM** at weekends, followed by a biometric roll call.
• 📱 **Digital Out-Pass**: Mandatory online pass via **Sruniv portal** with parent SMS confirmation.
• 📚 **Study Extensions**: Extended up to **11:00 PM** for hackathons and library projects with warden approval.

Would you like room options, mess details, or fee structure?"""

_HOSTEL_SAFETY_TEXT = """### 🛡️ Campus Safety, Security & Student Support

The safety and well-being of residential students are our highest priorities:

• **Round-the-Clock Security**: Gated campus with 24/7 uniformed security personnel, comprehensive CCTV surveillance, and biometric checkpoints.
• **Medical & Emergency Care**: On-campus Health Centre with resident nurses, visiting physicians, 24/7 stationed ambulance, and institutional tie-up with Aaditya Hospital.
• **Student Counsellors**: Dedicated male and female student counsellors for personal and emotional guidance.
• **Zero-Tolerance Discipline**: 100% ragging-free campus with active flying squads, anti-substance policy, and digital out-pass verification via Sruniv portal.

Would you like details on hostel living facilities, mess food, or room fees?"""

_HOSTEL_FEE_TEXT = _hostel_fee_text()

_HOSTEL_INFO_CHIPS = ["Mess Food & Timings", "Hostel Rules & Curfew", "Safety & Wardens", "Hostel Fee Breakdown"]
_HOSTEL_MESS_CHIPS = ["Hostel Facilities & Rooms", "Curfew & In-Time Rules", "Hostel Room Fees", "Safety & Security"]
_HOSTEL_CURFEW_CHIPS = ["Mess & Dining timings", "Hostel Facilities & Rooms", "Hostel Wardens & Contacts", "Hostel Fees"]
_HOSTEL_SAFETY_CHIPS = ["Hostel Facilities & Rooms", "Mess Food & Timings", "Curfew & Rules", "Hostel Fees"]
_HOSTEL_FEE_CHIPS = ["Hostel Facilities & Rooms", "Mess Food & Timings", "Curfew & Rules", "Calculate B.Tech Fee"]

_COMBINED_HOSTEL_FEE_TEXT = _combined_hostel_text()

_COMBINED_HOSTEL_FEE_CHIPS = ["Calculate scholarship for my marks", "Hostel room options", "Placement records for this course", "Hostel Rules & Curfew"]

_CAMPUS_CANTEEN_TEXT = """### ☕ Campus Cafeteria & Dining Options

SR University offers vibrant on-campus dining for day scholars and hostellers:

• 🍽️ **Central Cafeteria**: Hot meals, juices, and snacks in a spacious food court (8:30 AM – 6:00 PM).
• 🥪 **Campus Food Kiosks**: *Tasty Treat*, *Meet & Eat*, and *Bharat Foods* for quick bites (9:00 AM – 7:00 PM).
• 🍱 **Mega Dining Mess**: 4,000-seat hall serving 4 nutritious meals daily for residential students.

All outlets accept UPI. Would you like details on hostel fees or campus facilities?"""

_CAMPUS_CANTEEN_CHIPS = ["Hostel Mess & Dining", "Hostel Facilities & Rooms", "Campus Tour & Visit", "B.Tech CSE Fees"]

_ACADEMIC_EVALUATION_TEXT = """### 📊 Academic Regulations & Examination Evaluation at SR University (R22/R23)

SR University follows a comprehensive Credit-Based Semester System (CBSS) governed by the Academic Council:

#### 📝 Evaluation Structure
• **Continuous Internal Evaluation (CIE)**: Conducted during the semester through mid-term examinations, quizzes, assignments, and laboratory assessments.
• **End Semester Examination (ESE)**: Comprehensive university examinations conducted at the conclusion of each semester.

#### 🎯 10-Point Letter Grading Scale
| Letter Grade | Performance | Grade Point | Remarks |
| :--- | :--- | :--- | :--- |
| **O** | Outstanding | **10** | Exceptional performance |
| **A** | Excellent | **10** | Pass grade |
| **B** | Very Good | **8** | Pass grade |
| **C** | Good | **6** | Pass grade |
| **D** | Average | **4** | **Minimum Pass Grade (40% aggregate for UG)** |
| **F** | Fail | **0** | Backlog course; must appear in supplementary |
| **R** | Detained | **0** | Attendance < 75%; must re-register in Summer/Winter |

#### 📈 Percentage Conversion & Progression
• **Percentage Formula**: $\\text{Percentage of Marks} = 10 \\times \\text{CGPA}$
• **Attendance Requirement**: Minimum **75% aggregate** in each course (condonation board waiver up to 10–25% for verified medical emergencies).
• **Progression Criteria**: To promote to 2nd year: CGPA $\\ge 3.50$ (or 40% of 1st-year credits); to 3rd & 4th year: CGPA $\\ge 4.00$ (or 50% credits)."""

_ACADEMIC_EVALUATION_CHIPS = ["Attendance & Condonation Rules", "Honours & Minor Degrees", "B.Tech CSE Fees", "Placement Records"]

_LAB_FACILITIES_TEXT = """### 🔬 Research Labs & Infrastructure

SR University organizes high-tech laboratories across three specialized levels:

• 🏢 **11 Research Centers**: Dedicated centers for AI & Deep Learning (CAIDL), Embedded Systems, IoT, and EV Powertrains.
• 🚀 **SRiX Innovation Exchange**: 14+ maker spaces, IoT prototyping labs, and 3D design studios with ₹76+ Cr funding.
• 🖥️ **Departmental Labs**: Robotics arenas, VLSI suites, and an ICAR experimental farm.

Which department's labs would you like to explore?"""

_LAB_FACILITIES_CHIPS = ["AI & Computer Science Labs", "SRiX Startup Maker Spaces", "Robotics & IoT Labs", "B.Tech CSE Curriculum"]

_WHY_CHOOSE_SRU_VARIANTS = [
    """### 🏛️ Why Choose SR University

SR University is among the youngest private universities in Telangana to earn national and global rankings, with industry-ready learning and strong placements:

• 🌏 **QS Asia Rankings 2027**: 701–710 band (ahead of ~60% of ranked Asian institutions; 19th private in India).
• 🏆 **National Recognition**: NIRF 2025 91st in Engineering (Top 100 for 4 years) & THE World Rankings 2026 (801–1000).
• 🎯 **Proven Outcomes**: 95% placement rate with top package of ₹51 LPA; Tier-1 NBA & ICAR accreditations.
• 🚀 **Innovation at SRiX**: 171+ startups, 9,300+ publications, and 2,700+ patents on a 170-acre campus.

Would you like to explore our programs, fee structure, or campus facilities?""",

    """### 🚀 Young University, Proven Results

In a short span, SR University has built a record that older institutions take decades to match, backed by independent rankings and strong career outcomes:

• 🌟 **Rapid Rise**: Among the youngest private universities in Telangana with national and global ranks.
• 🌏 **Global Standings**: Debuted in QS Asia 2027 (701–710 band; 19th private in India) and 7th among private universities in India (THE).
• 📚 **Accreditations**: Tier-1 NBA accredited B.Tech programmes and ICAR-accredited School of Agriculture.
• 💼 **Placement Track Record**: 95% placement rate with ₹51 LPA highest offer; marquee recruiters include Microsoft and Amazon.

Which program or branch are you most curious about?""",

    """### 🔬 Ranked, Research-Driven, Career-Ready

SR University pairs national and global recognition with a strong research and innovation culture, where you learn by doing and graduate ready for industry:

• 📊 **Global & National Ranks**: QS Asia 2027 (701–710 band), THE World Rankings 2026 (801–1000), and NIRF 2025 91st in Engineering (Top 100 four years running).
• 💡 **Research Excellence**: Dedicated research centres, 9,300+ publications, 2,700+ patents filed, and SRiX incubator with 171+ startups.
• 🛠️ **Practical Learning**: Multidisciplinary hands-on curriculum, live projects, and international academic collaborations.
• 📈 **Verified Salaries**: 95% placement rate with milestone packages reaching ₹51 LPA.

Would you like to know more about research opportunities or admission eligibility?""",

    """### 🏆 Rankings You Can Trust

Choosing a university is easier when independent rankings back the decision. SR University is ranked nationally and globally, and continues to grow rapidly:

• 🌏 **International Accolades**: Debuted in QS Asia 2027 (701–710 band; ahead of 60% of ranked Asian institutions) and 19th among private universities in India.
• 🏅 **Top Tier in India**: 7th among private universities in India (THE) and 91st in Engineering (NIRF 2025).
• 🎓 **Quality Assured**: Tier-1 NBA accredited B.Tech and ICAR-accredited School of Agriculture.
• 💼 **Global Connections**: 80+ international university collaborations and a 95% placement rate.

Can I share details on merit scholarships or specific department offerings?""",

    """### 💼 Learn, Innovate, Get Placed

At SR University, classroom learning connects directly to industry, research, and global opportunities:

• 🎯 **Industry-Oriented Learning**: Live industry projects, internship exposure, and active mentoring by corporate experts.
• 🚀 **Startups & Patents**: ₹76+ Cr DST-funded SRiX incubator with 171+ ventures, 9,300+ publications, and 2,700+ patents.
• 📊 **Hiring Benchmarks**: 95% placement success rate with highest offer of ₹51 LPA (Microsoft, Amazon, and leading MNCs).
• 🏛️ **Ranked Excellence**: QS Asia 2027 (701–710 band) and NIRF 2025 91st in Engineering.

Would you like to see the placement highlights for a specific branch?""",

    """### 🌟 The Complete SRU Experience

SR University offers more than a degree: top rankings, practical learning, global exposure, and a vibrant residential campus:

• 🏛️ **Ranked Distinction**: Among the youngest private universities in Telangana with QS Asia 2027 (701–710) and NIRF 91st rank.
• 🌍 **Global Exposure**: 80+ international collaborations (2+2 degree pathways) and Tier-1 NBA & ICAR accreditations.
• 💼 **Placements & Innovation**: 95% placement rate, ₹51 LPA highest package, and 171+ startups incubated at SRiX.
• 🌳 **Vibrant Campus**: 170-acre green campus, modern research labs, student clubs, and merit scholarships.

Would you like to explore our admissions process or plan a campus visit?""",
]

_WHY_CHOOSE_SRU_CHIPS = ["B.Tech CSE Fee Structure", "Merit Scholarships & Slabs", "Top Placements & Recruiters", "Hostel Living & Facilities"]

def get_why_choose_sru_text(variant_id: int | None = None, session_id: str | None = None) -> str:
    """Return one of the 6 Why Choose SRU drafts dynamically based on variant_id or session."""
    if variant_id is not None and 1 <= variant_id <= len(_WHY_CHOOSE_SRU_VARIANTS):
        return _WHY_CHOOSE_SRU_VARIANTS[variant_id - 1]
    seed = (session_id or "default_why_sru").encode("utf-8")
    idx = int(hashlib.md5(seed).hexdigest(), 16) % len(_WHY_CHOOSE_SRU_VARIANTS)
    return _WHY_CHOOSE_SRU_VARIANTS[idx]

_OTHER_FEES_TEXT = _other_fees_text()

_OTHER_FEES_CHIPS = ["B.Tech CSE tuition", "Calculate my scholarship", "Hostel accommodation", "Plan a campus visit"]

_BRANCH_GUIDANCE_CHIPS = [
    "Software & Artificial Intelligence",
    "Hardware, VLSI & Robotics",
    "Core Engineering (Mech, Civil, EEE)",
    "Talk to an admission counsellor",
]

def get_branch_guidance_text(marks: int | float | None = None, session_id: str | None = None) -> str:
    """Natural branch guidance response explaining SRU engineering tracks and asking one follow-up question."""
    # The marks are acknowledged, not judged: eligibility depends on the branch and is checked separately.
    ack = (f"Thanks for sharing your marks (**{marks}**). Here is an overview so you can compare the branches by "
           f"what interests you." if marks else
           "Choosing an engineering branch is an important decision. Here is an overview so you can compare them "
           "by what interests you.")
    return f"""{ack}

Here is a quick overview of the key B.Tech engineering pathways available at SR University:

• 💻 **Computer Science & Engineering (CSE)**: For students who enjoy software programming, algorithms, AI & Machine Learning, Data Science and cybersecurity, with a strong coding focus.
• 🤖 **AI & Robotics**: For students who want to work at the intersection of intelligent software, automated mechanical systems, autonomous robots, and drone engineering.
• ⚡ **Electronics & Communication (ECE)**: For students interested in VLSI chip design, embedded systems, IoT devices, wireless communications, and hardware-software integration.
• ⚙️ **Core Engineering (Mechanical, EEE, Civil)**: Strong hands-on focus in smart manufacturing, electric vehicle (EV) powertrains, sustainable infrastructure, and renewable energy.

Which area interests you more — building software and apps, working with hardware and robotics, or core physical engineering?"""

_ADMISSION_GUARANTEE_TEXT = """### 📋 SR University Admission & Seat Allocation Policy

Admissions at SR University are **merit-based and subject to seat availability** during the active admission and counselling cycle. Seats are **never unconditionally guaranteed** or confirmed solely on a score, percentage, or rank.

Key facts regarding admission:
• **Eligibility vs. Allocation**: Having qualifying marks (such as 50%+ in 10+2 PCM for B.Tech, or 90%+ for scholarships) makes you fully eligible to apply and qualifies you for merit tuition fee waivers, but actual seat allotment depends on available branch vacancies during counselling.
• **No Informal Reservations**: SR University strictly follows transparent merit-based counselling and document verification; no confirmed seat guarantees are issued without the formal application process.
• **How to Apply**: To secure your preferred branch, register early through the official admissions portal at [apply.sru.edu.in](https://apply.sru.edu.in) or connect with the Admissions Office at **833 100 3030**.

Would you like to calculate your merit scholarship slab, or review the step-by-step application process?"""

_ADMISSION_GUARANTEE_CHIPS = ["Calculate scholarship", "How to apply", "Fee structure", "Contact Admissions"]

_FUTURE_YEAR_FEE_TEXT = """### 📅 Fees for later academic years

The official fee card covers the **2027-28** admission year only. Fees for admissions in later years are **not published yet**, so I can't give a verified figure for them.

• **What the 2027-28 fee card does list**: each programme's tuition for 2027-28 and a fixed **yearly tuition increase** for that programme, which applies to students admitted in 2027-28 as they move into later years of study. It is not a forecast of fees for later admission years.
• **Keeping a scholarship in later years**: the conditions are not stated on the 2027-28 fee card; the Admissions Office confirms them.
• **Questions about later years**: Admissions Office, **833 100 3030** or **info@sru.edu.in**.

Would you like the 2027-28 fees for a particular programme?"""

_FUTURE_YEAR_FEE_CHIPS = ["B.Tech CSE fees", "BBA fees", "MBA fees", "Contact Admissions"]

# ----------------------------------------------------------------------------
# Program Explorations & Branch Overviews
# ----------------------------------------------------------------------------

_BTECH_PROGRAMS_OVERVIEW_TEXT = """### 🚀 B.Tech Engineering Programs at SR University (2027–28)

SR University offers industry-aligned B.Tech programs recognized nationally for academic and research excellence (**#6 in India for Research Quality by Times Higher Education**, **NIRF 91st in Engineering**, Tier-1 NBA accredited):

1. 🤖 **B.Tech Artificial Intelligence & Robotics**: Advanced interdisciplinary degree covering Robot Operating System (ROS), Autonomous Systems, Computer Vision, and Industrial Automation.
2. 💻 **B.Tech Computer Science & Engineering (CSE) & Allied**: Flagship engineering program with cutting-edge specializations in AI & ML, Data Science, Cyber Security, Quantum AI, and Cloud Computing.
3. ⚡ **B.Tech Electronics & Communication Engineering (ECE)**: Core industry focus on VLSI Chip Design, Embedded Systems, IoT, and Next-Gen 5G/6G Wireless Networks.
4. 🏗️ **B.Tech Core Engineering (Mechanical, Civil, EEE)**: Smart industry 4.0 manufacturing, Electric Vehicle (EV) engineering, Smart Grids, and Sustainable Infrastructure.
5. 🌐 **2+2 International Engineering Program (IEP)**: Study 2 years at SRU and 2 years at premier partner universities in the USA/UK with global degree pathways.

Which engineering branch would you like to explore?"""

_BTECH_PROGRAMS_OVERVIEW_CHIPS = [
    "B.Tech AI & Robotics",
    "B.Tech CSE & Allied",
    "B.Tech ECE",
    "B.Tech Core Engineering",
]

_BTECH_AI_ROBOTICS_OVERVIEW_TEXT = """### 🤖 B.Tech in Artificial Intelligence & Robotics at SR University

The **B.Tech in Artificial Intelligence & Robotics** is a specialized, future-ready program designed to prepare engineers at the intersection of intelligent software and physical machines:

• 🛠️ **Project-Based Experiential Learning**: Hands-on curriculum covering Robot Operating System (ROS), Computer Vision, Autonomous Navigation, Deep Learning, and Industrial Robotics from Year 1.
• 🔬 **Cutting-Edge Labs & Innovation**: Specialized Robotics & AI Lab, NVIDIA AI computing workstations, Maker Spaces, and incubation support at **SRiX (SR Innovation Exchange)** hosting 171+ startups.
• 🏆 **National & Global Distinctions**: SR University ranks **#6 in India for Research Quality** by Times Higher Education (THE) and **NIRF 91st in Engineering** (Tier-1 NBA accredited).
• 💼 **Placements & Career Pathways**: High-demand roles as Robotics Engineer, AI/ML Specialist, and Autonomous Vehicle Engineer with leading tech innovators (top package ₹51 LPA, avg ₹6–6.5 LPA).

What would you like to explore about **B.Tech in AI & Robotics**?"""

_BTECH_AI_ROBOTICS_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "Laboratories & facilities",
    "Eligibility criteria",
    "Placements for this branch",
]

_BTECH_CSE_OVERVIEW_TEXT = """### 💻 B.Tech in Computer Science & Engineering (CSE) at SR University

The **B.Tech CSE** program is SR University's flagship engineering degree, designed for high-impact careers in software innovation:

• 🎯 **Specialization Tracks**: AI & Machine Learning, Data Science, Cyber Security, Quantum AI, and Cloud Computing.
• 💡 **Experiential Pedagogy**: Project-based learning from Year 1, competitive coding sprints, hackathons, and industry mentorship.
• 🏢 **High Placement Track Record**: Top recruiters including Microsoft, Amazon, Cisco, TCS, Cognizant, and Infosys (top package ₹51 LPA, avg ₹6–6.5 LPA).
• 🌐 **Global Opportunities**: Active IEEE and ACM student branches, collaborative faculty research, and 2+2 International Engineering Programs.

What would you like to explore about **B.Tech CSE**?"""

_BTECH_CSE_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "Laboratories & facilities",
    "Eligibility criteria",
    "Placements for this branch",
]

_BTECH_ECE_OVERVIEW_TEXT = """### ⚡ B.Tech in Electronics & Communication Engineering (ECE)

The **B.Tech ECE** program bridges advanced silicon engineering, intelligent hardware, and wireless communications:

• 🔌 **Specialized Focus**: VLSI Chip Design, Embedded Systems, Internet of Things (IoT), and 5G/6G Wireless Networks.
• 🔬 **Advanced Labs**: Cadence VLSI Lab, Embedded IoT Development Lab, and High-Frequency RF testing facilities.
• 💼 **Career Pathways**: Core hardware majors (Qualcomm, Intel, AMD, Texas Instruments) and top technology consulting firms.

What would you like to explore about **B.Tech ECE**?"""

_BTECH_ECE_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "Laboratories & facilities",
    "Eligibility criteria",
    "Placements for this branch",
]

_BTECH_CORE_OVERVIEW_TEXT = """### 🏗️ B.Tech Core Engineering (Mechanical, Civil & EEE)

SR University redefines core engineering by embedding AI, robotics, and smart industry 4.0 automation:

• ⚙️ **Mechanical Engineering**: Smart manufacturing, 3D printing, CAD/CAM/CAE, and electric vehicle (EV) engineering.
• 🏢 **Civil Engineering**: Smart infrastructure, structural design, GIS, and sustainable green construction.
• ⚡ **Electrical & Electronics (EEE)**: Smart grids, renewable energy systems, power electronics, and EV battery tech.

What would you like to explore about **Core Engineering**?"""

_BTECH_CORE_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "Laboratories & facilities",
    "Eligibility criteria",
    "Placements for this branch",
]

_PROGRAM_MANAGEMENT_OVERVIEW_TEXT = """### 📊 Astra School of Business (BBA & MBA)

Astra School of Business at SR University delivers modern management education driven by experiential case studies and business analytics:

• 🎓 **Programs**: BBA (General & Specializations in Analytics, Finance, Marketing, HR) and MBA (Dual Specializations).
• 📈 **Pedagogy**: Case-study methodology, industry simulations, Bloomberg terminal training, and leadership conclaves.
• 💼 **Placements**: Top corporate recruiters across consulting, banking, FMCG, and tech management.

What would you like to explore about **Management Programs**?"""

_PROGRAM_MANAGEMENT_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "MBA specializations",
    "Eligibility criteria",
    "Placements for MBA",
]

_PROGRAM_AGRICULTURE_OVERVIEW_TEXT = """### 🌾 School of Agriculture (B.Sc. Hons Agriculture)

The School of Agriculture at SR University is the **1st private university in Telangana & AP with prestigious ICAR accreditation**:

• 🚜 **Hands-on Farming**: 100+ acres of dedicated agricultural research farms, hi-tech greenhouses, and precision agriculture technology.
• 🌱 **Specializations**: Agronomy, Genetics & Plant Breeding, Soil Science, Horticulture, and Plant Pathology.
• 💼 **Career Pathways**: Agricultural Officer (AO), agri-business managers, research scientists, and agri-entrepreneurship via SRiX.

What would you like to explore about **B.Sc. (Hons) Agriculture**?"""

_PROGRAM_AGRICULTURE_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "ICAR Accreditation & Farm",
    "Eligibility criteria",
    "Career opportunities",
]

_PROGRAM_COMP_APP_OVERVIEW_TEXT = """### 🖥️ Computer Applications (BCA & MCA)

The Department of Computer Applications offers practical, career-oriented computing degrees:

• 💻 **Curriculum**: Full-stack web development, Python, mobile apps, database systems, cloud architectures, and machine learning.
• 🚀 **Career Outcomes**: Software developer, cloud engineer, systems analyst, and database administrator.

What would you like to explore about **BCA / MCA**?"""

_PROGRAM_COMP_APP_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "MCA specializations",
    "Eligibility criteria",
    "Placements",
]

_PROGRAM_DESIGN_OVERVIEW_TEXT = """### 🎨 School of Design (B.Des)

The School of Design provides an immersive, studio-based learning environment for creative innovators:

• 📐 **Programs**: B.Des in Interior Design and B.Des in Fashion Design.
• 🎨 **Facilities**: Digital design studios, material testing labs, prototyping workshops, and fashion runways.

What would you like to explore about **Design Programs**?"""

_PROGRAM_DESIGN_OVERVIEW_CHIPS = [
    "Fee & scholarships",
    "Design studios & labs",
    "Eligibility criteria",
    "Career paths",
]

# Generated from fee_policy_2027_28.json by eligibility.py (never hand-written thresholds).
from .eligibility import overview_text as _eligibility_overview

_ELIGIBILITY_TEXT = (_eligibility_overview() + "\n\nShare your programme and marks and I'll check your eligibility, "
                     "or I can show the fees or calculate your scholarship.")

_ELIGIBILITY_CHIPS = [
    "Calculate my scholarship",
    "Fee Structure 2027-28",
    "Hostel details",
    "How do I apply?",
]

_CSE_VS_AIML_TEXT = """### 💻 B.Tech CSE vs. B.Tech CSE (AI & ML) Comparison

• **B.Tech Computer Science & Engineering (Core)**:
  - **Focus & Foundations**: Builds comprehensive mastery across core computing fundamentals — Data Structures & Algorithms, Operating Systems, Database Management Systems, Compilers, Computer Networks, and Software Engineering.
  - **Career Scope**: Offers maximum versatility across Full-Stack Software Engineering, Cloud Architecture, Distributed Systems, and DevOps.

• **B.Tech CSE (Artificial Intelligence & Machine Learning)**:
  - **Specialized Deep-Dive**: Dedicated specialization immersing students in Neural Networks, Deep Learning, Natural Language Processing (NLP), Computer Vision, Robotics, and Predictive Analytics from foundational to elective semesters.
  - **Target Careers**: Tailored for high-demand AI roles: AI/ML Engineer, Data Scientist, Machine Learning Researcher, and Computer Vision Specialist.

• **At SR University**:
  - Both programs are backed by **Tier-1 NBA accreditation**, state-of-the-art computing labs, AI MakerSpace, and the DST-funded **SRiX Technology Business Incubator** (171+ startups).
  - Students in both streams enjoy **equal eligibility** for marquee campus placements with packages up to **₹51 LPA (Microsoft)**, **₹49.3 LPA (ServiceNow)**, and **₹46.38 LPA (Amazon)**."""

_CSE_VS_AIML_CHIPS = [
    "B.Tech CSE fees",
    "Calculate my scholarship",
    "Placement records",
    "Plan a campus visit",
]

_SCHOLARSHIP_CRITERIA_TEXT = """### 🎓 SR University Merit Scholarships (2027–28)

SR University offers generous **merit-based tuition fee waivers (10% to 40%)** to encourage academic excellence:

• **10+2 / Intermediate PCM Slabs**:
  - **≥ 95% / ≥ 950 marks**: **40% Tuition Fee Waiver**
  - **90% – 94.9% / 900–949 marks**: **30% Tuition Fee Waiver**
  - **80% – 89.9% / 800–899 marks**: **20% Tuition Fee Waiver**
  - **70% – 79.9% / 700–799 marks**: **10% Tuition Fee Waiver**

• **Entrance Exam Ranks (TG/AP EAPCET & JEE Main)**:
  - High rankers in EAPCET and JEE Main receive top merit slabs; the best applicable scholarship is granted automatically.
  - Only the highest eligible scholarship slab applies (no stacking).

• **Special Category Concessions (19 categories)**:
  - Additional concessions for siblings, defense personnel wards, single-parent/orphan students, NCC cadets, and sports achievers.

*Share your 10+2 marks or entrance rank to calculate your exact scholarship savings!*"""

_SCHOLARSHIP_CRITERIA_CHIPS = [
    "Calculate my scholarship",
    "B.Tech CSE fees",
    "Hostel fee details",
    "How do I apply?",
]





# ---------------------------------------------------------------- placements (v4.9.0)
# Short, student-style answers, one per aspect, each with a few wordings so a repeated question does not get a
# word-for-word repeat. Figures come from the placement card (card_service.PLACEMENT_EXCELLENCE_CARD).

def _pick(options: list[str], seed: str) -> str:
    return options[int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(options)]


def placement_aspect(message: str) -> str:
    low = (message or "").lower()
    if re.search(r"guarantee|assur|promise|100\s*%|100\s*percent|definitely\s+get|surely\s+get", low):
        return "guarantee"
    if re.search(r"intern", low):
        return "internships"
    if re.search(r"train|prepar|support\s+students|coaching|mock", low):
        return "training"
    if re.search(r"recruit|compan|employer|hiring|who\s+hires", low):
        return "recruiters"
    return "record"


_PLACEMENT_CHIPS = {
    "record": ["Top recruiters", "Internships", "Placement training"],
    "recruiters": ["Packages & record", "Internships", "Placement training"],
    "training": ["Packages & record", "Top recruiters", "Internships"],
    "internships": ["Packages & record", "Top recruiters", "Placement training"],
    "guarantee": ["Startup Incubator (SRiX)", "Top recruiters", "Packages & record"],
}


def placement_reply(message: str, seed: str) -> tuple[str, list[str], str]:
    """(answer, follow-up chips, aspect) for a placement question."""
    from app.services.card_service import PLACEMENT_EXCELLENCE_CARD as card

    stats = {s["label"]: s["value"] for s in card.get("stats", [])}
    offers = stats.get("Total Job Offers", "1,300+")
    interns = stats.get("Paid Internships", "3,500+")
    top = sorted(card.get("top_mnc_offers", []), key=lambda m: -int(m["offers"]))[:5]
    top_txt = ", ".join(f"{m['company']} ({m['offers']})" for m in top)
    aspect = placement_aspect(message)
    if aspect == "guarantee":
        text = _pick([
            f"SRU gives **100% placement assistance**: training by CSSP and the Career Guidance Cell, and campus drives "
            f"with 150+ recruiters ({offers} offers so far). The offer itself depends on your interviews and coding "
            f"skills, so no college can promise one. Average is **6 to 6.5 LPA**; top offers ₹51 LPA (Microsoft), "
            f"₹49.30 LPA (ServiceNow) and ₹46.38 LPA (Amazon). If you'd rather build a startup, SRiX (DST-backed) "
            f"incubates student ventures.",
            f"You get **100% placement assistance** at SRU (CSSP and Career Guidance Cell training, 150+ recruiters, "
            f"{offers} offers). Whether you get an offer depends on your own interviews and skills. Packages average "
            f"**6 to 6.5 LPA**, with ₹51 LPA (Microsoft), ₹49.30 LPA (ServiceNow) and ₹46.38 LPA (Amazon) at the top. "
            f"Students who want to start up get incubation at SRiX (DST-backed).",
        ], seed)
    elif aspect == "recruiters":
        text = _pick([
            f"Most offers came from **{top_txt}**. The highest packages were from Microsoft, ServiceNow, Amazon, "
            f"Salesforce and PayPal. 150+ companies recruit on campus.",
            f"150+ companies recruit at SRU. By number of offers the top ones are **{top_txt}**; for the biggest "
            f"packages, Microsoft, ServiceNow, Amazon, Salesforce and PayPal.",
        ], seed)
    elif aspect == "training":
        text = _pick([
            "Placement prep is run by **CSSP** and the Career Guidance Cell from 2nd year: coding practice, aptitude, "
            "mock interviews and soft skills, plus internships with industry mentors.",
            "From 2nd year you get structured prep through **CSSP**: coding and aptitude training, mock interviews "
            "and communication sessions, then internships and campus drives.",
        ], seed)
    elif aspect == "internships":
        text = _pick([
            f"Students have done **{interns} paid internships**, with stipends up to **₹1.25 lakh/month** "
            f"(Microsoft, Batch 2025).",
            f"Internships are big here: **{interns} paid internships** so far, the highest stipend being "
            f"**₹1.25 lakh/month** at Microsoft.",
        ], seed)
    else:
        text = _pick([
            f"**{offers} job offers**, average **6 to 6.5 LPA**. Highest: **₹51 LPA** (Microsoft), then ₹49.30 LPA "
            f"(ServiceNow) and ₹46.38 LPA (Amazon). Details are in the card below.",
            f"The average package is **6 to 6.5 LPA** across {offers} offers. Top offers: **₹51 LPA** at Microsoft, "
            f"₹49.30 LPA at ServiceNow, ₹46.38 LPA at Amazon.",
            f"Quick numbers: {offers} offers, **6 to 6.5 LPA** average, and a highest of **₹51 LPA** (Microsoft). "
            f"ServiceNow (₹49.30 LPA) and Amazon (₹46.38 LPA) follow.",
        ], seed)
    return text, list(_PLACEMENT_CHIPS[aspect]), aspect


def special_concessions_lead(data: dict, program: str | None = None) -> str:
    """One line above the concessions table card."""
    n = len(data.get("all_categories", []))
    target = f"your **{_program_short(program)}** fee" if program else "your fee"
    return (f"SRU offers **{n} special concessions** on tuition every year, with valid proof. "
            f"Pick the one that applies to you and I'll show what it could mean for {target} "
            f"(each is approved only after the proof is verified).")


def _program_short(program: str | None) -> str:
    from . import fees as _fees
    try:
        return _fees.short_name(program) if program else ""
    except Exception:
        return ""


def special_concessions_text(data: dict) -> str:
    """The special-category concessions, grouped by amount (from fees.special_concessions())."""
    groups: dict[str, list[str]] = {}
    for c in data.get("all_categories", []):
        label = c["category"]
        if len(label) > 1 and label[1].islower():
            label = label[0].lower() + label[1:]          # "Students who..." -> "students who...", "NCC" stays
        groups.setdefault(c["per_year"], []).append(label)
    order = sorted(groups, key=lambda a: -int(re.sub(r"[^0-9]", "", a) or 0))
    lines = [f"SRU has **{len(data.get('all_categories', []))} special concessions** on tuition, per year, "
             f"with valid certificates:", ""]
    for amount in order:
        lines.append(f"• **{amount}**: " + "; ".join(groups[amount]))
    lines += ["", "Tell me which one applies to you and I'll add it to your fee."]
    return "\n".join(lines)


# ---------------------------------------------------------------- answers built from verified facts
# Used for "why SRU", "about SRU", rankings, accreditation, research, international and similar questions
# when no language model is available. The content always comes from the facts retrieved for the
# question (fact_service.retrieve); only the framing line varies. Nothing here states a figure itself.

_FACT_ASPECT_LABELS = {
    "rankings": "Rankings", "accreditation": "Accreditation", "placements": "Placement record",
    "research": "Research & patents", "innovation": "Startups at SRiX", "international": "Study abroad options",
    "campus": "Campus life", "academics": "How teaching works", "scholarships": "💰 Fee & Scholarship Info",
    "about": "About SRU",
}

_FACT_INTROS = {
    "broad": ["Here's what makes SRU stand out:", "A few reasons students choose SRU:",
              "SRU's strengths at a glance:"],
    "more": ["A few more things worth knowing about SRU:", "Beyond that, SRU also offers:",
             "Here's more that sets SRU apart:"],
    "recap": ["Here's a quick recap:", "To sum up what I shared:", "In short:"],
    "challenge": ["SRU is a strong choice, and the record backs it up:",
                  "Here's what SRU has achieved, so you can judge for yourself:",
                  "SRU has earned its place among India's fast-rising universities:"],
    "rankings": ["SRU holds strong national and global ranks:", "Here's where SRU stands in the rankings:",
                 "SRU's rankings, in short:"],
    "accreditation": ["SRU's programmes are fully recognised:", "Here's how SRU is accredited:"],
    "research": ["Research is a big part of SRU:", "SRU's research record:"],
    "innovation": ["SRU backs student startups in a big way:", "Innovation at SRU:"],
    "international": ["SRU gives you plenty of global exposure:", "Here's SRU's international side:"],
    "campus": ["Life at SRU in a nutshell:", "Here's what campus life looks like:"],
    "academics": ["Learning at SRU is hands-on:", "How SRU prepares you for industry:"],
    "about": ["Here's a quick introduction to SRU:", "SRU in a few lines:"],
}

_FACT_CLOSES = ["Want details on any of these?", "Which of these matters most to you?",
                "Shall I go deeper into any one?"]

_FACT_CLOSES_NARROW = ["Anything else you'd like to know about SRU?", "What would you like to check next?"]

_CHALLENGE = re.compile(
    r"\b(bad|worst|poor|fake|scam|fraud|cheat\w*|waste|worth|better than|vs\.?|versus|compare|compared|good (?:college|university)|"
    r"reputation|why not|is it good|is sru good)\b", re.IGNORECASE)


def facts_reply(message: str, facts: list, seed: str, aspects: list[str] | None = None,
                repeat: bool = False, recap: bool = False) -> tuple[str, list[str]]:
    """A short answer built from the retrieved facts: one framing line, 2–4 bullets, one question.

    repeat: the student asked again and these facts are new ("a few more things"); recap: everything
    relevant was already said, so it is framed as a recap. Returns (text, chips). With no facts it says
    the information could not be verified.
    """
    aspects = aspects or []
    if not facts:
        return ("I couldn't find verified information on that. The Admissions Office (833 100 3030, "
                "info@sru.edu.in) can confirm it for you.", ["📞 Admissions Office"])
    if recap and not aspects:
        key = "recap"
    elif repeat:
        key = "more"
    elif _CHALLENGE.search(message or ""):
        key = "challenge"
    elif aspects and aspects[0] in _FACT_INTROS and (len(aspects) == 1 or recap):
        key = aspects[0]
    else:
        key = "broad"
    intro = _pick(_FACT_INTROS[key], seed)
    bullets = []
    for f in facts[:4]:
        short = ((f.metadata or {}).get("short") or "").strip()
        if short:
            bullets.append(f"• {short}")
    closes = _FACT_CLOSES if key in ("broad", "more", "recap", "challenge") else _FACT_CLOSES_NARROW
    text = intro + "\n\n" + "\n".join(bullets) + "\n\n" + _pick(closes, seed + "close")
    covered = {(f.metadata or {}).get("aspect") for f in facts} | set(aspects)
    order = ["placements", "rankings", "scholarships", "campus", "research", "international"]
    chips = [_FACT_ASPECT_LABELS[a] for a in order if a not in covered][:3]
    return text, chips
