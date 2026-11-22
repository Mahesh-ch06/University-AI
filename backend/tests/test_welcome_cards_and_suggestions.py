"""Tests for Welcome Quick-Action Cards and Smart 2+2 Suggestion Chips."""

import pytest
from app.sru_agent import followups
from app.services import card_service


def test_needs_yes_no_detection():
    # Binary / confirmation question patterns -> True
    assert followups.needs_yes_no("Would you like me to calculate your scholarship?") is True
    assert followups.needs_yes_no("Would you like to know about the fee structure?") is True
    assert followups.needs_yes_no("Shall I show you the hostel fee options?") is True
    assert followups.needs_yes_no("Do you want to know about placements at SRU?") is True
    assert followups.needs_yes_no("Can I help you with the admission process?") is True
    assert followups.needs_yes_no("Are you interested in exploring B.Tech CSE?") is True

    # Open-ended questions starting with question words -> False
    assert followups.needs_yes_no("Which program are you interested in?") is False
    assert followups.needs_yes_no("What was your score in Intermediate?") is False
    assert followups.needs_yes_no("How can I help you today?") is False
    assert followups.needs_yes_no("Why choose SR University?") is False
    assert followups.needs_yes_no("Where is the campus located?") is False
    assert followups.needs_yes_no("Who are the top recruiters?") is False

    # Non-questions / statements -> False
    assert followups.needs_yes_no("SR University is ranked #91 by NIRF.") is False
    assert followups.needs_yes_no("") is False
    assert followups.needs_yes_no(None) is False


def test_ensure_fixed_chips_binary_question():
    answer = "The B.Tech CSE tuition is ₹3,40,000/year. Would you like me to calculate your scholarship?"
    chips = followups.ensure_fixed_chips(["Some chip"], answer=answer)
    assert len(chips) == 4
    assert chips[0] == "Yes"
    assert chips[1] == "No"
    assert chips[2] == followups.FIXED_ADMISSION_CHIP
    assert chips[3] == followups.FIXED_UNIVERSITY_CHIP


def test_ensure_fixed_chips_contextual_and_fixed():
    # Contextual chips not overlapping with fixed chips
    ctx = ["AC vs Non-AC room fees", "Mess & dining facilities"]
    chips = followups.ensure_fixed_chips(ctx, answer="Here are the hostel facilities available.")
    assert len(chips) == 4
    assert chips[0] == "AC vs Non-AC room fees"
    assert chips[1] == "Mess & dining facilities"
    # Should include fixed admission & university chips
    assert followups.FIXED_ADMISSION_CHIP in chips or followups.FIXED_ADMISSION_ALT in chips
    assert followups.FIXED_UNIVERSITY_CHIP in chips or followups.FIXED_UNIVERSITY_ALT in chips


def test_ensure_fixed_chips_deduplication():
    # When contextual chips already mention fee/scholarship, it uses the alt admission chip
    ctx = ["B.Tech CSE fees", "Scholarship slabs"]
    chips = followups.ensure_fixed_chips(ctx, answer="Here is the CSE fee.")
    assert len(chips) == 4
    assert len(set(chips)) == 4  # No duplicates
    assert chips[0] == "B.Tech CSE fees"
    assert chips[1] == "Scholarship slabs"
    assert followups.FIXED_ADMISSION_ALT in chips  # Uses "How do I apply for 2027-28?"
    assert followups.FIXED_UNIVERSITY_CHIP in chips


def test_welcome_actions_card_structure():
    card = card_service.WELCOME_ACTIONS_CARD
    assert card["type"] == "welcome_actions"
    assert len(card["items"]) == 4
    titles = [item["title"] for item in card["items"]]
    assert "Explore Programs" in titles
    assert "Calculate Scholarship" in titles
    assert "Fee Structure" in titles
    assert "Campus & Admissions" in titles

    colors = [item["color"] for item in card["items"]]
    assert colors == ["blue", "green", "purple", "amber"]


@pytest.mark.asyncio
async def test_welcome_actions_shown_once_in_agent_workflow():
    from app.sru_agent.agent import run_agent
    from app.sru_agent import memory

    session_id = "test-welcome-card-session-001"
    conv_id = "conv-welcome-001"

    # Seed profile with valid contact details (as if lead form just completed)
    await memory.update_profile(session_id, name="Rahul Sharma", phone="9876543210")

    # Turn 1: Post-lead collection message ("Hi")
    events_t1 = []
    async for ev in run_agent("Hi", session_id, conv_id, require_contact_details=True):
        events_t1.append(ev)

    done_t1 = next(e for e in events_t1 if e["type"] == "done")
    # Verify welcome actions card was emitted
    cards_t1 = done_t1.get("cards", [])
    assert any(c.get("type") == "welcome_actions" for c in cards_t1), "Welcome actions card must be emitted on turn 1"
    assert "Rahul" in done_t1.get("answer", "")
    assert len(done_t1.get("suggestions", [])) == 4

    # Turn 2: User clicks "Explore Programs" or asks a question
    events_t2 = []
    async for ev in run_agent("Explore programs offered at SR University", session_id, conv_id, require_contact_details=True):
        events_t2.append(ev)

    done_t2 = next(e for e in events_t2 if e["type"] == "done")
    # Verify welcome actions card is NOT repeated!
    cards_t2 = done_t2.get("cards", [])
    assert not any(c.get("type") == "welcome_actions" for c in cards_t2), "Welcome actions card must NOT be shown again (only once)"
    assert len(done_t2.get("suggestions", [])) == 4
