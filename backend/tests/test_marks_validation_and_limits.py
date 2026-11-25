"""Tests for dynamic board maximum marks and strict marks-obtained upper limits."""

import pytest

from app.services.card_service import build_counsellor_marks_card
from app.sru_agent import agent, fee_intake


STEPS_TS_COMPLETED = {
    "counsellor_mode": True,
    "program": "btech_cse",
    "waiting_for": "marks",
    "turns": 3,
    "board": "state_board",
    "board_key": "ts_state_board",
    "board_label": "Telangana Intermediate (TSBIE)",
    "academic_stage": "completed",
    "asked": ["board", "stage"],
}


@pytest.mark.parametrize(
    "bad_input",
    [
        "90000",
        "9000000",
        "90000 out of 1000",
        "9000000 out of 1000",
        "my marks are 9000000",
        "scored 1500",
        "9999999",
    ],
)
def test_oversized_gibberish_marks_rejected_and_stay_on_step3(bad_input):
    res = fee_intake.decide(bad_input, {}, dict(STEPS_TS_COMPLETED))
    assert res is not None, f"{bad_input!r} should be handled and rejected, not dropped"
    assert res["action"] == "ask"
    assert res["state"].get("waiting_for") == "marks"
    assert res["state"].get("percent") is None
    assert "Step 3 of 4" in res["text"]
    assert res["cards"][0]["type"] == "counsellor_marks_input"
    assert res["cards"][0]["max_marks"] == 1000


def test_ssc_inter_completed_resolves_dynamically_to_1000_max():
    d_board = fee_intake.parse_details("ssc inter")
    assert d_board.get("board_key") == "ts_state_board"
    d_stage = fee_intake.parse_details("inter 2nd year completed")
    assert d_stage.get("academic_stage") == "completed"
    assert fee_intake.get_max_marks(d_board["board_key"], d_stage["academic_stage"]) == 1000


def test_other_board_also_rejects_absurdly_large_numbers():
    intake = {
        **STEPS_TS_COMPLETED,
        "board_key": "other_state_board",
        "board_label": "Other State Board",
    }
    res = fee_intake.decide("9000000", {}, intake)
    assert res is not None and res["action"] == "ask"
    assert res["state"].get("percent") is None


def test_ib_marks_card_and_validation_enforce_45_points_limit():
    card = build_counsellor_marks_card(board_key="ib", stage_key="completed", max_marks=45)
    assert card["unit"] == "/ 45"
    assert "45" in card["title"]
    ib_intake = {
        **STEPS_TS_COMPLETED,
        "board": "ib",
        "board_key": "ib",
        "board_label": "International Baccalaureate (IB)",
    }
    bad = fee_intake.decide("9000000", {}, ib_intake)
    assert bad["action"] == "ask" and bad["state"].get("ib_score") is None
    too_high = fee_intake.decide("60", {}, ib_intake)
    assert too_high["action"] == "ask" and "45" in too_high["text"]


def test_academic_form_validation_rejects_total_over_2000():
    updates, problems, _prog, _mode = agent._read_academic_form(
        {
            "mode": "scholarship",
            "program": "btech_cse",
            "board_key": "other_state_board",
            "academic_stage": "completed",
            "raw_marks": 9000000,
            "max_marks": 9000000,
        },
        {},
    )
    assert problems and not updates.get("percent")
