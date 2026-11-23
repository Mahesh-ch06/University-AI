"""Tests for interactive program exploration vs premature fee dumps (v4.1.6).

Verifies that:
1. When a user asks/clicks a program name like 'B.Tech in Artificial Intelligence & Robotics',
   it does NOT prematurely dump a fee table or fee card, but gives an engaging program overview
   and asks interactively what they want to explore.
2. When a user explicitly asks for fees (e.g. 'What is the fee for B.Tech in AI & Robotics?' or clicks 'Fee & scholarships'),
   it provides the detailed fee breakdown and fee card.
3. Welcome chip 'B.Tech programmes offered' gives the B.Tech overview with branch exploration chips.
4. Following up with 'Laboratories & facilities', 'Eligibility criteria', or 'Placements for this branch'
   routes to the respective dedicated responses.
"""

import pytest
from app.sru_agent.intents import classify_agent_intent
from app.sru_agent.agent import run_agent
from app.sru_agent import memory


class DummyClient:
    def __init__(self):
        self.requests = []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.requests.append({"contents": list(contents), "config": config})
        return None


@pytest.mark.asyncio
async def test_program_name_does_not_dump_fees():
    """Sending 'B.Tech in Artificial Intelligence & Robotics' must give program overview, NOT fee card."""
    prompt = "B.Tech in Artificial Intelligence & Robotics"
    intent = classify_agent_intent(prompt)
    assert intent == "PROGRAM_AI_ROBOTICS_QUERY"

    session_id = "test-ai-robotics-overview-session"
    events = [e async for e in run_agent(prompt, session_id, client=DummyClient())]
    done = [e for e in events if e["type"] == "done"][0]
    answer = done["answer"]
    cards = done.get("cards", [])

    # Must NOT be a fee dump
    assert "Official fee schedule" not in answer
    assert "Base Tuition Fee" not in answer
    assert not any(c.get("type") in ("fee_structure_detailed", "calculate_fee") for c in cards)

    # Must introduce AI & Robotics interactively
    assert "B.Tech in Artificial Intelligence & Robotics" in answer
    assert "Robot Operating System (ROS)" in answer or "ROS" in answer
    assert "What would you like to explore" in answer

    # Must provide exploration chips (2 contextual + 2 fixed)
    assert "Fee & scholarships" in done["suggestions"]
    assert "Laboratories & facilities" in done["suggestions"]
    assert len(done["suggestions"]) == 4

    # Must remember program interest in state
    state = await memory.get_conversation_state(session_id)
    assert state.get("active_program") == "btech_ai_robotics"


@pytest.mark.asyncio
async def test_followup_fee_chip_shows_branch_fees():
    """After exploring AI & Robotics, asking 'Fee & scholarships' returns the AI & Robotics fee breakdown."""
    session_id = "test-ai-robotics-fee-followup-session"

    # Step 1: User explores AI & Robotics
    events1 = [e async for e in run_agent("B.Tech in Artificial Intelligence & Robotics", session_id, client=DummyClient())]
    assert any(e["type"] == "done" for e in events1)

    # Step 2: User clicks 'Fee & scholarships'
    prompt = "Fee & scholarships"
    state = await memory.get_conversation_state(session_id)
    intent = classify_agent_intent(prompt, state)
    assert intent == "BTECH_AI_ROBOTICS_FEE_QUERY"

    events2 = [e async for e in run_agent(prompt, session_id, client=DummyClient())]
    done = [e for e in events2 if e["type"] == "done"][0]
    answer = done["answer"]
    cards = done.get("cards", [])

    # Now it should show the fee breakdown and fee card for AI & Robotics
    assert "B.Tech in Artificial Intelligence & Robotics" in answer
    assert "₹2,00,000" in answer
    assert "₹4,00,000" in answer
    assert any(c.get("type") in ("fee_structure_detailed", "calculate_fee") for c in cards)


