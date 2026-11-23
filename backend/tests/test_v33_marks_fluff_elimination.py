"""Test suite verifying elimination of canned celebratory hype and intermediate group survey questions.

Verifies that for 985, 800, 700, 600 marks:
- No 'Wow! Congratulations! 🎉' or cheesy fluff.
- No 'Which group did you study in Intermediate? MPC/BiPC/Commerce'.
- The total marks are asked, never assumed to be 1000.
- Accurate scholarship slab (40%, 25%, 20%, 10%) once the total is known, then the programme is asked.
"""
from app.sru_agent import fee_intake, prompt


_CASES = [("985", "40%"), ("800", "25%"), ("700", "20%"), ("600", "10%")]


def _two_step(raw: str):
    """Bare marks: the total is asked first (never assumed), then the slab is given."""
    first = fee_intake.decide(f"{raw} marks", {}, {})
    assert first is not None and first["action"] == "ask"
    assert first["state"]["waiting_for"] == "marks_max"
    assert f"out of how many total marks is **{raw}**" in first["text"].lower()
    second = fee_intake.decide(f"{raw} out of 1000", {}, first["state"])
    assert second is not None and second["action"] == "ask"
    return first, second


def test_no_fluff_and_no_assumed_total_for_bare_marks():
    for raw, slab in _CASES:
        first, second = _two_step(raw)
        for text in (first["text"], second["text"]):
            low = text.lower()
            # No canned hype, no group survey
            assert "wow!" not in low and "congratulations" not in low and "🎉" not in text
            assert "which group did you study" not in low
            assert "mpc" not in low and "bipc" not in low
        # Accurate slab once the total is known, and no other programme's fees dropped in
        assert f"{slab} merit scholarship" in second["text"].lower()
        assert "₹" not in second["text"]
        assert "Which programme are you interested in?" in second["text"]
        assert any(c.get("type") == "fee_scholarship_form" for c in second.get("cards", []))


def test_bare_numbers_routed_to_intake():
    for num in ("985", "800", "700", "600"):
        assert fee_intake.is_fee_enquiry(num) is True
        dec = fee_intake.decide(num, {}, {})
        assert dec is not None
        assert dec["action"] == "ask"
        assert "congratulations" not in dec["text"].lower()


def test_system_prompt_has_negative_constraints():
    p = prompt.build_system_prompt({})
    assert "NEVER use canned celebratory hype" in p
    assert "NEVER interrogate students with academic surveys" in p
    assert len(p) < 9000
