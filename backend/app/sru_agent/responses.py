"""Static response templates and quick reply catalogues for SRU Buddy.

Decouples agent.py from large multi-line markdown texts.
"""
from __future__ import annotations
import hashlib

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

_SPECIAL_CONCESSIONS_TEXT = """### 🎖️ Special Category Fee Concessions (2027–28)

At SR University, special category tuition fee concessions are offered annually to eligible students across 19 categories. These concessions are applied directly to your annual tuition fee upon verification of valid certificates by the Admissions Office:

| Category / Eligibility | Annual Concession |
| :--- | :--- |
| **Students who have lost both parents (Orphans)** | **₹50,000 / year** |
| **International-level sports achievers** | **₹50,000 / year** |
| **Children of regular SR University employees** | **₹50,000 / year** |
| **Students with 50% or above disability (Differently Abled)** | **₹20,000 / year** |
| **Children of Defence personnel, CRPF personnel & Martyrs** | **₹15,000 / year** |
| **Children of State Police personnel** | **₹15,000 / year** |
| **Only Girl Child from Telangana** | **₹15,000 / year** |
| **Girl students from states other than Telangana** | **₹15,000 / year** |
| **Students with a single living parent / Divorced parents** | **₹15,000 / year** |
| **Sibling enrolled at SR University (concurrent 2027–28)** | **₹15,000 / year** |
| **SRU Alumni, their children and siblings** | **₹15,000 / year** |
| **Students of SR Junior College** | **₹15,000 / year** |
| **NCC 'C' Certificate holders** | **₹15,000 / year** |
| **National-level sports achievers** | **₹15,000 / year** |
| **Children of Padma / Gallantry awardees & J&K migrant families** | **₹15,000 / year** |
| **Non-Local students (outside Telangana & Andhra Pradesh)** | **₹15,000 / year** |
| **Students from Andhra Pradesh** | **₹15,000 / year** |
| **Lateral Entry students** | **₹15,000 / year** |
| **International students** | **₹15,000 / year** |

> [!NOTE]
> - Concessions are applicable per academic year on tuition fees.
> - Required certificates and documentation must be submitted directly to the Admissions Office (833 100 3030 / info@sru.edu.in) during admission counselling."""

_NEXT_GEN_TECH_TEXT = """### 🚀 Next-Gen Technology Programs at SR University

SR University has pioneered futuristic, multidisciplinary undergraduate engineering programs designed to prepare students for the next industrial revolution:

---

#### 1. 🤖 B.Tech in Artificial Intelligence & Robotics
- **Focus**: Autonomous mobile robotics, ROS (Robot Operating System), computer vision, sensor fusion, cyber-physical systems, and robotic manipulation.
- **Key Labs**: Advanced Robotics Arena, Makerspace, and Embedded Systems Lab.
- **Tuition**: ₹4,00,000 / year (₹2,00,000 / semester) | Merit scholarships up to 40% available.

---

#### 2. 🌾 B.Tech CSE — AI & Precision Agriculture
- **Focus**: Integrating machine learning, computer vision, IoT sensing, and drone analytics with modern agricultural science to create high-yield, climate-smart farming solutions.
- **Unique Advantage**: Jointly offered with SRU’s **ICAR-accredited School of Agriculture** with hands-on learning on experiential research farms.
- **Tuition**: ₹3,40,000 / year (₹1,70,000 / semester) | Merit scholarships up to 40% available.

---

#### 3. 🦾 B.Tech CSE — Robotics & Automation
- **Focus**: Industrial automation, PLC/SCADA programming, kinematics, machine kinematics, robotic arm control, and smart Industry 4.0 manufacturing.
- **Career Pathways**: Automation engineer, robotics software engineer, mechatronics specialist in automotive, aerospace, and defense sectors.
- **Tuition**: ₹3,40,000 / year (₹1,70,000 / semester) | Merit scholarships up to 40% available.

---

#### 4. ⚛️ B.Tech CSE — Quantum AI
- **Focus**: Quantum computing algorithms, Qiskit framework, quantum neural networks, quantum annealing, and post-quantum cryptography.
- **Cutting Edge**: Equips students for future high-performance computing, drug discovery simulations, and next-generation cybersecurity.
- **Tuition**: ₹3,40,000 / year (₹1,70,000 / semester) | Merit scholarships up to 40% available.

---

> [!TIP]
> All programs feature practical prototyping at **SRiX (DST-supported Technology Business Incubator)** with ₹76+ Cr in funding and 171+ startups.

*Would you like to see the fee breakdown, eligibility cutoffs, or calculate your scholarship for any of these programs?*"""

