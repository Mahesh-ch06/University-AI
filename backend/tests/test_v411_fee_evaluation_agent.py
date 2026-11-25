"""v4.11.0: the fee evaluation agent (fee_journey).

eligibility -> qualification confirmed -> concessions offered -> special consideration (pending) -> academic
scholarship (existing rules, reused) -> hostel / bus -> final fee card (confirmed vs after approval).
Runs as in production: no model client; the model (only for side questions) is a counting fake.
"""
from __future__ import annotations

import uuid

import pytest
from google.genai import types

from app.sru_agent import agent, fee_journey, fee_plan, fees, memory


class CountingModel:
    def __init__(self):
        self.calls = 0
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.calls += 1
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text=f"Side answer {self.calls}.")]))])


@pytest.fixture(autouse=True)
def model(monkeypatch):
    m = CountingModel()
    monkeypatch.setattr(agent, "get_client", lambda *a, **k: m)
    return m


async def _chat(messages, sid=None, **profile):
    sid = sid or f"v411-{uuid.uuid4().hex[:10]}"
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


def _card(done, kind):
    found = [c for c in done.get("cards") or [] if c.get("type") == kind]
    return found[0]["data"] if found else None


STEPS = ["Calculate my scholarship", "B.Tech CSE", "Telangana State Board", "Completed", "870", "MPC"]
AP = 'Apply the "Students from Andhra Pradesh" concession to my fee'


# ------------------------------------------------------------------ 1. eligibility -> concessions -> final
async def test_eligibility_confirms_and_offers_concessions_before_any_fee_card():
    done = (await _chat(STEPS))[-1]
    assert "minimum" in done["answer"] and "qualify for this programme" not in done["answer"]
    assert "Before we finalise your fee" in done["answer"]
    assert _card(done, "get_special_concessions") and not _card(done, "calculate_fee") \
        and not _card(done, "fee_summary")                         # no premature fee card
    # v4.12.0: in the default grouped picker "None of these apply" is a button inside the card
    assert done["suggestions"] == [fee_journey.SHOW_FEE]
    assert _card(done, "get_special_concessions")["allow_none"] is True
    assert done.get("eligible") is True


async def test_full_flow_keeps_the_concession_pending_and_out_of_the_confirmed_fee():
    out = await _chat(STEPS + [AP, "Yes, I have it", "AC 4-sharing (₹1,25,000)"])
    pick, proof, final = out[-3], out[-2], out[-1]
    assert "isn't applied yet" in pick["answer"] and "supporting document" in pick["answer"]
    assert "hostel" in proof["answer"].lower() and "No hostel, I'm a day scholar" in proof["suggestions"]
    d = _card(final, "fee_summary")
    fee = fees.calculate_fee("btech_cse", percent=87, board="state_board", hostel="ac_4")
    assert d["payable_confirmed"] == fee["first_year_total_payable"]            # merit applied, concession not
    assert fee_plan._num(d["payable_after_approval"]) == fee_plan._num(fee["first_year_total_payable"]) - 15000
    assert d["special_consideration"]["status"] == "pending" and "proof ready" in d["special_consideration"]["label"]
    assert d["scholarship"]["status"] == "applied" and d["total_approved_concessions"] == fee["saving_first_year"]
    assert any("Admissions Office" in p for p in d["pending"])


async def test_none_of_these_apply_then_no_hostel_and_no_bus():
    out = await _chat(STEPS + [fee_journey.NONE_APPLY, "No hostel, I'm a day scholar", "No, I'll manage"])
    assert "bus" in out[-2]["answer"]
    d = _card(out[-1], "fee_summary")
    assert d["special_consideration"]["status"] == "none" and d["payable_after_approval"] is None
    assert d["payable_confirmed"] == fees.calculate_fee("btech_cse", percent=87)["first_year_total_payable"]


# ------------------------------------------------------------------ 2. the Special Consideration tile
async def test_special_consideration_starts_an_evaluation_not_a_discount():
    first, = await _chat(["Special consideration"])
    assert "evaluated for an additional fee concession" in first["answer"]
    assert _card(first, "get_special_concessions") and not _card(first, "fee_summary")


async def test_special_consideration_collects_only_missing_details_and_resumes_after_the_scholarship_steps():
    out = await _chat(["Special consideration", 'Apply the "Lateral entry students" concession to my fee',
                       "B.Tech ECE", "Not yet", "Yes, check my scholarship",
                       "CBSE", "Completed", "92", "MPC"])
    assert "Which programme" in out[1]["answer"]
    assert "academic scholarship" in out[3]["answer"] and out[3]["suggestions"] == ["Yes, check my scholarship",
                                                                                  "No, skip it"]
    assert "Step 1 of" in out[4]["answer"] and "B.Tech ECE" in out[4]["answer"]   # programme not asked again
    result = out[-1]
    assert "30% scholarship" in result["answer"] and "Before we finalise" not in result["answer"]  # not re-offered
    assert "hostel" in result["answer"].lower()


async def test_known_marks_are_reused_and_the_scholarship_question_is_skipped():
    out = await _chat(["Special consideration", 'Apply the "Lateral entry students" concession to my B.Tech CSE fee',
                       "Yes, I have it"], percent=85, board="state_board")
    assert "academic scholarship" not in out[-1]["answer"] and "hostel" in out[-1]["answer"].lower()


