"""v4.10.0: fresh, fact-grounded answers; relevant chips; concessions table with selection; fee chart.

The agent runs as in production: the API passes no model client, and the model (when one is needed) comes
from agent.get_client, replaced here by a small fake that counts calls.
"""
from __future__ import annotations

import uuid
from datetime import date

import pytest
from google.genai import types

from app.sru_agent import agent, fact_service, fee_plan, fees, followups, memory


class CountingModel:
    def __init__(self):
        self.calls = 0
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.calls += 1
        last = "".join(p.text or "" for p in contents[-1].parts)[:60]
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text=f"Model answer {self.calls} to: {last}")]))])


@pytest.fixture
def model(monkeypatch):
    m = CountingModel()
    monkeypatch.setattr(agent, "get_client", lambda *a, **k: m)
    return m


async def _chat(messages, sid=None):
    sid = sid or f"v410-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True)
    conv, out = None, []
    for m in messages:
        done = None
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                done = ev
        conv = done.get("conversation_id") or conv
        out.append(done)
    return out


def _bullets(text):
    return [line for line in text.splitlines() if line.startswith("• ")]


def _cards(done, kind):
    return [c for c in done.get("cards") or [] if c.get("type") == kind]


# ------------------------------------------------------------------ facts store and retrieval
def test_facts_have_status_source_and_only_usable_ones_are_retrieved():
    facts = fact_service.get_all_facts()
    assert all(f.source and f.verification_status in ("verified", "university_reported", "unverified")
               for f in facts)
    unverified = [f.fact_id for f in facts if f.verification_status == "unverified"]
    assert "fact.unverified.placement_rate_95" in unverified
    for q in ("why choose sru", "placement record", "is sru good", "rankings"):
        assert not set(unverified) & {f.fact_id for f in fact_service.retrieve(q, k=10)}


def test_expired_facts_are_not_retrieved():
    later = date(2031, 1, 1)
    assert fact_service.retrieve("rankings", k=10, today=later) == [] or all(
        date.fromisoformat(f.valid_until) >= later for f in fact_service.retrieve("rankings", k=10, today=later))


@pytest.mark.parametrize("question,aspect", [
    ("is SRU ranked number one in india?", "rankings"),
    ("is sru nba accredited", "accreditation"),
    ("study abroad options at sru", "international"),
    ("what about patents and research", "research"),
])
def test_retrieval_returns_the_aspect_asked(question, aspect):
    picked = fact_service.retrieve(question)
    assert picked and all(f.metadata["aspect"] == aspect for f in picked)


def test_retrieval_skips_facts_already_told():
    first = fact_service.retrieve("why choose sru")
    second = fact_service.retrieve("why choose sru", exclude=[f.fact_id for f in first])
    assert not {f.fact_id for f in first} & {f.fact_id for f in second}


def test_ranking_figures_match_the_official_fee_card():
    ranks = {r["body"]: r["claim"] for r in fees.load_data()["rankings"]}
    the = fact_service.get_fact("fact.rankings.the_2027_research").statement
    qs = fact_service.get_fact("fact.rankings.qs_asia_2027").statement
    assert "801-1000" in ranks["THE World University Rankings 2027"] and "801–1000" in the and "7th" in the
    assert "701-710" in ranks["QS World University Rankings: Asia 2027"] and "701–710" in qs and "19th" in qs


# ------------------------------------------------------------------ answers built from facts
async def test_why_sru_asked_twice_gives_new_points_not_the_same_text(model):
    one, two = await _chat(["why should I choose SRU", "why should I choose SRU"])
    b1, b2 = _bullets(one["answer"]), _bullets(two["answer"])
    assert 3 <= len(b1) <= 4 and b2
    assert not set(b1) & set(b2)
    assert "95%" not in one["answer"] + two["answer"]
    assert model.calls == 0          # grounded in the facts store; no free-form model text


async def test_challenge_questions_lead_with_distinctions_never_a_blunt_no(model):
    for q in ("Why is SRU bad?", "Is VIT better than SRU?"):
        (done,) = await _chat([q])
        assert not done["answer"].lower().startswith("no")
        assert any(k in done["answer"] for k in ("NIRF", "QS Asia", "THE World", "NBA", "LPA"))


async def test_a_new_question_is_not_taken_as_an_answer_to_the_last_clarification(model):
    _, done = await _chat(["research at sru", "what is the hostel curfew"])
    assert "curfew" in done["answer"].lower() or "in-time" in done["answer"].lower()
    assert "Research Quality" not in done["answer"]


async def test_bare_why_follow_up_goes_to_the_conversation_not_why_sru(model):
    _, done = await _chat(["tell me about cse placements", "why?"])
    assert not done["answer"].startswith(("Here's what makes SRU", "A few reasons", "SRU's strengths"))


async def test_exam_rank_question_is_not_a_rankings_question(model):
    (done,) = await _chat(["in eamcet i got 40000 rank what will be the scholarship"])
    assert "QS Asia" not in done["answer"] and "NIRF" not in done["answer"]


async def test_a_fixed_overview_is_not_sent_twice_in_one_conversation(model):
    one, two = await _chat(["Tell me about the next-gen tech programs", "Tell me about the next-gen tech programs"])
    assert model.calls >= 1 and two["answer"] != one["answer"]


