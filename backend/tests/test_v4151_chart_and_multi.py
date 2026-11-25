"""v4.15.1: the fee chart collects the student's details first; several questions in one message."""
import pytest

from tests.test_v410_fresh_answers_and_fee_plan import _cards, _chat, model  # noqa: F401

pytestmark = pytest.mark.asyncio


async def test_yes_to_the_chart_asks_marks_then_concessions_then_shows_the_chart(model):
    out = await _chat(["cse fee with ac hostel 4 sharing", "Yes, prepare my fee chart",
                       "Telangana Intermediate (TSBIE)", "Completed Intermediate (Passed out)", "900 out of 1000",
                       "MPC (Maths, Physics, Chemistry)", "None of these apply"])
    ask = out[1]
    assert "marks" in ask["answer"] and not _cards(ask, "fee_summary")          # no chart before the details
    assert _cards(ask, "counsellor_board_selection")
    assert not any(_cards(o, "fee_summary") for o in out[1:-1])
    (card,) = _cards(out[-1], "fee_summary")
    d = card["data"]
    assert d["scholarship"]["status"] == "applied" and "25%" in d["scholarship"]["label"]
    assert any("Hostel" in r["item"] for r in d["rows"])


async def test_prepare_chart_during_a_concession_asks_marks_first(model):
    out = await _chat(['Apply the "SRU old student or child of old student or Sibling of Old Student" concession to my B.Tech ECE fee',
                       "📋 Prepare my full fee chart"])
    assert not _cards(out[1], "fee_summary") and _cards(out[1], "counsellor_board_selection")


async def test_known_details_show_the_chart_at_once(model):
    import uuid
    from app.sru_agent import memory
    sid = f"v4151-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, percent=85, board="state_board")
    out = await _chat(['Apply the "SRU old student or child of old student or Sibling of Old Student" concession to my B.Tech ECE fee',
                       "Yes, I have it", "📋 Prepare my full fee chart"], sid)
    assert _cards(out[-1], "fee_summary")


# ------------------------------------------------------------------ several questions in one message
async def test_two_reasons_and_hostel_life_from_a_student_leaving_delhi(model):
    (o,) = await _chat(["hey I am leaving the Delhi just give me 2 reason and how is hostel life because if I join "
                        "for 4 years it's my home"])
    a = o["answer"]
    assert "2 reasons to choose SRU" in a and "\n1. " in a and "\n2. " in a and "\n3. " not in a.split("---")[0]
    assert "Residential Living" in a or "hostel" in a.lower()
    assert "₹15,000 a year" in a and "outside Telangana and AP" in a


@pytest.mark.parametrize("message,parts", [
    ("why sru? how are placements? is hostel safe? what is the fee? any scholarship?", 5),
    ("tell me about placements, hostel food, scholarships and is the campus safe?", 4),
    ("I am from Delhi, why sru and how are placements", 2),
])
async def test_every_question_in_a_message_is_answered(model, message, parts):
    (o,) = await _chat([message])
    assert o["answer"].count("\n---\n") >= parts - 1


def test_the_model_gets_the_list_of_questions():
    from app.sru_agent import compound
    note = compound.model_note("what is the attendance rule, how are exams held and when do classes start")
    assert note and "ASKS 3 THINGS" in note
    assert compound.model_note("what is the fee for cse") is None
    assert not compound.from_other_state("fees going up in the hostel")


@pytest.mark.parametrize("question,expected", [
    ("how far is the railway station", "**29 km** from Warangal Railway Station"),
    ("what is the attendance rule", "**10% to 25%** more"),
    ("is wifi there in hostel", "whole campus is on Wi-Fi"),
    ("can i bring a bike", "**bicycle is fine**"),
    ("is there an atm", "Canara Bank ATM"),
    ("is ragging there", "zero tolerance"),
    ("when do classes start", "hasn't been announced"),
])
def test_everyday_campus_facts_come_from_the_handbook(question, expected):
    from app.sru_agent import quick_facts
    a = quick_facts.answer(question)
    assert a and expected in a.text


@pytest.mark.parametrize("message,parts", [
    ("how is the food, what are the hostel timings, is ragging there, and how far is the railway station, "
     "and is there a gym", 5),
    ("what is the attendance rule, how are exams held and when do classes start", 3),
    ("is wifi there in hostel, can i bring a bike, and is there an atm", 3),
])
async def test_multi_questions_are_answered_from_verified_sources(model, message, parts):
    (o,) = await _chat([message])
    assert o["answer"].count("\n---\n") >= parts - 1
    assert "12 to 15" not in o["answer"]


def test_library_hours_and_size_from_the_handbook():
    from app.sru_agent import quick_facts
    a = quick_facts.answer("what are the library timings")
    assert a and "8:30 AM to 8:30 PM" in a.text and "1,000 sq. m" in a.text
    assert quick_facts.answer("what is the library like at sru?") is None


async def test_a_message_the_code_cannot_split_goes_to_the_model_whole(model):
    # gym + a part with no verified code answer: no single-topic answer may take only the gym
    (o,) = await _chat(["is there a gym and what is the dress code for students"])
    assert "Olympic-standard gym" not in o["answer"]


def test_campus_size_is_the_confirmed_170_acres():
    from app.sru_agent import quick_facts
    a = quick_facts.answer("how big is the campus")
    assert a and "170+ acres" in a.text and "150" not in a.text


async def test_library_gym_and_campus_size_are_all_answered(model):
    (o,) = await _chat(["what are the library timings and is there a gym and how big is the campus"])
    assert o["answer"].count("\n---\n") >= 2 and "170+ acres" in o["answer"] and "8:30 AM" in o["answer"]


