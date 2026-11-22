"""Tests for the Enhanced SRU Buddy Scholarship & Fee Counselling Workflow.

Verifies:
1. Entry trigger and opening message on scholarship inquiries.
2. Step 1: Academic board selection card and natural acknowledgment.
3. Step 2: Academic stage branching:
   - Branch A: Intermediate 1st Year (max marks 470 for TS/AP, projected)
   - Branch B: Intermediate 2nd Year (preliminary assessment, max 470, projected)
   - Branch C: Completed Intermediate (actual final score, max 1000, not projected)
4. Step 3: Admission route selection (TG EAPCET, AP EAPCET, JEE Main, SRSAT, Not decided yet).
5. Step 4: Optional / skippable entrance score collection.
6. Step 5: B.Tech programme selection.
7. Step 6: Final structured counsellor assessment and fee details presentation.
8. Anti-repetition rule: Never re-asking for information already collected.
9. Re-query handling: Reusing existing details with "Thanks! I already have your academic details."
10. Single-shot query completion without redundant questions.
"""
import pytest
from app.sru_agent import agent, fee_intake, fees


def test_counsellor_entry_on_scholarship_query():
    """Asking about scholarships triggers guided counselling with opening message and Board card."""
    res = fee_intake.decide("Tell me about scholarships for B.Tech", profile={}, intake={})
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "board"
    assert res["state"]["counsellor_mode"] is True
    assert "Absolutely! I can help you understand your potential scholarship" in res["text"]
    assert "I'll guide you through a few quick questions" in res["text"]
    assert "Where did you complete your schooling / Intermediate education?" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_board_selection"
    assert len(res["chips"]) >= 5
    assert any("TSBIE" in chip for chip in res["chips"])
    assert any("CBSE" in chip for chip in res["chips"])


def test_counsellor_step1_board_selection_advances_to_stage():
    """Selecting board records board and presents Academic Stage card with natural acknowledgment."""
    intake = {"counsellor_mode": True, "waiting_for": "board"}
    res = fee_intake.decide("Telangana Intermediate (TSBIE)", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "stage"
    assert res["state"]["board"] == "state_board"
    assert res["state"]["board_key"] == "ts_state_board"
    assert "Great! You've selected Telangana Intermediate (TSBIE)" in res["text"]
    assert "Which year are you currently studying in?" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_stage_selection"
    assert any("1st Year" in chip for chip in res["chips"])
    assert any("2nd Year" in chip for chip in res["chips"])
    assert any("Completed" in chip for chip in res["chips"])


def test_counsellor_stage_branching_1st_year():
    """Branch A: 1st Year asks for 1st-year marks out of 470 for TS Intermediate."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "stage",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
    }
    res = fee_intake.decide("Intermediate 1st Year (11th)", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "marks"
    assert res["state"]["academic_stage"] == "1st_year"
    assert res["state"]["is_projected"] is True
    assert "studying Intermediate 1st Year under Telangana Intermediate (TSBIE)" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_marks_input"
    assert res["cards"][0]["max_marks"] == 470


def test_counsellor_stage_branching_2nd_year():
    """Branch B: 2nd Year asks for completed 1st-year marks for preliminary assessment (max 470)."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "stage",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
    }
    res = fee_intake.decide("Intermediate 2nd Year (12th)", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "marks"
    assert res["state"]["academic_stage"] == "2nd_year"
    assert res["state"]["is_projected"] is True
    assert "preliminary assessment" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_marks_input"
    assert res["cards"][0]["max_marks"] == 470


def test_counsellor_stage_branching_completed():
    """Branch C: Completed Intermediate asks for actual final score out of 1000."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "stage",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
    }
    res = fee_intake.decide("Completed Intermediate (Passed out)", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "marks"
    assert res["state"]["academic_stage"] == "completed"
    assert res["state"]["is_projected"] is False
    assert "actual final examination marks" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_marks_input"
    assert res["cards"][0]["max_marks"] == 1000


def test_counsellor_step3_marks_input_advances_to_route():
    """Entering 1st year marks (430 out of 470) calculates percent (91.49%) and asks Admission Route."""
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
    res = fee_intake.decide("430 out of 470", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "route"
    assert res["state"]["raw_marks"] == 430
    assert res["state"]["max_marks"] == 470
    assert res["state"]["percent"] == 91.49
    assert "Which admission route are you planning to use for B.Tech?" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "counsellor_route_selection"
    assert any("TG EAPCET" in chip for chip in res["chips"])
    assert any("JEE Main" in chip for chip in res["chips"])
    assert any("Not decided" in chip for chip in res["chips"])


def test_counsellor_step4_and_5_flow_to_calculation():
    """Route selection -> optional rank -> program -> calculate action."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "route",
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "1st_year",
        "stage_label": "Intermediate 1st Year (11th)",
        "raw_marks": 430,
        "max_marks": 470,
        "percent": 91.49,
        "is_projected": True,
    }
    r_route = fee_intake.decide("TG EAPCET", profile={}, intake=intake)
    assert r_route is not None
    assert r_route["action"] == "ask"
    assert r_route["state"]["waiting_for"] == "rank"
    assert "TG EAPCET rank" in r_route["text"]

    r_rank = fee_intake.decide("15000", profile={}, intake=r_route["state"])
    assert r_rank is not None
    assert r_rank["action"] == "ask"
    assert r_rank["state"]["waiting_for"] == "program"
    assert r_rank["state"]["eapcet_rank"] == 15000
    assert len(r_rank["cards"]) == 1
    assert r_rank["cards"][0]["type"] == "counsellor_program_selection"

    r_prog = fee_intake.decide("B.Tech CSE", profile={}, intake=r_rank["state"])
    assert r_prog is not None
    assert r_prog["action"] == "calculate"
    assert r_prog["counsellor"] is True
    assert r_prog["args"]["program"] == "btech_cse"
    assert r_prog["args"]["percent"] == 91.49
    assert r_prog["args"]["eapcet_rank"] == 15000
    assert r_prog["counsellor_details"]["is_projected"] is True


