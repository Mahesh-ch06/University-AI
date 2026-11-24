"""Tests for strict program level scoping (UG vs PG) and multi-step fee affordability engine."""

import pytest
from app.services.card_service import build_fee_scholarship_form_card
from app.sru_agent import affordability, fee_flow


def test_build_fee_scholarship_form_card_ug_scoping():
    card = build_fee_scholarship_form_card(level="ug")
    assert card["level"] == "ug"
    prog_keys = [p["key"] for p in card["programs"]]
    assert "btech_cse" in prog_keys
    assert "bba" in prog_keys
    assert "bca" in prog_keys
    # No PG programs in UG form
    assert "mba" not in prog_keys
    assert "mca" not in prog_keys
    assert "mtech" not in prog_keys


def test_build_fee_scholarship_form_card_pg_scoping():
    card = build_fee_scholarship_form_card(level="pg")
    assert card["level"] == "pg"
    prog_keys = [p["key"] for p in card["programs"]]
    assert "mba" in prog_keys
    assert "mca" in prog_keys
    assert "mtech" in prog_keys
    # No UG programs in PG form
    assert "btech_cse" not in prog_keys
    assert "bba" not in prog_keys
    assert "bsc_agri" not in prog_keys


def test_build_fee_scholarship_form_card_only_selected():
    card = build_fee_scholarship_form_card(selected_program="btech_cse", only_selected=True)
    assert card["only_selected"] is True
    assert len(card["programs"]) == 1
    assert card["programs"][0]["key"] == "btech_cse"


def test_build_course_selection_card_level_scoping():
    school = fee_flow.SCHOOLS_DATA[0]  # School of CS & AI (has B.Tech and MCA/M.Tech)
    card_ug = fee_flow.build_course_selection_card(school, level="ug")
    assert len(card_ug["programs_ug"]) > 0
    assert len(card_ug["programs_pg"]) == 0

    card_pg = fee_flow.build_course_selection_card(school, level="pg")
    assert len(card_pg["programs_ug"]) == 0
    assert len(card_pg["programs_pg"]) > 0


def test_is_affordability_query():
    assert affordability.is_affordability_query("i can't afford that much fee")
    assert affordability.is_affordability_query("i cant afford this much fee")
    assert affordability.is_affordability_query("i can't effecot that much fee")
    assert affordability.is_affordability_query("fees are too high for middle class family")
    assert affordability.is_affordability_query("too expensive for my family, any discount?")
    assert affordability.is_affordability_query("we have financial problems")
    assert not affordability.is_affordability_query("What is the hostel fee?")
    assert not affordability.is_affordability_query("Tell me about B.Tech CSE placements")


def test_affordability_multi_step_flow_turn_by_turn():
    profile = {"name": "Mahesh"}
    conv_state = {}

    # Turn 1: Student mentions affordability concern without course/marks
    res1 = affordability.process_affordability_flow("i can't afford that much fee", profile, conv_state)
    assert res1 is not None
    assert "Mahesh" in res1["text"]
    assert "I will be asking you some questions, answer them, and at last I will let you know your final net fee after all concessions and deductions." in res1["text"]
    assert "Step 1 of 2: Academic Programme & Marks" in res1["text"]
    assert res1["new_state"]["affordability_flow"]["step"] == "awaiting_academics"
    assert len(res1["cards"]) == 1
    assert res1["cards"][0]["type"] == "counsellor_program_selection"   # v4.13.0: step card, not the old form

    # Turn 2: Student enters Course and Marks
    state2 = res1["new_state"]
    res2 = affordability.process_affordability_flow("B.Tech CSE with 90% marks in Telangana State Board", profile, state2)
    assert res2 is not None
    assert "Step 2 of 2: Special-Category Concessions" in res2["text"]
    assert "25% Merit Scholarship" in res2["text"]
    assert res2["new_state"]["affordability_flow"]["step"] == "awaiting_concession"
    assert any("Single parent" in c for c in res2["suggestions"])

    # Turn 3: Student claims Special Concession (Single Parent)
    state3 = res2["new_state"]
    res3 = affordability.process_affordability_flow("Single parent / Divorced", profile, state3)
    assert res3 is not None
    assert "final net fee breakdown after all considered deductions" in res3["text"].lower()
    assert "Single living parent / Divorced mother" in res3["text"]
    assert "₹15,000" in res3["text"]
    # Standard tuition: ₹3,40,000. 25% scholarship = ₹85,000.
    # Tuition after merit: ₹2,55,000. Special concession: ₹15,000.
    # Final net annual tuition: ₹2,40,000.
    # Net semester tuition: ₹1,20,000.
    assert "₹2,40,000" in res3["text"]
    assert "₹1,20,000" in res3["text"]
    assert "State Bank of India (SBI)" in res3["text"]
    assert "Union Bank of India" in res3["text"]
    assert len(res3["cards"]) == 1
    assert res3["cards"][0]["type"] == "calculate_fee"
    assert res3["new_state"]["affordability_flow"] is None


def test_affordability_flow_direct_jump_when_already_known():
    profile = {"name": "Priya", "twelfth_percent": 95}
    conv_state = {"fee_flow_prog": "btech_cse"}

    # Course and marks are already known from earlier conversation
    res = affordability.process_affordability_flow("fees are too high, can't pay this much", profile, conv_state)
    assert res is not None
    assert "Priya" in res["text"]
    assert "I will be asking you some questions" in res["text"]
    # Should jump directly to Step 2 (Special Concessions) without asking Step 1
    assert "Step 2: Special-Category Concessions" in res["text"]
    assert "30% Merit Scholarship" in res["text"]
    assert res["new_state"]["affordability_flow"]["step"] == "awaiting_concession"
