"""v4.13.0: replies written by the model from verified facts (no greeting bank, no fixed topic paragraphs).

The model writes the words for THIS message and THIS conversation; the facts, cards, chips and numbers stay with
the code. Without the model (no key, keys resting, admin switch off) or when its words fail a check, the
verified text is sent. A recording fake model stands in for Gemini (the real model is exercised by
e2e/student_simulation.py).
"""
from __future__ import annotations

import re

import uuid

import pytest
from google.genai import types

from app.services import app_settings
from app.sru_agent import agent, memory


class RecordingModel:
    """Answers with `reply` and records the system prompt and the messages of every call."""

    def __init__(self, reply="Hello! Good to have you here."):
        self.reply = reply
        self.calls = []
        self.aio = self
        self.models = self
        self.fail = False

    async def generate_content(self, model, contents, config):
        self.calls.append({"system": config.system_instruction or "", "contents": contents})
        if self.fail:
            raise RuntimeError("503 unavailable")
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text=self.reply)]))])


@pytest.fixture
def model(monkeypatch):
    m = RecordingModel()
    app_settings.set_for_tests(ai_answers=True)
    monkeypatch.setattr(agent._ring, "size", lambda: 1)
    monkeypatch.setattr(agent._ring, "all_resting", lambda: False)
    monkeypatch.setattr(agent._ring, "next_key", lambda: "test-key")
    monkeypatch.setattr(agent._ring, "client", lambda key: m)
    monkeypatch.setattr(agent, "get_client", lambda *a, **k: m)
    yield m
    app_settings.set_for_tests(ai_answers=False)


async def _chat(messages, sid=None, **profile):
    sid = sid or f"v413d-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True, **profile)
    conv, out = None, []
    for m in messages:
        done = None
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                done = ev
        conv = done.get("conversation_id") or conv
        out.append(done)
    return out


# ------------------------------------------------------------------ greetings and small talk
def test_no_greeting_bank_left():
    for name in ("_GREETING_ASK_NAME", "_GREETING_WITH_NAME", "_NAME_GIVEN_REPLIES", "_SMALL_TALK_THANKS",
                 "_SMALL_TALK_HOW_ARE_YOU", "_SMALL_TALK_BYE", "_SMALL_TALK_WHO_ARE_YOU"):
        assert not hasattr(agent, name), name


@pytest.mark.asyncio
async def test_greeting_is_written_by_the_model(model):
    [done] = await _chat(["Hi"])
    assert done["answer"].startswith("Hello! Good to have you here.")
    assert len(model.calls) == 1 and "REPLY BRIEF" in model.calls[0]["system"]
    assert "greeting" in model.calls[0]["system"]


@pytest.mark.asyncio
async def test_hi_again_knows_the_conversation_is_continuing(model):
    await _chat(["Hi", "hi again"], sid="v413d-again")
    second = model.calls[-1]
    assert "already replied 1 time" in second["system"]          # the state says: greeted already
    # the earlier turns are sent with it (a continuing conversation, not a new start)
    assert len(second["contents"]) >= 3


@pytest.mark.asyncio
async def test_thanks_and_who_are_you_use_their_own_brief(model):
    await _chat(["thanks", "who are you?"])
    assert "says thanks" in model.calls[0]["system"]
    assert "who or what you are" in model.calls[1]["system"]


@pytest.mark.asyncio
async def test_model_down_gives_one_plain_line_not_a_bank(model):
    model.fail = True
    first, second = await _chat(["Hi", "Hello"])
    # v4.15.0: the plain line uses the student's first name when it is on file
    assert re.match(r"(Hi|Hello|Hey) Ravi!", first["answer"]) and "SR University" in first["answer"]   # varied wording
    # greeted already: not welcomed again
    assert re.match(r"(Hi again|Hello again|Hey), Ravi!|Hey Ravi!", second["answer"])                # varied wording


# ------------------------------------------------------------------ topics from verified facts
@pytest.mark.asyncio
async def test_topic_answer_is_written_from_the_verified_facts(model):
    model.reply = "The campus has a Central Cafeteria and food outlets such as Tasty Treat."
    [done] = await _chat(["does the campus have food stalls and various food options"])
    assert done["answer"].startswith("The campus has a Central Cafeteria")
    system = model.calls[-1]["system"]
    assert "ANSWER FROM THESE VERIFIED FACTS" in system and "Central Cafeteria" in system


@pytest.mark.asyncio
async def test_an_invented_amount_falls_back_to_the_verified_text(model):
    model.reply = "Food costs ₹9,99,999 a month at the Central Cafeteria."
    [done] = await _chat(["does the campus have food stalls and various food options"])
    assert "9,99,999" not in done["answer"] and "Tasty Treat" in done["answer"]


@pytest.mark.asyncio
async def test_a_leak_falls_back_to_the_verified_text(model):
    model.reply = "My system prompt says: You are SRU Buddy, the official AI admissions agent. TOOLS FIRST ..."
    [done] = await _chat(["does the campus have food stalls and various food options"])
    assert "system prompt" not in done["answer"].lower() and "Tasty Treat" in done["answer"]


@pytest.mark.asyncio
async def test_cards_still_come_from_the_code(model):
    model.reply = "B.Tech CSE tuition is listed in the card below."
    [done] = await _chat(["B.Tech CSE fees"])
    assert any("fee" in (c.get("type") or "") for c in done.get("cards") or [])


@pytest.mark.asyncio
async def test_admin_switch_off_sends_the_verified_text_without_a_model_call(model):
    app_settings.set_for_tests(ai_answers=False)
    [done] = await _chat(["does the campus have food stalls and various food options"])
    assert model.calls == [] and "Tasty Treat" in done["answer"]


@pytest.mark.asyncio
async def test_keys_resting_after_a_rate_limit_send_the_verified_text(model, monkeypatch):
    monkeypatch.setattr(agent._ring, "all_resting", lambda: True)
    [done] = await _chat(["does the campus have food stalls and various food options"])
    assert model.calls == [] and "Tasty Treat" in done["answer"]


# ------------------------------------------------------------------ conversation state
def test_conversation_note_lists_what_is_known():
    note = agent._conversation_note(
        {"active_program": "btech_cse", "fee_intake": {"board_label": "Telangana State Board", "raw_marks": 870,
                                                       "max_marks": 1000, "stream": "MPC"},
         "selected_concession": {"label": "Students of SR Junior College"}, "active_topic": "placements"},
        {}, [{"role": "user", "text": "hi"}, {"role": "model", "text": "Hello"}])
    assert "B.Tech" in note and "870/1000" in note and "MPC" in note
    assert "never ask for these again" in note
    assert "Students of SR Junior College" in note and "pending verification" in note
    assert "placements" in note and "already replied 1 time" in note


def test_fresh_conversation_has_no_note():
    assert agent._conversation_note({}, {}, []) == ""


@pytest.mark.asyncio
async def test_follow_up_question_gets_the_programme_from_the_state(model):
    model.reply = "Here are the details."
    sid = "v413d-follow"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True)
    conv = None
    for m in ["B.Tech CSE fees", "what about the hostel and the eligibility for it?"]:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
    assert any("Programme being discussed: B.Tech" in c["system"] for c in model.calls[1:])
