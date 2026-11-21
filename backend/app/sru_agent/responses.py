"""Static response templates and quick reply catalogues for SRU Buddy.

Decouples agent.py from large multi-line markdown texts.
"""
from __future__ import annotations

_SMALL_TALK_CHIPS = ["B.Tech CSE fees", "Scholarship for my marks", "Placements at SRU", "Plan a campus visit"]

_PLACEMENT_ASSISTANCE_CHIPS = ["Top Recruiters & Packages", "Startup Incubator (SRiX)", "Placement Eligibility Rules", "Book a Campus Visit"]

_PLACEMENT_ASSISTANCE_RESPONSES = [
    """At **SR University**, we provide **100% placement assistance and career readiness support** to all eligible students across our undergraduate and postgraduate programs.

While no university can unconditionally guarantee job offers—as final placement selections depend entirely on an individual student's academic standing, technical competence, interview clearance, and recruiter hiring criteria—SRU provides an end-to-end launchpad to prepare you for industry success.

---

### 🌟 How SRU Empowers Your Career & Ambitions:
1. **💼 100% Placement & Career Support**:
   - Structured preparation via the **Center for Student Services and Placements (CSSP)** and **Career Guidance Cell (CGC)**: competitive coding, full-stack assessments, aptitude coaching, and mock technical interviews.
   - **3,500+ internships** completed with top stipends reaching up to ₹1.25 Lakh/month.
   - Dedicated on-campus recruitment drives featuring **150+ marquee companies** (including Microsoft, Amazon, ServiceNow, Salesforce, PayPal, Cisco, TCS, Cognizant, Accenture, and Capgemini).

2. **🚀 Explore Startups & Entrepreneurship (SRiX)**:
   - For students passionate about entrepreneurship or building their own ventures, SRU houses **SRiX (SR Innovation Exchange)**—a premier, DST-supported technology business incubator on campus.
   - Students gain access to **maker spaces, rapid prototyping labs, expert mentorship from venture leaders**, and **seed grant funding from a ₹76+ Crore startup ecosystem** with 171+ incubated startups.

3. **📊 Verified Placement Track Record**:
   - **1,300+ Total Job Offers** secured by students.
   - **Average Package**: ~**6 to 6.5 LPA** across graduating engineering cohorts.
   - **Top Milestone Packages**:
     - 💎 **₹51.00 LPA** — Microsoft (*Batch 2025*)
     - 💎 **₹49.30 LPA** — ServiceNow (*Batch 2027*)
     - 💎 **₹46.38 LPA** — Amazon (*Batch 2026*)
     - 💎 **₹44.00 LPA** — Salesforce & ServiceNow (*Batch 2025*)

> [!TIP]
> **Our Commitment**: We provide 100% institutional support, premium recruiters, and incubation backing—your dedication, skills, and preparation turn these opportunities into dream careers!""",

    """**SR University provides 100% placement assistance** and an end-to-end career launchpad for every eligible student.

Because final placement outcomes depend on individual student dedication, technical competence, academic consistency (CGPA and zero active backlogs), and company interview evaluations, placements cannot be unconditionally guaranteed by any institution. However, SRU equips every student with industry-grade skills, corporate drives, and entrepreneurial pathways.

---

### 💼 Comprehensive Career & Startup Ecosystem:
- **🎯 100% Placement Guidance**: Tailored career counselling, full-stack coding assessments, and intensive interview preparation conducted by the **Center for Student Services and Placements (CSSP)** with **150+ hiring partners**.
- **🚀 Passionate About Startups?**: If you want to pursue your own venture, SRU's on-campus incubator **SRiX (SR Innovation Exchange)**—recognized and supported by the Department of Science and Technology (DST)—provides seed funding, incubation labs, prototyping resources, and angel investor networking.
- **🛠️ Industry Internships**: Over **3,500+ internships** completed with monthly stipends reaching up to ₹1.25 Lakh/month.

### 📈 Verified Placement Benchmarks:
- **Average Package**: ~**6 LPA** (with university portals citing 6.5 LPA across engineering streams).
- **Highest Packages**: **₹51 LPA** at Microsoft, **₹49.30 LPA** at ServiceNow, and **₹46.38 LPA** at Amazon.
- **Over 1,300+ Placement Offers** spanning global IT giants, product companies, and core engineering firms.""",

    """At **SR University**, our core commitment is delivering **100% placement assistance, rigorous skill development, and diverse career pathways** for every student.

While final job offers naturally depend on each student's academic performance, technical skills, and interview success—meaning no higher education institution can give an unconditional job guarantee—SRU leaves no stone unturned in ensuring you are career-ready:

---

- 🎯 **100% Placement Assistance**: Rigorous coaching in data structures, system design, aptitude, and soft skills from the 2nd year onwards, connecting students directly to **150+ national and multinational recruiters**.
- 🚀 **Explore Startups & Innovation**: Have an entrepreneurial mindset? SRU’s **SRiX (SR Innovation Exchange)** incubator offers world-class maker spaces, seed capital, and mentorship to help students launch and scale their own startup ventures.
- 💼 **Proven Placement Record**: Over **1,300+ job offers** with an average package of **6 to 6.5 LPA**. Top offers include **₹51 LPA (Microsoft)**, **₹49.30 LPA (ServiceNow)**, and **₹46.38 LPA (Amazon)**.

Whether your aspiration is securing a dream role at a global technology leader or launching a disruptive startup, SR University provides the 100% mentorship, infrastructure, and opportunities to make it happen!""",

    """**SR University assures 100% placement assistance and career guidance** to help every graduate succeed in the professional world.

Rather than a passive "guarantee", SRU actively partners with you: final placement offers depend on your skills, consistency, and interview performance, while the university provides the entire launchpad—from industry certifications to campus drives.

---

### 🌟 What SRU Offers Every Student:
1. **100% Placement Assistance**: Dedicated recruitment drives with **150+ top companies** (Microsoft, Amazon, ServiceNow, Salesforce, Accenture, Cognizant, TCS), comprehensive mock interviews, and 3,500+ internships.
2. **Startup & Incubation Support (SRiX)**: Want to build your own company instead of a traditional corporate job? SRU's on-campus incubator **SRiX** offers seed funding, maker spaces, and startup mentoring to turn innovative ideas into commercial realities.
3. **Stellar Placement Records**: 
   - **Average Salary**: ~**6 – 6.5 LPA** across graduating engineering disciplines.
   - **Highest Packages**: **₹51 LPA** (Microsoft), **₹49.30 LPA** (ServiceNow), and **₹46.38 LPA** (Amazon).
   - **1,300+ Placement Offers** across global tech, fintech, core engineering, and consulting firms."""
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

_BTECH_CSE_FEE_TEXT = """### 💻 B.Tech CSE & Allied Streams — Fee Structure (2027–28)

Official fee schedule for **B.Tech Computer Science & Engineering** and its specialized streams (AIML, Data Science, Cyber Security, Quantum AI, Precision Agriculture):

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

_HOSTEL_INFO_TEXT = """### 🏢 Residential Campus Living at SR University

SR University offers a secure, vibrant, and disciplined residential experience with **dedicated separate hostel blocks** for Boys and Girls on campus:

• **Hostel Blocks**:
  - **Boys Hostels**: Dr. Sarvepalli Radhakrishnan Bhavan & APJ Abdul Kalam Bhavan
  - **Girls Hostels**: Kalpana Chawla Bhavan & Sarojini Naidu Bhavan
• **Room Options & Furnishings**:
  - **Air-Conditioned (AC)**: 3-Sharing & 4-Sharing
  - **Non-AC**: 3-Sharing & 4-Sharing
  - Every resident receives a dedicated bed, comfortable mattress, individual study desk, ergonomic chair, personal wardrobe, and 24/7 Wi-Fi.
• **Mega Dining Hall**:
  - 4,000 seating capacity serving 4 fresh, hygienic, unlimited meals daily (Breakfast, Lunch, Evening Snacks, Dinner) with balanced vegetarian and non-vegetarian menus.
• **Key Amenities & Utilities**:
  - 24/7 power backup and commercial RO-purified water dispensers on every floor.
  - Solar hot water supply (7:00–9:00 AM & 7:00–9:00 PM).
  - Modern gymnasium with fitness trainers, indoor sports (table tennis, carroms, chess, shuttle badminton) and recreation lounges.
  - On-campus health clinic, resident nurses, 24/7 stationed ambulance, and institutional tie-up with Aaditya Hospital.
• **Safety & Security**:
  - 100% CCTV surveillance, biometric access checkpoints, dedicated security personnel at all gates, and resident wardens in every block.

*Hostel accommodation is optional. Would you like to check the room fee breakdown, dining timings, or curfew rules?*"""

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

_HOSTEL_CURFEW_RULES_TEXT = """### ⏰ Hostel Curfew, Timings & Discipline Regulations

SR University maintains a secure and disciplined campus environment with strict curfew and movement policies:

• **Hostel In-Time (Night Curfew)**:
  - **Weekdays (Monday to Friday)**: Students must be inside the hostel premises by **9:00 PM**.
  - **Weekends & Holidays (Saturday & Sunday)**: Students must be inside by **9:30 PM**.
  - **Biometric Roll Call**: Mandatory nightly biometric attendance between **9:00 PM and 9:30 PM** (weekdays) / before **10:00 PM** (weekends).
  - **Morning Exit**: Students can leave the hostel in the morning after **5:30 AM** by signing the movement register.
• **Curfew Extensions**:
  - Extensions up to **11:00 PM** are granted for hackathons, club activities, festival preparations, or library study.
  - Requests must be submitted via the online **Sruniv portal** before 4:00 PM on the day and approved by the Warden.
• **Digital Out-Pass System**:
  - Resident students wishing to leave campus must apply via the online **Sruniv portal**.
  - Automated SMS notifications are sent to parents/guardians for approval before gate clearance is issued.
• **Silence Hours & Code of Conduct**:
  - **Silence Hours**: **10:00 PM to 7:00 AM** daily (strictly enforced for quiet study and rest).
  - **Cross-Gender Entry Policy**: Strictly prohibited. Male students/visitors cannot enter female blocks, and female students/visitors cannot enter male blocks.
  - **Prohibited Appliances**: Electric stoves, induction cooktops, immersion heaters, and electric irons are strictly forbidden in rooms.
  - **Substance Policy**: 100% zero-tolerance policy against ragging, bullying, alcohol, smoking, or unauthorized absences.

*Would you like to review safety and warden details, mess food, or room fees?*"""

_HOSTEL_SAFETY_TEXT = """### 🛡️ Campus Safety, Security & Hostel Wardens

The safety and well-being of residential students are our highest priorities:

• **Round-the-Clock Security**:
  - Gated campus with 24/7 professional uniformed security personnel at all hostel and campus gates.
  - Comprehensive CCTV surveillance covering all hostel corridors, staircases, common lounges, and perimeter grounds.
  - Biometric checkpoints for entry and roll call.
• **Dedicated Residential Wardens**:
  - **Girls Hostels Warden**: Ms. Anitha GP (📞 **+91 9599042878** | ✉️ `stu.girlshostel@sru.edu.in`)
  - **Boys Hostels Wardens**: Dr. Rupesh Mishra (📞 **+91 9716935695**) & Dr. Anshu Kumar (📞 **+91 6394355001**)
• **Student Counsellors**:
  - **Boys Counsellor**: Mr. Benson (📞 **+91 7893525257**)
  - **Girls Counsellor**: Ms. Swapna (📞 **+91 7207672300**)
• **Medical & Emergency Infrastructure**:
  - On-campus Health Centre with qualified resident nurse and visiting physicians.
  - Stationed 24/7 emergency ambulance on campus.
  - Direct tie-up with **Aaditya Hospital** for tertiary and emergency healthcare.
• **Zero-Tolerance Anti-Ragging**:
  - Fully compliant with Supreme Court & UGC Anti-Ragging Regulations 2009.
  - Active Anti-Ragging Committee and flying squads (`stu.antiraggingcell@sru.edu.in`).

*Would you like details on hostel living facilities, mess food, or room fees?*"""

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

_CAMPUS_CANTEEN_TEXT = """### ☕ Campus Cafeteria, Food Stalls & Dining Options at SR University

SR University offers vibrant on-campus dining and snacking spots for students, faculty, and visitors across its 170-acre campus:

#### 1. 🍽️ Central Cafeteria
• **Timings**: **8:30 AM to 6:00 PM** (Monday to Saturday)
• **Offerings**: Fresh breakfast, hot South & North Indian lunch platters, fresh juices, teas, coffees, and wholesome snacks in a spacious indoor seating setting.

#### 2. 🥪 Campus Food Kiosks & Stalls
Open **9:00 AM to 7:00 PM** across campus plazas:
• **Tasty Treat**: Quick bites, grilled sandwiches, rolls, patties, and cool beverages.
• **Meet and Eat**: Fast-food varieties, noodles, wraps, and quick evening snacks.
• **Bharat Foods**: Traditional snacks, chaat, samosas, and refreshing hot drinks.

#### 3. 🍱 4,000-Seat Mega Dining Hall (Residential Mess)
• Four nutritious, hygienic daily meals (Breakfast, Lunch, Evening Snacks, Dinner) for hostel residents with rotating South & North Indian multi-cuisine menus.

> [!TIP]
> All food kiosks and the central cafeteria accept digital payments (UPI/cards). The Canara Bank 24/7 ATM is conveniently located at the Main Gate."""

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

_LAB_FACILITIES_TEXT = """### 🔬 Laboratories & Research Infrastructure at SR University

SR University does not operate with a single combined count for all labs because facilities are organized across three distinct levels of advanced infrastructure:

#### 1. 🏢 11 Interdisciplinary Specialized Research Centers
Dedicated high-tech centers conducting cutting-edge research, patent creation, and industry projects:
• **Center for AI & Deep Learning (CAIDL)**: High-performance GPU computing clusters, neural network training environments, and computer vision systems.
• **Center for Creative Cognition (CCC)**: Houses 6 advanced labs (*Ideation Lab, Eye-tracking Lab, EEG Lab, Computational Neuroscience Lab, Driving Simulator Lab, Psychometric Testing Lab*).
• **Center for Embedded Systems & IoT (EIoT)**: Raspberry Pi platforms, ARM Cortex M4 development kits, and wireless sensor nodes.
• **Center for Emerging Energy Technologies (CEET)**: LabVIEW Advanced Simulation Lab, Energy Lab, and Electric Drives / EV Powertrain Lab.
• **Center for Materials & Manufacturing (CMM)**: Product Design Studio, CAD/CAM Lab, CNC Makers Space, and Additive Manufacturing (3D Printing).
• **Center for Construction Methods & Materials**: Concrete Technology, Triaxial Testing, Digital Consolidation, and Automatic Asphalt Compactor setups.
• **Centre for Nanomaterials**: Nanomaterial synthesis and high-resolution characterization microscopy.
• **Additional Centers**: *Center for Informetrics & Statistics*, *Center for Experiential Learning*, *Collaboratory for Social Innovation*, and *Center for Design*.

#### 2. 🚀 SR Innovation Exchange (SRiX) & Prototyping Studios
• **14+ Maker Spaces** and open innovation project studios.
• **IoT & ESDM Lab** (Electronic System Design & Manufacturing).
• **3D Rapid Prototyping Facility** & **Design Thinking Studio** supporting student startups from idea to scale (171+ startups incubated, ₹76+ Cr funding).

#### 3. 🖥️ Departmental Academic Laboratories Across 6 Schools
Every department maintains multiple specialized curriculum labs:
• **School of Computer Science & AI**: AI/ML, Big Data Analytics, Cloud Computing/DevOps, Cybersecurity, and Software Engineering Labs.
• **School of Engineering**: ECE (VLSI Design, DSP, Microprocessors, Microwave), EEE (Electric Machines, Power Electronics), Mechanical (Robotics & Automation, CAD/CAM, Metallurgy, Fluid Mechanics), and Civil (Surveying Total Station, Geotechnical, Environmental).
• **School of Agriculture (ICAR Accredited)**: 50+ acre experimental farm, polyhouses, Soil & Water Testing, Agronomy, and Plant Pathology labs.
• **Basic Sciences & Design**: Engineering Physics, Chemistry, AECS Multimedia English Lab, and Visual Design/Ergonomics Studios.

Which department or domain of laboratories would you like to explore in detail?"""

_LAB_FACILITIES_CHIPS = ["AI & Computer Science Labs", "SRiX Startup Maker Spaces", "Robotics & IoT Labs", "B.Tech CSE Curriculum"]


