"""The admission journey as one connected conversation (v4.6.0): the 25 scenarios of the Nov 2026 brief.

Every test drives run_agent with ``RecordingModel``, a stand-in for Gemini whose class name is NOT in the agent's
test-client list, so each message takes the production code path. ``model.calls`` shows whether the AI was
used; ``model.messages`` shows exactly what it was asked (after the conversation manager resolved context).
"""
import re
import uuid

import pytest
from google.genai import types

from app.sru_agent import dialogue, fees, memory
from app.sru_agent.agent import run_agent


def _text(text):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        role="model", parts=[types.Part.from_text(text=text)]))])


class RecordingModel:
    def __init__(self):
        self.calls, self.messages, self.prompts = 0, [], []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.calls += 1
        self.messages.append("".join(p.text or "" for p in contents[-1].parts))
        self.prompts.append(str(getattr(config, "system_instruction", "") or ""))
        return _text("Here is what the official sources say.")


class Student:
    """One student; conversations can be switched to test what is (not) carried over."""

    def __init__(self, name="Mahesh"):
        self.session = f"journey-{uuid.uuid4().hex[:10]}"
        self.conv = f"conv-{uuid.uuid4().hex[:8]}"
        self.model = RecordingModel()
        self.name = name

    async def setup(self):
        if self.name:
            await memory.update_profile(self.session, name=self.name.lower(), phone="9876543210")
        return self

    def new_conversation(self):
        self.conv = f"conv-{uuid.uuid4().hex[:8]}"

    async def say(self, message, form=None):
        events = [e async for e in run_agent(message, self.session, self.conv, client=self.model,
                                             require_contact_details=bool(self.name), form=form)]
        return next(e for e in events if e["type"] == "done")

    async def state(self):
        return await memory.get_conversation_state(self.session, self.conv)

    async def profile(self):
        return await memory.get_profile(self.session)


def _card(done, kind):
    return next((c for c in done.get("cards", []) if c.get("type") == kind), None)


FORM_CSE = {"mode": "eligibility", "program": "btech_cse", "board_key": "ts_state_board",
            "academic_stage": "completed", "raw_marks": 671, "max_marks": 1000, "stream": "MPC", "show_stream": True}


async def _through_eligibility(s: Student):
    await s.say("I want to join SR University")
    await s.say("B.Tech")
    await s.say("CSE")
    form = await s.say("Check my eligibility")
    assert _card(form, "academic_details_form")
    await s.say("671")
    await s.say("671 out of 1000")
    return await s.say("MPC")


# ---------------------------------------------------------------- 1-4: fee enquiries ----------------
@pytest.mark.asyncio
async def test_01_general_fee_question_asks_programme_first():
    s = await Student().setup()
    done = await s.say("What are the fee details?")
    assert "Which programme are you interested in?" in done["answer"]
    assert "₹" not in done["answer"] and not done.get("cards")
    assert s.model.calls == 0


@pytest.mark.asyncio
async def test_02_programme_without_branch_asks_branch_then_only_that_fee():
    s = await Student().setup()
    await s.say("What are the fee details?")
    branch = await s.say("B.Tech")
    assert "Which B.Tech branch" in branch["answer"] and "₹" not in branch["answer"]
    await s.say("CSE")
    assert s.model.messages[-1] == "B.Tech Computer Science & Engineering (CSE) fees"


@pytest.mark.asyncio
async def test_03_specific_course_fee_is_that_course_only_with_year():
    s = await Student().setup()
    done = await s.say("CSE fees")
    assert [c["type"] for c in done["cards"]] == ["calculate_fee"]
    data = done["cards"][0]["data"]
    assert data["academic_year"] == "2027-28" and data["tuition_first_year"] == "₹3,40,000"
    assert not _card(done, "fee_breakdown")                       # no all-branch table
    assert "CURRENT FOCUS: the student is asking about B.Tech Computer Science & Engineering (CSE)" in s.model.prompts[-1]


