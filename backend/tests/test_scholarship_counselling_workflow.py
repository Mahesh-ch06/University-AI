"""Tests for the SRU Buddy Scholarship & Fee Counselling Workflow (v4.6.0: one journey, nothing re-asked).

Verifies:
1. Programme first (scholarship rules and entrance options differ by programme).
2. Two or more of board / status / marks missing -> ONE consolidated academic details form, pre-filled.
3. Exactly one missing -> only that field (existing board / status / marks card); typed answers after the form
   continue field by field instead of showing the whole form again.
4. Status branching for marks: 1st / 2nd year use 1st-year marks out of 470 (TS/AP, projected); completed uses
   the final score out of 1000.
5. Entrance score is optional: "Add my EAPCET rank" asks only that, then recalculates.
6. Final structured assessment; anti-repetition; re-query wording; single-shot completion.
"""
import pytest
from app.sru_agent import agent, fee_intake, fees


def test_counsellor_entry_asks_programme_first():
    res = fee_intake.decide("Calculate my scholarship", profile={}, intake={})
    assert res["action"] == "ask" and res["state"]["waiting_for"] == "program"
    assert res["state"]["counsellor_mode"] is True
    assert "Which programme would you like the scholarship details for?" in res["text"]
    generic = fee_intake.decide("Tell me about scholarships for B.Tech", profile={}, intake={})
    assert generic["state"]["waiting_for"] == "program"
    assert "Which B.Tech branch" in generic["text"]


def test_counsellor_nothing_known_asks_one_step_at_a_time():
    """v4.9.0: no large form. One small card per step, with "Step n of N"."""
    res = fee_intake.decide("Calculate my scholarship for B.Tech CSE", profile={}, intake={}, first_name="Mahesh")
    assert res["action"] == "ask" and res["state"]["waiting_for"] == "board"
    assert "Let's work out your scholarship for **B.Tech CSE**" in res["text"]
    assert "Step 1 of 4" in res["text"]                  # board, status, marks, group (B.Tech needs MPC)
    assert [c["type"] for c in res["cards"]] == ["counsellor_board_selection"]
    assert res["cards"][0]["step_label"] == "Step 1 of 4" and res["cards"][0]["program"] == "btech_cse"


def test_counsellor_reuses_marks_and_group_asks_only_the_missing_fields():
    """After an eligibility check (marks + MPC known), only board and status are asked, one at a time."""
    profile = {"raw_marks": 670.0, "max_marks": 1000.0, "percent": 67.0, "stream": "MPC", "program_interest": "btech_cse"}
    res = fee_intake.decide("I want to know about the scholarship for B.Tech CSE", profile=profile, intake={})
    assert res["state"]["waiting_for"] == "board"
    assert "Noted: 670/1000 (67%), MPC" in res["text"]
    nxt = fee_intake.decide("Telangana Intermediate (TSBIE)", profile=profile, intake=res["state"])
    assert nxt["state"]["waiting_for"] == "stage"
    assert [c["type"] for c in nxt["cards"]] == ["counsellor_stage_selection"]
    assert "marks" not in nxt["text"].lower()          # marks are not asked again
    done = fee_intake.decide("Completed Intermediate (Passed out)", profile=profile, intake=nxt["state"])
    assert done["action"] == "calculate" and done["args"]["percent"] == 67.0


def test_counsellor_only_board_missing_asks_board_alone():
    profile = {"raw_marks": 900.0, "max_marks": 1000.0, "percent": 90.0, "academic_stage": "completed",
               "stage_label": "Completed Intermediate (Passed out)"}
    res = fee_intake.decide("Calculate my scholarship for B.Tech CSE", profile=profile, intake={})
    assert res["state"]["waiting_for"] == "board"
    assert [c["type"] for c in res["cards"]] == ["counsellor_board_selection"]
    assert "which board did you study under?" in res["text"]


def _marks_step(stage_text):
    intake = {"counsellor_mode": True, "waiting_for": "stage", "program": "btech_cse", "board": "state_board",
              "board_key": "ts_state_board", "board_label": "Telangana Intermediate (TSBIE)"}
    return fee_intake.decide(stage_text, profile={}, intake=intake)


def test_counsellor_stage_branching_1st_year():
    res = _marks_step("Intermediate 1st Year (11th)")
    assert res["state"]["waiting_for"] == "marks" and res["state"]["academic_stage"] == "1st_year"
    assert res["state"]["is_projected"] is True
    assert "1st-year marks (out of 470)" in res["text"]
    assert res["cards"][0]["type"] == "counsellor_marks_input" and res["cards"][0]["max_marks"] == 470


