"""Tests for Fee & Scholarship Assessment Form Flow and All-India 10+2 Boards.

Verifies:
1. All India 10+2 board recognition in fee_intake.py (TS, AP, CBSE, ICSE, NIOS, Other State Boards, IB).
2. Multi-step intake behavior (Course -> Board -> Marks/Rank -> Calculate).
3. In-chat Fee & Scholarship Form Card generation (build_fee_scholarship_form_card).
4. Single-shot query calculation.
5. fee_flow follow-up preservation of course when clicking "Calculate scholarship for my marks".
"""
import pytest
from app.services.card_service import build_fee_scholarship_form_card
from app.sru_agent import fee_flow, fee_intake, fees


def test_build_fee_scholarship_form_card():
    card = build_fee_scholarship_form_card(selected_program="btech_cse", selected_board="ts_state_board")
    assert card["type"] == "fee_scholarship_form"
    assert card["selected_program"] == "btech_cse"
    assert card["selected_board"] == "ts_state_board"
    assert len(card["programs"]) >= 10
    assert len(card["boards"]) >= 7

    # Check board options include all India options
    board_keys = [b["key"] for b in card["boards"]]
    assert "ts_state_board" in board_keys
    assert "ap_state_board" in board_keys
    assert "cbse" in board_keys
    assert "icse" in board_keys
    assert "other_state_board" in board_keys
    assert "nios" in board_keys
    assert "ib" in board_keys


def test_parse_details_all_india_boards():
    # Telangana State Board
    d1 = fee_intake.parse_details("I studied in Telangana State Board with 88%")
    assert d1.get("board") == "state_board"
    assert d1.get("percent") == 88.0

    # AP State Board
    d2 = fee_intake.parse_details("BIEAP with 920 marks out of 1000")
    assert d2.get("board") == "state_board"
    assert d2.get("percent") == 92.0

    # Other State Boards across India
    d3 = fee_intake.parse_details("I am from Maharashtra State Board with 85% in 12th")
    assert d3.get("board") == "state_board"
    assert d3.get("percent") == 85.0

    d4 = fee_intake.parse_details("Karnataka PUC board, 90%")
    assert d4.get("board") == "state_board"
    assert d4.get("percent") == 90.0

    d5 = fee_intake.parse_details("Other state board across India with 95%")
    assert d5.get("board") == "state_board"
    assert d5.get("percent") == 95.0

    # CBSE, ICSE, NIOS
    d6 = fee_intake.parse_details("CBSE board, 89%")
    assert d6.get("board") == "cbse"
    assert d6.get("percent") == 89.0

    d7 = fee_intake.parse_details("ICSE 12th with 94%")
    assert d7.get("board") == "cbse"
    assert d7.get("percent") == 94.0

    d8 = fee_intake.parse_details("NIOS student with 80%")
    assert d8.get("board") == "cbse"
    assert d8.get("percent") == 80.0

    # IB
    d9 = fee_intake.parse_details("IB Diploma with 36 points")
    assert d9.get("board") == "ib"
    assert d9.get("ib_score") == 36


