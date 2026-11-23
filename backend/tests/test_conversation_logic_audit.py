"""Conversation-logic audit (Nov 2026): eligibility accuracy, clarification of broad questions, incomplete
messages, context across turns and programme relevance.

The agent is driven with ``ProdModel``, a recording stand-in for Gemini whose class name is NOT in the
agent's test-client list, so every message takes the same code path as in production. It records each
request (the student's message as the AI received it, and the system prompt) and answers with a short
scripted text. ``model.calls == 0`` therefore proves a reply was produced by code without any AI call.
"""
import uuid

import pytest
from google.genai import types

from app.services import flow_service
from app.sru_agent import dialogue, eligibility, fee_intake, fees, memory
from app.sru_agent.agent import run_agent


def _text(text):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        role="model", parts=[types.Part.from_text(text=text)]))])


class ProdModel:
    """Records what reaches the model; always answers with a neutral line."""

    def __init__(self, reply="Here is what I found in the official sources."):
        self.reply, self.calls, self.messages, self.prompts = reply, 0, [], []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.calls += 1
        last = contents[-1]
        self.messages.append("".join(p.text or "" for p in last.parts))
        self.prompts.append(str(getattr(config, "system_instruction", "") or ""))
        return _text(self.reply)


class Chat:
    """One student's conversation."""

    def __init__(self):
        self.session = f"audit-{uuid.uuid4().hex[:10]}"
        self.conv = f"conv-{uuid.uuid4().hex[:8]}"
        self.model = ProdModel()

    async def say(self, message):
        events = [e async for e in run_agent(message, self.session, self.conv, client=self.model)]
        done = next(e for e in events if e["type"] == "done")
        return done

    async def state(self):
        return await memory.get_conversation_state(self.session, self.conv)


# =====================================================================================================
# 1. Admission eligibility: exact maths, verified thresholds, boundaries, separate from scholarship
# =====================================================================================================

def test_percentage_maths_is_exact():
    assert eligibility.percent_from_marks(230, 1000) == 23.0
    assert eligibility.percent_from_marks(500, 1000) == 50.0
    assert eligibility.percent_from_marks(499.9, 1000) < 50.0
    assert eligibility.percent_from_marks(1200, 1000) is None  # impossible pair is rejected, not guessed


@pytest.mark.parametrize("program,percent,status", [
    ("btech_cse", 23.0, eligibility.BELOW),         # the reported bug
    ("btech_cse", 49.99, eligibility.BELOW),        # just below the lowest documented minimum
    ("btech_cse", 50.0, eligibility.CONFIRM),       # fee card 50%, programme page 60%: disputed
    ("btech_cse", 59.99, eligibility.CONFIRM),
    ("btech_cse", 60.0, eligibility.MEETS),         # meets every documented minimum (inclusive)
    ("bba", 49.99, eligibility.BELOW),
    ("bba", 50.0, eligibility.MEETS),               # BBA: every source says 50% -> boundary meets
    ("mba", 52.0, eligibility.CONFIRM),             # fee card 50%, programme page 55%
    ("mba", 55.0, eligibility.MEETS),
])
def test_threshold_boundaries_use_every_documented_source(program, percent, status):
    assert eligibility.assess(program, percent)["status"] == status


def test_thresholds_come_only_from_the_fee_data_file():
    data = fees.load_data()["programs"]
    for key, prog in data.items():
        t = eligibility.thresholds(key)
        assert t["floor"] == min([prog["min_percent"]] + [v for v in (prog.get("fee_band_min_percent"),
                                 (prog.get("website_crosscheck") or {}).get("min_percent")) if v is not None])


def test_230_out_of_1000_reply_is_correct_and_never_claims_eligibility():
    text = eligibility.explain(eligibility.assess("btech_cse", 23.0), "230 marks out of 1000")
    assert "230 marks out of 1000" in text and "**23%**" in text
    assert "below the official **50% minimum**" in text
    assert "do not currently meet the general eligibility criteria" in text
    assert "meet the official" not in text and "you qualify" not in text.lower()
    # No invented pathways or exceptions
    for word in ("lateral", "diploma", "management quota", "alternative pathway", "special review"):
        assert word not in text.lower()


def test_disputed_score_is_not_presented_as_confirmed():
    text = eligibility.explain(eligibility.assess("btech_cse", 55.0))
    assert "official sources list different minimum marks" in text
    assert "50%" in text and "60%" in text
    assert "can't confirm your eligibility" in text
    assert "meets the minimum" not in text