# ------------------------------------------------------------------ chips
async def test_no_generic_chips_are_padded_on():
    for chips in (followups.ensure_fixed_chips(["Mess charges"], answer="Rooms are 4-sharing."),
                  followups.suggest("what is the hostel curfew", [], answer="9 PM.")):
        assert followups.FIXED_ADMISSION_CHIP not in chips and followups.FIXED_UNIVERSITY_CHIP not in chips
        assert len(chips) <= 4


# ------------------------------------------------------------------ special concessions
async def test_concessions_table_is_shown_every_time_with_a_short_lead(model):
    one, two = await _chat(["what special concessions are there?", "special concessions please"])
    for done in (one, two):
        (card,) = _cards(done, "get_special_concessions")
        assert len(card["data"]["all_categories"]) == 19
        assert len(done["answer"]) < 220 and "•" not in done["answer"]


def test_exact_category_wins_over_a_similar_one():
    assert fee_plan.find_concession('Apply the "Students from Andhra Pradesh" concession')["label"] == \
        "Students from Andhra Pradesh"
    assert fee_plan.find_concession(
        'Apply the "Students from states other than Telangana and Andhra Pradesh" concession')["label"] == \
        "Students from states other than Telangana and Andhra Pradesh"


async def test_picked_concession_asks_programme_then_shows_one_fee_card(model):
    _, ask, done = await _chat([
        "what special concessions are there?",
        'Apply the "SRU alumni, their children and siblings" concession to my fee',
        "B.Tech CSE"])
    assert "Which programme" in ask["answer"]
    (card,) = _cards(done, "concession_fee")
    assert len(done["cards"]) == 1                          # one card, no second table
    d = card["data"]
    tuition = fees.load_data()["programs"]["btech_cse"]["tuition_per_year"]
    assert d["tuition_after_concession"] == fees.inr(tuition - 15000)
    assert "proof" in d["proof_note"]


async def test_a_pending_concession_does_not_capture_a_later_question(model):
    out = await _chat(['Apply the "NCC \'C\' certificate holders" concession to my fee', "what is the hostel curfew",
                       "B.Tech CSE fee"])
    assert not _cards(out[2], "concession_fee")


async def test_concession_with_merit_scholarship_notes_the_admissions_office(model):
    sid = f"v410-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, percent=85, board="state_board")
    (done,) = await _chat(['Apply the "Lateral entry students" concession to my B.Tech CSE fee'], sid)
    d = _cards(done, "concession_fee")[0]["data"]
    assert d["merit_percent"] == 25 and "Admissions Office" in d["combine_note"]


# ------------------------------------------------------------------ fee chart
async def test_fee_with_hostel_offers_the_chart_and_yes_prepares_it(model):
    calc, chart = await _chat(["my inter percentage is 85, state board. cse fee with ac hostel 4 sharing", "yes"])
    assert "complete fee chart" in calc["answer"] and calc["suggestions"] == ["Yes, prepare my fee chart", "No, thanks"]
    assert len([c for c in calc["cards"] if c["type"] in ("calculate_fee", "fee_breakdown")]) == 1   # no double card
    (card,) = _cards(chart, "fee_plan")
    d = card["data"]
    total = sum((-1 if r["kind"] == "discount" else 1) * fee_plan._num(r["amount"]) for r in d["rows"])
    assert fee_plan._num(d["first_year_total"]) == total
    assert any("Hostel" in r["item"] for r in d["rows"])
    assert d["share_text"].startswith("SR University 2027-28 fee chart")


async def test_declining_the_chart_offer_is_respected(model):
    _, no = await _chat(["my inter percentage is 85, state board. cse fee with ac hostel 4 sharing", "no thanks"])
    assert not _cards(no, "fee_plan") and no["suggestions"] == []


async def test_chart_includes_a_selected_concession_as_if_approved(model):
    out = await _chat(['Apply the "SRU alumni, their children and siblings" concession to my B.Tech ECE fee',
                       "📋 Prepare my full fee chart"])
    d = _cards(out[1], "fee_plan")[0]["data"]
    assert d["program"] == fees.short_name("btech_ece")
    assert fee_plan._num(d["concession"]["total_if_approved"]) == fee_plan._num(d["first_year_total"]) - 15000


# ------------------------------------------------------------------ a new session starts empty
async def test_a_new_session_knows_nothing_from_the_previous_one(model):
    old = f"v410-old-{uuid.uuid4().hex[:8]}"
    await memory.update_profile(old, name="Asha", percent=91, program_interest="btech_cse")
    new = f"v410-new-{uuid.uuid4().hex[:8]}"
    profile = await memory.get_profile(new)
    assert not profile.get("name") and not profile.get("percent") and not profile.get("program_interest")


@pytest.mark.parametrize("message,expected", [
    ("my inter percentage is 85, state board. cse fee with ac hostel 4 sharing", {"percent": 85.0, "hostel": "ac_4"}),
    ("i got 92 in inter cse fee", {"percent": 92.0}),
    ("i got 98 percentile in jee cse fee", {"jee_percentile": 98.0}),
    ("in eamcet i got 40000 rank cse fee", {"eapcet_rank": 40000}),
])
def test_fee_question_details_are_read_correctly(message, expected):
    args = agent._fee_args_from_message(message, {})
    for k, v in expected.items():
        assert args.get(k) == v
    if "percent" not in expected:
        assert "percent" not in args          # a percentile or a rank is not a board percentage