@pytest.mark.asyncio
async def test_04_future_year_fees_are_not_invented():
    s = await Student().setup()
    done = await s.say("What are the fees for 2029-30?")
    assert "not published yet" in done["answer"] and "2027-28" in done["answer"]
    assert "CGPA" not in done["answer"]                           # no unverified retention rule
    assert s.model.calls == 0


# ---------------------------------------------------------------- 5-11: conversation handling --------
@pytest.mark.asyncio
async def test_05_hostel_question_asks_which_aspect():
    s = await Student().setup()
    done = await s.say("I want to know about the hostel.")
    assert "What would you like to know about the hostel?" in done["answer"]
    assert "₹" not in done["answer"]


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["I want to...", "Can you explain", "I need information about", "What about the"])
async def test_06_incomplete_messages_are_not_answered_with_a_dump(message):
    s = await Student().setup()
    done = await s.say(message)
    assert "Could you tell me a little more" in done["answer"]
    assert s.model.calls == 0


@pytest.mark.asyncio
async def test_06b_incomplete_message_keeps_the_hostel_context():
    s = await Student().setup()
    await s.say("Tell me about the hostel")
    done = await s.say("I want to...")
    assert done["answer"] == "No problem! What would you like to know about the hostel?"
    assert s.model.calls == 0


@pytest.mark.asyncio
async def test_07_short_contextual_follow_up_food_means_hostel_food():
    s = await Student().setup()
    await s.say("Tell me about the hostel")
    await s.say("I want to...")
    await s.say("Food.")
    assert s.model.messages[-1] == "Tell me about the hostel mess and food."


@pytest.mark.asyncio
async def test_08_user_changes_question_midway():
    s = await Student().setup()
    await s.say("I want to join")
    await s.say("Actually, what are the hostel fees?")
    assert s.model.messages[-1] == "Actually, what are the hostel fees?"
    assert not ((await s.state()).get("dialogue") or {}).get("step")


@pytest.mark.asyncio
async def test_09_ambiguous_question_gets_one_clarifying_question():
    s = await Student().setup()
    done = await s.say("Tell me about CSE")
    assert "What would you like to explore about B.Tech CSE" in done["answer"]
    assert 2 <= len(done["suggestions"]) <= 4


@pytest.mark.asyncio
async def test_10_unavailable_information_is_stated_honestly():
    s = await Student().setup()
    done = await s.say("How do I apply for 2027-28?")
    assert "does not list the documents to upload, the important dates or the refund policy" in done["answer"]
    assert fees.check_eligibility("astronomy", 80)["status"] == "unknown_program"


@pytest.mark.asyncio
async def test_11_unrelated_question_goes_to_the_scope_policy():
    s = await Student().setup()
    await s.say("Who won the cricket world cup?")
    assert s.model.messages[-1] == "Who won the cricket world cup?"
    assert "Off-topic requests" in s.model.prompts[-1]


# ---------------------------------------------------------------- 12 & 25: conversations -------------
@pytest.mark.asyncio
async def test_12_and_25_new_conversation_starts_clean_and_offers_saved_details():
    s = await Student().setup()
    await _through_eligibility(s)
    assert (await s.profile()).get("raw_marks") == 671.0

    s.new_conversation()
    await s.say("I want to join SR University")
    await s.say("B.Tech")
    await s.say("CSE")
    form = await s.say("Check my eligibility")
    card = _card(form, "academic_details_form")
    assert card["values"]["raw_marks"] is None and card["values"]["board_key"] is None   # clean form
    assert card["saved_summary"] == "671/1000, MPC"                                      # opt-in reuse only
    assert any(c.startswith("Use my saved details") for c in form["suggestions"])
    assert (await s.profile()).get("raw_marks") is None    # earlier marks are not assumed in this chat

    used = await s.say(form["suggestions"][0])
    assert "**67.1%**" in used["answer"] and "meets the minimum marks" in used["answer"]