def test_subject_requirement_is_asked_not_assumed_and_mismatch_is_clear():
    r = eligibility.assess("btech_cse", 85.0)
    assert r["needs_stream"] is True and r["eligible"] is None      # MPC not yet known
    assert eligibility.assess("btech_cse", 85.0, "MPC")["eligible"] is True
    bipc = eligibility.assess("btech_cse", 85.0, "BiPC")
    assert bipc["eligible"] is False
    assert "do not meet the listed subject requirement" in eligibility.explain(bipc)
    assert eligibility.assess("bsc_agri", 85.0, "BiPC")["eligible"] is True


def test_scholarship_is_never_admission_eligibility():
    # 55% earns no merit slab but is a valid BBA score; 23% is never eligible whatever the scholarship tables say
    fee = fees.calculate_fee("btech_cse", percent=23)
    assert fee["admission_eligibility"]["status"] == eligibility.BELOW
    assert "BELOW the programme minimum" in fee["instruction"]
    assert fees.check_eligibility("cse", 23)["eligible"] is False
    assert fees.check_eligibility("cse")["status"] == "need_marks"       # no silent 0%


@pytest.mark.parametrize("message", ["230 out of 1000", "fee for 230 out of 1000", "scholarship for 230/1000 marks"])
def test_fee_intake_never_says_230_meets_the_minimum(message):
    res = fee_intake.decide(message, {}, {"waiting_for": "program", "turns": 1, "asked": []})
    assert res is not None and res["action"] == "ineligible"
    assert "**23%**" in res["text"] and "meet the official 50%" not in res["text"]


def test_bare_marks_ask_for_the_total_instead_of_assuming_1000():
    first = fee_intake.decide("230 marks", {}, {})
    assert first["state"]["waiting_for"] == "marks_max"
    assert "%" not in first["text"]                      # nothing worked out from a guessed total
    second = fee_intake.decide("230 out of 1000", {}, first["state"])
    assert second["action"] == "ineligible" and "**23%**" in second["text"]


def test_legacy_wizard_uses_the_same_rules():
    text, info = flow_service.execute_wizard_step({"step": 4, "degree": "B.Tech", "branch": "CSE", "score": "23%"})
    assert info["is_eligible"] is False and "below the official **50% minimum**" in text
    text, info = flow_service.execute_wizard_step({"step": 4, "degree": "B.Tech", "branch": "CSE", "score": "92%"})
    assert "40% merit tuition waiver" not in text           # the old invented claim
    assert "30%" in text                                    # 92% State Board slab from the fee card


# =====================================================================================================
# 2. Mandatory conversation tests (production code path)
# =====================================================================================================

@pytest.mark.asyncio
async def test_hostel_broad_then_fees_only():
    chat = Chat()
    first = await chat.say("Tell me about the hostel.")
    assert "What would you like to know about the hostel?" in first["answer"]
    assert "₹" not in first["answer"] and "curfew" not in first["answer"].lower()   # no information dump
    assert "Hostel fees" in first["suggestions"]
    assert chat.model.calls == 0
    second = await chat.say("Hostel fees.")
    # The short reply became the specific question, answered with the verified hostel fee table only
    assert chat.model.messages[-1] == "What are the hostel fees?"
    assert [c["type"] for c in second["cards"]] == ["fee_breakdown"]
    card = str(second["cards"][0])
    assert "1,15,000" in card and "1,35,000" in card
    assert "curfew" not in card.lower() and "warden" not in card.lower()


@pytest.mark.asyncio
async def test_cse_broad_then_placements_stay_on_cse():
    chat = Chat()
    first = await chat.say("Tell me about CSE")
    assert "What would you like to explore about B.Tech CSE" in first["answer"]
    assert chat.model.calls == 0
    await chat.say("Placements")
    # The AI was asked about CSE placements, and told to stay on CSE
    assert chat.model.messages[-1] == "What are the placements for B.Tech Computer Science & Engineering (CSE)?"
    assert "CURRENT FOCUS: the student is asking about B.Tech Computer Science & Engineering (CSE)" in chat.model.prompts[-1]


@pytest.mark.asyncio
async def test_cse_fees_are_verified_and_cse_only():
    chat = Chat()
    done = await chat.say("CSE fees")
    # Verified CSE figures are handed to the AI and shown in the card; the AI is told to stay on CSE
    assert [c["type"] for c in done["cards"]] == ["calculate_fee"]
    assert done["cards"][0]["data"]["tuition_first_year"] == "₹3,40,000"
    assert "₹3,40,000" in chat.model.prompts[-1]
    assert "CURRENT FOCUS: the student is asking about B.Tech Computer Science & Engineering (CSE)" in chat.model.prompts[-1]


