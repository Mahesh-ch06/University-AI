"""Tests verifying that cards are frequency-capped per session and not shown repeatedly."""

import pytest
from app.services.card_service import (
    generate_cards,
    clear_session_cards,
    get_session_shown_cards,
    record_session_card,
    PLACEMENT_EXCELLENCE_CARD,
    PROGRAMS_OFFERED_CARD,
    CAMPUS_TOUR_CARD,
    APPLICATION_AD_CARD,
    COMPARISON_CSE_AIML,
    CURRICULUM_CARD,
)


def test_placement_card_shown_only_once_per_session():
    session_id = "test_placement_sess_001"
    clear_session_cards(session_id)

    query = "Tell me about SRU placements and highest package"
    answer = "SRU has a highest package of ₹50.5 LPA and average package of 6 LPA."

    # Turn 1: First time asking -> card should be shown
    cards_t1 = generate_cards(query, answer, session_id=session_id)
    assert any(c.get("type") == "placement_highlights" for c in cards_t1)
    assert "placement_highlights" in get_session_shown_cards(session_id)

    # Turn 2: Follow-up in same session -> card should NOT be shown again
    cards_t2 = generate_cards(query, answer, session_id=session_id)
    assert not any(c.get("type") == "placement_highlights" for c in cards_t2)

    # Turn 3: Different session -> card should be shown for new user
    other_session = "test_placement_sess_002"
    clear_session_cards(other_session)
    cards_other = generate_cards(query, answer, session_id=other_session)
    assert any(c.get("type") == "placement_highlights" for c in cards_other)


def test_programs_offered_card_shown_only_once_per_session():
    session_id = "test_prog_sess_001"
    clear_session_cards(session_id)

    query = "What programs and courses are offered at SRU?"
    answer = "SRU offers B.Tech, M.Tech, BBA, MBA, B.Sc Agriculture, and Ph.D."

    # Turn 1: First time -> card present
    cards_t1 = generate_cards(query, answer, session_id=session_id)
    assert any(c.get("type") == "programs_offered" for c in cards_t1)

    # Turn 2: Second time in same session -> card suppressed
    cards_t2 = generate_cards(query, answer, session_id=session_id)
    assert not any(c.get("type") == "programs_offered" for c in cards_t2)


def test_comparison_and_curriculum_cards_frequency_capped():
    session_id = "test_comp_curr_001"
    clear_session_cards(session_id)

    # Comparison
    comp_q = "compare cse vs aiml"
    cards_c1 = generate_cards(comp_q, "Here is CSE vs AIML", session_id=session_id)
    assert any(c.get("type") == "comparison" for c in cards_c1)

    cards_c2 = generate_cards(comp_q, "Here is CSE vs AIML", session_id=session_id)
    assert not any(c.get("type") == "comparison" for c in cards_c2)

    # Curriculum
    curr_q = "what is the curriculum for cse"
    cards_curr1 = generate_cards(curr_q, "Here is curriculum", session_id=session_id)
    assert any(c.get("type") == "curriculum" for c in cards_curr1)

    cards_curr2 = generate_cards(curr_q, "Here is curriculum", session_id=session_id)
    assert not any(c.get("type") == "curriculum" for c in cards_curr2)


def test_cards_suppression_via_seen_card_types():
    session_id = "test_seen_cards_001"
    clear_session_cards(session_id)

    seen = {"placement_highlights", "programs_offered", "campus_tour"}
    cards = generate_cards(
        "Tell me about placements and campus tour",
        "SRU placements and campus overview.",
        session_id=session_id,
        seen_card_types=seen,
    )
    assert not any(c.get("type") in seen for c in cards)


def test_video_recommendations_not_capped():
    session_id = "test_video_nocap_001"
    clear_session_cards(session_id)

    # Turn 1: Ask for campus tour videos
    cards_t1 = generate_cards(
        "show me campus tour videos",
        "Here are videos.",
        session_id=session_id,
        keyword_videos=True,
    )
    assert any(c.get("type") == "video_recommendations" for c in cards_t1)

    # Turn 2: Ask for videos again in the SAME session -> still shown (not capped!)
    cards_t2 = generate_cards(
        "show me campus tour videos",
        "Here are videos again.",
        session_id=session_id,
        keyword_videos=True,
    )
    assert any(c.get("type") == "video_recommendations" for c in cards_t2)
