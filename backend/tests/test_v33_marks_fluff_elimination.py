"""Test suite verifying elimination of canned celebratory hype and intermediate group survey questions.

Verifies that for 985, 800, 700, 600 marks:
- No 'Wow! Congratulations! 🎉' or cheesy fluff.
- No 'Which group did you study in Intermediate? MPC/BiPC/Commerce'.
- Accurate scholarship calculation (40%, 25%, 20%, 10%).
- Concrete fee quotes and interactive card.
"""
from app.sru_agent import fee_intake, prompt


def test_no_fluff_on_985_marks():
    dec = fee_intake.decide("985 marks", {}, {})
    assert dec is not None
    assert dec["action"] == "ask"
    text = dec["text"]
    text_lower = text.lower()

    # Must NOT contain canned celebratory hype
    assert "wow!" not in text_lower
    assert "congratulations" not in text_lower
    assert "🎉" not in text

    # Must NOT interrogate with academic groups
    assert "which group did you study" not in text_lower
    assert "mpc" not in text_lower
    assert "bipc" not in text_lower
    assert "arts / humanities" not in text_lower

    # Must state 40% Merit Scholarship and net tuition
    assert "40% merit scholarship" in text_lower or "40%" in text
    assert "₹2,04,000" in text
    assert "₹1,36,000" in text

    # Must include fee scholarship card
    assert any(c.get("type") == "fee_scholarship_form" for c in dec.get("cards", []))


def test_no_fluff_on_800_marks():
    dec = fee_intake.decide("800 marks", {}, {})
    assert dec is not None
    assert dec["action"] == "ask"
    text = dec["text"]
    text_lower = text.lower()

    assert "wow!" not in text_lower
    assert "congratulations" not in text_lower
    assert "which group did you study" not in text_lower

    assert "25% merit scholarship" in text_lower or "25%" in text
    assert "₹2,55,000" in text
    assert "₹85,000" in text


def test_no_fluff_on_700_marks():
    dec = fee_intake.decide("700 marks", {}, {})
    assert dec is not None
    assert dec["action"] == "ask"
    text = dec["text"]
    text_lower = text.lower()

    assert "wow!" not in text_lower
    assert "congratulations" not in text_lower
    assert "which group did you study" not in text_lower

    assert "20% merit scholarship" in text_lower or "20%" in text
    assert "₹2,72,000" in text
    assert "₹68,000" in text


def test_no_fluff_on_600_marks():
    dec = fee_intake.decide("600 marks", {}, {})
    assert dec is not None
    assert dec["action"] == "ask"
    text = dec["text"]
    text_lower = text.lower()

    assert "wow!" not in text_lower
    assert "congratulations" not in text_lower
    assert "which group did you study" not in text_lower

    assert "10% merit scholarship" in text_lower or "10%" in text
    assert "₹3,06,000" in text
    assert "₹34,000" in text


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
