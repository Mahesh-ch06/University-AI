"""The 2027-28 fee circular and the ONE fee engine (app/sru_agent/fees.py).

Covers every programme and scholarship slab, eligibility boundaries, the yearly increase, component-based
semester allocation, one-time and optional charges, concessions and totals. Expected figures are written out
from the circular (SRU_Fee_Structure_and_Scholarship_Policy.pdf), never computed with the engine's own code.
"""
import copy

import pytest

from app.sru_agent import eligibility, fees

SLAB_PCTS = (0, 10, 15, 20, 25, 30, 40)
# One Intermediate % per slab (CSE/ECE standard band starts at 55, other UG at 50).
INTER_FOR = {0: 56, 10: 60, 15: 65, 20: 70, 25: 80, 30: 92, 40: 98}

# programme: (tuition, yearly increase, minimum %, duration) as printed / configured
PROGRAMMES = {
    "btech_cse": (340000, 9000, 55, 4), "btech_ai_robotics": (400000, 12000, 50, 4),
    "btech_ece": (270000, 8000, 55, 4), "btech_eee": (200000, 6000, 50, 4), "btech_mech": (200000, 6000, 50, 4),
    "btech_civil": (200000, 6000, 50, 4), "btech_biotech": (200000, 6000, 50, 4),
    "btech_food_tech": (200000, 6000, 50, 4), "btech_engg_physics": (200000, 6000, 50, 4),
    "btech_iep": (340000, 10000, 50, 4), "bdes": (210000, 6000, 50, 4), "bsc_agri": (200000, 6000, 50, 4),
    "bba": (150000, 4000, 50, 3), "bsc_hospitality": (150000, 4000, 50, None),
    "bba_specialised": (200000, 6000, 50, 3), "bca": (150000, 4000, 50, 3), "bsc_cs": (150000, 4000, 50, 3),
    "bcom": (100000, 3000, 50, None), "bsc_physics": (100000, 3000, 50, 3), "bsc_chemistry": (100000, 3000, 50, 4),
    "bsc_maths_ai": (100000, 3000, 50, 3), "mba": (300000, 9000, 50, 2), "mca": (150000, 4000, 50, 2),
    "mtech": (100000, 3000, 50, 2), "msc": (100000, 3000, 50, 2), "mba_agri": (200000, 6000, 50, 2),
}
# The circular's printed per-year tuition for each slab (10% … 40% OFF), base 3,40,000 etc.
PRINTED = {
    340000: [340000, 306000, 289000, 272000, 255000, 238000, 204000],
    400000: [400000, 360000, 340000, 320000, 300000, 280000, 240000],
    270000: [270000, 243000, 229500, 216000, 202500, 189000, 162000],
    210000: [210000, 189000, 178500, 168000, 157500, 147000, 126000],
    200000: [200000, 180000, 170000, 160000, 150000, 140000, 120000],
    300000: [300000, 270000, 255000, 240000, 225000, 210000, 180000],
    150000: [150000, 135000, 127500, 120000, 112500, 105000, 90000],
    100000: [100000, 90000, 85000, 80000, 75000, 70000, 60000],
}
R = fees.inr
CHARGES_Y1_S1 = 5000 + 15000 + 5000          # enrollment + other + Year-1 exam


def _num(text):
    return int(str(text).replace("₹", "").replace(",", "").replace("-", "")) * (-1 if "-" in str(text) else 1)


def test_every_programme_is_on_the_circular():
    data = fees.load_data()["programs"]
    assert set(data) == set(PROGRAMMES)
    for key, (tuition, inc, minimum, years) in PROGRAMMES.items():
        p = data[key]
        assert (p["tuition_per_year"], p["yearly_increase"], p["min_percent"], p["duration_years"]) == \
            (tuition, inc, minimum, years), key


