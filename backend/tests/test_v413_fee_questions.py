"""v4.13.0: a fee question evaluates first (admin setting "fee_questions", default 'evaluate_first').

"B.Tech CSE fees" -> "Before I give you the fee, let's check your eligibility and scholarship..." -> the steps
(board, status, marks, group) -> eligibility and merit scholarship -> special concessions -> hostel -> bus ->
the final fee summary. "Just show the ... fee" gives the standard fee at once; hostel / other fees, a fee chart
and an evaluation already running are not changed. 'fee_card' shows the standard fee card at once, as before.
"""
from __future__ import annotations

import uuid

import pytest

from app.services import app_settings
from app.sru_agent import agent, memory


@pytest.fixture(autouse=True)
def evaluate_first():
    app_settings.set_for_tests(fee_questions="evaluate_first")
    yield
    app_settings.set_for_tests(fee_questions="fee_card")


async def _chat(messages, **profile):
    sid = f"v413q-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True, **profile)
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
async def test_fee_question_runs_the_whole_evaluation_to_the_final_fee():
    out = await _chat(["B.Tech CSE fees", "Telangana State Board", "Completed", "870", "MPC", "None of these apply",
                       "No hostel, I'm a day scholar", "No, I'll manage"])
    first = out[0]
    assert first["answer"].startswith("Before I give you the **B.Tech CSE** fee, let's check your eligibility")
    assert "Step 1 of 4: which board" in first["answer"] and "counsellor_board_selection" in _types(first)
    assert "Just show the B.Tech CSE fee" in first["suggestions"]
    assert "calculate_fee" not in _types(first)                         # no fee card before the evaluation
    assert "25% scholarship" in out[4]["answer"] and "Before we finalise your fee" in out[4]["answer"]
    final = out[-1]
    assert "fee_summary" in _types(final) and "₹2,80,000" in final["answer"]


@pytest.mark.asyncio
async def test_just_show_the_fee_gives_the_standard_fee_at_once():
    [done] = await _chat(["Just show the B.Tech CSE fee"])
    assert "Before I give you" not in done["answer"]
    assert "calculate_fee" in _types(done)


@pytest.mark.asyncio
@pytest.mark.parametrize("message, question", [("fees?", "Which programme are you interested in?"),
                                               ("B.Tech fee", "Which B.Tech branch are you interested in?")])
async def test_no_programme_yet_asks_it_first(message, question):
    [done] = await _chat([message])
    assert done["answer"].startswith("Before I give you the fee") and question in done["answer"]


@pytest.mark.asyncio
async def test_marks_already_known_evaluate_at_once():
    [done] = await _chat(["B.Tech CSE fees"], percent=87.0, raw_marks=870, max_marks=1000, board="state_board",
                         board_key="ts_state_board", board_label="Telangana State Board", academic_stage="completed",
                         stream="MPC")
    assert "Before I give you" not in done["answer"]
    assert "scholarship" in done["answer"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["hostel fees", "prepare my fee chart for B.Tech CSE", "B.Tech CSE fee per semester",
                                     "What will the fees be in 2029-30?"])
async def test_other_fee_topics_are_not_changed(message):
    [done] = await _chat([message])
    assert "Before I give you" not in done["answer"]


@pytest.mark.asyncio
async def test_fee_card_mode_shows_the_standard_fee_at_once():
    app_settings.set_for_tests(fee_questions="fee_card")
    [done] = await _chat(["B.Tech CSE fees"])
    assert "Before I give you" not in done["answer"]
