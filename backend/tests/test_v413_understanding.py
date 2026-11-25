"""v4.13.0: messages the student simulation found misread (the meaning before the keyword, docs/36 rule 1)."""
from __future__ import annotations

import uuid

import pytest

from app.sru_agent import agent, eligibility, fee_plan, fees, memory


async def _chat(messages):
    sid = f"v413u-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Rahul Naik", phone="9876543210", welcome_actions_shown=True)
    conv, out = None, []
    for m in messages:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    return out


@pytest.mark.parametrize("message, label", [
    ("my elder brother is studying at SRU, any discount for me?", "Real brother or sister"),
    ("my father works at SRU any concession", "Children of Regular SRU Staff"),
    ("i studied in SR junior college, discount?", "SR Junior College student"),
    ("my dad is in the army, any fee concession", "Defence / CRPF / martyr family"),
])
def test_described_category_maps_to_the_official_concession(message, label):
    found = fee_plan.infer_concession(message)
    assert found and found["label"].startswith(label)
    assert found["amount"] == next(c["amount"] for c in fees.load_data()["special_concessions"]
                                   if c["label"] == found["label"])


def test_no_category_described_no_guess():
    assert fee_plan.infer_concession("any discount?") is None
    assert fee_plan.infer_concession("I scored 92 percent, any discount") is None


@pytest.mark.asyncio
async def test_family_link_discount_question_opens_the_concessions_not_the_scholarship_steps():
    [done] = await _chat(["my elder brother is studying at SRU, any discount for me?"])
    assert "Real brother or sister" in done["answer"] and "₹15,000" in done["answer"]
    assert any(c.get("type") == "get_special_concessions" for c in done.get("cards") or [])
    assert "Which programme" not in done["answer"]


@pytest.mark.asyncio
async def test_cutoff_question_is_answered_as_unpublished_not_with_the_marks_step():
    [done] = await _chat(["What was the closing EAPCET cutoff rank for CSE last year?"])
    assert "does not publish" in done["answer"] and "833" in done["answer"]
    assert "Intermediate (10+2) marks" not in done["answer"]


def test_eligibility_rule_comes_from_the_data():
    text = eligibility.rule_text("btech_cse")
    t = eligibility.thresholds("btech_cse")
    for s in t["sources"]:
        assert eligibility.show_percent(s["percent"]) in text
    assert "seat availability" in text


@pytest.mark.asyncio
async def test_what_is_the_eligibility_uses_the_programme_already_chosen():
    out = await _chat(["I want to join SR University", "B.Tech", "CSE", "What is the eligibility?"])
    last = out[-1]["answer"]
    assert "Eligibility for B.Tech Computer Science" in last and "Which programme" not in last


@pytest.mark.asyncio
async def test_bare_eligibility_choice_still_starts_the_check():
    out = await _chat(["I want to join SR University", "B.Tech", "CSE", "Eligibility."])
    assert "Intermediate (10+2) marks" in out[-1]["answer"]


@pytest.mark.asyncio
async def test_am_i_eligible_is_the_check_not_the_rule():
    [done] = await _chat(["Am I eligible for B.Tech CSE?"])
    assert "Intermediate (10+2) marks" in done["answer"]