@pytest.mark.parametrize("key", sorted(PROGRAMMES))
@pytest.mark.parametrize("slab", SLAB_PCTS)
def test_every_programme_and_slab_matches_the_printed_matrix(key, slab):
    tuition, inc, _minimum, years = PROGRAMMES[key]
    r = fees.calculate_fee(key, percent=INTER_FOR[slab])
    assert r["scholarship_percent"] == slab
    net = PRINTED[tuition][SLAB_PCTS.index(slab)]
    assert r["tuition_first_year_after_scholarship"] == R(net)
    # Only tuition is split; Semester 1 also carries enrollment, other and the Year-1 exam fee.
    assert r["per_semester_after_scholarship"] == R(net / 2)
    assert r["sem1_total_payable"] == R(net / 2 + CHARGES_Y1_S1)
    assert r["sem2_total_payable"] == R(net / 2)
    assert r["first_year_total_payable"] == R(net + CHARGES_Y1_S1)
    if years:
        # Year y tuition = base - scholarship + (y - 1) x increase; other fee every year; one-time charges once.
        expected = sum(net + y * inc for y in range(years)) + 5000 + 5000 + 15000 * years
        assert r["full_course_total"] == R(expected)
        assert [y["after_scholarship"] for y in r["year_by_year"]] == [R(net + y * inc) for y in range(years)]
    else:
        assert "full_course_total" not in r


def test_the_circular_worked_example_cse_95_percent():
    r = fees.calculate_fee("btech_cse", percent=95)
    assert r["scholarship_percent"] == 30
    s1 = {i["key"]: i["amount"] for i in r["semester_1"]["items"]}
    s2 = {i["key"]: i["amount"] for i in r["semester_2"]["items"]}
    assert s1 == {"tuition": "₹1,19,000", "enrollment_fee": "₹5,000", "other_fee": "₹15,000", "exam_fee": "₹5,000"}
    assert s2 == {"tuition": "₹1,19,000"}
    assert (r["sem1_total_payable"], r["sem2_total_payable"], r["first_year_total_payable"]) == \
        ("₹1,44,000", "₹1,19,000", "₹2,63,000")
    assert r["sem1_total_payable"] != "₹1,31,500" and r["sem2_total_payable"] != "₹1,31,500"
    assert r["application_fee"] == "₹1,100"                                  # shown separately
    assert "₹1,100" not in str(r["semester_1"]) + str(r["semester_2"])


@pytest.mark.parametrize("score, pct", [
    ({"percent": 59.99}, 0), ({"percent": 60}, 10), ({"percent": 64.9}, 10), ({"percent": 65}, 15),
    ({"percent": 69.9}, 15), ({"percent": 70}, 20), ({"percent": 79.9}, 20), ({"percent": 80}, 25),
    ({"percent": 91.9}, 25), ({"percent": 92}, 30), ({"percent": 97.9}, 30), ({"percent": 98}, 40),
    ({"percent": 89.9, "board": "cbse"}, 25), ({"percent": 90, "board": "icse"}, 30),
    ({"percent": 94.9, "board": "cbse"}, 30), ({"percent": 95, "board": "cbse"}, 40),
    ({"jee_percentile": 49.9}, 0), ({"jee_percentile": 50}, 10), ({"jee_percentile": 60}, 15),
    ({"jee_percentile": 70}, 20), ({"jee_percentile": 80}, 25), ({"jee_percentile": 90}, 30),
    ({"jee_percentile": 94.5}, 30), ({"jee_percentile": 94.8}, 0), ({"jee_percentile": 95}, 40),
    ({"eapcet_rank": 1}, 40), ({"eapcet_rank": 2000}, 40), ({"eapcet_rank": 2001}, 30), ({"eapcet_rank": 8000}, 30),
    ({"eapcet_rank": 8001}, 25), ({"eapcet_rank": 20000}, 25), ({"eapcet_rank": 20001}, 0),
    ({"ib_score": 23}, 0), ({"ib_score": 24}, 20), ({"ib_score": 29}, 20), ({"ib_score": 30}, 25),
    ({"ib_score": 34}, 30), ({"ib_score": 38}, 40),
])
def test_score_types_and_slab_boundaries(score, pct):
    assert fees.calculate_fee("btech_cse", **score)["scholarship_percent"] == pct