def test_decide_multi_step_flow():
    # Step 1: User asks broad fee without course
    r1 = fee_intake.decide("what is the fee structure?", profile={}, intake={})
    assert r1 is not None
    assert r1["action"] == "ask"
    assert r1["state"]["waiting_for"] == "program"
    assert len(r1["cards"]) == 1
    assert r1["cards"][0]["type"] == "counsellor_program_selection"   # v4.13.0: step card, not the old form
    assert "course" in r1["text"].lower() and "board" in r1["text"].lower()

    # Step 2: User specifies course, but board is missing
    r2 = fee_intake.decide("B.Tech CSE", profile={}, intake=r1["state"])
    assert r2 is not None
    assert r2["action"] == "ask"
    assert r2["state"]["program"] == "btech_cse"
    assert r2["state"]["waiting_for"] == "board"
    assert len(r2["cards"]) == 1
    assert r2["cards"][0]["program"] == "btech_cse"
    assert any("board" in chip.lower() for chip in r2["chips"])

    # Direct course enquiry: "what is the fee for btech cse"
    r2_direct = fee_intake.decide("what is the fee for btech cse", profile={}, intake={})
    assert r2_direct is not None
    assert r2_direct["action"] == "ask"
    assert r2_direct["state"]["program"] == "btech_cse"
    assert r2_direct["state"]["waiting_for"] == "board"
    assert len(r2_direct["cards"]) == 1
    assert r2_direct["cards"][0]["program"] == "btech_cse"

    # Step 3: User specifies board, but marks/rank are missing
    r3 = fee_intake.decide("Telangana State Board", profile={}, intake=r2["state"])
    assert r3 is not None
    assert r3["action"] == "ask"
    assert r3["state"]["board"] == "state_board"
    assert r3["state"]["waiting_for"] == "percent"
    assert len(r3["cards"]) == 1
    # v4.13.0: the marks step card for the board chosen (Telangana Intermediate: out of 1000)
    assert r3["cards"][0]["type"] == "counsellor_marks_input" and r3["cards"][0]["max_marks"] == 1000
    assert any("%" in chip for chip in r3["chips"])

    # Step 4: User provides marks
    r4 = fee_intake.decide("88%", profile={}, intake=r3["state"])
    assert r4 is not None
    assert r4["action"] == "calculate"
    assert r4["args"]["program"] == "btech_cse"
    assert r4["args"]["board"] == "state_board"
    assert r4["args"]["percent"] == 88.0

    # Verify calculation
    calc = fees.calculate_fee(**r4["args"])
    assert calc["program_key"] == "btech_cse"
    assert calc["scholarship_percent"] == 25  # 80-91.99% TS State Board = 25%
    assert calc["tuition_first_year_after_scholarship"] == "₹2,55,000"  # 340000 - 25%


def test_decide_all_india_other_state_board_calculation():
    # Student from Maharashtra or UP board with 94% in B.Tech ECE
    intake = {"program": "btech_ece", "board": "state_board", "board_label": "Other State Board across India"}
    res = fee_intake.decide("94%", profile={}, intake=intake)
    assert res is not None
    assert res["action"] == "calculate"
    assert res["args"]["program"] == "btech_ece"
    assert res["args"]["board"] == "state_board"
    assert res["args"]["percent"] == 94.0

    calc = fees.calculate_fee(**res["args"])
    assert calc["scholarship_percent"] == 30  # 92-97.99% State Board = 30%
    assert calc["tuition_first_year_after_scholarship"] == "₹1,89,000"  # 270000 - 30%


def test_decide_single_shot_query():
    # User provides course, board, and marks in one go
    res = fee_intake.decide("What is the fee for B.Tech CSE, CBSE board with 95%?", profile={}, intake={})
    assert res is not None
    assert res["action"] == "calculate"
    assert res["args"]["program"] == "btech_cse"
    assert res["args"]["board"] == "cbse"
    assert res["args"]["percent"] == 95.0

    calc = fees.calculate_fee(**res["args"])
    assert calc["scholarship_percent"] == 40  # 95-100% CBSE = 40%
    assert calc["tuition_first_year_after_scholarship"] == "₹2,04,000"  # 340000 - 40%


def test_fee_flow_followup_preserves_course():
    # Simulate user in completed fee_flow state for B.Tech CSE clicking "Calculate scholarship for my marks"
    conv_state = {
        "fee_flow_state": "completed",
        "fee_flow_school": "school_cs_ai",
        "fee_flow_prog": "btech_cse",
        "fee_flow_year": "2027-28",
    }
    result = fee_flow.process_fee_flow("Calculate scholarship for my marks", "sess-1", {}, conv_state)
    assert result is not None
    assert "B.Tech CSE" in result["text"] or "Computer Science" in result["text"]
    assert "10+2 / Intermediate Board" in result["text"]
    assert len(result["cards"]) == 1
    assert result["cards"][0]["type"] == "counsellor_board_selection"   # v4.13.0: step card, not the old form
    assert result["cards"][0]["program"] == "btech_cse"
    assert result["new_state"]["fee_intake"]["program"] == "btech_cse"
    assert result["new_state"]["fee_intake"]["waiting_for"] == "board"