@pytest.mark.asyncio
async def test_explicit_fee_query_directly_shows_fees():
    """Explicitly asking 'What is the fee for B.Tech in AI & Robotics?' immediately shows fee structure via fee flow."""
    prompt = "What is the fee for B.Tech in AI & Robotics?"

    events = [e async for e in run_agent(prompt, "test-direct-fee-query-session", client=DummyClient())]
    done = [e for e in events if e["type"] == "done"][0]
    answer = done["answer"]
    cards = done.get("cards", [])

    assert "B.Tech in Artificial Intelligence & Robotics" in answer
    assert "4,00,000" in answer or "2,00,000" in answer
    assert any(c.get("type") in ("fee_structure_detailed", "calculate_fee") for c in cards)


@pytest.mark.asyncio
async def test_welcome_chip_btech_programmes_offered():
    """Welcome chip 'B.Tech programmes offered' gives B.Tech branches overview with branch chips."""
    prompt = "B.Tech programmes offered"
    intent = classify_agent_intent(prompt)
    assert intent == "BTECH_PROGRAMS_QUERY"

    events = [e async for e in run_agent(prompt, "test-btech-progs-welcome-session", client=DummyClient())]
    done = [e for e in events if e["type"] == "done"][0]
    answer = done["answer"]

    assert "B.Tech Engineering Programs at SR University" in answer
    assert "B.Tech Artificial Intelligence & Robotics" in answer
    assert "B.Tech Computer Science & Engineering" in answer
    assert "B.Tech Electronics & Communication" in answer
    assert "B.Tech AI & Robotics" in done["suggestions"]
    assert "B.Tech CSE & Allied" in done["suggestions"]


@pytest.mark.asyncio
async def test_eligibility_criteria_response():
    """Sending 'Eligibility criteria' returns official eligibility criteria."""
    prompt = "Eligibility criteria"
    intent = classify_agent_intent(prompt)
    assert intent == "ELIGIBILITY_QUERY"

    events = [e async for e in run_agent(prompt, "test-eligibility-session", client=DummyClient())]
    done = [e for e in events if e["type"] == "done"][0]
    answer = done["answer"]

    # Built from the data file: both sources shown where they differ, never one picked as confirmed
    assert "Admission eligibility at SR University" in answer
    assert "50% (2027-28 fee card)" in answer and "60% (university's programme page (2026-27))" in answer
    assert "MPC" in answer
    # Then one question: which programme
    assert "Which programme are you interested in?" in answer
    assert 1 <= len(done["suggestions"]) <= 4


@pytest.mark.asyncio
async def test_laboratories_facilities_response():
    """Sending 'Laboratories & facilities' returns research labs information."""
    prompt = "Laboratories & facilities"
    intent = classify_agent_intent(prompt)
    assert intent == "LAB_FACILITIES_QUERY"

    events = [e async for e in run_agent(prompt, "test-labs-session", client=DummyClient())]
    done = [e for e in events if e["type"] == "done"][0]
    answer = done["answer"]

    assert "Laboratories" in answer or "Research Labs" in answer


@pytest.mark.asyncio
async def test_placements_for_this_branch_response():
    """Sending 'Placements for this branch' returns placement details and placement card."""
    prompt = "Placements for this branch"
    intent = classify_agent_intent(prompt)
    assert intent == "PLACEMENT_INFO_QUERY"   # a placement question, not a guarantee question (v4.9.0)

    # No branch discussed yet: "this branch" is unknown, so ask which programme instead of guessing
    events = [e async for e in run_agent(prompt, "test-placements-branch-session", client=DummyClient())]
    done = [e for e in events if e["type"] == "done"][0]
    assert "Which programme" in done["answer"]

    # With a branch in the conversation, the placements question is about that branch
    from app.sru_agent import dialogue
    r = dialogue.decide(prompt, {"dialogue": {"program": "btech_cse"}}, {})
    assert r["kind"] == "rewrite" and "B.Tech Computer Science & Engineering (CSE)" in r["message"]
