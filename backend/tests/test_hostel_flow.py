"""Tests for hostel comprehensive information flow, intent classification, and non-hijacking."""

import pytest
from app.sru_agent import intents, fee_flow, agent
from app.services import card_service


def test_hostel_intent_classification():
    """Verify that different hostel questions classify into their specific intents."""
    # General hostel / facilities / living
    info_queries = [
        "tell me about hostel",
        "hostel facilities",
        "what are the hostel rooms like",
        "hostel accommodation details",
        "do you have ac rooms in hostel",
        "residential campus living",
        "hostel life at sru",
    ]
    for q in info_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "HOSTEL_INFO_QUERY", f"Query '{q}' classified as {intent}"

    # Mess / food / dining
    mess_queries = [
        "how is the mess food",
        "what is the mess menu",
        "dining timings in hostel",
        "is non-veg served in the mess",
        "breakfast timings in mega dining hall",
        "hostel food quality",
    ]
    for q in mess_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "HOSTEL_MESS_QUERY", f"Query '{q}' classified as {intent}"

    # Curfew / rules / in-time / out-pass
    curfew_queries = [
        "what are the curfew timings",
        "in-time for hostel",
        "hostel rules and regulations",
        "how to get out pass for hostel",
        "biometric attendance time in hostel",
        "silence hours in hostel",
    ]
    for q in curfew_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "HOSTEL_CURFEW_RULES_QUERY", f"Query '{q}' classified as {intent}"

    # Safety / wardens / security
    safety_queries = [
        "is hostel safe for girls",
        "who is the girls hostel warden",
        "hostel warden contact number",
        "security in campus hostels",
        "warden details",
    ]
    for q in safety_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "HOSTEL_SAFETY_QUERY", f"Query '{q}' classified as {intent}"

    # Pure hostel fees
    fee_queries = [
        "hostel fee details",
        "what is the hostel fee",
        "hostel charges per year",
        "how much is the room rent for ac hostel",
        "cost of hostel accommodation",
    ]
    for q in fee_queries:
        intent = intents.classify_agent_intent(q)
        assert intent == "HOSTEL_FEE_QUERY", f"Query '{q}' classified as {intent}"


def test_card_service_hostel_cards():
    """Verify that card service distinguishes between facilities card and fee breakdown card."""
    # Facilities query gets facilities card, not fee card
    fac_cards = card_service.generate_cards("tell me about hostel facilities", "Here is hostel info")
    fac_card_types = [c.get("type") for c in fac_cards]
    assert "hostel_facilities" in fac_card_types
    assert "fee_breakdown" not in fac_card_types

    # Fee query gets fee breakdown card
    fee_cards = card_service.generate_cards("what are the hostel fees", "Here are the fees")
    fee_card_types = [c.get("type") for c in fee_cards]
    assert "fee_breakdown" in fee_card_types
    assert "hostel_facilities" not in fee_card_types


def test_fee_flow_non_hijacking():
    """Verify that fee_flow follow-up logic does not hijack facilities queries into fee replies."""
    conv_state = {
        "fee_flow_state": "completed",
        "fee_flow_school": "school_cs_ai",
        "fee_flow_prog": "btech_cse_core",
        "fee_flow_year": "2027-28",
    }
    profile = {}

    # A facilities question must NOT be intercepted by fee_flow
    res_fac = fee_flow.process_fee_flow("tell me about hostel facilities", "test_session", profile, conv_state)
    assert res_fac is None, "Facilities inquiry was hijacked by fee_flow!"

    res_mess = fee_flow.process_fee_flow("how is the mess food?", "test_session", profile, conv_state)
    assert res_mess is None, "Mess inquiry was hijacked by fee_flow!"

    res_curfew = fee_flow.process_fee_flow("what are the curfew timings?", "test_session", profile, conv_state)
    assert res_curfew is None, "Curfew inquiry was hijacked by fee_flow!"

    # Explicit fee inquiry IS handled
    res_fee = fee_flow.process_fee_flow("what are the hostel fee charges?", "test_session", profile, conv_state)
    assert res_fee is not None
    assert "residential hostel charges" in res_fee["text"].lower()


@pytest.mark.asyncio
async def test_agent_hostel_deterministic_replies():
    """Verify that run_agent produces grounded, verified facts for hostel intents."""
    # Test HOSTEL_INFO_QUERY
    events_info = [ev async for ev in agent.run_agent("tell me about hostel facilities", "test_hostel_sess_1")]
    tokens_info = "".join(ev.get("delta", "") for ev in events_info if ev.get("type") == "token")
    cards_info = [ev.get("card", {}).get("type") for ev in events_info if ev.get("type") == "card"]
    assert "Residential Living & Campus Hostels" in tokens_info or "Residential" in tokens_info
    assert "3-sharing" in tokens_info.lower() or "sharing" in tokens_info.lower()
    assert "Sarvepalli" not in tokens_info
    assert "Kalpana Chawla" not in tokens_info
    assert "hostel_facilities" in cards_info

    # Test HOSTEL_MESS_QUERY
    events_mess = [ev async for ev in agent.run_agent("how is the mess food?", "test_hostel_sess_2")]
    tokens_mess = "".join(ev.get("delta", "") for ev in events_mess if ev.get("type") == "token")
    assert "4,000-seat Mega Dining Hall" in tokens_mess
    assert "Breakfast" in tokens_mess
    assert "Lunch" in tokens_mess
    assert "Unlimited Self-Service" in tokens_mess

    # Test HOSTEL_CURFEW_RULES_QUERY
    events_curfew = [ev async for ev in agent.run_agent("what is the in time curfew?", "test_hostel_sess_3")]
    tokens_curfew = "".join(ev.get("delta", "") for ev in events_curfew if ev.get("type") == "token")
    assert "9:00 PM" in tokens_curfew
    assert "9:30 PM" in tokens_curfew
    assert "biometric roll call" in tokens_curfew.lower()
    assert "Sruniv portal" in tokens_curfew

    # Test HOSTEL_SAFETY_QUERY
    events_safety = [ev async for ev in agent.run_agent("is hostel safe for girls and who is the warden?", "test_hostel_sess_4")]
    tokens_safety = "".join(ev.get("delta", "") for ev in events_safety if ev.get("type") == "token")
    assert "Round-the-Clock Security" in tokens_safety
    assert "Aaditya Hospital" in tokens_safety
    assert "Rupesh Mishra" not in tokens_safety
    assert "Anitha GP" not in tokens_safety

    # Test HOSTEL_FEE_QUERY
    events_fee = [ev async for ev in agent.run_agent("what is the hostel fee?", "test_hostel_sess_5")]
    tokens_fee = "".join(ev.get("delta", "") for ev in events_fee if ev.get("type") == "token")
    cards_fee = [ev.get("card", {}).get("type") for ev in events_fee if ev.get("type") == "card"]
    assert "₹1,15,000" in tokens_fee
    assert "₹1,35,000" in tokens_fee
    assert "fee_breakdown" in cards_fee
