"""v4.13.0: one message with several questions (Nikhil's decomposition) answered part by part, safely.

Splitting a message must never take it away from a flow that understands it better (callbacks, marks,
visits, programme fees, a button's own answer, our pending question), and every part must be answered from
verified content. Rules: app/sru_agent/compound.py. The chat runs as in production (no model client).
"""
from __future__ import annotations

import re
import uuid

import pytest
from google.genai import types

from app.sru_agent import agent, compound, dialogue, fee_journey, fees, memory


class FakeModel:
    def __init__(self):
        self.calls = 0
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.calls += 1
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text="Side answer.")]))])


@pytest.fixture(autouse=True)
def model(monkeypatch):
    m = FakeModel()
    monkeypatch.setattr(agent, "get_client", lambda *a, **k: m)
    return m


async def _chat(messages, sid=None, **profile):
    sid = sid or f"v413-{uuid.uuid4().hex[:10]}"
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


# ------------------------------------------------------------------ 1. when a message is split
@pytest.mark.parametrize("message, topics", [
    ("about sru and about hostels", ["about_sru", "hostel_info"]),
    ("cse vs aiml and why sru", ["cse_vs_aiml", "why_sru"]),
    ("What are the fees and hostel timings?", ["fees_ask", "hostel_curfew"]),
    ("B.Tech CSE fees and placements", ["fees", "placements"]),
    ("placements and scholarships", ["placements", "scholarships"]),
])
def test_genuine_multi_questions_are_split(message, topics):
    assert [t for _, t in compound.plan(message)] == topics


@pytest.mark.parametrize("message", [
    # actions and the student's own data go to the flows that save leads, calculate fees and book visits
    "please call me, Priya Sharma 9876512345. also is hostel available for girls?",
    "i got 85% and want cse",
    "can my parents also come for the campus visit and what are the timings?",
    "I want to apply and know the hostel fees",
    "talk to a counsellor and also tell me about placements",
    # one question, written with "and"
    "What are all the programs and courses available at SR University?",
    "How big is the campus and what infrastructure does it have?",
    "does the campus have food stalls and various food options",
    # button labels
    "Fee & scholarships",
    "Placements & Careers",
    # another programme's fees: the fee flow knows every programme, the split only knows B.Tech CSE
    "MBA fees and hostel facilities",
])
def test_messages_that_must_not_be_split(message):
    assert compound.plan(message) is None


def test_comparison_text_only_for_cse_vs_aiml():
    assert compound.topic("ece vs mech", "ece vs mech and why sru") is None
    assert compound.topic("cse vs aiml", "cse vs aiml and why sru") == "cse_vs_aiml"


def test_timings_belong_to_the_hostel_only_when_the_message_is_about_it():
    assert compound.topic("what are the timings", "visit and what are the timings") is None
    assert compound.topic("timings", "hostel fees and timings") == "hostel_curfew"


# ------------------------------------------------------------------ 2. every part is verified
def test_scholarship_overview_is_written_from_the_official_slabs():
    text = compound.scholarship_overview_text()
    data = fees.load_data()
    slab_set = data["slab_sets"][data["programs"]["btech_cse"]["slab_set"]]
    for kind, table in slab_set.items():
        for slab in table:
            assert f"{fees._range_text(kind, slab)} → **{slab['percent']}%**" in text, (kind, slab)
    # the calculator and the overview agree (the hand-typed text said 40% for 95-97.9%)
    assert fees.scholarship_for("btech_cse", percent=96)["percent"] == 30
    assert "92 – 97.9% → **30%**" in text
    assert "(AIML, Data Science" not in text and "**B.Tech CSE**" in text


@pytest.mark.asyncio
async def test_fees_without_a_programme_ask_which_programme_never_cse():
    [done] = await _chat(["What are the fees and hostel timings?"])
    answer = done["answer"]
    assert "Which programme are you considering?" in answer
    assert re.search(r"curfew|in-?time|timing", answer, re.I)
    assert not any("fee" in (c.get("type") or "") and "cse" in str(c).lower() for c in done.get("cards") or [])


@pytest.mark.asyncio
async def test_cse_fees_and_placements_answer_both():
    [done] = await _chat(["B.Tech CSE fees and placements"])
    answer = done["answer"]
    assert "B.Tech" in answer and "₹" in answer
    assert re.search(r"placement", answer, re.I)


# ------------------------------------------------------------------ 3. the flows keep their messages
@pytest.mark.asyncio
async def test_marks_and_programme_in_one_message_still_go_to_the_agent(model):
    # the model (with its remember/calculate tools) gets the whole message; it is not cut in two
    # (test_agent_loop checks the tools it then calls)
    [done] = await _chat(["i got 85% and want cse"])
    assert model.calls >= 1 and "---" not in done["answer"]


def test_pending_question_answer_is_not_skipped_by_the_split():
    state = {"dialogue": {"step": "program", "goal": "eligibility"}}
    assert dialogue._decide("CSE and AIML", state, {}) is not None
    # with nothing pending, a multi-question message is not taken over by a topic menu
    assert dialogue._decide("about sru and about hostels", {}, {}) is None


@pytest.mark.asyncio
async def test_about_sru_in_detail_keeps_its_answer():
    # "ai" inside "detail" used to drop this question to the model
    [done] = await _chat(["Tell me about SR University in detail"])
    assert "Side answer." not in done["answer"]


@pytest.mark.asyncio
async def test_side_multi_question_during_a_fee_evaluation_keeps_the_continue_button():
    steps = ["Calculate my scholarship", "B.Tech CSE", "Telangana State Board", "Completed", "870", "MPC",
             "None of these apply"]
    out = await _chat(steps + ["about sru and about hostels"])
    last = out[-1]
    assert "---" in last["answer"]
    assert fee_journey.RESUME in (last.get("suggestions") or [])