@pytest.mark.asyncio
async def test_hostel_fees_are_answered_directly():
    chat = Chat()
    done = await chat.say("What are the hostel fees?")
    assert "What would you like to know about the hostel" not in done["answer"]   # no clarification
    assert chat.model.messages[-1] == "What are the hostel fees?"
    assert "1,15,000" in str(done["cards"][0])


@pytest.mark.asyncio
async def test_i_want_to_join_asks_the_programme():
    chat = Chat()
    done = await chat.say("I want to join")
    assert done["answer"] == "That's great! Which programme or course are you interested in joining at SR University?"
    assert chat.model.calls == 0


@pytest.mark.asyncio
async def test_join_with_programme_keeps_it_and_moves_on():
    chat = Chat()
    done = await chat.say("I want to join B.Tech CSE")
    assert "check your B.Tech CSE eligibility" in done["answer"]
    assert "Which programme" not in done["answer"] and "Which B.Tech branch" not in done["answer"]


@pytest.mark.asyncio
async def test_im_interested_asks_what():
    chat = Chat()
    done = await chat.say("I'm interested")
    assert "What are you interested in exploring at SR University" in done["answer"]
    # Every chip it offers leads to a sensible next question
    for chip, expected in (("Programmes", "Which programme would you like to explore?"),
                           ("Admissions", "What would you like to know about admissions?"),
                           ("Scholarships", "What would you like to know about scholarships?"),
                           ("Campus life", "What part of student life")):
        r = dialogue.decide(chip, {"dialogue": {"step": "interest", "intent": "explore"}}, {})
        assert expected in r["text"], chip


@pytest.mark.asyncio
async def test_full_multi_message_journey_keeps_context():
    chat = Chat()
    steps = [
        ("I want to join SR University.", "Which programme or course"),
        ("B.Tech.", "Which B.Tech branch"),
        ("CSE.", "check your B.Tech CSE eligibility"),
        ("Eligibility.", "please share your 10+2 / Intermediate marks"),
        ("230 out of 1000", "your percentage is **23%**"),
    ]
    answers = []
    for message, expected in steps:
        done = await chat.say(message)
        assert expected in done["answer"], (message, done["answer"])
        answers.append(done["answer"])
    final = answers[-1]
    assert "B.Tech Computer Science & Engineering (CSE)" in final           # never lost the programme
    assert "below the official **50% minimum**" in final
    assert len(set(answers)) == len(answers)                                # no question repeated
    assert chat.model.calls == 0                                            # all of it without an AI call
    assert (await chat.state()).get("active_program") == "btech_cse"


@pytest.mark.asyncio
async def test_journey_above_minimum_asks_subjects_once_then_confirms():
    chat = Chat()
    await chat.say("I want to join B.Tech CSE")
    await chat.say("Check my eligibility")
    asks_total = await chat.say("850")
    assert "Out of how many total marks is **850**" in asks_total["answer"]
    asks_stream = await chat.say("850 out of 1000")
    assert "MPC" in asks_stream["answer"]
    verdict = await chat.say("MPC")
    assert "meets the minimum marks" in verdict["answer"] and "**85%**" in verdict["answer"]
    assert verdict.get("eligible") is True
    # The marks are remembered: asking again later does not re-ask
    again = await chat.say("am I eligible for B.Tech CSE?")
    assert "share your 10+2" not in again["answer"] and "**85%**" in again["answer"]


@pytest.mark.asyncio
async def test_exactly_at_minimum_and_below_in_conversation():
    chat = Chat()
    await chat.say("I want to join BBA")
    await chat.say("Check my eligibility")
    at_min = await chat.say("50%")
    assert "meets the minimum marks" in at_min["answer"]
    chat2 = Chat()
    await chat2.say("I want to join BBA")
    await chat2.say("Check my eligibility")
    below = await chat2.say("499.9 out of 1000")
    assert "**49.99%**" in below["answer"] and "do not currently meet" in below["answer"]
    assert below.get("eligible") is False


@pytest.mark.asyncio
async def test_unrelated_question_goes_to_the_scope_policy_unchanged():
    chat = Chat()
    await chat.say("Who won the cricket world cup?")
    assert chat.model.messages[-1] == "Who won the cricket world cup?"       # not intercepted or rewritten
    assert "Off-topic requests" in chat.model.prompts[-1]                    # the SRU-only rule is in force


def test_unavailable_data_is_acknowledged_not_invented():
    text = dialogue._process_text("btech_cse")
    assert "does not list the documents to upload, the important dates or the refund policy" in text
    text, info = flow_service.execute_wizard_step({"step": 4, "degree": "Ph.D.", "branch": "", "score": "80%"})
    assert "can't verify" in text
    assert fees.check_eligibility("astronomy", 80)["status"] == "unknown_program"


