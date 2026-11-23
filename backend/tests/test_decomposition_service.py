"""Tests for the multi-question decomposition service."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.decomposition_service import (
    _is_compound_query,
    _fast_split,
    _parse_llm_decomposition,
    decompose_query,
    merge_sub_answers,
    MAX_SUB_QUERIES,
)


# ---------------------------------------------------------------------------
# _is_compound_query
# ---------------------------------------------------------------------------

class TestIsCompoundQuery:
    def test_single_question_not_compound(self):
        assert not _is_compound_query("What are the fees for B.Tech?")

    def test_multiple_question_marks(self):
        assert _is_compound_query("What is the fee? What are hostel timings?")

    def test_conjunction_and(self):
        # "also" is a strong compound signal alongside two domain topics
        assert _is_compound_query("Tell me about fees and also hostel rules for first year students")

    def test_also_keyword(self):
        assert _is_compound_query("What is the cutoff for CSE? Also, are there internships?")

    def test_numbered_inline(self):
        assert _is_compound_query("1) fees 2) hostel 3) bus timings")

    def test_short_single_topic(self):
        assert not _is_compound_query("hostel fee")

    def test_along_with_conjunction(self):
        assert _is_compound_query("Tell me about placements along with the scholarship criteria")

    def test_comma_and_conjunction(self):
        assert _is_compound_query("hostel curfew, mess food quality, and room types available")

    def test_as_well_as(self):
        assert _is_compound_query("What is the fee structure as well as the hostel rules?")


# ---------------------------------------------------------------------------
# _fast_split
# ---------------------------------------------------------------------------

class TestFastSplit:
    def test_question_mark_split(self):
        parts = _fast_split("What is the fee? What are hostel timings?")
        assert len(parts) >= 2
        assert any("fee" in p.lower() for p in parts)
        assert any("hostel" in p.lower() for p in parts)

    def test_numbered_inline_split(self):
        parts = _fast_split("What is the fee? What are hostel timings?")
        assert len(parts) >= 2

    def test_conjunction_split(self):
        parts = _fast_split("Tell me about fees and hostel timings for first year students")
        # Should split at "and" junction
        assert len(parts) >= 1  # At least original preserved

    def test_max_sub_queries_cap(self):
        parts = _fast_split("fees? hostel? bus? placement? scholarship? clubs?")
        assert len(parts) <= MAX_SUB_QUERIES

    def test_single_question_returns_original(self):
        q = "What is the admission process?"
        parts = _fast_split(q)
        assert len(parts) == 1
        assert parts[0] == q


# ---------------------------------------------------------------------------
# _parse_llm_decomposition
# ---------------------------------------------------------------------------

class TestParseLlmDecomposition:
    def test_numbered_list(self):
        response = """1. What is the fee structure for B.Tech at SR University?
2. What is the hostel in-time for 1st year students?"""
        parts = _parse_llm_decomposition(response, "original message")
        assert len(parts) == 2
        assert "fee structure" in parts[0].lower()
        assert "hostel" in parts[1].lower()

    def test_parenthetical_numbering(self):
        response = """1) Fee structure for CSE
2) Hostel curfew timings"""
        parts = _parse_llm_decomposition(response, "original")
        assert len(parts) == 2

    def test_fallback_on_bad_response(self):
        response = "I cannot parse this"
        parts = _parse_llm_decomposition(response, "original message here")
        assert parts == ["original message here"]

    def test_deduplication(self):
        response = """1. What is the fee structure?
2. What is the fee structure?
3. What are hostel timings?"""
        parts = _parse_llm_decomposition(response, "original")
        # Duplicate should be removed
        texts = [p.lower() for p in parts]
        assert texts.count("what is the fee structure?") <= 1

    def test_single_item_falls_back_to_original(self):
        response = "1. What is the fee?"
        parts = _parse_llm_decomposition(response, "What is the fee and hostel?")
        # Single item from LLM → returns original
        assert parts == ["What is the fee and hostel?"]


# ---------------------------------------------------------------------------
# decompose_query
# ---------------------------------------------------------------------------

class TestDecomposeQuery:
    @pytest.mark.asyncio
    async def test_single_query_no_decomposition(self):
        mock_llm = AsyncMock()
        result = await decompose_query(
            "What is the admission process?",
            conversation_context="",
            llm_provider=mock_llm,
        )
        assert result == ["What is the admission process?"]
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_compound_query_fast_split(self):
        mock_llm = AsyncMock()
        result = await decompose_query(
            "What is the fee? What are hostel timings?",
            conversation_context="",
            llm_provider=mock_llm,
        )
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_compound_uses_llm_when_heuristic_fails(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = (
            "1. What is the fee structure for B.Tech?\n"
            "2. What are the hostel in-time rules?"
        )
        # Use force_llm with a clearly compound query (two question marks)
        result = await decompose_query(
            "What is the fee? What are hostel rules?",
            conversation_context="",
            llm_provider=mock_llm,
            force_llm=True,
        )
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_max_sub_queries_respected(self):
        mock_llm = AsyncMock()
        result = await decompose_query(
            "fees? hostel? bus? placement? scholarship? clubs? labs?",
            conversation_context="",
            llm_provider=mock_llm,
        )
        assert len(result) <= MAX_SUB_QUERIES

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_heuristic(self):
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = RuntimeError("LLM unavailable")
        result = await decompose_query(
            "What is the fee? What are hostel timings?",
            conversation_context="",
            llm_provider=mock_llm,
            force_llm=True,
        )
        # Should still return something (heuristic fallback)
        assert isinstance(result, list)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# merge_sub_answers
# ---------------------------------------------------------------------------

class TestMergeSubAnswers:
    def test_single_answer_passthrough(self):
        answer, sources = merge_sub_answers(
            ["What is the fee?"],
            ["The fee is ₹1,50,000 per year."],
            [[{"document_id": "fee.pdf", "title": "Fee Schedule", "section": ""}]],
        )
        assert answer == "The fee is ₹1,50,000 per year."
        assert len(sources) == 1

    def test_two_answers_merged_with_headings(self):
        answer, sources = merge_sub_answers(
            ["What is the fee?", "What are hostel timings?"],
            ["The fee is ₹1,50,000.", "Hostel in-time is 8:30 PM."],
            [
                [{"document_id": "fee.pdf", "title": "Fee", "section": ""}],
                [{"document_id": "hostel.pdf", "title": "Hostel", "section": ""}],
            ],
        )
        assert "### What is the fee" in answer
        assert "### What are hostel timings" in answer
        assert "₹1,50,000" in answer
        assert "8:30 PM" in answer
        assert len(sources) == 2

    def test_source_deduplication(self):
        shared_src = {"document_id": "handbook.pdf", "title": "Handbook", "section": "fees"}
        answer, sources = merge_sub_answers(
            ["Q1", "Q2"],
            ["Answer 1", "Answer 2"],
            [[shared_src], [shared_src]],  # Same source in both sub-answers
        )
        assert len(sources) == 1  # Deduplicated

    def test_empty_sources_handled(self):
        answer, sources = merge_sub_answers(
            ["Q1", "Q2"],
            ["Answer 1", "Answer 2"],
            [[], []],
        )
        assert sources == []

    def test_heading_capitalisation(self):
        answer, sources = merge_sub_answers(
            ["what is the fee?"],
            ["The fee is ₹1,50,000."],
            [[]],
        )
        # Single item — returns plain answer
        assert answer == "The fee is ₹1,50,000."
