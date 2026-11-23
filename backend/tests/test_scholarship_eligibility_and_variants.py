"""Tests for the Scholarship Flow Sequence, <50% Eligibility Gate, and Positive Marks Variants.

Verifies:
1. When user requests scholarship calculation ("Calculate my scholarship"), flow starts directly at Step 1: Board.
2. When student enters marks below 50% (percentage or raw marks out of 1000/470), agent immediately returns
   an ineligible rejection message with NO fee details or fee cards.
3. When student enters marks >= 50%, agent returns encouraging positive acknowledgment variants based on score tier
   (Outstanding >= 90%, Excellent 80-89%, Good 70-79%, Qualified 50-69%).
4. format_counsellor_assessment rejects scores < 50% and includes positive acknowledgment for scores >= 50%.
5. _done() event includes profile dictionary for frontend synchronization.
"""
import pytest
from app.sru_agent import agent, fee_intake, fees


def test_scholarship_query_starts_with_board():
    """Asking 'Calculate my scholarship' without specifying a course starts at Step 1: Schooling / Board."""
    res = fee_intake.decide("Calculate my scholarship", profile={}, intake={})
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "board"
    assert res["state"]["counsellor_mode"] is True
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_board_selection"
    assert "Where did you complete your schooling / Intermediate education?" in res["text"]


