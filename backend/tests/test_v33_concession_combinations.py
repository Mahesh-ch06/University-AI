"""Tests for Phase 3: Special Category Concessions and Combination Handling.

Verifies:
1. The circular's claimable concession categories (all but the recommendation-only one) have amounts.
2. match_all_special_concessions matches multiple categories when present in text.
3. match_special_concession selects the highest concession amount when multiple apply.
4. Affordability flow accurately computes merit waiver + highest special concession.
"""
import pytest
from app.sru_agent.affordability import (
    _official_categories,
    match_all_special_concessions,
    match_special_concession,
    process_affordability_flow,
)


def test_claimable_categories_come_from_the_circular():
    cats = _official_categories()
    assert len(cats) == 19                      # 20 on the circular; the Chancellor recommendation is not claimable
    assert "chancellor_recommendation" not in {c["key"] for c in cats}
    for cat in cats:
        assert cat["amount"] in (50000, 20000, 15000)
        assert len(cat["keywords"]) >= 1
        assert "label" in cat
        assert "key" in cat


def test_match_all_special_concessions_multiple_matches():
    # User mentions being an AP resident and having a sibling at SRU
    msg = "I am from Andhra Pradesh and my sibling is studying at SR University"
    matches = match_all_special_concessions(msg)
    keys = [m["key"] for m in matches]
    assert "andhra_pradesh" in keys
    assert "sibling" in keys
    assert len(matches) >= 2


def test_match_special_concession_picks_highest_amount():
    # Sibling is 15,000, Orphan is 50,000
    msg = "I have a sibling at SRU and I also lost both parents"
    best = match_special_concession(msg)
    assert best is not None
    assert best["key"] == "orphan"
    assert best["amount"] == 50000
    assert "all_eligible" in best
    assert len(best["all_eligible"]) >= 2


def test_affordability_flow_applies_highest_concession():
    conv_state = {
        "affordability_flow": {
            "step": "awaiting_concession",
            "program": "btech_cse",
            "percent": 88.0,
            "board": "state_board",
        }
    }
    # User claims sibling (15,000) and orphan (50,000)
    msg = "I lost both parents and my brother is at SRU"
    res = process_affordability_flow(msg, {}, conv_state)
    assert res is not None
    # Annual base = 3,40,000. 88% State Board gets 25% merit = 2,55,000
    # Concession = 50,000. Final net tuition = 2,05,000
    assert "₹2,05,000" in res["text"]
    assert "both parents not alive" in res["text"].lower()
    assert "applied highest benefit category" in res["text"]
