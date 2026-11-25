"""Tests for agent compound query decomposition and understanding."""

import pytest
from app.sru_agent.agent import run_agent


@pytest.mark.asyncio
async def test_compound_query_about_sru_and_about_hostels():
    """Verify 'about sru and about hostels' answers both topics and does NOT prompt clarification."""
    tokens = []
    cards = []
    async for ev in run_agent(
        "about sru and about hostels",
        session_id="test_compound_1",
        conversation_id="conv_compound_1",
    ):
        if ev["type"] == "token":
            tokens.append(ev["delta"])
        elif ev["type"] == "card":
            cards.append(ev["card"])

    full_text = "".join(tokens)
    # Must NOT prompt for clarification
    assert "What would you like to know about the hostel?" not in full_text
    # Must cover both SRU overview and hostel details
    assert "About SR University" in full_text or "SR University" in full_text
    assert "Hostel" in full_text or "Residential" in full_text or "Campus Amenities" in full_text


@pytest.mark.asyncio
async def test_compound_query_cse_vs_aiml_and_why_sru():
    """Verify 'cse vs aiml and why sru' answers both the comparison and why choose SRU."""
    tokens = []
    async for ev in run_agent(
        "cse vs aiml and why sru",
        session_id="test_compound_2",
        conversation_id="conv_compound_2",
    ):
        if ev["type"] == "token":
            tokens.append(ev["delta"])

    full_text = "".join(tokens)
    # Must cover course comparison
    assert "CSE vs" in full_text or "Computer Science & Engineering" in full_text
    assert "Artificial Intelligence" in full_text or "AI & ML" in full_text
    # Must also cover Why Choose SRU
    assert "Why students choose SRU" in full_text or "reasons to choose SRU" in full_text   # verified facts (v4.15.1)


@pytest.mark.asyncio
async def test_compound_query_fees_and_hostel_timings():
    """Verify 'What are the fees and hostel timings?' answers both fees and timings."""
    tokens = []
    cards = []
    async for ev in run_agent(
        "What are the fees and hostel timings?",
        session_id="test_compound_3",
        conversation_id="conv_compound_3",
    ):
        if ev["type"] == "token":
            tokens.append(ev["delta"])
        elif ev["type"] == "card":
            cards.append(ev["card"])

    full_text = "".join(tokens)
    assert "Fee" in full_text or "Tuition" in full_text or "₹" in full_text
    assert "Curfew" in full_text or "Timing" in full_text or "8:30 PM" in full_text or "In-Time" in full_text
