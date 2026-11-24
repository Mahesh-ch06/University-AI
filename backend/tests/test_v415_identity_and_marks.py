"""v4.15.0: identity on callbacks and the latest marks always used.

1. A callback is never saved or confirmed as "Unknown" (or any placeholder): the name the student gave in the
   contact form is used; with no name at all, it is asked for. "Start fresh" keeps the name.
2. Marks given or corrected in any wording replace the old ones at once, in the profile and in the fee steps,
   and the reply confirms the update; a percentage clears old raw marks; raw marks take the board's total.
3. A reply that asks for marks always carries the marks form.
"""
from __future__ import annotations

import uuid

import pytest

from app.sru_agent import agent, memory, tools
from app.services import app_settings


@pytest.fixture(autouse=True)
def _evaluate_first():
    app_settings.set_for_tests(fee_questions="evaluate_first", suggestion_chips="questions_only")
    yield
    app_settings.set_for_tests(fee_questions="fee_card", suggestion_chips="always")


async def _chat(messages, **profile):
    sid = f"v415-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, welcome_actions_shown=True, **profile)
    conv, out = None, []
    for m in messages:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    return out, sid, conv


@pytest.mark.parametrize("name", ["Unknown", "student", "User", "N/A", "undefined", "", "  "])
def test_placeholder_names(name):
    assert tools.is_placeholder_name(name)


def test_real_names_are_not_placeholders():
    for name in ("Mahesh", "Asha Rani", "Sai Charan"):
        assert not tools.is_placeholder_name(name)


@pytest.mark.asyncio
async def test_callback_with_a_placeholder_name_uses_the_contact_form_name():
    sid = f"v415cb-{uuid.uuid4().hex[:8]}"
    profile = await memory.update_profile(sid, name="Mahesh Kumar", phone="9876543210")
    saved = []

    async def saver(lead):
        saved.append(lead)
        return {"id": "lead-1"}
    tools.set_lead_saver(saver)
    try:
        ctx = {"session_id": sid, "conversation_id": "c1", "profile": profile}
        res = await tools.run_tool("request_counsellor_callback",
                                   {"name": "Unknown", "phone": "9876543210", "consent": True}, ctx)
        assert res["status"] == "saved" and res["name"] == "Mahesh Kumar" and saved[0]["name"] == "Mahesh Kumar"
        text = agent._saved_text("callback", res)
        assert "successfully submitted, Mahesh" in text and "Unknown" not in text
        again = await tools.run_tool("request_counsellor_callback",
                                     {"name": "Mahesh Kumar", "phone": "9876543210", "consent": True}, ctx)
        assert again.get("already_saved") and len(saved) == 1                       # no duplicate lead
    finally:
        tools.set_lead_saver(None)


@pytest.mark.asyncio
async def test_callback_without_any_name_asks_for_it():
    sid = f"v415cb-{uuid.uuid4().hex[:8]}"
    ctx = {"session_id": sid, "conversation_id": "c1", "profile": {"phone": "9876543210"}}
    res = await tools.run_tool("request_counsellor_callback", {"name": "Unknown", "phone": "9876543210",
                                                               "consent": True}, ctx)
    assert res["status"] == "invalid" and "name" in res["problem"].lower()


def test_fresh_start_keeps_the_name_for_the_model():
    p = agent._prompt_profile({"name": "Mahesh", "address_by_name": False})
    assert p.get("name_on_file") == "Mahesh"


@pytest.mark.asyncio
async def test_correction_after_the_final_fee_recalculates():
    out, sid, conv = await _chat(["Calculate my scholarship", "B.Tech CSE", "Telangana State Board", "Completed", "870",
                                  "MPC", "None of these apply", "No hostel, I'm a day scholar", "No, I'll manage",
                                  "No, these are not my marks. My actual marks are 671 out of 1000."],
                                 name="Mahesh Kumar", phone="9876543210")
    last = out[-1]["answer"]
    assert "671/1000" in last and "15% scholarship" in last
    state = await memory.get_conversation_state(sid, conv)
    assert state["fee_intake"]["raw_marks"] == 671 and state["fee_intake"]["percent"] == 67.1


