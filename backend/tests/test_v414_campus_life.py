"""v4.14.0: events, campus life, clubs, sports, hostel life and food from the approved facts; event photo cards and
official videos edited in the admin panel (Admin -> Campus media)."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.services import app_settings, video_service
from app.sru_agent import agent, campus_life, memory


@pytest.fixture(autouse=True)
def _defaults():
    app_settings.set_for_tests(event_highlights=app_settings.DEFAULT_EVENT_HIGHLIGHTS, videos={})
    yield
    app_settings.set_for_tests(event_highlights=app_settings.DEFAULT_EVENT_HIGHLIGHTS, videos={})


# ------------------------------------------------------------------ what a message is about
@pytest.mark.parametrize("message, expected", [
    ("what events happen at SRU", "events"),
    ("fests in sru?", "events"),
    ("tell me about Lumina", "event:lumina"),
    ("is there a hostel night", "event:lumina"),
    ("hostel hawa kab hota hai", "event:lumina"),
    ("what is sparkrill", "event:sparkrill"),
    ("sparkill date", "event:sparkrill"),
    ("what is navadhara", "event:navadhara"),
    ("bathukamma celebration?", "event:navadhara"),
    ("when is swagatham", "event:swagatham"),
    ("freshers party?", "event:swagatham"),
    ("project expo", "event:pragathi"),
    ("any hackathons?", "event:hackathon"),
    ("when is convocation", "event:more_events"),
    ("how is campus life", "campus_life"),
    ("what do students do after classes", "campus_life"),
    ("how is the hostel food", "food"),
    ("mess timings", "food"),
    ("non veg available?", "food"),
    ("how is hostel life", "hostel_life"),
    ("is the hostel good", "hostel_life"),
    ("what clubs are there", "clubs"),
    ("is there a dance club", "clubs"),
    ("tech clubs", "clubs"),
    ("what sports facilities are there", "sports"),
    ("is there a gym", "sports"),
    ("stress", "wellness"),
])
def test_topic(message, expected):
    assert campus_life.topic(message) == expected


@pytest.mark.parametrize("message", [
    "hostel fees", "is there sports quota", "hostel rules", "is hostel safe", "B.Tech CSE fees", "placements",
    "what is the fee of hostel night", "talk to a counsellor", "alumni placements", "hii", "B.Tech CSE",
    "scholarship for 90%", "hostel curfew timings", "AC room fee",
])
def test_not_ours(message):
    assert campus_life.topic(message) is None


def test_a_bare_word_answers_a_pending_step():
    assert campus_life.topic("sports", waiting=True) is None              # e.g. a concession step
    assert campus_life.topic("how is the hostel food?", waiting=True) == "food"   # a real question still is


# ------------------------------------------------------------------ the answers
def test_events_overview_lists_the_admin_events_and_asks_which():
    ans = campus_life.answer("events", "what events happen at SRU")
    assert "50+ events" in ans.text and "Lumina – Hostel Night" in ans.text and "Sparkrill" in ans.text
    assert ans.text.rstrip().endswith("?")
    assert ans.event_ids[0] == "sparkrill" and "http" not in ans.text           # no source links


def test_one_event_and_a_past_date_is_last_held():
    e = next(x for x in app_settings.DEFAULT_EVENT_HIGHLIGHTS if x["id"] == "swagatham")
    assert campus_life._when(e, today=date(2026, 11, 24)).startswith("last held")
    assert campus_life._when(e, today=date(2026, 10, 1)) == "16 October 2026"
    ans = campus_life.answer("event:lumina", "tell me about lumina")
    assert ans.event_ids == ["lumina"] and "Girls' and Boys'" in ans.text


def test_clubs_one_group_and_a_club_that_is_not_listed():
    assert "39 student clubs" in campus_life.answer("clubs", "what clubs are there").text
    dance = campus_life.answer("clubs", "is there a dance club").text
    assert dance.startswith("Yes, SR University has the **Dance Club**")
    tech = campus_life.answer("clubs", "tech clubs").text
    assert "Google Developers Club" in tech and "Dance Club" not in tech
    chess = campus_life.answer("clubs", "is there a chess club").text
    assert "Chess** club isn't on SR University's official list" in chess


def test_food_and_hostel_life_use_the_verified_facts():
    food = campus_life.answer("food", "is food good in hostel").text
    assert food.startswith("Yes!") and "4,000-seat" in food and "7:30–8:30 AM" in food
    hostel = campus_life.answer("hostel_life", "how is hostel life").text
    assert not hostel.startswith("Yes") and "8:30 PM" in hostel and "Lumina" in hostel


def test_admin_events_are_used_at_once():
    app_settings.set_for_tests(event_highlights=[
        {"id": "dandiya", "title": "Dandiya Night", "when": "Every October", "summary": "Garba and dandiya.",
         "image_url": "https://sru.edu.in/x.webp", "keywords": "dandiya, garba"},
        {"id": "lumina", "title": "Lumina – Hostel Night", "enabled": False}])
    assert campus_life.topic("is there a dandiya night?") == "event:dandiya"
    assert campus_life.topic("tell me about lumina") != "event:lumina"           # switched off
    card = campus_life.event_cards(["dandiya", "lumina"])
    assert [i["id"] for i in card["items"]] == ["dandiya"]


def test_event_settings_are_validated():
    for bad in ({"id": "x", "title": "A", "image_url": "http://insecure.example/a.png"},
                {"id": "x", "title": "<b>A</b>"},
                {"id": "Bad Id", "title": "A"},
                {"id": "x", "title": "A", "video_id": "watch?v=nope"}):
        with pytest.raises(Exception):
            app_settings.ChatSettings(event_highlights=[bad])
    ok = app_settings.EventHighlight(id="x", title="A", video_id="https://youtu.be/ITwoDHleH8g?t=4")
    assert ok.video_id == "ITwoDHleH8g"


# ------------------------------------------------------------------ videos edited in the admin panel
def test_hidden_moved_and_added_videos():
    app_settings.set_for_tests(videos={
        "hidden": ["rpRekBrnGYs"], "topics": {"ITwoDHleH8g": "Campus Life & Fests"},
        "added": [{"id": "https://www.youtube.com/shorts/rbQit8BTfUc", "title": "Lumina Girls Hostel Nights",
                   "category": "Hostels & Living", "type": "short", "keywords": "lumina, hostel night"}]})
    ids = {v["id"]: v for v in video_service.catalog()}
    assert "rpRekBrnGYs" not in ids
    assert ids["ITwoDHleH8g"]["category"] == "Campus Life & Fests"
    assert ids["rbQit8BTfUc"]["url"] == "https://www.youtube.com/shorts/rbQit8BTfUc"
    card = video_service.create_video_card([{"id": "rpRekBrnGYs", "title": "x"}, ids["rbQit8BTfUc"]])
    assert [v["id"] for v in card["videos"]] == ["rbQit8BTfUc"]                 # a hidden video is never shown


# ------------------------------------------------------------------ in the chat
async def _chat(messages):
    sid = f"v414-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True)
    conv, out = None, []
    for m in messages:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    return out


@pytest.mark.asyncio
async def test_chat_events_then_one_event_then_yes():
    events, lumina, yes = await _chat(["what events happen at SRU", "tell me about Lumina", "yes"])
    assert any(c["type"] == "event_highlights" for c in events["cards"])
    assert "Lumina – Hostel Night" in lumina["answer"]
    card = next(c for c in lumina["cards"] if c["type"] == "event_highlights")
    assert card["items"][0]["video_url"].endswith("ITwoDHleH8g")
    assert "50+ events" in yes["answer"]                                     # "yes" to "see the other events?"


@pytest.mark.asyncio
async def test_chat_food_has_the_official_food_video():
    [food] = await _chat(["how is the hostel food"])
    assert "4,000-seat" in food["answer"]
    vids = next(c for c in food["cards"] if c["type"] == "video_recommendations")["videos"]
    assert vids[0]["id"] == "rpRekBrnGYs"


@pytest.mark.asyncio
async def test_chat_hostel_fee_is_not_taken_over():
    [fee] = await _chat(["hostel fees"])
    assert "₹" in fee["answer"] and "Hostel life at SR University" not in fee["answer"]


# ------------------------------------------------------------------ v4.14.0 (cont.): random videos, ads, admin lists
def test_videos_are_picked_at_random_from_the_topic():
    seen = set()
    for _ in range(40):
        vids = video_service.get_keyword_videos("hostel video", limit=2)
        assert len(vids) == 2 and all("Hostels" in v["category"] for v in vids)
        seen.update(v["id"] for v in vids)
    assert len(seen) >= 4                                   # not the same two every time
    shown = {v["id"] for v in video_service.get_keyword_videos("hostel video", limit=2)}
    for _ in range(10):                                      # already shown in this chat: others first
        assert not shown & {v["id"] for v in video_service.get_keyword_videos("hostel video", limit=2,
                                                                                exclude=shown)}


def test_ads_are_validated_and_only_enabled_ones_are_public():
    with pytest.raises(Exception):
        app_settings.ChatSettings(chat_ads=[{"id": "a", "title": "A", "link_url": "javascript:alert(1)"}])
    with pytest.raises(Exception):
        app_settings.ChatSettings(chat_ads=[{"id": "a", "title": "A", "enabled": True}])   # on, but no link
    with pytest.raises(Exception):
        app_settings.ChatSettings(chat_ads=[{"id": f"a{i}", "title": "A", "link_url": "https://sru.edu.in"}
                                            for i in range(7)])


@pytest.mark.asyncio
async def test_public_ads_and_admin_video_list():
    from httpx import ASGITransport, AsyncClient

    from app.config import settings
    from app.main import app
    app_settings.set_for_tests(chat_ads=[
        {"id": "on", "title": "Admissions open", "tag": "New", "link_url": "https://apply.sru.edu.in",
         "image_url": "https://sru.edu.in/a.webp"},
        {"id": "off", "title": "Old offer", "link_url": "https://sru.edu.in", "enabled": False}])
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/agent/chat-ads")
            assert res.status_code == 200 and [a["id"] for a in res.json()["items"]] == ["on"]
            assert (await client.get("/api/v1/admin/videos")).status_code in (401, 403, 422)
            ok = await client.get("/api/v1/admin/videos", headers={"X-Admin-Key": settings.ADMIN_API_KEY})
            assert ok.status_code == 200 and len(ok.json()["builtin"]) >= 50
            assert "Hostels & Living" in ok.json()["topics"]
    finally:
        app_settings.set_for_tests(chat_ads=app_settings.DEFAULT_CHAT_ADS)
