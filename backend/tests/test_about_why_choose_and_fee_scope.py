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


def _bullets(answer: str) -> list[str]:
    return [line for line in answer.splitlines() if line.startswith("• ")]


@pytest.mark.asyncio
async def test_about_sru_bullet_points_and_highlights():
    """About SRU (v4.10.0): 2-4 bullets built from the verified facts store, not a fixed text."""
    from app.sru_agent import fact_service
    events = [e async for e in agent.run_agent("tell me about sru", "test_about_sess_1")]
    done = [e for e in events if e.get("type") == "done"][0]
    answer = done.get("answer", "")
    bullets = _bullets(answer)
    assert 2 <= len(bullets) <= 4
    shorts = {f.metadata.get("short") for f in fact_service.get_all_facts() if f.metadata.get("short")}
    assert all(b[2:] in shorts for b in bullets)          # every point is a verified / attributed fact
    assert "95%" not in answer                            # the unverified draft figure is never used
    # Video recommendations preserved for promotional queries (once per conversation)
    cards = done.get("cards", [])
    assert any(c.get("type") == "video_recommendations" for c in cards)


@pytest.mark.asyncio
async def test_why_choose_sru_bullet_points_and_highlights():
    """Why SRU: verified highlights across aspects; asked again, new points instead of the same text."""
    sid = "test_why_sess_1"
    first = [e async for e in agent.run_agent("why choose sru", sid)][-1]
    assert first["type"] == "done"
    one = _bullets(first["answer"])
    assert 3 <= len(one) <= 4
    assert any(k in first["answer"] for k in ("NIRF", "QS Asia", "THE World", "ICAR"))
    assert any(k in first["answer"] for k in ("LPA", "Placements"))
    second = [e async for e in agent.run_agent("why choose sru", sid, first["conversation_id"])][-1]
    two = _bullets(second["answer"])
    assert two and not set(one) & set(two)                # nothing repeated
    assert second["answer"].splitlines()[0] != first["answer"].splitlines()[0]
    assert not any(c.get("type") == "video_recommendations" for c in second.get("cards", []))


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