_FEE_TREE_TEXT = """### 💰 SR University Fee Structure (2027–28)

Here is the **Program Category Directory**. Select an academic school below or tap a category to explore its branch fees and scholarship slabs:

• **📘 B.Tech Engineering** — CSE & Allied, AI & Robotics, ECE, Core Engineering
• **🏢 Management & Commerce** — BBA (General & Analytics), MBA (Finance, Marketing, HR, Analytics)
• **🌾 Agriculture (ICAR-Accredited)** — B.Sc. (Hons) Agriculture
• **💻 Computer Applications & IT** — BCA (Hons), B.Sc Computer Science, MCA
• **🎨 Design** — B.Des (Interior & Fashion Design)
• **🔬 Postgraduate & Sciences** — M.Tech, M.Sc (Computer Science / Agriculture)

👉 **Which program category would you like to see the fee structure for?** Tap an option below or type your branch:"""

_BTECH_TREE_TEXT = """### 📘 B.Tech Fee Structure (2027–28)

For **B.Tech (Bachelor of Technology)**, SR University offers several engineering streams. Which branch would you like to view the detailed fee structure for?

• **1. B.Tech CSE & Allied** (AIML, Data Science, Cyber, Quantum AI) — **₹3,40,000 / yr** (₹1,70,000 / sem)
• **2. B.Tech AI & Robotics** — **₹4,00,000 / yr** (₹2,00,000 / sem)
• **3. B.Tech ECE** (VLSI & Embedded) — **₹2,70,000 / yr** (₹1,35,000 / sem)
• **4. B.Tech Core** (Biotech, Civil, EEE, Mech, Food Tech) — **₹2,00,000 / yr** (₹1,00,000 / sem)

*All B.Tech programs offer **10% to 40% Merit Scholarships** based on your 10+2 marks or EAPCET rank.*

👉 **Select a branch below to see the complete semester breakdown:**"""

def get_btech_cse_fee_text(specialization: str | None = None, user_msg: str | None = None) -> str:
    from app.sru_agent import fees
    clean_name = fees.clean_program_name("btech_cse", specialization=specialization, user_text=user_msg)
    if user_msg and "allied" in user_msg.lower():
        title = "B.Tech CSE & Allied Streams"
        intro = "Official fee schedule for **B.Tech Computer Science & Engineering** and its specialized streams:"
    else:
        title = clean_name
        intro = f"Official fee schedule for **{clean_name}**:"

    return f"""### 💻 {title} — Fee Structure (2027–28)

{intro}

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹1,70,000** | **₹3,40,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | ₹15,000 other + ₹5,000 exam |
| **Semester 1 Total (Day-Scholar)** | **₹1,85,000** | — | Includes enrollment + exam/other |
| **Regular Semester Total** | **₹1,80,000** | **₹3,60,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Inter ≥ 98% / CBSE ≥ 95% / EAPCET 1–2000 → **₹2,04,000 / yr** (Save ₹1,36,000)
- **30% Waiver**: Inter 92–97.9% / CBSE 90–94.9% / EAPCET 2001–8000 → **₹2,38,000 / yr** (Save ₹1,02,000)
- **25% Waiver**: Inter 80–91.9% / CBSE 80–89.9% / EAPCET 8001–20000 → **₹2,55,000 / yr** (Save ₹85,000)
- **20% Waiver**: Inter 70–79.9% → **₹2,72,000 / yr** (Save ₹68,000)
- **10%–15% Waiver**: Inter 60–69.9% → **₹2,89,000 – ₹3,06,000 / yr**

> [!NOTE]
> - Annual tuition escalation: ₹9,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year (includes 4 meals daily, AC/Non-AC options, Wi-Fi & laundry)."""


_BTECH_CSE_FEE_TEXT = get_btech_cse_fee_text()

