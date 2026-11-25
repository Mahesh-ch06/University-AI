"""Tests for engagement features: suggestions, rich cards, guided flows, and streaming."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.schemas.chat import ChatRequest
from app.services.suggestion_service import generate_suggestions
from app.services.card_service import generate_cards
from app.services.flow_service import (
    detect_flow_trigger,
    get_wizard_step_from_history,
    execute_wizard_step,
)
from app.services.chat_service import handle_chat_stream, get_conversational_response


def test_suggestion_generation_eligibility():
    suggestions = generate_suggestions(
        intent="UNIVERSITY",
        user_message="Am I eligible with 93% in 12th?",
        answer="You are fully eligible for B.Tech CSE!",
    )
    assert any("How to Apply" in s for s in suggestions)
    assert len(suggestions) >= 3


def test_suggestion_generation_placements():
    suggestions = generate_suggestions(
        intent="UNIVERSITY",
        user_message="What are the placement statistics?",
        answer="Our highest package is 34 LPA with top recruiters.",
    )
    assert any("Recruiters" in s or "Package" in s for s in suggestions)


def test_suggestion_generation_comparison():
    suggestions = generate_suggestions(
        intent="UNIVERSITY",
        user_message="Compare CSE vs CSE AI and ML",
        answer="CSE covers broad core foundations while AI/ML specializes in data models.",
    )
    assert any("Lab Facilities" in s or "Compare" in s for s in suggestions)


def test_cards_comparison():
    cards = generate_cards(
        user_message="What is the difference between CSE and CSE AIML?",
        answer="Here is a breakdown of CSE vs AIML.",
    )
    assert len(cards) >= 1
    assert cards[0]["type"] == "comparison"
    assert len(cards[0]["columns"]) == 2


def test_cards_fee_breakdown():
    """The all-branch fee table is attached only when the student asks to see / compare every branch."""
    cards = generate_cards(
        user_message="Compare the fee structure of all B.Tech branches",
        answer="The tuition fee is ₹1,47,500 per semester.",
    )
    assert any(c.get("type") == "fee_breakdown" for c in cards)
    # "fee details" with no programme (or one programme) never gets the all-branch table
    for msg in ("What are the fee details?", "What is the complete fee structure and merit scholarship details for B.Tech?"):
        assert not any(c.get("type") == "fee_breakdown" for c in generate_cards(user_message=msg, answer=""))


def test_cards_curriculum():
    cards = generate_cards(
        user_message="What is the curriculum and subjects for CSE?",
        answer="The curriculum has core and elective components.",
    )
    assert len(cards) >= 1
    assert cards[0]["type"] == "curriculum"
    assert len(cards[0]["structure"]) >= 3


def test_cards_campus_tour():
    cards = generate_cards(
        user_message="Tell me about campus facilities and hostels",
        answer="SR University has a vibrant campus.",
    )
    assert any(c["type"] == "campus_tour" for c in cards)


def test_flow_trigger_detection():
    assert detect_flow_trigger("I want to start the admission wizard") == "admission_wizard"
    assert detect_flow_trigger("guided admission please") == "admission_wizard"
    assert detect_flow_trigger("random query") is None


def test_wizard_step_progression():
    # Step 1
    step1 = get_wizard_step_from_history([], "admission wizard")
    assert step1["step"] == 1
    assert "B.Tech" in step1["options"][0]

    # Step 2: after B.Tech selected
    step2 = get_wizard_step_from_history([{"role": "user", "content": "admission wizard"}], "B.Tech")
    assert step2["step"] == 2
    assert "CSE" in step2["options"][0]

    # Step 3: after branch selected
    step3 = get_wizard_step_from_history(
        [
            {"role": "user", "content": "admission wizard"},
            {"role": "user", "content": "B.Tech"},
        ],
        "CSE",
    )
    assert step3["step"] == 3

    # Step 4: after score selected (93%)
    step4 = get_wizard_step_from_history(
        [
            {"role": "user", "content": "admission wizard"},
            {"role": "user", "content": "B.Tech"},
            {"role": "user", "content": "CSE"},
        ],
        "93%",
    )
    assert step4["step"] == 4
    # The verdict comes from eligibility.py when the step is rendered
    text, info = execute_wizard_step(step4)
    assert "meets the minimum marks" in text and info["is_eligible"] is not False


def test_wizard_completion_prevents_loop():
    """Verify that once Step 4 is rendered, subsequent queries (like Hostel Details) exit the wizard."""
    step4_answer, _ = execute_wizard_step({
        "flow_name": "admission_wizard",
        "step": 4,
        "total_steps": 4,
        "step_title": "Eligibility Verdict & Next Steps",
        "degree": "B.Tech",
        "branch": "CSE (Core)",
        "score": "78%",
        "is_eligible": True,
        "completed": True,
    })
    history = [
        {"role": "user", "content": "admission wizard"},
        {"role": "assistant", "content": "Welcome to the SR University Admission Wizard! (Step 1 of 4)"},
        {"role": "user", "content": "B.Tech"},
        {"role": "assistant", "content": "Step 2 of 4: Select Your Branch"},
        {"role": "user", "content": "CSE"},
        {"role": "assistant", "content": "Step 3 of 4: Qualifying Percentage"},
        {"role": "user", "content": "78%"},
        {"role": "assistant", "content": step4_answer},
    ]

    # Follow-up button click or question must NOT re-trigger step 4
    next_step = get_wizard_step_from_history(history, "🏠 Hostel Details")
    assert next_step is None

    next_step_fee = get_wizard_step_from_history(history, "💰 Fee Structure")
    assert next_step_fee is None

    next_step_general = get_wizard_step_from_history(history, "What is the hostel fee?")
    assert next_step_general is None


def test_calculator_handoff_query_does_not_trigger_wizard():
    """Verify calculator handoff query does NOT falsely hijack into admission wizard."""
    calc_query = (
        "I evaluated the scholarship for B.Tech Computer Science and Engineering with 78% "
        "which qualifies for a 20% merit waiver (Payable: ₹60,000/sem). "
        "Please share details on admission verification and hostel accommodation."
    )
    assert detect_flow_trigger(calc_query) is None
    assert get_wizard_step_from_history([], calc_query) is None


def test_wizard_eligibility_50_percent_cutoff():
    """The wizard uses eligibility.py: below every documented minimum is not eligible, and a score between
    the fee card's 50% and the programme page's 60% for B.Tech is reported as needing confirmation."""
    step4_55 = get_wizard_step_from_history(
        [
            {"role": "user", "content": "admission wizard"},
            {"role": "user", "content": "B.Tech"},
            {"role": "user", "content": "CSE"},
        ],
        "55%",
    )
    text55, info55 = execute_wizard_step(step4_55)
    # 2027-28 circular: 55% is the B.Tech CSE minimum (inclusive); meeting it is not a guarantee of admission
    assert info55["is_eligible"] is not False
    assert "meets the minimum marks (**55%**" in text55 and "fully eligible" not in text55.lower()

    # 45% should require additional guidance (below 50% cutoff)
    step4_45 = get_wizard_step_from_history(
        [
            {"role": "user", "content": "admission wizard"},
            {"role": "user", "content": "B.Tech"},
            {"role": "user", "content": "CSE"},
        ],
        "45%",
    )
    text45, info45 = execute_wizard_step(step4_45)
    assert info45["is_eligible"] is False
    assert "below the official **55% minimum**" in text45


def test_wizard_cancellation():
    """Verify that users can exit the wizard with cancel/stop keywords."""
    history = [
        {"role": "user", "content": "admission wizard"},
        {"role": "assistant", "content": "Welcome to the SR University Admission Wizard! (Step 1 of 4)"},
    ]
    assert get_wizard_step_from_history(history, "cancel") is None
    assert get_wizard_step_from_history(history, "stop") is None
    assert get_wizard_step_from_history(history, "nevermind") is None


def test_time_aware_greeting():
    greeting = get_conversational_response("GREETING", has_context=False)
    assert "SRU Buddy" in greeting or "SR University" in greeting


def test_btech_cse_join_and_fee_card():
    """Verify that asking to join B.Tech CSE yields both per-semester fee breakdown and the Early Bird Ad Card."""
    cards = generate_cards(
        user_message="I want to join B.Tech CSE",
        answer="We would be delighted to have you join B.Tech CSE! Here is the per-semester fee breakdown.",
    )
    assert len(cards) >= 2
    types = [c.get("type") for c in cards]
    assert "fee_breakdown" in types
    assert "application_ad" in types

    # Check fee card details
    fee_card = next(c for c in cards if c.get("type") == "fee_breakdown")
    assert "B.Tech CSE" in fee_card["title"]
    categories = [item["category"] for item in fee_card["items"]]
    assert any(cat.startswith("Semester 1") for cat in categories)
    assert any("Enrollment" in cat for cat in categories)

    # Check Ad card details (media_1794676975023.png reference)
    ad_card = next(c for c in cards if c.get("type") == "application_ad")
    assert "SR University Admissions" in ad_card["sponsor_name"]
    assert "50% Off" in ad_card["title"]
    assert "https://apply.sru.edu.in" in ad_card["cta_url"]


def test_application_ad_card_on_discount_query():
    """Verify that asking for early bird application discount attaches the Ad Card."""
    cards = generate_cards(
        user_message="Is there any 50% off on online application early bird offer?",
        answer="Yes, early applicants get a 50% waiver on the online application fee.",
    )
    assert any(c.get("type") == "application_ad" for c in cards)


def test_application_ad_on_interested_to_join_sru():
    """Verify that asking general 'interested to join SRU' questions attaches the compact Ad Card."""
    queries = [
        "I am interested to join SR University",
        "How can I join SRU?",
        "I want to take admission in SRU",
        "How do I apply to SRU for 2027-28?",
    ]
    for q in queries:
        cards = generate_cards(user_message=q, answer="Welcome to SR University!")
        types = [c.get("type") for c in cards]
        assert "application_ad" in types, f"Expected application_ad card for query: {q}"
        ad_card = next(c for c in cards if c.get("type") == "application_ad")
        assert "50% Off" in ad_card["title"]
        assert "https://apply.sru.edu.in" in ad_card["cta_url"]



def test_btech_cse_semester_fee_structure():
    """B.Tech CSE standard fee, semester by semester, from the fee engine: only tuition is split."""
    from app.services.card_service import BTECH_CSE_SEMESTER_FEE_CARD
    items = {i["category"]: i["amount"] for i in BTECH_CSE_SEMESTER_FEE_CARD["items"]}
    assert items["Semester 1: Tuition"] == items["Semester 2: Tuition"] == "₹1,70,000"
    assert items["Semester 1: Enrollment fee"] == "₹5,000"
    assert items["Semester 1: Other fee"] == "₹15,000" and items["Semester 1: Exam fee (Year 1)"] == "₹5,000"
    assert "Semester 2: Other fee" not in items and "Semester 2: Enrollment fee" not in items
    assert items["Semester 1 payable"] == "₹1,95,000" and items["Semester 2 payable"] == "₹1,70,000"
    assert items["First-year payable"] == "₹3,65,000"


def test_btech_cse_fee_without_hostel_does_not_add_hostel():
    """Asking for the B.Tech CSE fee without hostel never adds a hostel fee."""
    from app.services.card_service import generate_cards
    cards = generate_cards(
        user_message="What is the fee breakdown for B.Tech CSE per semester?",
        answer="Here is the per semester fee breakdown for B.Tech CSE.",
    )
    fee_card = next(c for c in cards if c.get("type") == "fee_breakdown")
    assert "B.Tech CSE" in fee_card["title"] and "Hostel" not in fee_card["title"]
    assert not any("Hostel" in item["category"] for item in fee_card["items"])
    item_map = {i["category"]: i["amount"] for i in fee_card["items"]}
    assert item_map.get("Semester 1 payable") == "₹1,95,000"
    assert item_map.get("Semester 2 payable") == "₹1,70,000"


def test_btech_cse_fee_with_hostel_adds_hostel_per_sem():
    """Asking for the fee WITH hostel adds the hostel (and its one-time deposit) where the policy places them."""
    from app.services.card_service import generate_cards
    cards = generate_cards(
        user_message="I want to join B.Tech CSE with hostel, what is the total fee breakdown per sem?",
        answer="Here is the total per-semester fee breakdown including tuition and hostel.",
    )
    fee_card = next(c for c in cards if c.get("type") == "fee_breakdown")
    assert "Hostel" in fee_card["title"]
    item_map = {i["category"]: i["amount"] for i in fee_card["items"]}
    assert item_map["Semester 1: Hostel (AC, 4-sharing)"] == "₹1,25,000"
    assert item_map["Semester 1: Electricity deposit (hostel)"] == "₹10,000"
    assert item_map.get("Semester 1 payable") == "₹3,30,000"
    assert item_map.get("Semester 2 payable") == "₹1,70,000"


def test_calculate_fee_conditional_hostel():
    """Hostel is optional: never added unless asked, and then placed by the policy (not split by half)."""
    from app.sru_agent.fees import calculate_fee

    res_no_hostel = calculate_fee(program="btech_cse", hostel="none")
    assert res_no_hostel["has_hostel"] is False and res_no_hostel["hostel"] is None
    assert res_no_hostel["sem1_total_payable"] == "₹1,95,000"
    assert res_no_hostel["sem2_total_payable"] == "₹1,70,000"
    assert not any(i["key"] in ("hostel", "electricity_deposit") for i in res_no_hostel["semester_1"]["items"])

    res_with_hostel = calculate_fee(program="btech_cse", hostel="ac_4")
    assert res_with_hostel["has_hostel"] is True and res_with_hostel["hostel"]["per_year"] == "₹1,25,000"
    s1 = {i["key"]: i["amount"] for i in res_with_hostel["semester_1"]["items"]}
    assert s1["hostel"] == "₹1,25,000" and s1["electricity_deposit"] == "₹10,000"
    assert res_with_hostel["sem1_total_payable"] == "₹3,30,000"
    assert res_with_hostel["sem2_total_payable"] == "₹1,70,000"
    # the one-time deposit is not repeated in later years
    assert not any(i["key"] == "electricity_deposit" for y in res_with_hostel["schedule"][1:]
                   for s in y["semesters"] for i in s["items"])


@pytest.fixture(autouse=True)
def _early_bird_offer_on(monkeypatch, request):
    """The advertisement tests above check how the card behaves WHEN the offer is switched on.
    It is off by default (not on the 2027-28 fee card); see test_early_bird_offer_is_off_by_default."""
    if request.node.name != "test_early_bird_offer_is_off_by_default":
        from app.config import settings
        monkeypatch.setattr(settings, "SHOW_EARLY_BIRD_OFFER", True)


def test_early_bird_offer_is_off_by_default():
    from app.config import Settings
    from app.services.card_service import generate_cards
    assert Settings().SHOW_EARLY_BIRD_OFFER is False
    cards = generate_cards(user_message="I want to join SRU, how do I apply?", answer="")
    assert not any(c.get("type") == "application_ad" for c in cards)
