"""Tests for refined placement guarantee and 100% placement assistance flow.

Verifies:
1. Classification of diverse placement guarantee query variations.
2. Positive opening with 100% placement assistance & comprehensive career support.
3. Realistic, transparent clarification that final outcomes depend on individual student performance.
4. Clear highlight of startup & entrepreneurship avenues via SRiX.
5. Grounded placement records (₹51 LPA Microsoft, ₹49.30 LPA ServiceNow, ₹46.38 LPA Amazon, 6 LPA avg, 150+ recruiters).
6. Rich PlacementHighlightsCard emission.
7. Multi-response variation across sessions.
"""

import pytest
from app.sru_agent.intents import classify_agent_intent
from app.sru_agent.agent import run_agent, _PLACEMENT_ASSISTANCE_RESPONSES


def test_placement_guarantee_intent_classification():
    """Verify various phrasing variations are recognized as PLACEMENT_GUARANTEE_QUERY."""
    variations = [
        "does sru guarantee placements",
        "Does SR University guarantee placements?",
        "is placement guaranteed",
        "is placement guaranteed at sru",
        "is there 100% placement guarantee",
        "do you guarantee jobs",
        "does sru provide job guarantee",
        "will i get a guaranteed job",
        "will i get guaranteed placement in cse",
        "is 100% placement assured",
        "placement assurance",
        "job assurance",
        "100 percent placement",
        "do you give 100% placement",
        "does sru provide 100% placement?",
        "placement guarantee",
        "job guarantee",
        "will i definitely get a job",
        "can sru guarantee my placement",
        "can you guarantee a job after graduation",
        "are placements guaranteed at sru",
        "I scored 85% in inter, does sru guarantee placement?",
    ]

    for q in variations:
        intent = classify_agent_intent(q)
        assert intent == "PLACEMENT_GUARANTEE_QUERY", f"Failed for query: '{q}', got '{intent}'"


def test_non_guarantee_placement_queries():
    """Verify general placement inquiries do NOT falsely trigger guarantee intent."""
    general_queries = [
        "What are the placements in CSE?",
        "Tell me the average package at SRU",
        "Who are the top recruiters?",
        "What is the highest package in 2025?",
        "Tell me about the hostel fee",
    ]

    for q in general_queries:
        intent = classify_agent_intent(q)
        assert intent != "PLACEMENT_GUARANTEE_QUERY", f"Query '{q}' should not be PLACEMENT_GUARANTEE_QUERY"


@pytest.mark.asyncio
async def test_placement_guarantee_agent_response():
    """Verify the agent emits a constructive 100% assistance response with SRiX startups and cards."""
    prompt = "does sru guarantee placements"
    events = [e async for e in run_agent(prompt, "test-placement-guar-session")]
    
    done = [e for e in events if e["type"] == "done"][0]
    answer = done["answer"]

    # Must NOT start with a blunt negative "No, SR University does not guarantee placements"
    assert not answer.strip().startswith("No, SR University does not guarantee placements")
    assert not answer.strip().startswith("No, placements are not guaranteed")

    # Must prominently state 100% placement assistance & comprehensive support
    assert "100% placement assistance" in answer or "100% Placement Assistance" in answer

    # Must state that outcomes depend on student performance / interview
    assert "individual student" in answer.lower() or "student" in answer.lower()
    assert "interview" in answer.lower()

    # Must prominently highlight Startups & SRiX incubator
    assert "SRiX" in answer
    assert "startup" in answer.lower() or "entrepreneurship" in answer.lower()

    # Must highlight verified package benchmarks
    assert "51" in answer and "Microsoft" in answer
    assert "49.30" in answer and "ServiceNow" in answer
    assert "46.38" in answer and "Amazon" in answer
    assert "1,300+" in answer or "1300+" in answer
    assert "6" in answer  # 6 to 6.5 LPA

    # Must include relevant interactive suggestion chips
    assert any("Startup Incubator (SRiX)" in s for s in done["suggestions"])
    assert any("Top recruiters" in s for s in done["suggestions"])

    # Must emit rich placement card
    card_events = [e for e in events if e["type"] == "card"]
    assert len(card_events) >= 1
    card = card_events[0]["card"]
    assert card["type"] == "placement_highlights"
    assert "Microsoft" in str(card)
    assert "ServiceNow" in str(card)
    assert "Amazon" in str(card)


def test_placement_assistance_variations_content():
    """Verify all defined response variations have required components."""
    assert len(_PLACEMENT_ASSISTANCE_RESPONSES) >= 4
    for idx, resp in enumerate(_PLACEMENT_ASSISTANCE_RESPONSES):
        # 100% placement assistance
        assert "100% placement assistance" in resp.lower() or "100% institutional support" in resp.lower(), f"Variation {idx} missing 100% assistance"
        # Startup / SRiX
        assert "srix" in resp.lower(), f"Variation {idx} missing SRiX"
        assert "startup" in resp.lower(), f"Variation {idx} missing startup mention"
        # Performance dependency
        assert "student" in resp.lower() and "interview" in resp.lower(), f"Variation {idx} missing performance transparency"
        # Top packages
        assert "51" in resp, f"Variation {idx} missing 51 LPA"
        assert "49.30" in resp, f"Variation {idx} missing 49.30 LPA"
        assert "46.38" in resp, f"Variation {idx} missing 46.38 LPA"
        assert "1,300+" in resp, f"Variation {idx} missing 1,300+ offers"
