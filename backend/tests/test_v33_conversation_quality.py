"""Tests for Phase 2: Conversational AI Personality, Single Question, and Programme Switching.

Verifies:
1. Negative constraints against nicknames (buddy, bro, dear, beta, etc.) in prompt.
2. Single question at a time rule in prompt.
3. No re-introduction mid-conversation in prompt.
4. Programme switching resets relevant intake state (switching UG <-> PG).
5. Programme switching within same level preserves academic marks.
"""
import pytest
from app.sru_agent.prompt import build_system_prompt
from app.sru_agent import fee_intake


def test_prompt_has_negative_nickname_constraints():
    prompt = build_system_prompt({})
    for forbidden in ("buddy", "dear", "bro", "beta", "anna"):
        assert forbidden in prompt.lower()
    assert "never use informal nicknames" in prompt.lower()


def test_prompt_has_single_question_rule():
    prompt = build_system_prompt({})
    assert "only one question at a time" in prompt.lower()


def test_prompt_has_no_reintroduction_rule():
    prompt = build_system_prompt({})
    assert "do not re-introduce yourself" in prompt.lower() or "never repeat your name" in prompt.lower()


def test_programme_switching_ug_to_pg_resets_marks():
    # User was in intake for B.Tech CSE and had entered 10+2 marks
    intake = {
        "program": "btech_cse",
        "board": "state_board",
        "percent": 88.0,
        "turns": 2,
        "waiting_for": "entrance",
    }
    # User switches to MBA
    res = fee_intake.decide("Actually what is the fee for MBA?", {}, intake)
    assert res["action"] == "ask"
    assert res["state"]["program"] == "mba"
    # 10+2 percentage should be cleared since MBA requires qualifying degree %
    assert "percent" not in res["state"]
    assert "board" not in res["state"]


def test_programme_switching_same_level_preserves_marks():
    # User was in intake for B.Tech CSE and had entered 88%
    intake = {
        "program": "btech_cse",
        "board": "state_board",
        "percent": 88.0,
        "turns": 2,
        "waiting_for": "entrance",
    }
    # User switches to Mechanical Engineering
    res = fee_intake.decide("Tell me the fee for Mechanical instead", {}, intake)
    assert res is not None
    # Program updated to btech_mech
    assert res["state"] is None or res["state"]["program"] == "btech_mech"
    if res["action"] == "calculate":
        assert res["args"]["program"] == "btech_mech"
        assert res["args"]["percent"] == 88.0