def test_counsellor_result_formatting_projected_vs_completed():
    """Verify format_counsellor_assessment creates proper structure with projected note distinction."""
    fee_res = fees.calculate_fee("btech_cse", percent=91.49, board="state_board", eapcet_rank=15000)

    proj_details = {
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "1st_year",
        "stage_label": "Intermediate 1st Year (11th)",
        "raw_marks": 430,
        "max_marks": 470,
        "percent": 91.49,
        "is_projected": True,
        "admission_route": "tg_eapcet",
        "route_label": "TG EAPCET",
        "eapcet_rank": 15000,
        "program": "btech_cse",
    }
    proj_text = agent.format_counsellor_assessment(fee_res, proj_details)
    assert "### Your Scholarship Assessment" in proj_text
    assert "• **Academic Qualification**: Telangana Intermediate (TSBIE) (Intermediate 1st Year (11th))" in proj_text
    assert "• **Academic Score**: 430/470 (91.49%)" in proj_text
    assert "• **Admission Route**: TG EAPCET (Rank: 15,000)" in proj_text
    assert "### Your Fee Details" in proj_text
    assert "• **Original Tuition Fee**: ₹3,40,000 per year" in proj_text
    assert "Tuition Waiver" in proj_text
    assert "• **Remaining Annual Tuition**: " in proj_text
    assert "• **First Semester Payable**: " in proj_text
    assert "Preliminary Projection" in proj_text

    compl_details = {
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "raw_marks": 920,
        "max_marks": 1000,
        "percent": 92.0,
        "is_projected": False,
        "admission_route": "not_decided",
        "route_label": "Not decided yet",
        "program": "btech_cse",
    }
    compl_text = agent.format_counsellor_assessment(fee_res, compl_details)
    assert "### Your Scholarship Assessment" in compl_text
    assert "Preliminary Projection" not in compl_text


def test_counsellor_anti_repetition_rule():
    """Information already in profile/state is never asked for again."""
    profile = {
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "percent": 93.0,
        "raw_marks": 930,
        "max_marks": 1000,
        "admission_route": "tg_eapcet",
        "route_label": "TG EAPCET",
        "eapcet_rank": 12000,
        "program": "btech_cse",
    }
    res = fee_intake.decide("What is my scholarship?", profile=profile, intake={})
    assert res is not None
    assert res["action"] == "calculate"
    assert res["counsellor"] is True
    assert res["args"]["program"] == "btech_cse"
    assert res["args"]["percent"] == 93.0
    assert "cards" not in res or not res.get("cards")


def test_counsellor_re_query_handling():
    """Re-querying after completing counselling emits 'Thanks! I already have your academic details.'"""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "done",
        "turns": 4,
        "board": "state_board",
        "board_key": "ts_state_board",
        "board_label": "Telangana Intermediate (TSBIE)",
        "academic_stage": "2nd_year",
        "stage_label": "Intermediate 2nd Year (12th)",
        "raw_marks": 440,
        "max_marks": 470,
        "percent": 93.62,
        "is_projected": True,
        "admission_route": "not_decided",
        "program": "btech_cse",
    }
    res = fee_intake.decide("Calculate my scholarship again", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "calculate"
    assert res["counsellor"] is True
    assert res["counsellor_details"]["re_query"] is True

    fee_res = fees.calculate_fee("btech_cse", percent=93.62, board="state_board")
    output_text = agent.format_counsellor_assessment(fee_res, res["counsellor_details"])
    assert "Thanks! I already have your academic details. Let's continue with your scholarship assessment." in output_text


def test_counsellor_program_already_known_skips_program_step():
    """If user specifies 'What is the scholarship for B.Tech CSE?' programme is remembered and skipped."""
    r1 = fee_intake.decide("What is the scholarship for B.Tech CSE?", profile={}, intake={})
    assert r1 is not None
    assert r1["state"]["program"] == "btech_cse"
    assert r1["state"]["waiting_for"] == "board"

    r2 = fee_intake.decide("CBSE", profile={}, intake=r1["state"])
    assert r2["state"]["waiting_for"] == "stage"

    r3 = fee_intake.decide("Completed Intermediate (Passed out)", profile={}, intake=r2["state"])
    assert r3["state"]["waiting_for"] == "marks"

    r4 = fee_intake.decide("92%", profile={}, intake=r3["state"])
    assert r4["state"]["waiting_for"] == "route"

    r5 = fee_intake.decide("Not decided yet", profile={}, intake=r4["state"])
    assert r5 is not None
    assert r5["action"] == "calculate"
    assert r5["args"]["program"] == "btech_cse"
    assert r5["args"]["percent"] == 92.0