def test_conflicting_sources_are_flagged_in_the_overview():
    text = eligibility.overview_text()
    assert "50% (2027-28 fee card)" in text and "60% (university's programme page (2026-27))" in text
    assert "Admissions Office confirms" in text


# =====================================================================================================
# 3. Edge cases: spelling, short replies, interruptions, topic changes, follow-ups
# =====================================================================================================

@pytest.mark.parametrize("message,topic", [
    ("tell me abt hostal", "hostel"), ("placments", "placements"), ("scolarships", "scholarships"),
    ("what about transport?", "transport"), ("Tell me about the campus facilities", "campus"),
    ("faculty", "faculty"), ("labs", "labs"), ("internships", "internships"), ("research", "research"),
    ("student life", "student_life"), ("events", "events"), ("Tell me about admissions", "admissions"),
])
def test_broad_topics_get_one_clarifying_question(message, topic):
    r = dialogue.decide(message, {}, {})
    assert r["kind"] == "reply" and r["state"]["topic"] == topic
    assert 1 <= len(r["chips"]) <= 4


@pytest.mark.parametrize("message", [
    "What are the hostel fees?", "hostel curfew timings", "CSE fee with 85%", "What scholarships are available?",
    "Calculate my scholarship", "Which companies recruit at SRU?", "hi", "thank you",
])
def test_specific_questions_are_not_turned_into_clarifications(message):
    r = dialogue.decide(message, {}, {})
    assert r is None or r["kind"] != "reply"


@pytest.mark.parametrize("message,key", [("btech cse", "btech_cse"), ("B Tech ECE", "btech_ece"),
                                         ("mechanical", "btech_mech"), ("tell me about mba", "mba")])
def test_programme_spelling_variants(message, key):
    r = dialogue.decide(message, {}, {})
    assert r["kind"] == "reply" and r["state"]["program"] == key


def test_short_follow_ups_use_the_programme_being_discussed():
    state = {"dialogue": {"program": "btech_cse"}}
    assert dialogue.decide("fees", state, {})["message"] == "B.Tech Computer Science & Engineering (CSE) fees"
    assert "B.Tech Computer Science & Engineering (CSE)" in dialogue.decide("what about placements?", state, {})["message"]
    assert "B.Tech Computer Science & Engineering (CSE)" in dialogue.decide("Placements for this branch", state, {})["message"]
    # A longer question is its own question
    assert dialogue.decide("Calculate my scholarship", state, {}) is None


def test_after_a_fee_answer_what_about_hostel_means_hostel_fees():
    r = dialogue.decide("What about hostel?", {"active_topic": "fee"}, {})
    assert r == {"kind": "rewrite", "message": "What are the hostel fees?", "state": {}, "profile_updates": {}}


@pytest.mark.asyncio
async def test_interruption_and_topic_change():
    chat = Chat()
    await chat.say("I want to join")
    interrupted = await chat.say("What are the hostel fees?")
    assert chat.model.messages[-1] == "What are the hostel fees?"   # the new question is answered as asked
    assert "1,15,000" in str(interrupted["cards"][0])
    back = await chat.say("CSE")                                # a fresh short message is read on its own
    assert "B.Tech CSE" in back["answer"]
    changed = await chat.say("Tell me about MBA")               # topic change is followed
    assert "about MBA" in changed["answer"]
    assert (await chat.state()).get("active_program") == "mba"


@pytest.mark.asyncio
async def test_skip_ends_a_pending_question_politely():
    chat = Chat()
    await chat.say("Tell me about the hostel")
    done = await chat.say("skip")
    assert "What else would you like to know" in done["answer"]
    assert not ((await chat.state()).get("dialogue") or {}).get("step")


@pytest.mark.asyncio
async def test_branch_guidance_request_is_not_hijacked():
    r = dialogue.decide("I scored 850 marks in Intermediate. I'm planning to join B.Tech, but I'm confused "
                        "about which branch to choose.", {}, {})
    assert r is None


@pytest.mark.asyncio
async def test_first_question_after_signup_is_answered_not_swallowed_by_greeting():
    session, conv = f"audit-{uuid.uuid4().hex[:8]}", "conv-first"
    await memory.update_profile(session, name="Ravi Kumar", phone="9876543210")
    events = [e async for e in run_agent("I want to join", session, conv, client=ProdModel(),
                                         require_contact_details=True)]
    done = next(e for e in events if e["type"] == "done")
    assert "Which programme or course" in done["answer"]
    assert "Welcome to SR University" not in done["answer"]
