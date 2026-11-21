"""Tests for Other Fees Scoping, Non-Tuition Charges, and Category Disambiguation.

Validates:
1. "Any exact fee other than sem fee" does NOT trigger scholarship board intake or hostel keywords.
2. _contextual_query cleanly separates "exact" from hostel "ac" via word boundaries.
3. fee_intake.decide returns None for queries asking about fees other than tuition/semester fee.
4. OTHER_FEES_CARD contains the 6 official components and exact amounts matching user reference:
   - Enrolment Fee: ₹5,000
   - Other Academic / University Charges: ₹15,000
   - Examination Fee (First Year): ₹5,000
   - Application Form Fee: ₹1,100
   - Specialisation Fee: ₹30,000
   - PhD Fee: ₹70,000
5. card_service.generate_cards returns OTHER_FEES_CARD for other-fee queries.
6. classify_agent_intent correctly maps other fee questions to OTHER_FEES_QUERY while preserving standard queries.
7. End-to-end agent run yields other fees and does NOT ask for 10+2 board.
"""

import pytest
from app.services.card_service import OTHER_FEES_CARD, ADMISSION_FEE_CARD, generate_cards
from app.sru_agent import agent, fee_intake, intents, responses


def test_other_fees_card_contents_and_amounts():
    """Verify OTHER_FEES_CARD has all 6 official heads and exact amounts."""
    items = OTHER_FEES_CARD["items"]
    assert len(items) == 6

    heads_and_amounts = {item["category"]: item["amount"] for item in items}
    assert heads_and_amounts.get("Enrolment Fee") == "₹5,000"
    assert heads_and_amounts.get("Other Academic / University Charges") == "₹15,000"
    assert heads_and_amounts.get("Examination Fee (First Year)") == "₹5,000"
    assert heads_and_amounts.get("Application Form Fee") == "₹1,100"
    assert heads_and_amounts.get("Specialisation Fee") == "₹30,000"
    assert heads_and_amounts.get("PhD Fee") == "₹70,000"


def test_contextual_query_no_hostel_collision_on_exact():
    """Verify that 'exact' does not trigger 'ac' in _contextual_query."""
    q = agent._contextual_query("Any exact fee other than sem fee")
    low_q = q.lower()
    assert "hostel" not in low_q
    assert "mess" not in low_q
    assert "non-ac" not in low_q
    assert "room amenities" not in low_q
    assert "other fees and charges" in low_q or "enrolment fee" in low_q


def test_fee_intake_skips_non_tuition_and_other_fees():
    """Verify fee_intake.decide returns None when asked about fees other than sem/tuition fee."""
    queries = [
        "Any exact fee other than sem fee",
        "exact fee other than sem fee",
        "other fees",
        "what other fees are there",
        "any fee other than sem fee",
        "charges other than semester fee",
        "annual charges",
        "other academic charges",
        "specialisation fee",
        "phd fee",
        "additional fees besides tuition",
    ]
    for q in queries:
        decision = fee_intake.decide(q, {}, {})
        assert decision is None, f"Expected None for '{q}', but got {decision}"


def test_card_service_attaches_other_fees_card():
    """Verify generate_cards attaches OTHER_FEES_CARD for other-fees inquiries."""
    cards = generate_cards("Any exact fee other than sem fee", "")
    assert len(cards) >= 1
    assert cards[0] == OTHER_FEES_CARD

    cards2 = generate_cards("What are the other academic charges and enrolment fee?", "")
    assert len(cards2) >= 1
    assert cards2[0] == OTHER_FEES_CARD


def test_classify_intent_other_fees_query():
    """Verify classify_agent_intent maps non-tuition queries to OTHER_FEES_QUERY."""
    assert intents.classify_agent_intent("Any exact fee other than sem fee") == "OTHER_FEES_QUERY"
    assert intents.classify_agent_intent("What other fees are there besides semester fee?") == "OTHER_FEES_QUERY"
    assert intents.classify_agent_intent("other academic university charges") == "OTHER_FEES_QUERY"
    assert intents.classify_agent_intent("specialisation fee") == "OTHER_FEES_QUERY"
    assert intents.classify_agent_intent("phd fee per year") == "OTHER_FEES_QUERY"


def test_classify_intent_preserves_standard_queries():
    """Verify classify_agent_intent preserves standard queries without false positives."""
    assert intents.classify_agent_intent("What is the fee for B.Tech CSE?") != "OTHER_FEES_QUERY"
    assert intents.classify_agent_intent("How much is hostel fee?") == "HOSTEL_FEE_QUERY"
    assert intents.classify_agent_intent("What are the hostel mess timings?") == "HOSTEL_MESS_QUERY"


@pytest.mark.asyncio
async def test_agent_e2e_other_fees_query_no_board_intake():
    """Verify end-to-end agent does NOT ask for 10+2 board when user asks for other fees."""
    events = [
        e async for e in agent.run_agent(
            message="Any exact fee other than sem fee",
            session_id="test-other-fees-sess-1",
            conversation_id="conv-other-fees-1",
        )
    ]

    done_ev = next((ev for ev in events if ev.get("type") == "done"), None)
    assert done_ev is not None
    full_text = done_ev.get("reply", "") or "".join(
        ev.get("delta", "") for ev in events if ev.get("type") == "token"
    )

    # Must NOT ask for board or entrance rank
    assert "Which board (10+2 / Intermediate Board) did you study under?" not in full_text
    assert "Telangana State Board (TS BIE)" not in full_text
    assert "In the next step, I'll ask for your marks" not in full_text

    # Must contain official other fee components
    assert "5,000" in full_text or "₹5,000" in full_text
    assert "15,000" in full_text or "₹15,000" in full_text
    assert "1,100" in full_text or "₹1,100" in full_text

    # Must include OTHER_FEES_CARD
    cards = done_ev.get("cards", [])
    has_card = any(c.get("title") == OTHER_FEES_CARD["title"] for c in cards)
    assert has_card, f"Expected OTHER_FEES_CARD in {cards}"