@pytest.mark.asyncio
async def test_12b_switching_back_to_the_first_conversation_finds_its_details():
    s = await Student().setup()
    await _through_eligibility(s)
    first = s.conv
    s.new_conversation()
    await s.say("hello")
    s.conv = first
    again = await s.say("Am I eligible for B.Tech CSE?")
    assert "**67.1%**" in again["answer"] and "share your" not in again["answer"]


# ---------------------------------------------------------------- 13-19: the journey ----------------
@pytest.mark.asyncio
async def test_13_to_16_join_programme_branch_eligibility_marks_confirmation_group():
    s = await Student().setup()
    start = await s.say("I want to join SR University.")
    assert start["answer"].startswith("That's great, Mahesh!")                 # natural first use of the name
    assert "Which B.Tech branch" in (await s.say("B.Tech."))["answer"]
    assert "check your B.Tech CSE eligibility" in (await s.say("CSE."))["answer"]
    form = await s.say("Check my eligibility")
    assert _card(form, "academic_details_form")["show_stream"] is True
    total = await s.say("671")
    assert "Out of how many total marks is **671**" in total["answer"]          # never assumed
    group = await s.say("671 out of 1000")
    assert "MPC" in group["answer"]
    verdict = await s.say("MPC")
    assert "Based on the 671 marks out of 1000 you provided, your percentage is **67.1%**" in verdict["answer"]
    assert "meets the minimum marks" in verdict["answer"]
    assert s.model.calls == 0
    st = await s.state()
    assert st["dialogue"]["eligibility"] == {"program": "btech_cse", "status": "meets_minimum"}


@pytest.mark.asyncio
async def test_17_18_19_scholarship_after_eligibility_reuses_everything():
    s = await Student().setup()
    await _through_eligibility(s)
    done = await s.say("I want to know about the scholarship")
    text = done["answer"]
    assert "I can help you understand the scholarship details for **B.Tech CSE**" in text
    assert "I'll use the details you've already shared (671/1000 (67.1%), MPC)" in text
    assert "Which programme" not in text and "Which branch" not in text
    card = _card(done, "academic_details_form")
    assert card["values"]["raw_marks"] == 671.0 and card["values"]["stream"] == "MPC"   # pre-filled
    assert card["show_stream"] is False                                               # not asked again
    # Only the missing details: board typed -> status only
    nxt = await s.say("Telangana Intermediate (TSBIE)")
    assert _card(nxt, "counsellor_stage_selection") and "marks" not in nxt["answer"].lower()
    result = await s.say("Completed Intermediate (Passed out)")
    assert "### Your Scholarship Assessment" in result["answer"]
    assert "15% Tuition Waiver" in result["answer"]                     # 67.1% State Board slab
    assert s.model.calls == 0


@pytest.mark.asyncio
async def test_17b_what_scholarships_are_available_inside_the_journey():
    s = await Student().setup()
    await _through_eligibility(s)
    await s.say("Check", form={**FORM_CSE})                  # board + status known from the form
    done = await s.say("What scholarships are available?")
    assert "### Your Scholarship Assessment" in done["answer"]
    assert "B.Tech Computer Science & Engineering (CSE)" in done["answer"]


# ---------------------------------------------------------------- 20-23: the form -------------------
@pytest.mark.asyncio
async def test_20_22_form_collects_board_status_marks_and_submit_evaluates():
    s = await Student().setup()
    await s.say("I want to join B.Tech CSE")
    await s.say("Check my eligibility")
    done = await s.say("My details: TSBIE, completed, 671/1000, MPC", form={**FORM_CSE})
    assert "your percentage is **67.1%**" in done["answer"] and "meets the minimum marks" in done["answer"]
    p = await s.profile()
    assert (p["board_key"], p["academic_stage"], p["raw_marks"], p["max_marks"], p["stream"]) == \
        ("ts_state_board", "completed", 671.0, 1000.0, "MPC")
    assert p["marks_confirmed"] is True
    assert s.model.calls == 0