async def test_information_question_shows_the_table_without_starting_an_evaluation():
    done, = await _chat(["What are the special category fee concessions available?"])
    assert _card(done, "get_special_concessions") and "evaluated" not in done["answer"]


# ------------------------------------------------------------------ 3. agentic behaviour
async def test_a_side_question_keeps_progress_and_offers_to_continue(model):
    out = await _chat(STEPS + [AP, "what is the hostel curfew", fee_journey.RESUME])
    side, back = out[-2], out[-1]
    assert fee_journey.RESUME in side["suggestions"]
    assert "Picking up where we left off" in back["answer"] and "supporting document" in back["answer"]


async def test_how_much_will_i_pay_mid_flow_gives_the_summary_with_open_steps():
    out = await _chat(STEPS + [AP, "how much will I pay after the scholarship?"])
    d = _card(out[-1], "fee_summary")
    assert d and "25% scholarship" in out[-1]["answer"]
    assert any("Hostel: not chosen" in p for p in d["pending"])
    assert d["special_consideration"]["status"] == "pending"


async def test_changing_marks_recalculates_and_keeps_the_other_choices():
    out = await _chat(STEPS + [fee_journey.NONE_APPLY, "Non-AC 4-sharing (₹1,15,000)",
                               "Change my academic details", "Telangana State Board", "Completed", "960", "MPC"])
    before = _card(out[7], "fee_summary")
    after = _card(out[-1], "fee_summary")
    assert before and after and "updated fee summary" in out[-1]["answer"]
    assert "30%" in after["scholarship"]["label"] and "25%" in before["scholarship"]["label"]
    assert any("Non-AC, 4-sharing" in r["item"] for r in after["rows"])                # hostel kept
    assert after["payable_confirmed"] == fees.calculate_fee("btech_cse", percent=96, hostel="non_ac_4")[
        "first_year_total_payable"]


async def test_the_same_concession_is_counted_once_and_another_replaces_it():
    out = await _chat(STEPS + [AP, AP, 'Apply the "Lateral entry students" concession to my fee', "Yes, I have it",
                               "No hostel, I'm a day scholar", "No, I'll manage"])
    assert "counted once" in out[7]["answer"]
    assert "replaces Students from Andhra Pradesh" in out[8]["answer"]
    d = _card(out[-1], "fee_summary")
    assert [r for r in d["rows"] if r["kind"] == "pending"] == [
        {"item": "Special consideration: Lateral Entry Students", "amount": "− ₹15,000", "kind": "pending",
         "status": "pending"}]


async def test_removing_the_concession():
    out = await _chat(STEPS + [AP, "remove the concession"])
    assert "Removed" in out[-1]["answer"]


async def test_wrapping_up_with_the_fee_unfinished_offers_to_finish_it():
    out = await _chat(STEPS + [AP, "Yes, I have it", "thanks"])
    assert "Before you go" in out[-1]["answer"] and fee_journey.SHOW_FEE in out[-1]["suggestions"]


async def test_a_bare_yes_to_some_other_question_is_not_taken_as_a_fee_answer(model):
    out = await _chat(STEPS + [AP, "tell me about placements", "yes"])
    assert not _card(out[-1], "fee_summary") and "Great — keep it ready" not in out[-1]["answer"]


async def test_below_minimum_keeps_the_existing_explanation():
    out = await _chat(["Calculate my scholarship", "B.Tech CSE", "Telangana State Board", "Completed", "420", "MPC"])
    assert "Before we finalise" not in out[-1]["answer"] and not _card(out[-1], "fee_summary")


# ------------------------------------------------------------------ 4. the evaluation itself (pure)
def test_projected_marks_make_the_scholarship_an_estimate_outside_the_confirmed_fee():
    st = fee_journey.new_state("btech_cse", scholarship="yes", hostel="none", transport=False)
    st["concession_decided"] = True
    d = fee_journey.evaluate(st, {"percent": 85, "board": "state_board", "is_projected": True})
    base = fees.calculate_fee("btech_cse")
    merit = fees.calculate_fee("btech_cse", percent=85)
    assert d["scholarship"]["status"] == "estimated" and d["total_approved_concessions"] == "₹0"
    assert d["payable_confirmed"] == base["first_year_total_payable"]
    assert d["payable_after_approval"] == merit["first_year_total_payable"]


def test_unknown_programme_is_asked_again():
    st = fee_journey.new_state("not a course", scholarship="no", hostel="none", transport=False)
    st["concession_decided"] = True
    step = fee_journey.final(st, {})
    assert step["kind"] == "reply" and step["state"]["awaiting"] == "program"


def test_all_amounts_come_from_the_fee_data():
    for program in ("btech_cse", "btech_ece", "bba"):
        if not fees.find_program(program):
            continue
        st = fee_journey.new_state(program, scholarship="yes", hostel="ac_3", transport=False)
        st.update(concession_decided=True, concession={"key": "lateral_entry", "label": "Lateral Entry Students", "amount": 15000},
                  proof="needed")
        d = fee_journey.evaluate(st, {"percent": 92, "board": "cbse"})
        fee = fees.calculate_fee(program, percent=92, board="cbse", hostel="ac_3")
        assert d["payable_confirmed"] == fee["first_year_total_payable"]
        assert d["original_tuition"] == fee["tuition_first_year"]
