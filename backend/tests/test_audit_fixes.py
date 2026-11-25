"""Tests verifying fixes for audit issues identified in conversation logs."""
import pytest
from datetime import date
from app.sru_agent import tools, intents, fee_flow, agent


def test_academic_marks_not_parsed_as_visit_dates():
    """Verify that 10th/12th marks or boards are never parsed as calendar days."""
    today = date(2026, 11, 20)
    
    # Queries from PDF audit
    assert tools.resolve_campus_visit_date("Scholarship for 978 marks i. 12th", today=today)["date"] is None
    assert tools.resolve_campus_visit_date("scholarship for 12th marks", today=today)["date"] is None
    assert tools.resolve_campus_visit_date("what is the cutoff for 10th and 12th", today=today)["date"] is None
    assert tools.resolve_campus_visit_date("I got 95% in 12th board", today=today)["date"] is None
    
    # Legitimate visit dates should still resolve correctly
    res_visit = tools.resolve_campus_visit_date("I want to visit on 25th", today=today)
    assert res_visit["date"] == date(2026, 11, 25)
    
    res_tmrw = tools.resolve_campus_visit_date("visit tomorrow", today=today)
    assert res_tmrw["date"] == date(2026, 11, 21)


def test_intent_active_topic_not_hijacked_by_marks():
    """Verify active_topic='campus_visit' doesn't hijack academic/fee queries."""
    state = {"active_topic": "campus_visit"}
    
    # Should NOT classify as visit booking
    intent = intents.classify_agent_intent("Scholarship for 978 marks i. 12th", state=state)
    assert intent != "CAMPUS_VISIT_BOOKING_WITH_DATE"
    
    intent_vc = intents.classify_agent_intent("tell about VC", state=state)
    assert intent_vc != "CAMPUS_VISIT_BOOKING_WITH_DATE"


def test_campus_canteen_and_academic_evaluation_intents():
    """Verify routing to new specialized intents."""
    # Campus canteen & food stalls
    assert intents.classify_agent_intent("does the campus have food stalls and various food options") == "CAMPUS_CANTEEN_QUERY"
    assert intents.classify_agent_intent("is there a cafeteria on campus") == "CAMPUS_CANTEEN_QUERY"
    assert intents.classify_agent_intent("tell me about tasty treat and food kiosks") == "CAMPUS_CANTEEN_QUERY"
    
    # Academic evaluation & pass marks
    assert intents.classify_agent_intent("B tech exams total marks and passmarks") == "ACADEMIC_EVALUATION_QUERY"
    assert intents.classify_agent_intent("what are cie and ese marks") == "ACADEMIC_EVALUATION_QUERY"
    assert intents.classify_agent_intent("passing marks in sru semester exams") == "ACADEMIC_EVALUATION_QUERY"
    assert intents.classify_agent_intent("grading scale 10-point scale") == "ACADEMIC_EVALUATION_QUERY"
    
    # Combined fee queries
    assert intents.classify_agent_intent("Add hostel to my B.Tech CSE fee") == "COMBINED_FEE_HOSTEL_QUERY"
    assert intents.classify_agent_intent("total fee including hostel") == "COMBINED_FEE_HOSTEL_QUERY"
    assert intents.classify_agent_intent("combine my entire one sem fee of both hostel and college") == "COMBINED_FEE_HOSTEL_QUERY"
    
    # Standalone hostel fee queries
    assert intents.classify_agent_intent("what is the hostel fee") == "HOSTEL_FEE_QUERY"


def test_fee_flow_awaiting_school_selection_escape():
    """Verify user can escape awaiting_school_selection trap when asking about VC or general info."""
    state = {"fee_flow_state": "awaiting_school_selection"}
    profile = {}
    
    # Asking about VC should escape fee flow
    res = fee_flow.process_fee_flow("tell about VC", "sess_1", profile, state)
    assert res is None
    assert state.get("fee_flow_state") is None
    
    # Cancel should escape
    state2 = {"fee_flow_state": "awaiting_school_selection"}
    res2 = fee_flow.process_fee_flow("no need, cancel", "sess_1", profile, state2)
    assert res2 is None
    assert state2.get("fee_flow_state") is None


def test_fee_flow_total_not_intercepting_exam_marks():
    """Verify that asking for exam total marks doesn't trigger total cost breakdown in completed state."""
    state = {
        "fee_flow_state": "completed",
        "fee_flow_school": "cs_ai",
        "fee_flow_prog": "btech_cse",
        "fee_flow_year": "2027-28",
    }
    profile = {}
    
    # "B tech exams total marks and passmarks" should NOT be intercepted as total fee!
    res = fee_flow.process_fee_flow("B tech exams total marks and passmarks", "sess_1", profile, state)
    assert res is None
    
    # Genuine total fee query SHOULD trigger total cost breakdown
    res_total = fee_flow.process_fee_flow("total cost for btech cse", "sess_1", profile, state)
    assert res_total is not None
    assert "total cost breakdown" in res_total["text"].lower()


def test_fee_flow_combined_hostel_and_tuition():
    """Verify combined hostel + tuition calculation in completed and initial states."""
    state = {
        "fee_flow_state": "completed",
        "fee_flow_school": "cs_ai",
        "fee_flow_prog": "btech_cse",
        "fee_flow_year": "2027-28",
    }
    profile = {}
    
    res = fee_flow.process_fee_flow("Add hostel to my B.Tech CSE fee", "sess_1", profile, state)
    assert res is not None
    assert "combined fee breakdown" in res["text"].lower()
    assert "Semester 1 payable: ₹3,30,000" in res["text"] and "₹1,70,000" in res["text"]
    assert len(res["cards"]) == 1
    assert res["cards"][0]["type"] == "fee_breakdown"
    
    # Initial trigger with combined hostel request
    state_init = {}
    res_init = fee_flow.process_fee_flow("btech cse fee with hostel", "sess_2", profile, state_init)
    assert res_init is not None
    assert "combined fee breakdown" in res_init["text"].lower()
    assert len(res_init["cards"]) == 1


@pytest.mark.asyncio
async def test_agent_canteen_and_academic_responses():
    """Verify canonical agent responses for canteen and academic evaluation."""
    events_canteen = [
        ev async for ev in agent.run_agent(
            "does the campus have food stalls and various food options",
            "sess_canteen",
            require_contact_details=False,
        )
    ]
    canteen_text = "".join(ev.get("delta", "") for ev in events_canteen if ev.get("type") == "token")
    assert "Central Cafeteria" in canteen_text
    assert "Tasty Treat" in canteen_text
    assert "8:30 AM" in canteen_text and "6:00 PM" in canteen_text

    events_acad = [
        ev async for ev in agent.run_agent(
            "B tech exams total marks and passmarks",
            "sess_acad",
            require_contact_details=False,
        )
    ]
    acad_text = "".join(ev.get("delta", "") for ev in events_acad if ev.get("type") == "token")
    assert "Continuous Internal Evaluation (CIE)" in acad_text
    assert "Minimum Pass Grade (40% aggregate for UG)" in acad_text
