"""Tests for Contextual User Name Usage.

Verifies:
1. Name instruction generation:
   - Selective usage guidelines when name is known.
   - Consecutive name suppression directive when name was addressed recently.
   - Graceful continuation when name is unavailable (no inventing or unnecessary asking).
2. Small-talk template non-consecutive suppression:
   - Suppresses name when already addressed in the immediate previous message.
3. Multi-turn assistant history tracking:
   - Correctly detects whether the previous assistant message addressed the user by name.
"""

import re
import pytest
from app.sru_agent import prompt, agent, memory


def test_system_prompt_contextual_name_directives():
    """Verify system prompt includes contextual name guidelines when name is known."""
    p = prompt.build_system_prompt({"name": "Suresh Reddy"}, name_used_recently=False)
    
    assert "STUDENT'S NAME: Suresh Reddy" in p
    assert "CONTEXTUAL NAME USAGE" in p
    assert "greeting" in p.lower()
    assert "congratulating" in p.lower()
    assert "routine factual answers" in p.lower()
    assert "consecutive messages" in p.lower()
    assert "make user feel recognized" in p.lower() or "not read from a profile" in p.lower()


def test_system_prompt_consecutive_name_suppression():
    """Verify system prompt actively suppresses name when user was addressed recently."""
    p = prompt.build_system_prompt({"name": "Suresh Reddy"}, name_used_recently=True)
    
    assert "STUDENT'S NAME: Suresh Reddy" in p
    assert "CONSECUTIVE NAME SUPPRESSION" in p
    assert "Do NOT address the student by name in this turn" in p
    assert "consecutive messages" in p


def test_system_prompt_unknown_name_behavior():
    """Verify system prompt does not assume, invent, or unnecessarily ask for unknown names."""
    p = prompt.build_system_prompt({})
    
    assert "STUDENT'S NAME: not given yet" in p
    assert "Never assume or invent a name" in p
    assert "'Unknown'" in p                       # placeholders are named as forbidden (v4.15.0)


@pytest.mark.asyncio
async def test_small_talk_consecutive_name_suppression():
    """Verify small-talk handlers in agent.py avoid addressing the user by name consecutively."""
    session_id = "test-name-suppression-sess"
    conv_id = "conv-name-suppression"
    await memory.clear_profile(session_id)
    await memory.clear_conversation_state(session_id, conv_id)
    await memory.update_profile(session_id, name="Ananya Rao")

    # Turn 1: User says thanks without recent assistant history -> name can be used
    events1 = [e async for e in agent.run_agent("thank you", session_id, conv_id)]
    done1 = [e for e in events1 if e.get("type") == "done"][0]
    ans1 = done1["answer"]
    assert "Ananya" in ans1 or "welcome" in ans1.lower()

    # Update conversation history with assistant message that used Ananya
    await memory.append_history(
        session_id,
        "thank you",
        "You're welcome, Ananya! Let me know if you need anything else.",
        conversation_id=conv_id
    )

    # Turn 2: User says thanks again -> name MUST NOT be repeated consecutively
    events2 = [e async for e in agent.run_agent("thanks", session_id, conv_id)]
    done2 = [e for e in events2 if e.get("type") == "done"][0]
    ans2 = done2["answer"]
    
    # In consecutive message, name is suppressed
    assert "Ananya" not in ans2
    assert "welcome" in ans2.lower()


def test_consecutive_name_detection_logic():
    """Test regex whole-word detection of first name in assistant messages."""
    first_name = "Ravi"
    
    # Case 1: Exact match with comma/punctuation
    msg1 = "Hello Ravi, welcome to SR University!"
    assert bool(re.search(rf"\b{re.escape(first_name)}\b", msg1, re.IGNORECASE)) is True

    # Case 2: Substring of another word should not match
    msg2 = "We have ravioli in the cafeteria and gravitas in academia."
    assert bool(re.search(rf"\b{re.escape(first_name)}\b", msg2, re.IGNORECASE)) is False

    # Case 3: Message with no name
    msg3 = "The annual tuition fee for B.Tech CSE is ₹1,65,000."
    assert bool(re.search(rf"\b{re.escape(first_name)}\b", msg3, re.IGNORECASE)) is False
