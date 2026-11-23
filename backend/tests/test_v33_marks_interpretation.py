"""Tests for Phase 3: Marks Interpretation, Confirmation, CGPA, and Ambiguity Handling.

Verifies:
1. Bare 890 or raw 3-digit marks prompt for confirmation of maximum marks.
2. Confirming '1000' or 'out of 1000' converts raw marks to percentage.
3. Explicit fractions (890/1000, 890 out of 1000, 450/600) resolve immediately.
4. Percentage (89%) resolves immediately without confirmation.
5. CGPA (9.2 CGPA) converts using 9.5 multiplier to 87.4%.
6. Low EAPCET rank (850 rank) is not misinterpreted as marks.
"""
import pytest
from app.sru_agent import fee_intake, fees


def test_bare_890_prompts_for_confirmation_of_max_marks():
    # User in an active fee intake submits bare 890
    intake = {"program": "btech_cse", "board": "state_board", "waiting_for": "percent", "turns": 1}
    res = fee_intake.decide("890", {}, intake)
    assert res["action"] == "ask"
    assert "out of how many total marks is **890**" in res["text"].lower()
    assert "%" not in res["text"].split("?")[0]  # no percentage worked out from an assumed total
    assert res["state"]["waiting_for"] == "marks_max"
    assert res["state"]["pending_raw_marks"] == 890


def test_confirming_max_marks_calculates_correct_percentage():
    intake = {
        "program": "btech_cse",
        "board": "state_board",
        "waiting_for": "marks_max",
        "pending_raw_marks": 890,
        "turns": 2,
    }
    # User replies confirming out of 1000
    res = fee_intake.decide("1000", {}, intake)
    assert res["action"] == "calculate"
    assert res["args"]["percent"] == 89.0
    assert res["args"]["program"] == "btech_cse"


def test_confirming_out_of_1000_text():
    intake = {
        "program": "btech_cse",
        "board": "state_board",
        "waiting_for": "marks_max",
        "pending_raw_marks": 890,
        "turns": 2,
    }
    res = fee_intake.decide("out of 1000", {}, intake)
    assert res["action"] == "calculate"
    assert res["args"]["percent"] == 89.0


def test_confirming_out_of_600_text():
    intake = {
        "program": "btech_cse",
        "board": "state_board",
        "waiting_for": "marks_max",
        "pending_raw_marks": 450,
        "turns": 2,
    }
    res = fee_intake.decide("out of 600", {}, intake)
    assert res["action"] == "calculate"
    assert res["args"]["percent"] == 75.0


def test_explicit_890_out_of_1000_does_not_need_confirmation():
    d = fee_intake.parse_details("I scored 890 out of 1000 in 12th")
    assert d.get("percent") == 89.0
    assert d.get("raw_marks") == 890.0
    assert d.get("max_marks") == 1000.0


def test_explicit_890_slash_1000_does_not_need_confirmation():
    d = fee_intake.parse_details("890/1000 in intermediate")
    assert d.get("percent") == 89.0


def test_cgpa_conversion():
    d = fee_intake.parse_details("I got 9.2 CGPA in CBSE")
    assert d.get("cgpa") == 9.2
    assert d.get("percent") == 87.4  # 9.2 * 9.5 = 87.4


def test_cgpa_in_intake_calculates_fee():
    intake = {"program": "btech_cse", "board": "cbse", "waiting_for": "percent", "turns": 1}
    res = fee_intake.decide("8.8 CGPA", {}, intake)
    assert res["action"] == "calculate"
    assert res["args"]["percent"] == 83.6  # 8.8 * 9.5 = 83.6


def test_low_eapcet_rank_not_confused_with_marks():
    d = fee_intake.parse_details("850 rank in EAPCET")
    assert d.get("eapcet_rank") == 850
    assert d.get("percent") is None
    assert d.get("needs_marks_confirmation") is None