def test_scholarship_below_50_percent_rejected():
    """Entering 42% Intermediate marks triggers ineligible response with NO fee details."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "marks",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "is_projected": False,
    }
    res = fee_intake.decide("42%", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ineligible"
    assert res["cards"] == []
    assert "do not currently meet the general eligibility criteria" in res["text"]
    assert "below **50%**" in res["text"]
    assert "₹" not in res["text"]  # no fee or scholarship details
    assert res["state"]["waiting_for"] is None


def test_scholarship_below_50_raw_marks_out_of_1000_rejected():
    """Entering 450 out of 1000 (45%) triggers ineligible response with NO fee details."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "marks",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "is_projected": False,
    }
    res = fee_intake.decide("450 out of 1000", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ineligible"
    assert res["cards"] == []
    assert "do not currently meet the general eligibility criteria" in res["text"]
    assert "450 marks out of 1000" in res["text"] and "**45%**" in res["text"]
    assert "₹" not in res["text"]
    assert res["state"]["waiting_for"] is None


def test_scholarship_below_50_first_year_marks_rejected():
    """Entering 200 out of 470 (42.55%) in 1st year triggers ineligible response."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "marks",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "1st_year",
        "stage_label": "Intermediate 1st Year (11th)",
        "is_projected": True,
    }
    res = fee_intake.decide("200 out of 470", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ineligible"
    assert res["cards"] == []
    assert "do not currently meet the general eligibility criteria" in res["text"]
    assert res["state"]["waiting_for"] is None


def test_outstanding_marks_acknowledgment_variants():
    """Scores >= 90% receive outstanding acknowledgment variants praising performance and top-tier scholarship."""
    v0 = fee_intake.get_marks_acknowledgment("**94.5%**", 94.5, variant_idx=0)
    v1 = fee_intake.get_marks_acknowledgment("**94.5%**", 94.5, variant_idx=1)
    v2 = fee_intake.get_marks_acknowledgment("**94.5%**", 94.5, variant_idx=2)

    assert "Outstanding" in v0 or "Sensational" in v0 or "Brilliant" in v0 or "Exceptional" in v0
    # The compliment is about the marks; admission eligibility is stated separately per programme
    assert "eligible" not in v0.lower()
    assert "merit scholarship" in v0.lower() or "fee waiver" in v0.lower()
    assert v0 != v1 or v1 != v2


def test_excellent_marks_acknowledgment_variants():
    """Scores 80-89% receive great/excellent acknowledgment variants."""
    v = fee_intake.get_marks_acknowledgment("85%", 85.0, variant_idx=0)
    assert "eligible" not in v.lower()
    assert "merit scholarship" in v.lower() or "scholarship reduction" in v.lower()


def test_good_marks_acknowledgment_variants():
    """Scores 70-79% receive good marks acknowledgment variants."""
    v = fee_intake.get_marks_acknowledgment("74%", 74.0, variant_idx=0)
    assert "eligible" not in v.lower()
    assert "scholarship" in v.lower()


def test_qualifying_marks_acknowledgment_variants():
    """Scores below 60% (no merit slab) are only acknowledged: the compliment never claims admission
    eligibility, which depends on the programme (58% is disputed for B.Tech, fine for BBA)."""
    v = fee_intake.get_marks_acknowledgment("58%", 58.0, variant_idx=0)
    assert "**58%**" in v
    assert "eligible" not in v.lower() and "scholarship" not in v.lower()


def test_format_counsellor_assessment_rejects_under_50():
    """format_counsellor_assessment with score < 50% returns rejection text without fee details."""
    fee_res = fees.calculate_fee("btech_cse", percent=45.0, board="state_board")
    details = {
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "raw_marks": 450,
        "max_marks": 1000,
        "percent": 45.0,
        "is_projected": False,
        "admission_route": "not_decided",
        "program": "btech_cse",
    }
    text = agent.format_counsellor_assessment(fee_res, details)
    assert "do not currently meet the general eligibility criteria" in text
    assert "below the official **50% minimum**" in text and "450 marks out of 1000" in text
    assert "Your Fee Details" not in text
    assert "Original Tuition Fee" not in text


def test_format_counsellor_assessment_includes_positive_variant_for_good_marks():
    """format_counsellor_assessment with score >= 90% includes positive praise banner."""
    fee_res = fees.calculate_fee("btech_cse", percent=95.0, board="state_board")
    details = {
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "raw_marks": 950,
        "max_marks": 1000,
        "percent": 95.0,
        "is_projected": False,
        "admission_route": "not_decided",
        "program": "btech_cse",
    }
    text = agent.format_counsellor_assessment(fee_res, details)
    assert "### Your Scholarship Assessment" in text
    assert "### Your Fee Details" in text
    assert "Outstanding" in text or "Sensational" in text or "Brilliant" in text or "Exceptional" in text


def test_done_helper_includes_profile():
    """_done() emits profile dictionary when passed."""
    prof = {"name": "Mahesh", "phone": "9876543210"}
    ev = agent._done("conv-123", "Test reply", profile=prof)
    assert ev["type"] == "done"
    assert ev["profile"] == prof


def test_done_helper_eligible_flag_handling():
    """_done() sets eligible flag explicitly or infers from calculate_fee card."""
    # Explicit False
    ev_false = agent._done("conv-1", "Not eligible", eligible=False)
    assert ev_false.get("eligible") is False

    # Explicit True
    ev_true = agent._done("conv-2", "Eligible for scholarship", eligible=True)
    assert ev_true.get("eligible") is True

    # Inferred True only from a personal assessment (a fee card that used the student's own score)
    personal = {"status": "ok", "scores_considered": [{"score": "Intermediate 85%", "scholarship_percent": 25}],
                "admission_eligibility": {"status": "meets_minimum", "eligible": True}}
    ev_inferred = agent._done("conv-3", "Fee calculated", cards=[{"type": "calculate_fee", "data": personal}])
    assert ev_inferred.get("eligible") is True

    # Marks that are disputed between sources: no confetti
    disputed = {**personal, "admission_eligibility": {"status": "needs_confirmation", "eligible": None}}
    assert "eligible" not in agent._done("conv-3c", "x", cards=[{"type": "calculate_fee", "data": disputed}])

    # A plain programme fee ("CSE fee", no marks) is not an eligibility result: no confetti
    ev_plain = agent._done("conv-3b", "CSE fee", cards=[{"type": "calculate_fee", "data": {"status": "ok", "scores_considered": []}}])
    assert "eligible" not in ev_plain

    # General chat without fee card does not set eligible: True
    ev_general = agent._done("conv-4", "Hello there")
    assert "eligible" not in ev_general

