"""Tests for Natural Conversation Before Structured Workflows (v4.0.0).

Verifies:
1. Acceptance Test:
   Input: "I scored 850 marks in Intermediate. I'm planning to join B.Tech, but I'm confused about which branch to choose."
   - No automatic scholarship calculator launch
   - No board-selection form immediately
   - Natural branch-guidance response
   - One relevant follow-up question
   - No invented academic details (board, total marks, percentage, eligibility)
2. Context Preservation across turns:
   Turn 1: Branch guidance with 850 marks in Intermediate for B.Tech
   Turn 2: "What scholarship can I get for my 850 marks?" -> activates scholarship workflow, reuses 850 marks and B.Tech interest without re-asking, asks only for missing board.
"""
import pytest
from app.sru_agent import memory
from app.sru_agent.agent import run_agent
from app.sru_agent import fee_intake, intents


class DummyClient:
    def __init__(self):
        self.requests = []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.requests.append({"contents": list(contents), "config": config})
        return None


async def _run(message, session_id, conv_id="conv-nat", client=None):
    events = []
    cl = client or DummyClient()
    async for ev in run_agent(message, session_id, conversation_id=conv_id, client=cl):
        events.append(ev)
    return events


@pytest.mark.asyncio
async def test_acceptance_test_branch_guidance_natural_conversation():
    session_id = "test-session-nat-acc"
    conv_id = "conv-nat-1"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    query = "I scored 850 marks in Intermediate. I'm planning to join B.Tech, but I'm confused about which branch to choose."
    events = await _run(query, session_id, conv_id)

    # 1. No tool calls to calculate_fee
    tool_events = [e for e in events if e.get("type") == "tool" and e.get("name") == "calculate_fee"]
    assert len(tool_events) == 0, "Must not launch calculate_fee tool"

    done_ev = events[-1]
    assert done_ev["type"] == "done"
    answer = done_ev["answer"]
    cards = done_ev.get("cards", [])
    suggestions = done_ev.get("suggestions", [])

    # 2. No board-selection or fee forms immediately
    assert not any(c.get("type") in ("fee_scholarship_form", "counsellor_board", "counsellor_stage", "calculate_fee") for c in cards), \
        f"Unexpected cards returned: {[c.get('type') for c in cards]}"

    # 3. Natural conversational branch guidance acknowledging marks
    assert "850" in answer
    assert "Intermediate" in answer or "engineering" in answer.lower()
    assert "Computer Science" in answer or "CSE" in answer
    assert "Robotics" in answer or "AI & Robotics" in answer
    assert "Electronics" in answer or "ECE" in answer

    # 4. Concludes with at most ONE relevant follow-up question
    assert answer.strip().endswith("?")
    question_marks = answer.count("?")
    assert question_marks == 1, f"Expected exactly 1 follow-up question, found {question_marks}"

    # 5. Information correctly extracted and retained without invented details
    profile = await memory.get_profile(session_id)
    assert profile.get("raw_marks") == 850
    assert profile.get("degree_interest") == "btech"
    # Must NOT assume board or percentage or max marks without information
    assert profile.get("board") is None or profile.get("board") == ""
    assert profile.get("percent") is None

    # Suggestions provide branch exploration options
    assert any("Software" in s or "CSE" in s for s in suggestions)
    assert any("Hardware" in s or "VLSI" in s or "ECE" in s for s in suggestions)


@pytest.mark.asyncio
async def test_context_preservation_followup_scholarship():
    """Turn 1 gives branch guidance + 850 marks.

    Turn 2 asks for scholarship -> reuses 850 marks and B.Tech interest without re-asking.
    """
    session_id = "test-session-nat-multiturn"
    conv_id = "conv-nat-2"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)

    # Turn 1: Branch guidance enquiry
    t1_query = "I scored 850 marks in Intermediate. I'm planning to join B.Tech, but I'm confused about which branch to choose."
    events1 = await _run(t1_query, session_id, conv_id)
    done1 = events1[-1]
    assert "850" in done1["answer"]

    # Turn 2: Scholarship enquiry
    t2_query = "What scholarship can I get for my 850 marks?"
    events2 = await _run(t2_query, session_id, conv_id)
    done2 = events2[-1]
    ans2 = done2["answer"]
    cards2 = done2.get("cards", [])

    # Must activate scholarship intake for board
    assert any(c.get("type") in ("counsellor_board", "fee_scholarship_form") for c in cards2) or "board" in ans2.lower()
    # Must NOT re-ask what marks they scored because 850 marks is already remembered
    assert "how many marks" not in ans2.lower()
    assert "what marks did you score" not in ans2.lower()

    # Turn 3: User provides board
    t3_query = "Telangana Intermediate (TSBIE)"
    events3 = await _run(t3_query, session_id, conv_id)
    done3 = events3[-1]
    ans3 = done3["answer"]
    cards3 = done3.get("cards", [])

    # Next step asks for academic stage, not marks
    assert any(c.get("type") == "counsellor_stage" for c in cards3) or "year" in ans3.lower() or "stage" in ans3.lower()
    assert "how many marks" not in ans3.lower()


def test_intent_classification_branch_guidance():
    msg1 = "I scored 850 marks in Intermediate. I'm planning to join B.Tech, but I'm confused about which branch to choose."
    assert intents.classify_agent_intent(msg1) == "BRANCH_GUIDANCE_QUERY"
    assert intents.is_branch_guidance_query(msg1) is True

    msg2 = "Which branch should I choose between CSE and ECE?"
    assert intents.classify_agent_intent(msg2) == "BRANCH_GUIDANCE_QUERY"
    assert intents.is_branch_guidance_query(msg2) is True

    msg3 = "Guide me to select a course"
    assert intents.classify_agent_intent(msg3) == "BRANCH_GUIDANCE_QUERY"
    assert intents.is_branch_guidance_query(msg3) is True


def test_fee_intake_does_not_intercept_branch_guidance():
    msg = "I scored 850 marks in Intermediate. I'm planning to join B.Tech, but I'm confused about which branch to choose."
    assert fee_intake.is_fee_enquiry(msg) is False
    assert fee_intake.decide(msg, profile={}, intake={}) is None
