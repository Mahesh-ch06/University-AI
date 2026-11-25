"""v4.12.0: admin chat settings (concessions picker switch), grouped concessions, the lowest-fee agent with its
visible plan, the answer self-check, the counsellor case summary and copilot, "talk to a counsellor", and /ping.

The chat runs as in production: no model client is passed; the model (only for side questions) is a fake.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from google.genai import types
from httpx import ASGITransport, AsyncClient

from app.services import app_settings, copilot_service, live_connect
from app.sru_agent import agent, answer_check, case_summary, fee_journey, fee_plan, fees, followups, intents, memory, tools


class FakeModel:
    def __init__(self):
        self.calls = 0
        self.aio = self
        self.models = self
        self.reply = "Side answer."

    async def generate_content(self, model, contents, config):
        self.calls += 1
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            role="model", parts=[types.Part.from_text(text=self.reply)]))])


@pytest.fixture(autouse=True)
def model(monkeypatch):
    m = FakeModel()
    monkeypatch.setattr(agent, "get_client", lambda *a, **k: m)
    return m


@pytest.fixture
def leads(monkeypatch):
    saved = []

    async def saver(lead):
        saved.append(lead)
        return {"id": str(uuid.uuid4())}

    tools.set_lead_saver(saver)
    yield saved
    tools.set_lead_saver(None)


async def _chat(messages, sid=None, **profile):
    sid = sid or f"v412-{uuid.uuid4().hex[:10]}"
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


# ------------------------------------------------------------------ 1. settings and the concessions switch
def test_settings_defaults_and_validation():
    s = app_settings.current()
    assert s["concession_picker"] == "grouped" and s["connect_enabled"] is True and s["connect_wait_seconds"] == 30
    for bad in ({"concession_picker": "list"}, {"office_hours_start": "9am"}, {"connect_wait_seconds": 5},
                {"office_days": [9]}):
        with pytest.raises(Exception):
            app_settings.ChatSettings(**{**s, **bad})


def test_every_concession_is_in_exactly_one_group():
    placed = [k for g in fee_plan.CONCESSION_GROUPS for k in g["items"]]
    # every category a student can claim (the Chancellor recommendation is granted, never picked)
    keys = [c["key"] for c in fees.load_data()["special_concessions"] if c.get("selectable", True)]
    assert sorted(placed) == sorted(keys) and len(placed) == len(set(placed)) == 19
    other = next(g for g in fee_plan.CONCESSION_GROUPS if g["key"] == "other")
    assert other.get("private") and {"orphan", "single_parent", "disability"} <= set(other["items"])


async def test_grouped_mode_card_and_chips():
    app_settings.set_for_tests(concession_picker="grouped")
    done = (await _chat(STEPS))[-1]
    card = _card(done, "get_special_concessions")
    assert card["mode"] == "grouped" and len(card["groups"]) == 5 and card["allow_none"] is True
    assert sum(len(g["items"]) for g in card["groups"]) == 19
    assert done["suggestions"] == [fee_journey.SHOW_FEE]          # "None of these apply" is in the card


async def test_table_mode_card_and_chips():
    app_settings.set_for_tests(concession_picker="table")
    done = (await _chat(STEPS))[-1]
    card = _card(done, "get_special_concessions")
    assert card["mode"] == "table" and "groups" not in card and len(card["all_categories"]) == 20
    assert done["suggestions"] == [fee_journey.NONE_APPLY, fee_journey.SHOW_FEE]


@pytest.mark.parametrize("mode", ["grouped", "table"])
async def test_both_modes_complete_the_fee_flow(mode):
    app_settings.set_for_tests(concession_picker=mode)
    out = await _chat(STEPS + ["None of these apply", "No hostel, I'm a day scholar", "No, I'll manage"])
    assert _card(out[-1], "fee_summary")["special_consideration"]["status"] == "none"
    out = await _chat(STEPS + ['Apply the "Lateral entry students" concession to my fee', "Yes, I have it",
                               "No hostel, I'm a day scholar", "No, I'll manage"])
    assert _card(out[-1], "fee_summary")["special_consideration"]["status"] == "pending"


async def test_information_question_follows_the_switch_and_offers_no_none_button():
    app_settings.set_for_tests(concession_picker="grouped")
    done, = await _chat(["What are the special category fee concessions available?"])
    card = _card(done, "get_special_concessions")
    assert card["mode"] == "grouped" and card["allow_none"] is False


def test_model_made_concession_cards_follow_the_switch():
    app_settings.set_for_tests(concession_picker="grouped")
    cards = [{"type": "get_special_concessions", "data": fees.special_concessions()}]
    agent._done("c", "x", cards=cards)
    assert cards[0]["data"]["mode"] == "grouped" and cards[0]["data"]["groups"]


async def test_admin_settings_api_round_trip():
    from app.config import settings
    from app.main import app

    transport = ASGITransport(app=app)
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    app_settings.reset_for_tests()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/admin/settings")).status_code in (401, 403, 422)
        try:
            res = await client.put("/api/v1/admin/settings", json={"concession_picker": "table"}, headers=headers)
            if res.status_code == 503:
                pytest.skip("database not reachable")
            assert res.status_code == 200 and res.json()["settings"]["concession_picker"] == "table"
            assert app_settings.get("concession_picker") == "table"
            got = await client.get("/api/v1/admin/settings", headers=headers)
            assert got.json()["settings"]["concession_picker"] == "table"
            bad = await client.put("/api/v1/admin/settings", json={"office_hours_start": "9am"}, headers=headers)
            assert bad.status_code == 422
        finally:
            await client.put("/api/v1/admin/settings", json={"concession_picker": "grouped"}, headers=headers)
            app_settings.set_for_tests()


# ------------------------------------------------------------------ 2. the lowest-fee agent
async def test_lowest_fee_goal_shows_a_plan_and_runs_the_checks():
    out = await _chat(["Find me the lowest fee for B.Tech CSE", "Telangana State Board", "Completed", "720", "MPC",
                       "my jee percentile is 96", "None of these apply", "AC 4-sharing (₹1,25,000)"])
    first = out[0]
    plan = _card(first, "agent_plan")
    assert plan and [s["title"] for s in plan["steps"]][0] == "Programme" and "my plan" in first["answer"].lower()
    entrance = out[4]
    assert "EAPCET rank or a JEE Main percentile" in entrance["answer"]
    assert "Share it and I'll check" not in entrance["answer"]                # not asked twice
    compared = out[5]
    assert "JEE Main 96 percentile → 40%" in compared["answer"] and "40%" in compared["answer"]
    final = out[-1]
    assert "lowest first-year fee" in final["answer"] and "Switch to Non-AC 4-sharing" in final["suggestions"]
    assert all(s["status"] == "done" for s in _card(final, "agent_plan")["steps"])
    d = _card(final, "fee_summary")
    assert d["payable_confirmed"] == fees.calculate_fee("btech_cse", percent=72, jee_percentile=96,
                                                        hostel="ac_4")["first_year_total_payable"]


async def test_lowest_fee_switch_to_the_cheapest_room():
    out = await _chat(["Find me the lowest fee for B.Tech CSE", "No entrance exam", "None of these apply",
                       "AC 3-sharing (₹1,35,000)", "Switch to Non-AC 4-sharing"],
                      percent=87, board="state_board")
    assert any("Non-AC, 4-sharing" in r["item"] for r in _card(out[-1], "fee_summary")["rows"])


def test_entrance_scores_are_read_carefully():
    assert fee_journey._read_entrance("my eapcet rank is 18,500", "entrance") == {"eapcet_rank": 18500}
    assert fee_journey._read_entrance("96.5 percentile in JEE", "entrance") == {"jee_percentile": 96.5}
    assert fee_journey._read_entrance("18500", "eapcet_value") == {"eapcet_rank": 18500}
    assert fee_journey._read_entrance("150", "jee_value") == {}
    assert fee_journey._read_entrance("no", "entrance") == {}


# ------------------------------------------------------------------ 3. the self-check
def test_self_check_corrects_the_scholarship_and_flags_unknown_amounts():
    fee = fees.calculate_fee("btech_cse", percent=87)
    text, problems = answer_check.check("With 87% you get a 40% scholarship: tuition ₹2,55,000.", fee_result=fee)
    assert "25% scholarship" in text and "40%" not in text and problems
    text, problems = answer_check.check("The mess costs ₹77,777 a year.")
    assert "couldn't verify" in text and problems
    text, problems = answer_check.check("CSE tuition is ₹3,40,000 (₹1,70,000 a semester).")
    assert problems == [] and "couldn't verify" not in text


async def test_self_check_runs_on_model_answers(model):
    model.reply = "Sure! The library membership costs ₹99,999 a year."
    done, = await _chat(["tell me something about the library please"])
    assert "couldn't verify" in done["answer"]


# ------------------------------------------------------------------ 4. case summary and copilot
async def test_callback_lead_carries_the_case_summary(leads):
    await _chat(STEPS + ['Apply the "Students from Andhra Pradesh" concession to my fee', "Yes, I have it",
                         "please call me"])
    case = leads[-1]["metadata"]["case"]
    assert case["program"] == "B.Tech CSE" and "25%" in case["scholarship"]
    assert "Students from Andhra Pradesh" in case["concession"] and "proof_ready" in case["signals"]


def test_case_summary_masks_numbers_typed_in_questions():
    case = case_summary.build({}, {}, [{"role": "user", "text": "call me on 9876543210 about fees please"}])
    assert "9876543210" not in str(case) and "******3210" in str(case)


def _lead(hours_ago, request_type="callback", signals=(), status="new", preferred="any time"):
    return SimpleNamespace(
        id=uuid.uuid4(), name="Asha Rani", phone="9876543210", program_interest="btech_cse", status=status,
        created_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        metadata_={"request_type": request_type, "preferred_time": preferred,
                   "case": {"program": "B.Tech CSE", "signals": list(signals), "fee": "₹4,05,000 confirmed",
                            "concession": "Students from Andhra Pradesh: Pending verification", "scholarship": "25% (applied)"}})


def test_copilot_ranks_by_what_the_student_did():
    hot = _lead(2, signals=("fee_summary_done", "concession_pending", "proof_ready"))
    warm = _lead(30, signals=("scholarship",))
    done_ = _lead(1, signals=("fee_summary_done",), status="contacted")
    s_hot, reasons, tier = copilot_service.score(hot)
    assert tier == "hot" and "finished a fee summary" in reasons and "asked in the last 24 hours" in reasons
    assert copilot_service.score(warm)[2] in ("warm", "later")
    assert copilot_service.score(done_)[0] < s_hot and "already contacted" in copilot_service.score(done_)[1]


def test_copilot_draft_uses_the_case_and_never_sends():
    d = copilot_service.draft(_lead(1, signals=("fee_summary_done",)))
    assert d["text"].startswith("Hi Asha,") and "B.Tech CSE" in d["text"] and "₹4,05,000" in d["text"]
    assert "proof" in d["text"] and d["whatsapp_url"].startswith("https://wa.me/919876543210?text=")


# ------------------------------------------------------------------ 5. talk to a counsellor
def test_connect_intent():
    for t in ("I want to talk to a counsellor", "can I speak to a real person", "connect me to someone",
              "Talk to a counsellor", "talk to an admission counsellor"):
        assert intents.is_connect_request(t), t
    for t in ("please call me", "call me back", "don't connect me", "how do counsellors help?"):
        assert not intents.is_connect_request(t), t


def _office(open_now: bool):
    now = datetime.now(live_connect.IST)
    if open_now:
        app_settings.set_for_tests(office_days=list(range(7)), office_hours_start="00:00", office_hours_end="23:59")
    else:
        h = (now + timedelta(hours=2)).strftime("%H:00")
        app_settings.set_for_tests(office_days=list(range(7)), office_hours_start=h,
                                   office_hours_end=h if h != "23:00" else "23:30")


async def test_connect_in_office_hours_rings_then_times_out_to_a_callback(leads):
    _office(True)
    app_settings.set_for_tests(connect_wait_seconds=10)
    sid = f"v412-c-{uuid.uuid4().hex[:8]}"
    done, = await _chat(["I want to talk to a counsellor"], sid)
    req = _card(done, "counsellor_connect")
    assert done["answer"].startswith("Connecting you") and req["status"] == "waiting" and req["phone_last4"] == "3210"
    assert leads and leads[-1]["metadata"]["request_type"] == "callback"           # saved before the wait
    ringing = await live_connect.waiting()
    assert any(r["request_id"] == req["request_id"] and r["phone"] == "9876543210" for r in ringing)
    # time passes: nobody accepted
    key = live_connect._key(req["request_id"])
    stored = await memory._get(key, None)
    stored["deadline"] = time.time() - 1
    await memory._set(key, stored)
    st = await live_connect.status(req["request_id"], sid)
    assert st["status"] == "busy" and st["seconds_left"] == 0
    assert await live_connect.status(req["request_id"], "someone-else-000000") is None     # not another student's


async def test_connect_accepted_by_a_counsellor(leads):
    _office(True)
    sid = f"v412-a-{uuid.uuid4().hex[:8]}"
    done, = await _chat(["can I speak to a real person"], sid)
    rid = _card(done, "counsellor_connect")["request_id"]
    outcome, req = await live_connect.accept(rid, "Priya")
    assert outcome == "ok" and req["phone"] == "9876543210"
    st = await live_connect.status(rid, sid)
    assert st["status"] == "accepted" and st["counsellor"] == "Priya"
    assert (await live_connect.accept(rid, "Ravi"))[0] == "too_late"                # first one wins
    again, = await _chat(["talk to a counsellor"], sid)
    assert "already calling you" in again["answer"]                                  # no duplicate request


async def test_connect_outside_office_hours_arranges_the_callback_without_a_timer(leads):
    _office(False)
    done, = await _chat(["I want to talk to a counsellor"])
    assert not _card(done, "counsellor_connect")
    assert "******3210" in done["answer"] and "call you back" in done["answer"] and leads


async def test_connect_switched_off_in_the_admin_panel(leads):
    _office(True)
    app_settings.set_for_tests(connect_enabled=False)
    done, = await _chat(["I want to talk to a counsellor"])
    assert not _card(done, "counsellor_connect") and "******3210" in done["answer"] and leads


async def test_connect_without_a_number_asks_for_it():
    sid = f"v412-n-{uuid.uuid4().hex[:8]}"
    await memory.update_profile(sid, welcome_actions_shown=True)
    done = None
    async for ev in agent.run_agent("I want to talk to a counsellor", sid, None, client=None):
        if ev["type"] == "done":
            done = ev
    assert "10-digit mobile number" in done["answer"] and not _card(done, "counsellor_connect")


async def test_connect_status_endpoint_is_private():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/agent/connect/" + "a" * 32, params={"session_id": "x" * 20})
        assert res.status_code == 404


# ------------------------------------------------------------------ 6. rules and the keep-awake ping
def test_no_chip_ever_suggests_the_four_year_fee():
    chips = []
    for topic in ("fee_personal", "fee", "scholarship", "concessions", "programs", "default", "placements"):
        chips += followups._chips(topic, "B.Tech CSE", None)
    chips += [fee_journey.NONE_APPLY, fee_journey.SHOW_FEE, fee_journey.RESUME] + fee_journey.ENTRANCE_CHIPS
    for c in chips:
        assert not any(w in c.lower() for w in ("4-year", "4 year", "four year", "full course", "total course",
                                                 "all years")), c


async def test_ping_touches_nothing():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/ping")
        assert res.status_code == 200 and res.json() == {"status": "ok"}


# ------------------------------------------------------------------ v4.12.1: understand what the student asks
SRJC = 'Apply the "SR Junior College student" concession to my fee'
DAY_SCHOLAR = ["No hostel, I'm a day scholar", "No, I'll manage"]


@pytest.mark.parametrize("program_answer,expected", [
    ("B.Tech CSE", "B.Tech Computer Science & Engineering (CSE)"),
    ("B.Tech CSE AIML", "B.Tech CSE (Artificial Intelligence & Machine Learning)"),
    ("CSE with robotics", "B.Tech CSE (Robotics & Automation)"),
])
async def test_fee_summary_shows_the_programme_the_student_chose(program_answer, expected):
    out = await _chat(["Calculate my scholarship", program_answer, "Telangana State Board", "Completed", "885", "MPC",
                       "None of these apply"] + DAY_SCHOLAR)
    course = _card(out[-1], "fee_summary")["course"]
    assert course == expected and "Data Science" not in course.replace(expected, "")


async def test_documents_question_answers_about_the_selected_concession():
    out = await _chat(STEPS[:-1] + ["885", "MPC", SRJC, "Not yet"] + DAY_SCHOLAR + ["Documents needed for the concession"])
    ans = out[-1]["answer"]
    assert "SR Junior College student" in ans and "₹15,000" in ans
    assert "₹2,80,000 → ₹2,65,000" in ans                      # the effect on this student's fee
    assert "I already have your details" not in ans            # never sent to the scholarship steps
    assert "Yes, I have the proof" in out[-1]["suggestions"]


async def test_documents_question_without_a_selection_explains_and_offers_to_check():
    done, = await _chat(["Documents needed for the concession"])
    assert "haven't selected one" in done["answer"] and "Explore special concessions" in done["suggestions"]


async def test_documents_question_mid_flow_answers_then_returns_to_the_open_step():
    out = await _chat(STEPS + [SRJC, "what documents do I need for it?"])
    ans = out[-1]["answer"]
    assert "SR Junior College student" in ans and "back to your fee" in ans and "supporting document" in ans
    assert out[-1]["suggestions"] == ["Yes, I have it", "Not yet"]          # the proof question again


async def test_is_my_concession_approved_and_proof_ready():
    out = await _chat(STEPS + [SRJC, "Not yet"] + DAY_SCHOLAR + ["is my concession approved?", "Yes, I have the proof"])
    assert out[-2]["answer"].startswith("Not yet") and "pending verification" in out[-2]["answer"]
    d = _card(out[-1], "fee_summary")
    assert "proof ready" in d["special_consideration"]["label"] and "updated fee summary" in out[-1]["answer"]


async def test_add_hostel_goes_to_the_hostel_question_even_with_open_steps():
    out = await _chat(["Show my final fee", "B.Tech CSE", "Add hostel to my fee"])
    assert "hostel" in out[-1]["answer"].lower() and not _card(out[-1], "get_special_concessions")
    assert "No hostel, I'm a day scholar" in out[-1]["suggestions"]


@pytest.mark.parametrize("setup", [
    STEPS + [SRJC, "Not yet"] + DAY_SCHOLAR,                        # final with a concession
    ["Show my final fee", "B.Tech CSE"],                            # final, concessions not explored
    STEPS + [SRJC, "Not yet"] + DAY_SCHOLAR + ["Documents needed for the concession"],
    ["Find me the lowest fee for B.Tech CSE", "Telangana State Board", "Completed", "885", "MPC", "No entrance exam",
     "None of these apply", "AC 3-sharing (₹1,35,000)"],
])
async def test_every_button_the_fee_agent_offers_gets_a_relevant_answer(setup, leads, model, monkeypatch):
    # Outside office hours "Talk to a counsellor" arranges the callback at once (inside, it rings the admin panel
    # first): fixed here so the result does not depend on the time the test runs.
    monkeypatch.setattr(live_connect, "in_office_hours", lambda *a, **k: False)
    base = (await _chat(setup))[-1]
    assert base["suggestions"]
    expect = {"Add hostel to my fee": "hostel", "Change hostel": "hostel", "Documents needed for the concession": "document",
              "Talk to a counsellor": "******3210", "Explore special concessions": "category",
              "How do I apply for 2027-28?": "apply", "Show my final fee": "fee summary",
              "Yes, I have the proof": "proof", "Switch to Non-AC 4-sharing": "Non-AC, 4-sharing"}
    for chip in base["suggestions"]:
        before = model.calls
        out = (await _chat(setup + [chip]))[-1]
        text = out["answer"] + " " + " ".join(str(c.get("data", "")) for c in out.get("cards") or [])
        assert "I already have your details" not in text, chip
        assert expect.get(chip, chip.split()[0]).lower() in text.lower(), (chip, out["answer"][:200])
        assert model.calls == before, chip                         # answered by the agent, not a generic model reply
