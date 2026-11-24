"""v4.13.0: the fee flow from a real production chat (24 Nov 2026), fixed.

Reported: "any merit schorshipp" was not recognised (the scholarship flow never started); "867" got the old
consolidated "Fee & Merit Scholarship Assessment Form", whose marks field is a percentage, so the student's
Telangana Intermediate marks (out of 1000) became "867%"; "yes" to "did you mean 866 out of 1000?" went to the
AI (which was out of quota); the agentic flow (concessions -> proof -> hostel -> final fee) had to be found by
hand. Now: the step-by-step cards only, marks read with the board's total, the whole flow without an AI call.
"""
from __future__ import annotations

import uuid

import pytest

from app.sru_agent import agent, fee_intake, memory

OLD_FORM = "fee_scholarship_form"


async def _chat(messages):
    sid = f"v413f-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Arhan Reddy", phone="9876544328", welcome_actions_shown=True)
    conv, out = None, []
    for m in messages:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    return out


def _types(done):
    return [c.get("type") for c in done.get("cards") or []]


@pytest.mark.asyncio
async def test_the_reported_conversation_runs_the_whole_agentic_flow_with_the_new_cards_only():
    out = await _chat(["I want to join sru", "B.Tech", "AI & Robotics", "admission process", "any merit schorshipp",
                       "867", "Telangana State Board", "Completed", "MPC", "Students of SR Junior College",
                       "Yes, I have it", "AC 3-sharing (₹1,35,000)"])
    assert all(OLD_FORM not in _types(d) for d in out)
    scholarship, marks = out[4], out[5]
    assert "Step 1 of 4: which board" in scholarship["answer"] and "counsellor_board_selection" in _types(scholarship)
    assert "Noted: **867** marks" in marks["answer"]                    # kept, not dropped or read as a %
    result = out[8]["answer"]
    assert "**86.7%** (867/1000)" in result and "25% scholarship" in result
    assert "Before we finalise your fee" in result                      # the agentic flow continues by itself
    final = out[-1]
    assert "fee_summary" in _types(final)
    assert "₹4,60,000" in final["answer"] and "₹4,45,000" in final["answer"]


@pytest.mark.parametrize("typo", ["any merit schorshipp", "skolarship for cse", "scholership details", "scolarship?"])
def test_scholarship_typos_start_the_flow(typo):
    assert fee_intake.decide(typo, {"program_interest": "btech_cse"}, None) is not None


@pytest.mark.asyncio
async def test_percent_typo_with_the_telangana_board_known_is_read_as_marks_out_of_1000():
    out = await _chat(["Calculate my scholarship", "B.Tech AI & Robotics", "Telangana State Board", "Completed",
                       "Calculate fee for B.Tech in Artificial Intelligence & Robotics, Telangana State Board (BIE TS) "
                       "with 866% marks", "MPC"])
    assert "isn't possible" not in out[4]["answer"]
    assert "**86.6%** (866/1000)" in out[-1]["answer"]


@pytest.mark.asyncio
async def test_yes_to_did_you_mean_out_of_1000_is_handled_by_the_code():
    out = await _chat(["Calculate my scholarship", "B.Tech AI & Robotics", "I got 866%", "yes",
                       "Telangana State Board", "Completed", "MPC"])
    assert "Did you mean **866 out of 1000**" in out[2]["answer"]
    assert "**86.6%** (866/1000)" in out[-1]["answer"]


def test_old_form_is_never_returned_by_the_intake():
    for message, intake in (("what is the fee structure?", {}), ("cse fee", {}), ("890", {}),
                            ("B.Tech CSE", {"waiting_for": "program", "turns": 1})):
        r = fee_intake.decide(message, {}, intake)
        assert r is None or OLD_FORM not in [c.get("type") for c in r.get("cards") or []], message


def test_a_board_without_a_fixed_total_still_asks_out_of_how_many():
    r = fee_intake.decide("890", {}, {"program": "btech_cse", "board": "state_board", "waiting_for": "percent",
                                      "turns": 1})
    assert "out of how many total marks is **890**" in r["text"].lower()