@pytest.mark.asyncio
async def test_correction_in_the_middle_of_the_steps_is_confirmed_and_used():
    out, sid, conv = await _chat(["B.Tech CSE fees", "Telangana State Board", "Completed", "870",
                                  "wait, my marks are 671 out of 1000", "MPC"], name="Asha Rani", phone="9876543210")
    assert out[4]["answer"].startswith("Updated: I'm now using your marks **671/1000 (67.1%)**")
    assert "Step 4 of 4" in out[4]["answer"]
    assert "67.1%" in out[5]["answer"] and "15% scholarship" in out[5]["answer"]


@pytest.mark.asyncio
async def test_a_percentage_correction_clears_old_raw_marks():
    out, sid, conv = await _chat(["Calculate my scholarship", "B.Tech CSE", "CBSE", "Completed", "92%", "MPC",
                                  "None of these apply", "No hostel, I'm a day scholar", "No, I'll manage",
                                  "not 92, I got 82 percent"], name="Ravi Kumar", phone="9876543210")
    assert "82%" in out[-1]["answer"] and "25% scholarship" in out[-1]["answer"]
    profile = await memory.get_profile(sid)
    assert profile.get("percent") == 82.0 and profile.get("raw_marks") is None


@pytest.mark.asyncio
async def test_raw_marks_take_the_board_total_and_the_stage_is_not_asked_again():
    out, sid, conv = await _chat(["what is my scholarship for 870 marks in TS inter for cse", "no my marks are 760",
                                  "MPC"], name="Ravi Kumar", phone="9876543210")
    assert "None%" not in out[0]["answer"] and "870/1000 (87%)" in out[0]["answer"]
    assert "760/1000 (76%)" in out[1]["answer"] and "Step 4 of 4" in out[1]["answer"]
    assert "20% scholarship" in out[2]["answer"]


def test_a_marks_question_always_has_the_form():
    cards = agent._with_marks_form("Sure! What were your Intermediate (10+2) marks? A percentage like 78%.", [])
    assert cards[0]["type"] == "counsellor_marks_input" and cards[0]["max_marks"] is None
    cards = agent._with_marks_form("Step 3 of 4: what are your final marks (out of 1000)?", [])
    assert cards[0]["max_marks"] == 1000
    assert agent._with_marks_form("Step 1 of 4: which board did you study under?", []) == []


# ------------------------------------------------------------------ 4. the conversation's workflow outlives the cache
@pytest.mark.asyncio
async def test_continue_a_day_later_restores_the_workflow_from_the_database():
    from app.db.session import engine
    from app.services import agent_profile_store
    await engine.dispose()            # connections pooled by an earlier test belong to another event loop
    sid, conv = f"v415d-{uuid.uuid4().hex[:10]}", str(uuid.uuid4())      # the API gives every chat an id
    await memory.update_profile(sid, name="Mahesh Kumar", phone="9876543210", welcome_actions_shown=True)
    for m in ["Calculate my scholarship", "B.Tech CSE", "Telangana State Board"]:
        async for _ev in agent.run_agent(m, sid, conv, client=None):
            pass
    state = await memory.get_conversation_state(sid, conv)
    assert state["fee_intake"]["waiting_for"] == "stage"
    try:
        await agent_profile_store.save_conversation_state(sid, str(conv), state)
    except Exception:
        pytest.skip("database not reachable")
    # a day later: the 24-hour cache is empty
    key = memory._state_key(sid, conv)
    memory._hot.pop(key, None)
    memory._local.pop(key, None)
    r = memory._client()
    if r:
        await r.delete(key)
    memory._state_saved.pop(key, None)
    memory.set_state_store(agent_profile_store.load_conversation_state, agent_profile_store.save_conversation_state)
    try:
        restored = await memory.get_conversation_state(sid, conv)
        assert restored["fee_intake"]["waiting_for"] == "stage" and restored["fee_intake"]["board_key"] == "ts_state_board"
        nxt = []
        async for ev in agent.run_agent("Completed", sid, conv, client=None):
            if ev["type"] == "done":
                nxt.append(ev)
        assert "Step 3 of 4" in nxt[0]["answer"]                        # carries on at the marks step
        assert any(c["type"] == "counsellor_marks_input" for c in nxt[0]["cards"])
    finally:
        memory.set_state_store(None, None)