_BTECH_AI_ROBOTICS_FEE_TEXT = """### 🤖 B.Tech in Artificial Intelligence & Robotics — Fee Structure (2027–28)

Official fee schedule for the specialized **B.Tech in Artificial Intelligence & Robotics**:

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹2,00,000** | **₹4,00,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | Per semester breakdown |
| **Semester 1 Total (Day-Scholar)** | **₹2,15,000** | — | With enrollment fee |
| **Regular Semester Total** | **₹2,10,000** | **₹4,20,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Net Tuition **₹2,40,000 / yr** (Save ₹1,60,000/yr)
- **30% Waiver**: Net Tuition **₹2,80,000 / yr** (Save ₹1,20,000/yr)
- **25% Waiver**: Net Tuition **₹3,00,000 / yr** (Save ₹1,00,000/yr)
- **20% Waiver**: Net Tuition **₹3,20,000 / yr** (Save ₹80,000/yr)

> [!NOTE]
> - Annual tuition escalation: ₹12,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year."""

_BTECH_ECE_FEE_TEXT = """### ⚡ B.Tech Electronics & Communication (ECE) — Fee Structure (2027–28)

Official fee schedule for **B.Tech ECE** (Specializations in VLSI, Embedded Systems, and Robotics):

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹1,35,000** | **₹2,70,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | Per semester breakdown |
| **Semester 1 Total (Day-Scholar)** | **₹1,50,000** | — | With enrollment fee |
| **Regular Semester Total** | **₹1,45,000** | **₹2,90,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Net Tuition **₹1,62,000 / yr** (Save ₹1,08,000/yr)
- **30% Waiver**: Net Tuition **₹1,89,000 / yr** (Save ₹81,000/yr)
- **25% Waiver**: Net Tuition **₹2,02,500 / yr** (Save ₹67,500/yr)
- **20% Waiver**: Net Tuition **₹2,16,000 / yr** (Save ₹54,000/yr)

> [!NOTE]
> - Annual tuition escalation: ₹8,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year."""

_BTECH_CORE_FEE_TEXT = """### ⚙️ B.Tech Core Engineering — Fee Structure (2027–28)

Official fee schedule for **B.Tech Core Programs** (Mechanical, Civil, Electrical & Electronics, Biotechnology, Food Technology):

| Component | Semester Fee | Annual Total | Notes |
| :--- | :--- | :--- | :--- |
| **Base Tuition Fee** | **₹1,00,000** | **₹2,00,000** | Payable per semester |
| **One-Time Enrollment Fee** | **₹5,000** | — | Semester 1 only |
| **Examination & Other Fees** | **₹10,000** | **₹20,000** | Per semester breakdown |
| **Semester 1 Total (Day-Scholar)** | **₹1,15,000** | — | With enrollment fee |
| **Regular Semester Total** | **₹1,10,000** | **₹2,20,000** | Semesters 2 through 8 |

#### 🎓 Merit Scholarships (Tuition Waiver):
- **40% Waiver**: Net Tuition **₹1,20,000 / yr** (Save ₹80,000/yr)
- **30% Waiver**: Net Tuition **₹1,40,000 / yr** (Save ₹60,000/yr)
- **25% Waiver**: Net Tuition **₹1,50,000 / yr** (Save ₹50,000/yr)
- **20% Waiver**: Net Tuition **₹1,60,000 / yr** (Save ₹40,000/yr)

> [!NOTE]
> - Annual tuition escalation: ₹6,000/year for subsequent academic years.
> - Hostel is optional: ₹1,15,000 to ₹1,35,000/year."""

_MANAGEMENT_FEE_TEXT = """### 🏢 Astra School of Business — Fee Structure (2027–28)

Official fee schedule for Management & Commerce programs:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **BBA (General)** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **BBA (Business Analytics / Specialized)** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |
| **B.Com** | **₹1,00,000** | ₹50,000 | +₹3,000 / yr |
| **MBA (Finance, Marketing, HR, Analytics)** | **₹3,00,000** | ₹1,50,000 | +₹9,000 / yr |
| **MBA in Agri-Business Management** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |

- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers based on qualifying exam scores; eligible PG students receive an additional 10% scholarship."""

_AGRICULTURE_FEE_TEXT = """### 🌾 School of Agriculture — Fee Structure (2027–28)

Official fee schedule for the **ICAR-Accredited** Agricultural programs:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **B.Sc. (Hons) Agriculture** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |
| **B.Tech Food Technology** | **₹2,00,000** | ₹1,00,000 | +₹6,000 / yr |
| **M.Sc Agriculture (All Disciplines)** | **₹1,00,000** | ₹50,000 | +₹3,000 / yr |

- **Accreditation**: First private university in the Telugu States with ICAR accreditation.
- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers based on 10+2 BiPC marks or EAPCET rank."""