@pytest.mark.parametrize("percent, pct", [(59.9, 0), (60, 10), (65, 15), (70, 20), (80, 25), (92, 30), (98, 40)])
def test_pg_percentage_slabs(percent, pct):
    assert fees.calculate_fee("mba", percent=percent)["scholarship_percent"] == pct


@pytest.mark.parametrize("key, below, at", [
    ("btech_cse", 54.99, 55), ("btech_ece", 54.9, 55), ("btech_mech", 49.99, 50), ("btech_ai_robotics", 49.9, 50),
    ("bba", 49.9, 50), ("bsc_agri", 49.9, 50), ("mba", 49.9, 50), ("mtech", 49.9, 50),
])
def test_eligibility_boundaries(key, below, at):
    assert eligibility.assess(key, below)["status"] == eligibility.BELOW
    assert eligibility.assess(key, at)["status"] == eligibility.MEETS
    r = fees.calculate_fee(key, percent=below)
    assert r["admission_eligibility"]["status"] == eligibility.BELOW and "instruction" in r
    assert any("below the" in f and "verification" in f for f in r["flags"])     # flagged, not hidden


def test_pg_minimum_is_flagged_subject_to_confirmation():
    r = fees.calculate_fee("mba", percent=72)
    assert any("subject to confirmation" in f for f in r["flags"])
    assert not any("subject to confirmation" in f for f in fees.calculate_fee("bba", percent=72)["flags"])


def test_ambiguous_scholarship_conditions_are_flagged():
    assert any("94.5" in f for f in fees.calculate_fee("btech_cse", jee_percentile=94.7)["flags"])
    assert any("overlap" in f for f in fees.calculate_fee("btech_cse", ib_score=31)["flags"])


def test_increment_applies_from_year_2_irrespective_of_scholarship():
    r = fees.calculate_fee("btech_ai_robotics", percent=98)                     # 40%: 2,40,000
    assert [y["after_scholarship"] for y in r["year_by_year"]] == ["₹2,40,000", "₹2,52,000", "₹2,64,000", "₹2,76,000"]
    later = r["schedule"][1]["semesters"]
    assert later[0]["items"][0]["amount"] == later[1]["items"][0]["amount"] == "₹1,26,000"


def test_one_time_charges_are_never_repeated_and_other_fee_is_not_split():
    r = fees.calculate_fee("btech_cse", percent=80)
    for year in r["schedule"]:
        s1 = {i["key"] for i in year["semesters"][0]["items"]}
        s2 = {i["key"] for i in year["semesters"][1]["items"]}
        assert s2 == {"tuition"}                                    # nothing but tuition in Semester 2
        assert "other_fee" in s1                                    # whole, in Semester 1, every year
        assert ("enrollment_fee" in s1) == ("exam_fee" in s1) == (year["year"] == 1)


def test_specialisation_fee_from_year_2_only_and_only_when_chosen():
    plain = fees.calculate_fee("btech_cse", percent=80)
    spec = fees.calculate_fee("btech_cse", percent=80, specialization=True)
    assert plain["first_year_total_payable"] == spec["first_year_total_payable"]   # never in Year 1
    for year in spec["schedule"][1:]:
        s1 = {i["key"]: i["amount"] for i in year["semesters"][0]["items"]}
        assert s1["specialization_fee"] == "₹30,000"
    assert _num(spec["full_course_total"]) - _num(plain["full_course_total"]) == 30000 * 3
    # not applied to a programme the policy does not list for it
    assert fees.calculate_fee("btech_mech", specialization=True)["full_course_total"] == \
        fees.calculate_fee("btech_mech")["full_course_total"]


