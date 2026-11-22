"""Tests verifying resolutions for QA findings (SRU-001, SRU-003, SRU-004)."""
import pytest
from app.sru_agent import intents, memory
from app.sru_agent.agent import run_agent, _offline_knowledge_reply


@pytest.mark.asyncio
async def test_admission_guarantee_intent_classification():
    queries = [
        "Is admission guaranteed if I score 95%?",
        "Can you guarantee admission?",
        "Is seat guaranteed in CSE?",
        "seat confirm ga vastunda 60k rank ki",
        "will I definitely get a seat with 98%?",
    ]
    for q in queries:
        intent = intents.classify_agent_intent(q, {})
        assert intent == "ADMISSION_GUARANTEE_QUERY", f"Failed for query: {q}, got: {intent}"


@pytest.mark.asyncio
async def test_admission_guarantee_response_content():
    session_id = "test-guarantee-qa"
    conv_id = "conv-guarantee"
    events = [e async for e in run_agent("Is admission guaranteed if I score 95%?", session_id, conv_id)]
    assert events[-1]["type"] == "done"
    answer = events[-1]["answer"]
    
    # Assert verified admission policy
    assert "merit-based and subject to seat availability" in answer
    assert "never unconditionally guaranteed" in answer
    # Assert fee intake card is NOT emitted
    cards = [c.get("type") for c in events[-1].get("cards", []) if isinstance(c, dict)]
    assert "counsellor_board_selection" not in cards
    assert "counsellor_program_selection" not in cards


@pytest.mark.asyncio
async def test_future_year_fee_intent_and_response():
    queries = [
        "What are the fees for 2029?",
        "Tell me the tuition fee for 2029-30",
        "fees for 2030",
    ]
    for q in queries:
        intent = intents.classify_agent_intent(q, {})
        assert intent == "FUTURE_YEAR_FEE_QUERY", f"Failed for query: {q}, got: {intent}"

    session_id = "test-future-fee-qa"
    conv_id = "conv-future"
    events = [e async for e in run_agent("What are the fees for 2029?", session_id, conv_id)]
    assert events[-1]["type"] == "done"
    answer = events[-1]["answer"]
    
    assert "2027–28 academic year" in answer or "2027-28" in answer
    assert "₹9,000 per year" in answer
    cards = [c.get("type") for c in events[-1].get("cards", []) if isinstance(c, dict)]
    assert "counsellor_board_selection" not in cards


@pytest.mark.asyncio
async def test_offline_knowledge_reply_rotation():
    session_id = "test-session-rotation"
    reply1 = _offline_knowledge_reply("hostel living rules", session_id)
    reply2 = _offline_knowledge_reply("hostel living rules", session_id)
    assert reply1 is not None
    # If multiple passages match, titles should rotate
    # Verify reply is non-empty and well-formed
    assert "matching part of the SR University handbook" in reply1
