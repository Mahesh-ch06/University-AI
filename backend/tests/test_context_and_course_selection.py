"""Tests for Conversation Context & Course Selection Improvements (v4.0.0).

Verifies the 5 core scenarios:
1. Scenario A: Never Assume the User's Course (General interest queries ask course with broad suggestions).
2. Scenario B: Maintain Course Context Once Selected (Retains course across turns for scholarship inquiry).
3. Scenario C: Course Selection after General Enquiry (General fees -> course asked -> course selected -> scholarship intake).
4. Scenario D: Avoid Repetitive Questions (Remembers previously stated board/stage and asks only missing marks/route).
5. Scenario E: Course Change & Topic Transitions (Switches from CSE to ECE seamlessly and retains course across topic transitions like hostels).
"""
import pytest
from app.sru_agent import memory
from app.sru_agent.agent import run_agent


class DummyClient:
    def __init__(self):
        self.requests = []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.requests.append({"contents": list(contents), "config": config})
        return None


async def _run(message, session_id, conv_id="conv-ctx", client=None):
    events = []
    cl = client or DummyClient()
    async for ev in run_agent(message, session_id, conversation_id=conv_id, client=cl):
        events.append(ev)
    return events


# ---- Scenario A: Never Assume Course on General Enquiry ----
@pytest.mark.asyncio
async def test_scenario_a_never_assume_course_join_sru():
    session_id = "test-sc-a-join"
    conv_id = "conv-a1"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    events = await _run("I want to join SRU", session_id, conv_id)
    done_ev = events[-1]
    assert done_ev["type"] == "done"
    answer = done_ev["answer"]
    suggestions = done_ev.get("suggestions", [])
    cards = done_ev.get("cards", [])

    # Must ask which course without assuming CSE
    assert "Which course" in answer or "interested in pursuing" in answer
    assert "B.Tech" in suggestions or any("Engineering" in s for s in suggestions)
    assert any("MBA" in s for s in suggestions)
    assert any("BBA" in s for s in suggestions)
    assert any(c.get("type") == "school_selection" for c in cards)


@pytest.mark.asyncio
async def test_scenario_a_general_fee_and_scholarship():
    session_id = "test-sc-a-fees"
    conv_id = "conv-a2"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    events = await _run("I want to know about fees and scholarships", session_id, conv_id)
    done_ev = events[-1]
    assert done_ev["type"] == "done"
    answer = done_ev["answer"]
    suggestions = done_ev.get("suggestions", [])
    cards = done_ev.get("cards", [])

    assert "Which course" in answer or "considering" in answer
    assert any("B.Tech" in s for s in suggestions)
    assert any("MBA" in s for s in suggestions)
    assert any("BBA" in s for s in suggestions)
    assert any(c.get("type") == "counsellor_program_selection" for c in cards)


# ---- Scenario B: Maintain Course Context Once Selected ----
@pytest.mark.asyncio
async def test_scenario_b_maintain_course_context():
    session_id = "test-sc-b-context"
    conv_id = "conv-b"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    # Turn 1: Explicit course selection with fee query
    events1 = await _run("I am interested in B.Tech CSE. What are the fees?", session_id, conv_id)
    assert "3,40,000" in events1[-1]["answer"]
    assert any(c.get("type") == "fee_structure_detailed" for c in events1[-1].get("cards", []))

    # Turn 2: Follow-up scholarship query
    events2 = await _run("What scholarship can I get?", session_id, conv_id)
    done_ev2 = events2[-1]
    assert done_ev2["type"] == "done"
    answer2 = done_ev2["answer"]
    cards2 = done_ev2.get("cards", [])

    # Must NOT ask which course again; proceeds straight to academic background / board
    assert "Which course" not in answer2
    assert any(c.get("type") == "counsellor_board_selection" for c in cards2)

    # State must reflect btech_cse
    state = await memory.get_conversation_state(session_id, conv_id)
    assert state.get("active_program") == "btech_cse"