@pytest.mark.asyncio
async def test_21_invalid_form_keeps_what_was_entered_and_saves_nothing():
    s = await Student().setup()
    await s.say("I want to join B.Tech CSE")
    bad = {**FORM_CSE, "academic_stage": None, "raw_marks": 1200}
    done = await s.say("My details", form=bad)
    assert "select your current academic status" in done["answer"]
    assert "the marks cannot be more than the total" in done["answer"]
    card = _card(done, "academic_details_form")
    assert card["values"]["board_key"] == "ts_state_board" and card["values"]["raw_marks"] == 1200
    assert (await s.profile()).get("board_key") is None                  # nothing saved from a bad form


@pytest.mark.asyncio
async def test_22b_scholarship_form_with_entrance_score():
    s = await Student().setup()
    await s.say("I want to join B.Tech CSE")
    form = {**FORM_CSE, "mode": "scholarship", "show_stream": False, "show_entrance": True,
            "entrance_type": "tg_eapcet", "entrance_value": 9000}
    done = await s.say("My details", form=form)
    assert "### Your Scholarship Assessment" in done["answer"]
    assert "TG EAPCET (Rank: 9,000)" in done["answer"]
    assert "25% Tuition Waiver" in done["answer"]                         # rank 9,000 beats the 15% marks slab


@pytest.mark.asyncio
async def test_23_admission_and_scholarship_are_evaluated_separately():
    s = await Student().setup()
    await s.say("I want to join B.Tech CSE")
    form = {**FORM_CSE, "mode": "scholarship", "raw_marks": 550, "show_stream": False}
    done = await s.say("My details", form=form)
    text = done["answer"]
    assert "### Admission Eligibility" in text and "0% (Standard Fee)" in text    # 55%: no merit slab
    assert "official sources list different minimum marks" in text               # 55% is disputed for B.Tech
    low = Student()
    await low.setup()
    await low.say("I want to join B.Tech CSE")
    below = await low.say("My details", form={**FORM_CSE, "raw_marks": 230})
    assert "do not currently meet the general eligibility criteria" in below["answer"]
    assert "Scholarship" not in below["answer"]


# ---------------------------------------------------------------- 24: change of course --------------
@pytest.mark.asyncio
async def test_24_changing_the_branch_midway_keeps_the_marks():
    s = await Student().setup()
    await s.say("I want to join B.Tech CSE")
    await s.say("Check my eligibility")
    await s.say("671 out of 1000")
    switched = await s.say("Actually ECE")
    assert "switching to **B.Tech ECE**" in switched["answer"]
    assert "Out of how many" not in switched["answer"] and "share your" not in switched["answer"]
    assert (await s.state())["active_program"] == "btech_ece"


# ---------------------------------------------------------------- cross-cutting checks --------------
@pytest.mark.asyncio
async def test_name_is_used_naturally_not_in_every_reply():
    s = await Student().setup()
    replies = [(await s.say(m))["answer"] for m in
               ("I want to join SR University", "B.Tech", "CSE", "Check my eligibility")]
    with_name = [r for r in replies if "Mahesh" in r]
    assert len(with_name) == 1 and replies[0] in with_name


@pytest.mark.asyncio
async def test_results_received_is_answered_with_the_name_and_a_question():
    s = await Student().setup()
    done = await s.say("I received my entrance examination results")
    assert done["answer"].startswith("That's great, Mahesh! How did you do?")


def test_no_course_pushing_wording_in_fixed_replies():
    from app.sru_agent import responses
    texts = [responses.get_branch_guidance_text(230), responses.get_branch_guidance_text(None)]
    for m in ("Tell me about CSE", "I want to join", "B.Tech", "What are the fee details?"):
        texts.append(dialogue.decide(m, {}, {})["text"])
    for t in texts:
        assert not re.search(r"best (?:fit|option|course|branch)|you should choose|let me suggest|great choice|"
                             r"strong academic foundation|high campus recruitment", t, re.IGNORECASE), t


def test_agent_does_not_claim_marks_quality_for_low_scores():
    from app.sru_agent import responses
    first_line = responses.get_branch_guidance_text(230).splitlines()[0].lower()
    assert "230" in first_line and "strong" not in first_line and "foundation" not in first_line