def test_optional_charges_only_when_chosen_and_no_scholarship_on_them():
    base = fees.calculate_fee("btech_cse", percent=98)
    assert not any(i["kind"] == "optional" for y in base["schedule"] for s in y["semesters"] for i in s["items"])
    both = fees.calculate_fee("btech_cse", percent=98, hostel="non_ac_4", transport=True)
    s1 = {i["key"]: i["amount"] for i in both["semester_1"]["items"]}
    assert s1["hostel"] == "₹1,15,000" and s1["bus"] == "₹30,000" and s1["electricity_deposit"] == "₹5,000"
    assert _num(both["first_year_total_payable"]) - _num(base["first_year_total_payable"]) == 115000 + 30000 + 5000
    # the deposit is one-time; hostel and bus recur each year at full price (no scholarship on charges)
    y2 = {i["key"]: i["amount"] for i in both["schedule"][1]["semesters"][0]["items"]}
    assert "electricity_deposit" not in y2 and y2["hostel"] == "₹1,15,000" and y2["bus"] == "₹30,000"
    ac = fees.calculate_fee("btech_cse", hostel="ac_3")
    assert {i["key"]: i["amount"] for i in ac["semester_1"]["items"]}["electricity_deposit"] == "₹10,000"


def test_concessions_are_annual_deductions_counted_once():
    one = fees.calculate_fee("btech_cse", percent=80, concessions=["sibling"])
    plain = fees.calculate_fee("btech_cse", percent=80)
    for y_one, y_plain in zip(one["schedule"], plain["schedule"]):
        assert _num(y_plain["total"]) - _num(y_one["total"]) == 15000            # once a year
    twice = fees.calculate_fee("btech_cse", percent=80, concessions=["sibling", "sibling"])
    assert twice["first_year_total_payable"] == one["first_year_total_payable"]  # no double counting
    assert not fees.calculate_fee("btech_cse", concessions=["chancellor_recommendation"])["concessions_applied"]
    assert any("combined" in f for f in fees.calculate_fee("btech_cse", concessions=["sibling", "ncc_c"])["flags"])


def test_a_concession_never_makes_tuition_negative():
    r = fees.calculate_fee("bcom", percent=98, concessions=["orphan", "staff_child"])   # 60,000 tuition
    for year in r["schedule"]:
        for sem in year["semesters"]:
            tuition = _num(next(i["amount"] for i in sem["items"] if i["key"] == "tuition"))
            deduction = sum(-_num(i["amount"]) for i in sem["items"] if i["key"] == "concession")
            assert deduction <= tuition


def test_schedule_assumptions_are_configurable(monkeypatch):
    data = copy.deepcopy(fees.load_data())
    data["schedule"]["other_fee_every_year"] = False
    data["schedule"]["scholarship_continues_every_year"] = False
    monkeypatch.setattr(fees, "load_data", lambda: data)
    r = fees.calculate_fee("btech_cse", percent=98)
    y2 = r["schedule"][1]
    assert y2["annual_tuition"] == "₹3,49,000"                                   # scholarship not continued
    assert "other_fee" not in {i["key"] for i in y2["semesters"][0]["items"]}


def test_every_consumer_uses_the_same_engine():
    from app.services.card_service import BTECH_CSE_SEMESTER_FEE_CARD
    from app.sru_agent import fee_flow, fee_plan, responses
    std = fees.calculate_fee("btech_cse")
    card = {i["category"]: i["amount"] for i in BTECH_CSE_SEMESTER_FEE_CARD["items"]}
    assert card["Semester 1 payable"] == std["sem1_total_payable"]
    detailed = fee_flow.build_detailed_fee_card({"key": "btech_cse"}, fee_flow.SCHOOLS_DATA[0], "2027-28")
    assert detailed["formatted_first_year_total"] == std["first_year_total_payable"]
    chart = fee_plan.full_fee_chart("btech_cse", {"percent": 95})
    assert (chart["sem1_total"], chart["sem2_total"], chart["first_year_total"]) == ("₹1,44,000", "₹1,19,000", "₹2,63,000")
    assert std["sem1_total_payable"] in responses._BTECH_CSE_FEE_TEXT
    cfg = next(p for p in fees.fee_config()["programs"] if p["id"] == "btech_cse")
    assert next(s for s in cfg["slabs"] if s["scholarship_percent"] == 30)["first_year_total"] == 263000