# ---- Scenario C: Course Selection After General Question ----
@pytest.mark.asyncio
async def test_scenario_c_select_course_after_general_enquiry():
    session_id = "test-sc-c-flow"
    conv_id = "conv-c"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    # Turn 1: General enquiry
    events1 = await _run("I want to know about fees and scholarships", session_id, conv_id)
    assert any(c.get("type") == "counsellor_program_selection" for c in events1[-1].get("cards", []))

    # Turn 2: User specifies course
    events2 = await _run("B.Tech CSE", session_id, conv_id)
    done_ev2 = events2[-1]
    assert done_ev2["type"] == "done"
    cards2 = done_ev2.get("cards", [])

    # Proceeds to board selection with CSE context
    assert any(c.get("type") == "counsellor_board_selection" for c in cards2)
    state = await memory.get_conversation_state(session_id, conv_id)
    assert state.get("active_program") == "btech_cse"


# ---- Scenario D: Avoid Repetitive Questions (Remember Board & Stage) ----
@pytest.mark.asyncio
async def test_scenario_d_remember_academic_info():
    session_id = "test-sc-d-academic"
    conv_id = "conv-d"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    # Turn 1: User mentions they completed Intermediate with TSBIE
    events1 = await _run("I completed Intermediate with TSBIE. Tell me about B.Tech CSE", session_id, conv_id)
    assert events1[-1]["type"] == "done"

    profile = await memory.get_profile(session_id)
    assert profile.get("board_key") in ("ts_state_board", "state_board") or profile.get("board") == "state_board"
    assert profile.get("academic_stage") in ("completed", "2nd_year")

    # Turn 2: User asks to calculate scholarship
    events2 = await _run("Calculate my scholarship", session_id, conv_id)
    done_ev2 = events2[-1]
    assert done_ev2["type"] == "done"
    answer2 = done_ev2["answer"]
    cards2 = done_ev2.get("cards", [])

    # Must NOT re-ask board or stage
    assert "Which board" not in answer2
    assert "Where did you complete" not in answer2
    assert not any(c.get("type") == "counsellor_board_selection" for c in cards2)
    assert not any(c.get("type") == "counsellor_stage_selection" for c in cards2)

    # Must ask for marks (out of 1000 for completed Intermediate)
    assert any(c.get("type") == "counsellor_marks_input" for c in cards2)
    assert any("1000" in s for s in done_ev2.get("suggestions", []))


# ---- Scenario E: Course Change and Topic Transitions ----
@pytest.mark.asyncio
async def test_scenario_e_course_change():
    session_id = "test-sc-e-switch"
    conv_id = "conv-e"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    # Turn 1: Inquire about B.Tech CSE
    events1 = await _run("I am interested in B.Tech CSE. What are the fees?", session_id, conv_id)
    assert "3,40,000" in events1[-1]["answer"]

    # Turn 2: Change course to ECE
    events2 = await _run("Actually, I want ECE", session_id, conv_id)
    done_ev2 = events2[-1]
    assert done_ev2["type"] == "done"
    answer2 = done_ev2["answer"]

    # Must provide ECE fees (₹2,70,000) and update state
    assert "2,70,000" in answer2 or "ECE" in answer2
    state2 = await memory.get_conversation_state(session_id, conv_id)
    assert state2.get("active_program") == "btech_ece"

    # Turn 3: Calculate scholarship uses ECE
    events3 = await _run("What is the fee after scholarship?", session_id, conv_id)
    done_ev3 = events3[-1]
    assert done_ev3["type"] == "done"
    cards3 = done_ev3.get("cards", [])
    assert any(c.get("type") == "counsellor_board_selection" for c in cards3)
    state3 = await memory.get_conversation_state(session_id, conv_id)
    assert state3.get("active_program") == "btech_ece"


@pytest.mark.asyncio
async def test_scenario_topic_transition_preserves_course():
    session_id = "test-topic-transition"
    conv_id = "conv-trans"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    # Turn 1: Select B.Tech CSE fees
    events1 = await _run("What is the B.Tech CSE fee?", session_id, conv_id)
    assert "3,40,000" in events1[-1]["answer"]

    # Turn 2: Ask about hostels
    events2 = await _run("What are the hostel facilities and fee?", session_id, conv_id)
    assert "hostel" in events2[-1]["answer"].lower()

    # Turn 3: Ask for scholarship - should still retain btech_cse
    events3 = await _run("What scholarship can I get?", session_id, conv_id)
    assert events3[-1]["type"] == "done"
    state3 = await memory.get_conversation_state(session_id, conv_id)
    assert state3.get("active_program") == "btech_cse"
    cards3 = events3[-1].get("cards", [])
    assert any(c.get("type") == "counsellor_board_selection" for c in cards3)
