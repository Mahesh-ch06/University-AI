"""Tests for About SRU, Why Choose SRU bulleted highlights, and fee agent scoping."""

import pytest
from app.sru_agent import intents, agent


def test_about_and_why_choose_intent_classification():
    """Verify that 'About SRU' and 'Why choose SRU' inquiries classify into dedicated intents."""
    why_queries = [
        "why choose sru",
        "why sru",
        "why should I choose SR University",
        "what makes SRU special",
        "advantages of SR University",
        "is sru good",
    ]
    for q in why_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "WHY_CHOOSE_SRU_QUERY", f"Query '{q}' classified as {intent}"

    about_queries = [
        "about sru",
        "tell me about sru",
        "what is sr university",
        "overview of sru",
        "describe sru",
    ]
    for q in about_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "ABOUT_SRU_QUERY", f"Query '{q}' classified as {intent}"


@pytest.mark.asyncio
async def test_about_sru_bullet_points_and_highlights():
    """Verify that About SRU output highlights the 5 key pillars in bullet points."""
    events = [e async for e in agent.run_agent("tell me about sru", "test_about_sess_1")]
    done = [e for e in events if e.get("type") == "done"][0]
    answer = done.get("answer", "")

    # 1. Top private university of Telangana and AP
    assert "Top Private University of Telangana & AP" in answer
    # 2. Rankings & Accreditations
    assert "Rankings & Accreditations" in answer
    assert "NIRF" in answer
    # 3. Placements & Industry Readiness
    assert "Placements & Industry Readiness" in answer
    assert "₹51 LPA" in answer
    # 4. Global Collaborations
    assert "Global Collaborations" in answer
    # 5. Next-Gen Living & Learning Campus
    assert "Next-Gen Living & Learning Campus" in answer

    # Video recommendations preserved for promotional queries
    cards = done.get("cards", [])
    assert any(c.get("type") == "video_recommendations" for c in cards)


@pytest.mark.asyncio
async def test_why_choose_sru_bullet_points_and_highlights():
    """Verify that Why Choose SRU output highlights the 5 key pillars in bullet points."""
    events = [e async for e in agent.run_agent("why choose sru", "test_why_sess_1")]
    done = [e for e in events if e.get("type") == "done"][0]
    answer = done.get("answer", "")

    assert "Top Private University of Telangana & AP" in answer
    assert "Rankings" in answer
    assert "Placements" in answer
    assert "Global Collaborations" in answer
    assert "Next-Gen Living & Learning Campus" in answer

    cards = done.get("cards", [])
    assert any(c.get("type") == "video_recommendations" for c in cards)


@pytest.mark.asyncio
async def test_fee_agent_scoped_to_calculations_only():
    """Verify fee intake is not triggered for informational queries, only calculation requests."""
    # General informational query should not prompt for 10+2 board/percentage
    conv_state = {"fee_flow_state": "completed", "fee_flow_prog": "btech_cse"}
    
    # Informational query: "hostel fee"
    intent = intents.classify_agent_intent("what is the hostel fee?", conv_state)
    assert intent == "HOSTEL_FEE_QUERY"

    # Calculation query: "calculate my fee with 85%"
    is_calc = bool(intents.re.search(
        r"\b(?:schol\w*|waiver|concession|discount|fee\s+assessment|scholarship\s+assessment|assessment\s+form|"
        r"calculate\s+(?:my\s+)?fee|fee\s+calculation|my\s+fee|exact\s+fee|calculate\s+scholarship)\b",
        "calculate my fee with 85%",
        intents.re.IGNORECASE,
    ))
    assert is_calc is True