def test_counsellor_stage_branching_2nd_year():
    res = _marks_step("Intermediate 2nd Year (12th)")
    assert res["state"]["academic_stage"] == "2nd_year" and res["state"]["is_projected"] is True
    assert res["cards"][0]["max_marks"] == 470


def test_counsellor_stage_branching_completed():
    res = _marks_step("Completed Intermediate (Passed out)")
    assert res["state"]["academic_stage"] == "completed" and res["state"]["is_projected"] is False
    assert "final marks (out of 1000)" in res["text"]
    assert res["cards"][0]["max_marks"] == 1000


def test_counsellor_all_known_calculates_and_entrance_is_optional():
    """Everything known -> calculate at once; an EAPCET rank can be added afterwards, reusing the rest."""
    intake = {"counsellor_mode": True, "waiting_for": "marks", "program": "btech_cse", "board": "state_board",
              "board_key": "ts_state_board", "board_label": "Telangana Intermediate (TSBIE)",
              "academic_stage": "1st_year", "stage_label": "Intermediate 1st Year (11th)", "is_projected": True,
              "stream": "MPC"}
    r = fee_intake.decide("430 out of 470", profile={}, intake=intake)
    assert r["action"] == "calculate" and r["args"]["percent"] == 91.49
    assert r["counsellor_details"]["uses_entrance"] is True
    assert r["counsellor_details"]["has_entrance_score"] is False
    add = fee_intake.decide("Add my EAPCET rank", profile={}, intake=r["state"])
    assert add["action"] == "ask" and add["state"]["waiting_for"] == "rank"
    assert "What is your TG EAPCET rank?" in add["text"]
    again = fee_intake.decide("15000", profile={}, intake=add["state"])
    assert again["action"] == "calculate"
    assert again["args"]["eapcet_rank"] == 15000 and again["args"]["percent"] == 91.49
    assert again["counsellor_details"]["has_entrance_score"] is True


