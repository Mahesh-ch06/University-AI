"""v4.13.0: quick-response buttons only when asked; Quick Start tiles set in the admin panel.

1. Buttons under an answer (admin setting "suggestion_chips", default 'questions_only'): the answer options of a
   step (Yes / No, rooms, boards...) and the "continue my fee estimate" button are always kept; other suggestions
   only when the reply asks the student something. 'always' gives the earlier behaviour.
2. The Quick Start tiles under the welcome message are a setting (Admin -> Agent -> Quick Start tiles): edited,
   reordered, switched off, up to 8, served to the widget by GET /api/v1/agent/welcome-actions. Long values are
   saved in pieces (the settings column holds 255 characters): no migration.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.services import app_settings
from app.sru_agent import agent, fee_journey, memory


@pytest.fixture
def questions_only():
    app_settings.set_for_tests(suggestion_chips="questions_only")
    yield
    app_settings.set_for_tests(suggestion_chips="always")


# ------------------------------------------------------------------ 1. buttons only when asked
def test_rule(questions_only):
    info = "SR University has 4,000-seat dining and AC / non-AC hostels."
    asks = "Do you want to add the hostel fee to your estimate?"
    chips = ["Hostel fees", "Placements"]
    assert agent._chips_for(info, chips, options=False) == []
    assert agent._chips_for(info + "\n\n" + asks, chips, options=False) == chips
    assert agent._chips_for(info, ["Yes, add it", "No hostel"], options=True) == ["Yes, add it", "No hostel"]
    assert agent._chips_for(info, ["Hostel fees", fee_journey.RESUME], options=False) == [fee_journey.RESUME]


def test_always_mode_keeps_every_suggestion():
    app_settings.set_for_tests(suggestion_chips="always")
    assert agent._chips_for("A plain answer.", ["Hostel fees"], options=False) == ["Hostel fees"]


async def _chat(messages):
    sid = f"v413c-{uuid.uuid4().hex[:10]}"
    await memory.update_profile(sid, name="Ravi Kumar", phone="9876543210", welcome_actions_shown=True)
    conv, out = None, []
    for m in messages:
        async for ev in agent.run_agent(m, sid, conv, client=None):
            if ev["type"] == "done":
                conv = ev.get("conversation_id") or conv
                out.append(ev)
    return out


@pytest.mark.asyncio
async def test_a_step_question_keeps_its_answer_buttons(questions_only):
    out = await _chat(["Calculate my scholarship", "B.Tech CSE", "Telangana State Board", "Completed", "870", "MPC",
                       "None of these apply"])
    hostel = out[-1]
    assert any("No hostel" in c for c in hostel["suggestions"])           # the room options of the hostel step


@pytest.mark.asyncio
async def test_a_plain_answer_gets_no_unrelated_buttons(questions_only):
    [done] = await _chat(["does the campus have food stalls and various food options"])
    if not agent._asks_question(done["answer"]):
        assert done["suggestions"] == []


# ------------------------------------------------------------------ 2. Quick Start tiles
def test_default_tiles_include_why_choose_sru_and_validate():
    tiles = app_settings.ChatSettings().model_dump()["welcome_tiles"]
    assert [t["id"] for t in tiles][:4] == ["calculate_scholarship", "explore_programs", "placements",
                                           "special_consideration"]
    why = next(t for t in tiles if t["id"] == "why_sru")
    assert why["title"] == "Why Choose SRU?" and why["prompt"] == "Why should I choose SR University?"
    for bad in ([{"id": "x", "title": "", "prompt": "hi"}],                           # empty title
                [{"id": "Bad Id!", "title": "A", "prompt": "hi"}],                   # id pattern
                [{"id": "a", "title": "A", "prompt": "hi", "icon": "rocket"}],       # unknown icon
                [{"id": "a", "title": "<b>A</b>", "prompt": "hi"}],                  # markup
                [{"id": "a", "title": "A", "prompt": "hi"}] * 2,                     # same id twice
                [{"id": f"t{i}", "title": "A", "prompt": "hi"} for i in range(9)]):  # more than 8
        with pytest.raises(Exception):
            app_settings.ChatSettings(welcome_tiles=bad)


@pytest.mark.asyncio
async def test_public_endpoint_serves_the_enabled_tiles_in_order():
    from app.main import app
    tiles = [{"id": "why_sru", "title": "Why Choose SRU?", "badge": "#6 Research", "icon": "award",
              "prompt": "Why should I choose SR University?"},
             {"id": "hidden", "title": "Hidden", "prompt": "x", "enabled": False},
             {"id": "calc", "title": "Calculate", "icon": "calculator", "prompt": "Calculate my scholarship"}]
    app_settings.set_for_tests(welcome_tiles=tiles)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/api/v1/agent/welcome-actions")
        assert res.status_code == 200
        assert [t["id"] for t in res.json()["items"]] == ["why_sru", "calc"]
        assert res.json()["items"][0]["badge"] == "#6 Research"
    finally:
        app_settings.set_for_tests(welcome_tiles=app_settings.DEFAULT_WELCOME_TILES)


@pytest.mark.asyncio
async def test_admin_saves_tiles_longer_than_one_database_value_and_reads_them_back():
    from app.main import app
    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    tiles = [{"id": f"tile{i}", "title": f"Tile number {i} for students", "badge": "₹15K–₹50K/yr", "icon": "book",
              "prompt": f"Tell me about topic number {i} at SR University in detail please", "subtitle": "x" * 40}
             for i in range(8)]
    app_settings.reset_for_tests()
    # Connections pooled by an earlier test belong to that test's event loop: start with a fresh pool.
    from app.db.session import engine
    await engine.dispose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        try:
            res = await client.put("/api/v1/admin/settings", json={"welcome_tiles": tiles}, headers=headers)
            if res.status_code == 503:
                pytest.skip("database not reachable")
            assert res.status_code == 200, res.text
            await app_settings.refresh(force=True)                       # read back from the database
            assert [t["id"] for t in app_settings.get("welcome_tiles")] == [t["id"] for t in tiles]
            assert app_settings.get("welcome_tiles")[0]["badge"] == "₹15K–₹50K/yr"
            # shorter again: leftover pieces are removed and the value still reads back
            res = await client.put("/api/v1/admin/settings", json={"welcome_tiles": tiles[:1]}, headers=headers)
            assert res.status_code == 200
            await app_settings.refresh(force=True)
            assert [t["id"] for t in app_settings.get("welcome_tiles")] == ["tile0"]
        finally:
            await client.put("/api/v1/admin/settings", json={"welcome_tiles": app_settings.DEFAULT_WELCOME_TILES},
                             headers=headers)
            app_settings.set_for_tests(ai_answers=False, suggestion_chips="always")


def test_an_open_question_after_a_greeting_is_not_a_yes_no_question():
    from app.sru_agent import followups
    assert followups.needs_yes_no("Hello! What would you like to know about SR University?") is False
    assert followups.needs_yes_no("Do you want to add the hostel fee?") is True
    assert followups.needs_yes_no("Great. Would you like me to check your eligibility?") is True
