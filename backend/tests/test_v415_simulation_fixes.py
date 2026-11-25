"""v4.15.0: what the 2,000-student simulation found, fixed and kept fixed.

Each test is one real failure from the simulation (e2e/student_simulation_2000.py), at the level of the code that
answers it: the fee steps (fee_intake), the fee evaluation (fee_journey), the concessions (fee_plan), the dialogue
manager, the typo reader and the durable conversation state (memory).
"""
import re
import asyncio

import pytest

from app.sru_agent import agent, dialogue, fee_intake, fee_journey, fee_plan, memory

MARKS_STEP = {"counsellor_mode": True, "program": "btech_cse", "waiting_for": "marks", "turns": 3,
              "board": "state_board", "board_key": "ts_state_board", "academic_stage": "completed",
              "asked": ["board", "stage"]}


# ------------------------------------------------------------------ the fee steps
@pytest.mark.parametrize("answer,key", [("telangana", "ts_state_board"), ("TS", "ts_state_board"),
                                        ("ap pls", "ap_state_board"), ("andhra pradesh borad", "ap_state_board"),
                                        ("from telangana", "ts_state_board")])
def test_short_board_answers(answer, key):
    assert fee_intake.parse_details(answer).get("board_key") == key


@pytest.mark.parametrize("answer", ["inter aipoyindi", "pass ho gaya", "khatam ho gaya", "done with inter",
                                    "Completed Intermediate / Class 12 (passed out)"])
def test_completed_stage_in_any_wording(answer):
    assert fee_intake.parse_details(answer).get("academic_stage") == "completed"


def test_class_12_still_studying_is_second_year():
    assert fee_intake.parse_details("Studying Intermediate 2nd Year (Class 12)").get("academic_stage") == "2nd_year"


@pytest.mark.parametrize("answer,problem", [("1200 out of 1000", "more than the maximum"), ("-5", "negative"),
                                            ("abc", "as a number"), ("150%", "can't be more than 100"),
                                            ("20", "too low"), ("I don't know", "approximate")])
def test_impossible_marks_are_not_used_and_asked_again(answer, problem):
    r = fee_intake.decide(answer, {}, dict(MARKS_STEP))
    assert r["action"] == "ask" and problem in r["text"]
    assert r["state"].get("percent") is None and "Step 3 of 4" in r["text"]


@pytest.mark.parametrize("answer,pct", [("92%", 92.0), ("87", 87.0), ("870", 87.0), ("naaku 985 vachayi", 98.5),
                                        ("mere 870 marks hai", 87.0), ("866%", 86.6)])
def test_marks_at_a_1000_step(answer, pct):
    assert fee_intake.decide(answer, {}, dict(MARKS_STEP))["state"]["percent"] == pct


def test_degree_named_in_the_mba_flow_is_the_qualifying_degree():
    intake = {"counsellor_mode": True, "program": "mba", "waiting_for": "degree_percent", "turns": 1}
    r = fee_intake.decide("I did BCom", {}, intake)
    assert r["state"]["program"] == "mba" and "Noted, your degree is **BCom**" in r["text"]
    assert fee_intake.decide("72 percent", {}, r["state"])["args"] == {"program": "mba", "percent": 72.0}


def test_how_much_do_i_pay_is_a_fee_question():
    assert fee_intake.is_fee_enquiry("yo how much do i pay for ai and robotics")
    assert not fee_intake.is_fee_enquiry("how do I pay the fee")


def test_after_the_estimate_a_programme_named_elsewhere_is_not_an_answer():
    done = {"counsellor_mode": True, "program": "btech_cse", "waiting_for": "done", "turns": 1}
    assert fee_intake.decide("What are the placements for B.Tech CSE?", {"percent": 80}, done) is None


# ------------------------------------------------------------------ the fee evaluation
EVAL = {"active": True, "origin": "eligibility", "program": "btech_cse", "concession": None,
        "concession_decided": False, "proof": None, "scholarship": "yes", "hostel": None, "transport": None,
        "awaiting": "concession", "asked_text": "Before we finalise", "final_shown": False}


def test_a_marks_correction_is_not_read_as_no_to_the_open_step():
    r = fee_journey.decide("no my marks are 671 out of 1000", dict(EVAL), {"percent": 67.1},
                           {"last_reply": "x Before we finalise y", "marks_corrected": True})
    assert "**15%**" in r["text"] and "**B.Tech CSE**" in r["text"]
    assert r["state"]["concession_decided"] is False            # the concession question is asked again


@pytest.mark.parametrize("answer", ["none", "nothing", "ledu", "None of these apply"])
def test_no_concession_in_any_wording(answer):
    r = fee_journey.decide(answer, dict(EVAL), {"percent": 80}, {"last_reply": "x Before we finalise y"})
    assert re.match(r"(No problem, no special concession then|Okay, no special concession|Got it, we'll skip the special concessions)", r["text"])


def test_programme_change_in_the_middle_keeps_the_evaluation():
    st = {**EVAL, "concession_decided": True, "hostel": "none", "transport": False, "final_shown": True,
          "awaiting": None}
    r = fee_journey.decide("actually I want ece", st, {"percent": 90, "board": "state_board"}, {})
    assert r["state"]["program"] == "btech_ece" and "**B.Tech ECE**" in r["text"]


def test_pay_question_from_a_new_student_starts_the_evaluation_not_the_final_card():
    assert fee_journey.decide("how much will I pay for cse", None, {}, {"evaluate_first": True}) is None


# ------------------------------------------------------------------ concessions, programmes, typos
def test_a_group_with_several_categories_lists_them_all():
    labels = [c["label"] for c in fee_plan.concessions_for_group("is there any concession for girls?")]
    assert labels == ["Only girl child from Telangana", "Girl Child from Outside Telangana"]
    assert len(fee_plan.concessions_for_group("sports quota available?")) == 2
    assert fee_plan.concessions_for_group("any fee concession for single parent?") == []


def test_programme_overview_comes_from_the_fee_policy():
    text = dialogue.program_overview("btech_cse")
    assert "₹3,40,000 a year" in text and "4 years" in text and "55%" in text
    assert "qualifying-degree percentage" in dialogue.program_overview("mba")


def test_can_i_join_offers_both_kinds_of_help():
    r = dialogue.decide("Can I join SRU?", {}, {})
    assert r["text"].startswith("Yes, you can!") and "How do I apply?" in r["chips"]


@pytest.mark.parametrize("typed,meant", [("hostal fees?", "hostel fees?"), ("fess for cse", "fees for cse"),
                                         ("placment record", "placement record"), ("admision process",
                                                                                   "admission process")])
def test_typos_are_read_as_the_word_meant(typed, meant):
    assert agent._fix_typos(typed) == meant


def test_seats_and_vernacular_counsellor_requests():
    from app.sru_agent import intents
    assert agent._SEATS_Q.search("how many seats in cse?")
    assert intents.is_connect_request("counsellor tho matladali")
    assert intents.is_connect_request("mujhe counsellor se baat karni hai")


# ------------------------------------------------------------------ durable state: the latest state wins
@pytest.mark.asyncio
async def test_state_writes_are_serialised_and_the_last_one_wins():
    saved = []

    async def slow_saver(sid, conv, state):
        await asyncio.sleep(0.01)
        saved.append(state["step"])

    before = (memory._state_loader, memory._state_saver)
    memory.set_state_store(None, slow_saver)
    try:
        for i in range(5):
            await memory.update_conversation_state("v415-order-session", "c0nv-1", step=i)
        await memory.flush_state_writes()
    finally:
        memory.set_state_store(*before)
    assert saved[-1] == 4 and saved == sorted(saved)