def test_counsellor_non_entrance_programme_skips_route():
    """BBA has no EAPCET / JEE scholarship: no route question, straight to the result."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "program",
        "board": "cbse",
        "board_key": "cbse",
        "board_label": "CBSE",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "percent": 88.0,
        "raw_marks": 88,
        "max_marks": 100,
        "ack_shown": True,
    }
    res = fee_intake.decide("Bachelor of Business Administration (BBA)", profile={}, intake=intake)
    assert res["action"] == "calculate"
    assert res["args"]["program"] == "bba"
    assert res["args"]["percent"] == 88.0
    assert "eapcet_rank" not in res["args"] and "jee_percentile" not in res["args"]


def test_counsellor_pg_programme_asks_degree_percent_not_intermediate():
    """MBA scholarship uses the qualifying-degree %, so no board, year of study or entrance questions."""
    r1 = fee_intake.decide("Calculate my scholarship for MBA", profile={}, intake={})
    assert r1["action"] == "ask"
    assert r1["state"]["waiting_for"] == "degree_percent"
    assert "qualifying degree" in r1["text"] and "not your 12th marks" in r1["text"]
    assert r1["cards"][0]["type"] == "counsellor_marks_input"
    assert r1["cards"][0]["max_marks"] == 100

    r2 = fee_intake.decide("75%", profile={}, intake=r1["state"])
    assert r2["action"] == "calculate"
    assert r2["args"] == {"program": "mba", "percent": 75.0}
    assert r2["counsellor_details"]["level"] == "pg"

    fee_res = fees.calculate_fee("mba", percent=75.0)
    text = agent.format_counsellor_assessment(fee_res, r2["counsellor_details"])
    assert "MBA" in text and "20% scholarship" in text
    assert "Admission Route" not in text
    assert "Intermediate" not in text


def test_counsellor_pg_chosen_after_intermediate_marks_asks_degree_percent():
    """A student who gave 12th marks and then picks MBA is asked for the degree %, not scored on 12th marks."""
    intake = {
        "counsellor_mode": True,
        "waiting_for": "program",
        "board": "state_board",
        "board_key": "ap_state_board",
        "board_label": "Andhra Pradesh Intermediate (BIEAP)",
        "academic_stage": "completed",
        "stage_label": "Completed Intermediate (Passed out)",
        "raw_marks": 850,
        "max_marks": 1000,
        "percent": 85.0,
        "ack_shown": True,
    }
    res = fee_intake.decide("Master of Business Administration (MBA)", profile={}, intake=intake)
    assert res["action"] == "ask"
    assert res["state"]["waiting_for"] == "degree_percent"


def test_counsellor_pg_below_50_degree_percent_is_ineligible():
    r1 = fee_intake.decide("Calculate my scholarship for MBA", profile={}, intake={})
    res = fee_intake.decide("45%", profile={}, intake=r1["state"])
    assert res["action"] == "ineligible"
    assert "below the official **50% minimum**" in res["text"]
    assert "Master of Business Administration" in res["text"]


def test_counsellor_assessment_formatting_matches_conversation_fixes():
    """850/1000 shows as 850/1000 (not 1000.0), semester tuition in Indian format, compliment not repeated."""
    fee_res = fees.calculate_fee("btech_cse", percent=85.0, board="state_board")
    details = {
        "board_label": "Andhra Pradesh Intermediate (BIEAP)",
        "stage_label": "Completed Intermediate (Passed out)",
        "raw_marks": 850,
        "max_marks": 1000.0,
        "percent": 85.0,
        "route_label": "Not decided yet",
        "program": "btech_cse",
        "re_query": False,
        "ack_shown": True,
    }
    text = agent.format_counsellor_assessment(fee_res, details)
    # v4.9.0: short. Headline (score -> slab), one tuition line, one eligibility line; figures in the fee card.
    assert "**85%** (850/1000)" in text and "1000.0" not in text
    assert "**25% scholarship**" in text and "₹2,55,000/year" in text and "₹3,40,000" in text
    assert "Great performance" not in text and "###" not in text and "Note" not in text
    assert len(text.split()) <= 60


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
    assert "**91.49%** (430/470)" in proj_text and "scholarship" in proj_text
    assert "estimate from your Intermediate 1st Year (11th) marks" in proj_text
    assert "###" not in proj_text and len(proj_text.split()) <= 70

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
    assert "**92%** (920/1000)" in compl_text
    assert "estimate from" not in compl_text


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
        "stream": "MPC",
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
        "stream": "MPC",
    }
    # v4.9.0: asked again after an estimate -> confirm the saved details first (use them, or change them)
    res = fee_intake.decide("Calculate my scholarship again", profile={}, intake=intake)
    assert res["action"] == "ask" and res["state"]["waiting_for"] == "confirm_details"
    assert "I already have your details" in res["text"] and "440/470" in res["text"]
    assert res["chips"] == ["Use these details", "Change my details"]
    use = fee_intake.decide("Use these details", profile={}, intake=res["state"])
    assert use["action"] == "calculate" and use["counsellor"] is True and use["args"]["program"] == "btech_cse"
    change = fee_intake.decide("Change my details", profile={}, intake=res["state"])
    assert change["action"] == "ask" and change["state"]["waiting_for"] == "board"
    assert "percent" not in change["state"] and "raw_marks" in change["profile_clear"]


def test_counsellor_program_already_known_skips_program_step():
    """'What is the scholarship for B.Tech CSE?': the programme is remembered and never asked again."""
    r1 = fee_intake.decide("What is the scholarship for B.Tech CSE?", profile={}, intake={})
    assert r1["state"]["program"] == "btech_cse"
    assert r1["state"]["waiting_for"] == "board"         # one step at a time
    assert "Which programme" not in r1["text"]

    r2 = fee_intake.decide("CBSE", profile={}, intake=r1["state"])
    assert r2["state"]["waiting_for"] == "stage"

    r3 = fee_intake.decide("Completed Intermediate (Passed out)", profile={}, intake=r2["state"])
    assert r3["state"]["waiting_for"] == "marks"

    r4 = fee_intake.decide("92%", profile={}, intake=r3["state"])
    assert r4["state"]["waiting_for"] == "stream"        # B.Tech lists MPC: the group is the last step
    r4 = fee_intake.decide("MPC (Maths, Physics, Chemistry)", profile={}, intake=r4["state"])
    assert r4["action"] == "calculate"
    assert r4["args"]["program"] == "btech_cse"
    assert r4["args"]["percent"] == 92.0
    assert r4["args"]["board"] == "cbse"


def test_counsellor_bipc_student_for_btech_is_told_clearly():
    """B.Tech lists MPC. A BiPC student is told they do not meet the listed subject requirement, no fee."""
    intake = {"counsellor_mode": True, "waiting_for": "stream", "board": "state_board",
              "board_key": "ts_state_board", "board_label": "Telangana Intermediate (TSBIE)",
              "academic_stage": "completed", "raw_marks": 900, "max_marks": 1000, "percent": 90.0,
              "program": "btech_cse", "ack_shown": True}
    res = fee_intake.decide("BiPC (Biology, Physics, Chemistry)", profile={}, intake=intake)
    assert res["action"] == "ineligible"
    assert "don't meet its subject requirement" in res["text"]
    assert "₹" not in res["text"]


def test_counsellor_non_science_answer_only_read_as_stream_when_asked():
    """'commerce' is a subject answer only when we asked for subjects."""
    assert "stream" not in fee_intake.decide("B.Com fee", profile={}, intake={})["state"]
