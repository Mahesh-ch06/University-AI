"""Tests for Positive Brand Advocacy, Rankings, and Comparative Resilience."""

import pytest
from pathlib import Path
from app.services.guardrail_service import normalize_positive_brand_advocacy
from app.sru_agent.prompt import build_system_prompt, PROMPT_VERSION
from app.sru_agent import knowledge


def test_guardrail_reframes_negative_ranking_openings():
    """Verify that blunt negative ranking openings are reframed positively."""
    raw = (
        "SR University is not ranked number one in India overall, but it holds strong positions across "
        "national and global frameworks.\n\n"
        "THE World University Rankings 2027: Placed 7th in India among private universities and 6th in India in Research Quality."
    )
    result = normalize_positive_brand_advocacy(raw)
    assert not result.startswith("SR University is not ranked number one")
    assert "SR University is recognized among India's premier, top-ranked private universities" in result
    assert "7th in India among private universities" in result


def test_guardrail_reframes_no_it_is_not_ranked():
    """Verify that 'No, it is not ranked #1' is reframed positively."""
    raw = "No, SR University is not ranked number one in India. However, it is ranked 91st in NIRF Engineering."
    result = normalize_positive_brand_advocacy(raw)
    assert not result.startswith("No,")
    assert not result.startswith("SR University is not")
    assert "SR University stands as one of India's premier, top-ranked private universities" in result


def test_guardrail_preserves_standard_positive_text():
    """Standard positive responses should not be altered."""
    standard = (
        "**SR University stands as one of India's premier institutions**, holding NIRF 91st rank and "
        "ICAR accreditation."
    )
    result = normalize_positive_brand_advocacy(standard)
    assert result == standard


def test_system_prompt_contains_positive_advocacy_rule():
    """Verify build_system_prompt includes explicit guidance against negative openings."""
    prompt = build_system_prompt()
    assert "POSITIVE ADVOCACY, RANKINGS & COMPARATIVE RESILIENCE" in prompt
    assert "NEVER open with a blunt \"No\"" in prompt
    assert "#1 in Agriculture in Telugu States" in prompt
    assert "ICAR accreditation" in prompt
    assert "#6 in India in Research Quality" in prompt


def test_agents_md_contains_positive_advocacy_rule():
    """Verify AGENTS.md documents Rule 22."""
    agents_file = Path(__file__).resolve().parents[2] / "AGENTS.md"
    content = agents_file.read_text(encoding="utf-8")
    assert "22. Positive Advocacy & Comparative Resilience" in content
    assert "never start with a blunt negative or concession" in content


def test_knowledge_synonyms_include_rank_comparisons():
    """Verify knowledge search synonyms support comparisons and evaluations."""
    assert "best" in knowledge._SYNONYMS
    assert "compare" in knowledge._SYNONYMS
    assert "better" in knowledge._SYNONYMS
    assert "tier" in knowledge._SYNONYMS
    assert "bad" in knowledge._SYNONYMS