_COMP_APP_FEE_TEXT = """### 💻 Computer Applications & IT — Fee Structure (2027–28)

Official fee schedule for Computer Applications:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **BCA (Hons)** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **B.Sc Computer Science (Hons)** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **MCA** | **₹1,50,000** | ₹75,000 | +₹4,000 / yr |
| **M.Sc Computer Science** | **₹1,00,000** | ₹50,000 | +₹3,000 / yr |

- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers."""

_DESIGN_FEE_TEXT = """### 🎨 School of Design — Fee Structure (2027–28)

Official fee schedule for Design programs:

| Program | Annual Tuition | Semester Fee | Annual Escalation |
| :--- | :--- | :--- | :--- |
| **B.Des Interior Design** | **₹2,10,000** | ₹1,05,000 | +₹6,000 / yr |
| **B.Des Fashion Design** | **₹2,10,000** | ₹1,05,000 | +₹6,000 / yr |

- **One-time enrollment**: ₹5,000 (Sem 1 only). Exam & other fees: ₹20,000/yr.
- **Scholarships**: 10% to 40% merit waivers."""

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

• ⏰ **In-Time Curfew**: **9:00 PM** weekdays and **9:30 PM** weekends, followed by nightly biometric roll call.
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

_HOSTEL_FEE_TEXT = """### 💰 SR University Residential Hostel Fee Structure (2027–28)

Hostel accommodation is optional. Annual fees cover both **room accommodation and all 4 daily meals** in the 4,000-seat mega dining hall:

| Room Type | Sharing | Annual Fee (Room + Mess) | Notes |
| :--- | :--- | :--- | :--- |
| **Non-AC** | **4-Sharing** | **₹1,15,000 / year** | 4 meals/day, Wi-Fi, study desk, power backup |
| **Non-AC** | **3-Sharing** | **₹1,25,000 / year** | 4 meals/day, Wi-Fi, study desk, power backup |
| **Air-Conditioned (AC)** | **4-Sharing** | **₹1,25,000 / year** | AC room, 4 meals/day, Wi-Fi, study desk |
| **Air-Conditioned (AC)** | **3-Sharing** | **₹1,35,000 / year** | AC room, 4 meals/day, Wi-Fi, study desk |

#### 📋 Additional Deposits & Charges:
• **Caution Deposit**: **₹5,000** (one-time, refundable at end of degree)
• **Laundry Services**: **₹5,000 / year** (in-house mechanized laundry)
• **Electricity Deposit (AC Rooms)**: **₹10,000 / year** (Non-AC: **₹5,000 / year**)

> [!NOTE]
> - Hostel fees are billed annually at the beginning of each academic year.
> - Separate hostel blocks are provided for Boys and Girls on campus."""

_HOSTEL_INFO_CHIPS = ["Mess Food & Timings", "Hostel Rules & Curfew", "Safety & Wardens", "Hostel Fee Breakdown"]
_HOSTEL_MESS_CHIPS = ["Hostel Facilities & Rooms", "Curfew & In-Time Rules", "Hostel Room Fees", "Safety & Security"]
_HOSTEL_CURFEW_CHIPS = ["Mess & Dining timings", "Hostel Facilities & Rooms", "Hostel Wardens & Contacts", "Hostel Fees"]
_HOSTEL_SAFETY_CHIPS = ["Hostel Facilities & Rooms", "Mess Food & Timings", "Curfew & Rules", "Hostel Fees"]
_HOSTEL_FEE_CHIPS = ["Hostel Facilities & Rooms", "Mess Food & Timings", "Curfew & Rules", "Calculate B.Tech Fee"]

