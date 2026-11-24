"""v4.14.0 (1,000-student test): what the student asks is what gets answered.

1. While the fee steps wait for the board / marks, another question (placements, events, food, a room fee) is
   answered, with "Continue my fee estimate"; the steps are kept and continue with the next answer.
2. "Just show the B.Tech CSE fee" ends the steps and gives the standard fee, whatever step was waiting.
3. "What scholarships does SRU give?" gets the merit scholarship slabs from the fee data (not the steps).
4. Placement questions get the verified placement answer at once; a bare "placements" still asks which aspect.
5. The same step question asked again says why; a campus topic asked again gets a short recap; specific
   questions (mess timings, a cricket ground, a swimming pool, non-veg) get their own answer.
"""
from __future__ import annotations

import re

import uuid

import pytest

from app.services import app_settings
from app.sru_agent import agent, fee_journey, memory


@pytest.fixture(autouse=True)
def _evaluate_first():
    app_settings.set_for_tests(fee_questions="evaluate_first", suggestion_chips="questions_only")
    yield
    app_settings.set_for_tests(fee_questions="fee_card", suggestion_chips="always")


async def _chat(messages):
    sid = f"v414s-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True)
    conv, out = None, []
    for m in messages:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    return out, sid, conv


@pytest.mark.asyncio
async def test_side_questions_are_answered_and_the_steps_continue():
    out, sid, conv = await _chat(["B.Tech CSE fees", "how are the placements?", "fests in sru", "mess timings",
                                  fee_journey.RESUME, "Telangana State Board"])
    start, placements, fests, mess, resume, board = out
    assert "Step 1 of 4" in start["answer"]
    assert "LPA" in placements["answer"] and "board" not in placements["answer"].lower()
    assert fee_journey.RESUME in placements["suggestions"]
    assert "50+ events" in fests["answer"] and fee_journey.RESUME in fests["suggestions"]
    assert "Breakfast" in mess["answer"] and "7:30" in mess["answer"]
    assert "which board" in resume["answer"]
    assert "Step 2 of 4" in board["answer"]


@pytest.mark.asyncio
async def test_just_show_the_fee_ends_the_steps():
    out, sid, conv = await _chat(["B.Tech CSE fees", "Just show the B.Tech CSE fee"])
    state = await memory.get_conversation_state(sid, conv)
    assert not (state.get("fee_intake") or {}).get("waiting_for")
    assert "which board" not in out[1]["answer"].lower()


@pytest.mark.asyncio
async def test_general_scholarship_question_gets_the_slabs():
    [done], _, _ = await _chat(["what scholarships does SRU give"])
    assert "40%" in done["answer"] and "CBSE" in done["answer"] and "Step 1" not in done["answer"]


@pytest.mark.asyncio
async def test_placement_questions():
    (high,), _, _ = await _chat(["highest package at SRU?"])
    assert "51 LPA" in high["answer"]
    (bba,), _, _ = await _chat(["do students get jobs after bba"])
    assert "including **BBA**" in bba["answer"]
    (bare,), _, _ = await _chat(["placements"])
    assert "What would you like to know about placements" in bare["answer"]


@pytest.mark.asyncio
async def test_repeats_and_specific_questions():
    out, _, _ = await _chat(["B.Tech CSE fees", "cse fees?"])
    assert re.match(r"(To work out your exact fee I still need|Just one more detail|I need this one detail|Almost there)",
                    out[1]["answer"])   # v4.15.0: varied wording, same step
    assert "Just show the B.Tech CSE fee" in out[1]["suggestions"]
    out, _, _ = await _chat(["how is hostel life", "is the hostel good?"])
    assert out[1]["answer"].startswith("In short") and len(out[1]["answer"]) < len(out[0]["answer"])
    out, _, _ = await _chat(["is there a cricket ground", "swimming pool?", "non veg?"])
    assert out[0]["answer"].startswith("Yes. **Cricket**")
    assert "isn't among the facilities" in out[1]["answer"]
    assert "non-vegetarian" in out[2]["answer"]


@pytest.mark.asyncio
async def test_hi_after_answers_is_not_welcomed_again():
    sid = f"v414w-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Divya Teja", phone="9876543210")   # no welcome shown yet
    conv, out = None, []
    for m in ["is there a canteen", "good morning"]:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    assert "Welcome to SR University" not in out[1]["answer"]
