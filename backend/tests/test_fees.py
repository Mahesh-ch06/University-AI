"""Run: pytest -q     (no API key needed)
These numbers match the CURRENT fee_policy_2027_28.json. Update both together."""
from app.sru_agent import fees
from app.sru_agent.tools import clean_phone


def test_cse_92_percent_gets_30_percent():
    r = fees.calculate_fee("cse", percent=92)
    assert r["scholarship_percent"] == 30
    assert r["tuition_first_year"] == "₹3,40,000"
    assert r["tuition_first_year_after_scholarship"] == "₹2,38,000"
    assert r["per_semester_after_scholarship"] == "₹1,19,000"


def test_cse_no_marks_full_course_total():
    r = fees.calculate_fee("B.Tech CSE")
    # tuition 3,40,000 + 3,49,000 + 3,58,000 + 3,67,000 = 14,14,000
    # + enrollment 5,000 + Year-1 exam 5,000 + other fee 15,000 x 4 = 14,84,000 (application fee shown separately)
    assert r["full_course_total"] == "₹14,84,000"
    assert r["application_fee"] == "₹1,100"


def test_mech_75_percent():
    assert fees.calculate_fee("mech", percent=75)["tuition_first_year_after_scholarship"] == "₹1,60,000"


def test_hostel_added_to_first_year():
    r = fees.calculate_fee("ece", percent=56, hostel="ac_3")
    assert r["hostel"]["per_year"] == "₹1,35,000"
    # 2,70,000 tuition + 5,000 enrollment + 15,000 other + 5,000 exam + 1,35,000 hostel + 10,000 AC deposit
    assert r["first_year_total_payable"] == "₹4,40,000"


def test_eapcet_rank_scholarship():
    # Rank 9,000 falls in 8,001–20,000 slab which gets 25% scholarship
    r = fees.calculate_fee("cse", eapcet_rank=9000)
    assert r["scholarship_percent"] == 25
    assert r["scholarship_basis"] == "eapcet rank 9000"


def test_jee_main_percentile_scholarship():
    # The circular prints 90–94.5 percentile for 30% and 95+ for 40%
    r = fees.calculate_fee("cse", jee_percentile=94.5)
    assert r["scholarship_percent"] == 30
    assert r["scholarship_basis"] == "jee percentile 94.5"
    assert fees.calculate_fee("cse", jee_percentile=95)["scholarship_percent"] == 40


def test_jee_gap_between_94_5_and_95_is_flagged_not_guessed():
    r = fees.calculate_fee("cse", jee_percentile=94.7)
    assert r["scholarship_percent"] == 0
    assert any("94.5" in f and "Admissions Office" in f for f in r["flags"])


def test_score_without_table_is_not_guessed():
    # PG has no eapcet_rank configured
    r = fees.calculate_fee("mba", eapcet_rank=500)
    assert r["scholarship_percent"] == 0
    assert any("eapcet_rank" in n for n in r["notes"])


def test_eligibility_uses_the_circular_minimum():
    # 2027-28 circular: 55% for B.Tech CSE / ECE (and their specialisations), 50% for other UG, 50% PG
    r58 = fees.check_eligibility("cse", 58, stream="MPC")
    assert r58["eligibility_status"] == "meets_minimum" and r58["eligible"] is True
    assert r58["sources_disagree"] is False
    assert fees.check_eligibility("cse", 54.99)["eligible"] is False
    assert fees.check_eligibility("cse ai ml", 55, stream="MPC")["eligible"] is True
    assert fees.check_eligibility("ece", 54.9)["eligible"] is False
    assert fees.check_eligibility("ece vlsi", 55, stream="MPC")["eligible"] is True
    assert fees.check_eligibility("mech", 50, stream="MPC")["eligible"] is True
    assert fees.check_eligibility("mech", 49.99)["eligible"] is False
    assert fees.check_eligibility("bba", 50)["eligible"] is True
    assert fees.check_eligibility("bba", 49.9)["eligible"] is False
    mba = fees.check_eligibility("mba", 50)
    assert mba["eligible"] is True and "subject to confirmation" in mba["explanation"]
    assert fees.check_eligibility("mba", 49.9)["eligible"] is False
    # No marks given: ask, never assume 0%
    assert fees.check_eligibility("cse")["status"] == "need_marks"


def test_program_matching_and_unknown():
    assert fees.find_program("btech ai & ml") == "btech_cse"
    assert fees.find_program("wat r d fess for mech") == "btech_mech"
    assert fees.calculate_fee("astrology")["status"] == "unknown_program"


def test_phone_cleaning():
    assert clean_phone("+91 98765 43210") == "9876543210"
    assert clean_phone("09876543210") == "9876543210"
    assert clean_phone("12345") is None
    assert clean_phone("1234567890") is None