_COMBINED_HOSTEL_FEE_TEXT = """### 🎓 B.Tech CSE Fee + Hostel Combined Breakdown (Academic Year 2027–28)

Here is the complete combined fee breakdown for **B.Tech Computer Science & Engineering (Core)** including **Residential Hostel & Mess (AC 4-Sharing)**:

#### 📅 Per-Semester Breakdown (Regular):
• **Tuition Fee**: **₹1,70,000 / sem** (Annual base ₹3,40,000; up to 40% merit scholarship applies)
• **Hostel & Dining (AC 4-Sharing)**: **₹62,500 / sem** (Annual ₹1,25,000; includes 4 daily meals, Wi-Fi & laundry)
• **Academic & Exam Fee**: **₹10,000 / sem** (Annual ₹20,000)
👉 **Combined Regular Semester Fee**: **₹2,42,500 / semester**

#### 📋 First-Year Total Outlay:
• **Year 1 Combined Total**: **₹4,91,100** (Tuition ₹3.40L + Hostel ₹1.25L + Academic ₹20k + One-time admission/enrolment ₹6,100)
*(With Non-AC 4-Sharing, the combined total is **₹4,81,100 / year** or **₹2,37,500 / semester**).*

> [!NOTE]
> Merit scholarships (up to 40% waiver based on 10+2 marks or entrance ranks) directly reduce the tuition portion!"""

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
• 🚀 **Innovation at SRiX**: 171+ startups, 8,900+ publications, and 2,700+ patents on a 170-acre campus.

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
• 💡 **Research Excellence**: Dedicated research centres, 8,900+ publications, 2,700+ patents filed, and SRiX incubator with 171+ startups.
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
• 🚀 **Startups & Patents**: ₹76+ Cr DST-funded SRiX incubator with 171+ ventures, 8,900+ publications, and 2,700+ patents.
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


_OTHER_FEES_TEXT = """As per the official 2027-28 Fee Structure, the fee components and charges other than semester tuition are:

| Fee Component / Head | Amount | Notes / Frequency |
| :--- | :--- | :--- |
| **Enrolment Fee** | **₹5,000** | One-time (payable at admission / Semester 1) |
| **Other Academic / University Charges** | **₹15,000** | Annual (laboratories, library & campus amenities) |
| **Examination Fee (First Year)** | **₹5,000** | Annual (as printed on fee card for Year 1) |
| **Application Form Fee** | **₹1,100** | One-time (paid with online application at apply.sru.edu.in) |
| **Specialisation Fee** | **₹30,000** | Applicable annually from the 2nd year onwards where specialisation applies |
| **PhD Fee** | **₹70,000** | Per year (for doctoral research scholars) |

• **Optional Living & Transport Services**:
  - **Hostel (Accommodation + Food)**: ₹1,15,000 – ₹1,35,000/year (includes 4 daily meals in the 4,000-seat Mega Dining Hall)
  - **Hostel Caution Deposit**: ₹5,000 (refundable) + ₹5,000 laundry
  - **Transportation (University Bus)**: ₹30,000/year (covers Warangal, Hanamkonda, Kazipet and outstation routes)

There is no separate "admission fee" charged on the 2027-28 fee card."""

_OTHER_FEES_CHIPS = ["B.Tech CSE tuition", "Calculate my scholarship", "Hostel accommodation", "Plan a campus visit"]

_BRANCH_GUIDANCE_CHIPS = [
    "Software & Artificial Intelligence",
    "Hardware, VLSI & Robotics",
    "Core Engineering (Mech, Civil, EEE)",
    "Talk to an admission counsellor",
]


def get_branch_guidance_text(marks: int | float | None = None, session_id: str | None = None) -> str:
    """Natural branch guidance response explaining SRU engineering tracks and asking one follow-up question."""
    ack = f"With **{marks} marks in Intermediate**, you have a strong academic foundation for engineering at SR University." if marks else "Choosing the right engineering branch is an important decision, and we can help you find the best fit."
    return f"""{ack}

Here is a quick overview of the key B.Tech engineering pathways available at SR University:

• 💻 **Computer Science & Engineering (CSE)**: Ideal if you enjoy software programming, algorithms, AI & Machine Learning, Data Science, and cybersecurity. High campus recruitment and coding focus.
• 🤖 **AI & Robotics**: Best if you want to work at the intersection of intelligent software, automated mechanical systems, autonomous robots, and drone engineering.
• ⚡ **Electronics & Communication (ECE)**: Excellent if you are interested in VLSI chip design, embedded systems, IoT devices, wireless communications, and hardware-software integration.
• ⚙️ **Core Engineering (Mechanical, EEE, Civil)**: Strong hands-on focus in smart manufacturing, electric vehicle (EV) powertrains, sustainable infrastructure, and renewable energy.

Which area interests you more — building software and apps, working with hardware and robotics, or core physical engineering?"""