async def test_the_chart_asks_the_room_type_when_the_student_never_chose_one(model):
    out = await _chat(["Hostel fees", "B.Tech CSE", "Yes, prepare my fee chart"])
    assert not any(_cards(o, "fee_summary") for o in out)


async def test_wifi_part_gets_the_wifi_answer(model):
    (o,) = await _chat(["is wifi there in hostel, can i bring a bike, and is there an atm"])
    assert "on Wi-Fi" in o["answer"] and "bicycle is fine" in o["answer"] and "Canara Bank ATM" in o["answer"]


def test_robotics_club_is_not_the_degree_answer():
    from app.sru_agent import quick_facts
    assert quick_facts.answer("is there a robotics club") is None
    assert quick_facts.answer("is there a robotics course")


async def test_a_concession_question_during_the_fee_steps_is_answered_first(model):
    out = await _chat(["B.Tech Civil fee", "any fee concession for single parent"])
    assert "only one parent alive" in out[-1]["answer"].lower() or "single parent" in out[-1]["answer"].lower()
    assert "Almost there" not in out[-1]["answer"]


async def test_cutoff_question_after_how_to_apply_says_it_is_not_published(model):
    out = await _chat(["how to get admission in sru", "what was the cutoff rank for CSE last year?"])
    assert "does not publish" in out[-1]["answer"] and "What were your" not in out[-1]["answer"]


# ------------------------------------------------------------------ live chat 25 Nov: not eligible, videos, programmes
async def test_no_fee_for_a_programme_the_student_cannot_join(model):
    out = await _chat(["CSE", "Eligibility", "450 out of 1000", "can u show my fee", "BBA fees"])
    for o in out[-2:]:
        assert "can't show you a fee" in o["answer"] and not _cards(o, "fee_summary") and not _cards(o, "calculate_fee")
        assert "50%" in o["answer"] and o["suggestions"] == ["Talk to a counsellor"]


async def test_corrected_marks_give_the_fee_again(model):
    import uuid
    from app.sru_agent import memory
    sid = f"v4151-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, percent=82, board="state_board", program_interest="btech_cse")
    (o,) = await _chat(["can u show my fee"], sid)
    assert "can't show you a fee" not in o["answer"]


def test_why_sru_videos_are_not_programme_specific():
    from app.services import video_service
    vids = video_service.get_keyword_videos("Why Choose SR University", limit=2)
    assert vids and all(v["category"] not in ("School of Agriculture", "MBA & Business") for v in vids)
    assert video_service.get_keyword_videos("why choose agriculture at sru", limit=2)[0]["category"] == "School of Agriculture"


async def test_programme_overview_asks_ug_or_pg_and_lists_pdf_courses(model):
    out1 = await _chat(["Explore programs offered at SR University"])
    assert out1[0]["cards"] and out1[0]["cards"][0]["type"] == "counsellor_choice"
    labels = [opt["label"] for opt in out1[0]["cards"][0]["options"]]
    assert labels == ["Undergraduate (UG)", "Postgraduate (PG)"]

    from app.sru_agent import dialogue, quick_facts

    out_ug = await _chat(["Explore programs offered at SR University", "Undergraduate (UG)"])
    ug_text = out_ug[-1]["answer"]
    assert "Undergraduate (UG) Programmes" in ug_text
    assert "BTech CSE (AIML, Data Science, Cyber Security, Robotics and Automation, Quantum AI)" in ug_text
    assert "B.Tech IEP" in ug_text
    assert "BSc in Hospitality and Event Management" in ug_text
    assert "B.Des (Design)" in ug_text
    assert "₹" not in ug_text
    assert "MTech" not in ug_text

    out_pg = await _chat(["Explore programs offered at SR University", "Postgraduate (PG)"])
    pg_text = out_pg[-1]["answer"]
    assert "Postgraduate (PG) Programmes" in pg_text
    assert "MBA (Finance, Operations, HR, Business Analytics, Marketing)" in pg_text
    assert "MCA" in pg_text
    assert "MTech (" in pg_text
    assert "MSc (" in pg_text
    assert "MBA in Agri Business Management" in pg_text
    assert "₹" not in pg_text
    assert "BTech" not in pg_text

    # Switching directly via chip also works without restarting
    switch = dialogue.decide("View PG programmes", {"dialogue": {}}, {})
    assert switch and "MBA in Agri Business Management" in switch["text"] and "₹" not in switch["text"]

    assert quick_facts.answer("courses for bipc students").text.startswith("With **BiPC**")


@pytest.mark.parametrize("question,expected", [
    ("can i stay outside the campus", True), ("is hostel compulsory", True), ("can i be a day scholar", True),
    ("No hostel, I'm a day scholar", False),          # the fee-step chip, not a question
])
def test_day_scholar_question_vs_the_hostel_step_answer(question, expected):
    from app.sru_agent import quick_facts
    a = quick_facts.answer(question)
    assert bool(a) is expected
    if a:
        assert "day scholar" in a.text and "₹30,000" in a.text and "required to stay" not in a.text


def test_music_band_is_the_sangeetam_club():
    from app.sru_agent import campus_life
    assert campus_life.topic("is there a music band") == "clubs"
    assert "Sangeetam" in campus_life.answer("clubs", "is there a music band").text


@pytest.mark.parametrize("message,key", [("b.des?", "bdes"), ("b.com?", "bcom"), ("m.tech", "mtech")])
def test_dotted_programme_names_alone_are_recognised(message, key):
    from app.sru_agent import dialogue
    assert dialogue._broad_program(message) == (key, False)
