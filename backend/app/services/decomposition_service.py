"""Query decomposition service — splits compound/multi-question messages into sub-queries.

Handles inputs like:
  - "What are the fees and hostel timings?"
  - "Tell me about placements and also the scholarship for 90%+ PCM"
  - "What is the cutoff for CSE? Also, are there internships?"
  - "hostel rules, fees, and curfew timings?"

Returns a list of independent sub-queries that can each be retrieved and answered separately,
then merged into a single cohesive response.
"""

from __future__ import annotations

import logging
import re

from app.providers.base import LLMProvider
from app.services.prompt_service import render_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fast heuristic patterns to detect compound / multi-question inputs
# ---------------------------------------------------------------------------

# "also", "along with", "as well as", "besides", etc. are strong compound signals
_STRONG_COMPOUND_SIGNALS = re.compile(
    r"\b(also|along\s+with|as\s+well\s+as|besides|moreover|furthermore|in\s+addition|on\s+top\s+of\s+that|not\s+only|and\s+also)\b",
    re.IGNORECASE,
)

# Multiple question marks inside a single message
_MULTI_QUESTION_MARK = re.compile(r"\?.*\?")

# Explicit "and" or comma joining two distinct domain topics (not just adjectives)
# Split and check that both sides have domain-relevant words
_DOMAIN_TOPICS = re.compile(
    r"\b(fee|fees|hostel|placement|scholarship|bus|transport|admission|eligibility|"
    r"curfew|timings|mess|room|internship|cutoff|ranking|lab|course|semester|attendance|"
    r"library|club|sports|canteen|faculty|registration|deadline)\b",
    re.IGNORECASE,
)

# Enumerated / bulleted queries joined inline (e.g. "1) fees 2) hostel 3) bus")
# Match inline numbering patterns on the same line
_NUMBERED_INLINE_GLOBAL = re.compile(
    r"(?:(?:^|\s|\,)(?:\d+[.)]\s+))([^0-9?!]{3,}?)(?=\s*(?:\d+[.)]\s+)|$)",
    re.MULTILINE,
)
_NUMBERED_INLINE_SIMPLE = re.compile(r"\b\d+[.)]\s+\S")

# Minimum meaningful sub-query length (tokens)
_MIN_SUB_QUERY_WORDS = 3
# Maximum sub-queries to process (avoid runaway fan-out)
MAX_SUB_QUERIES = 4

# Explicit conjunction split points (separating two clauses in list form)
_COMMA_CONJUNCTION_SPLIT = re.compile(
    r"\s*(?:"
    r",\s*and\s+(?:also\s+)?"       # ", and", ", and also"
    r"|;\s*"                          # semicolons
    r"|,\s*(?=(?:\w+\s*){1,4}(?:,|$|\band\b))"  # list commas (e.g. "X, Y, Z")
    r"|\band\s+also\b"
    r"|\balong\s+with\b"
    r"|\bas\s+well\s+as\b"
    r"|\bbesides\b"
    r"|\bmoreover\b"
    r"|\bfurthermore\b"
    r")\s*",
    re.IGNORECASE,
)


def _is_compound_query(message: str) -> bool:
    """Return True if the message likely contains more than one distinct question."""
    # Multiple question marks → almost certainly compound
    if _MULTI_QUESTION_MARK.search(message):
        return True

    # Strong compound signal words ("also", "along with", etc.)
    if _STRONG_COMPOUND_SIGNALS.search(message):
        # Confirm both sides have domain topics
        parts = _STRONG_COMPOUND_SIGNALS.split(message, maxsplit=1)
        filtered = [p.strip() for p in parts if p and not _STRONG_COMPOUND_SIGNALS.match(p.strip())]
        both_have_topics = all(_DOMAIN_TOPICS.search(p) for p in filtered if p)
        if both_have_topics and len(filtered) >= 2:
            return True
        # Even if only one side has domain topics, still treat as compound
        if any(_DOMAIN_TOPICS.search(p) for p in filtered if p):
            return True

    # Numbered inline queries ("1) fees 2) hostel")
    if _NUMBERED_INLINE_SIMPLE.search(message):
        # Count inline numbering occurrences
        count = len(re.findall(r"\b\d+[.)]\s+\S", message))
        if count >= 2:
            return True

    # Comma/semicolon-separated list with multiple domain topics
    topic_hits = _DOMAIN_TOPICS.findall(message)
    if len(topic_hits) >= 3:
        # Multiple different domain topics mentioned → likely compound
        unique_topics = {t.lower() for t in topic_hits}
        if len(unique_topics) >= 2:
            return True

    # Explicit conjunction-separated clause check: split and ensure ≥2 meaningful fragments
    parts = _COMMA_CONJUNCTION_SPLIT.split(message)
    meaningful = [p.strip() for p in parts if len(p.split()) >= _MIN_SUB_QUERY_WORDS]
    if len(meaningful) >= 2:
        return True

    return False


def _fast_split(message: str) -> list[str]:
    """Split a compound message heuristically into sub-queries without an LLM call."""
    # Strategy 1: Split on numbered/bulleted inline patterns
    # Find all occurrences of "N) text" or "N. text"
    numbered_parts = re.split(r"\s*\b\d+[.)]\s+", message)
    if len(numbered_parts) >= 3:  # First element is text before "1)", rest are numbered parts
        # First element might be empty or preamble, skip it
        candidates = [p.strip() for p in numbered_parts[1:] if len(p.split()) >= _MIN_SUB_QUERY_WORDS]
        if len(candidates) >= 2:
            return candidates[:MAX_SUB_QUERIES]

    # Strategy 2: Split on explicit "?"-terminated sub-questions
    q_parts = [p.strip() for p in message.split("?") if p.strip()]
    if len(q_parts) >= 2:
        candidates = [p + "?" for p in q_parts if len(p.split()) >= _MIN_SUB_QUERY_WORDS]
        if len(candidates) >= 2:
            return candidates[:MAX_SUB_QUERIES]

    # Strategy 3: Split on strong compound conjunctions
    if _STRONG_COMPOUND_SIGNALS.search(message):
        parts = _STRONG_COMPOUND_SIGNALS.split(message)
        candidates = [p.strip() for p in parts if p and not _STRONG_COMPOUND_SIGNALS.match(p.strip()) and len(p.split()) >= _MIN_SUB_QUERY_WORDS]
        if len(candidates) >= 2:
            return candidates[:MAX_SUB_QUERIES]

    # Strategy 4: Comma/conjunction-based split
    parts = _COMMA_CONJUNCTION_SPLIT.split(message)
    candidates = [p.strip() for p in parts if len(p.split()) >= _MIN_SUB_QUERY_WORDS]
    if len(candidates) >= 2:
        return candidates[:MAX_SUB_QUERIES]

    return [message]


async def decompose_query(
    message: str,
    conversation_context: str,
    llm_provider: LLMProvider,
    *,
    force_llm: bool = False,
) -> list[str]:
    """Decompose a compound message into individual sub-queries.

    Algorithm:
    1. Fast heuristic check — if not compound, return [message] immediately.
    2. Try fast heuristic splitting first (zero LLM cost).
    3. If fast split yields <2 meaningful parts OR force_llm=True,
       fall back to an LLM decomposition call.

    Args:
        message: The raw user message.
        conversation_context: Stringified recent conversation history.
        llm_provider: Injected LLM provider.
        force_llm: If True, always use the LLM even when heuristics succeed.

    Returns:
        A deduplicated list of standalone sub-query strings, in order.
        Returns [message] when it is a single-question input.
    """
    if not _is_compound_query(message):
        logger.debug("Single-question query detected, skipping decomposition.")
        return [message]

    # Try cheap heuristic split first
    if not force_llm:
        fast_parts = _fast_split(message)
        if len(fast_parts) >= 2:
            logger.info(
                "Decomposed compound query heuristically into %d sub-queries: %s",
                len(fast_parts),
                fast_parts,
            )
            return fast_parts[:MAX_SUB_QUERIES]

    # Fall back to LLM for ambiguous compound queries
    try:
        prompt = render_prompt(
            "decomposition",
            conversation=conversation_context or "No prior conversation.",
            message=message,
        )
        response = await llm_provider.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        sub_queries = _parse_llm_decomposition(response, original=message)
        if len(sub_queries) >= 2:
            logger.info(
                "LLM decomposed query into %d sub-queries: %s",
                len(sub_queries),
                sub_queries,
            )
            return sub_queries[:MAX_SUB_QUERIES]
    except Exception as exc:
        logger.warning("LLM decomposition failed ('%s'): %s — falling back to heuristic.", message[:50], exc)

    # Last resort: heuristic split (may return single item)
    return _fast_split(message)[:MAX_SUB_QUERIES]


def _parse_llm_decomposition(response: str, original: str) -> list[str]:
    """Parse the numbered list returned by the decomposition LLM prompt.

    Expected format (from decomposition.md prompt):
        1. <sub-query one>
        2. <sub-query two>
        ...

    Falls back to the original message if parsing fails.
    """
    lines = response.strip().splitlines()
    sub_queries: list[str] = []
    for line in lines:
        line = line.strip()
        # Match numbered list items: "1.", "1)", "1:", or plain lines
        match = re.match(r"^(?:\d+[.):\s]+)(.+)$", line)
        if match:
            candidate = match.group(1).strip().strip('"').strip("'")
            if len(candidate.split()) >= _MIN_SUB_QUERY_WORDS:
                sub_queries.append(candidate)
        elif line and not re.match(r"^[#\-*>]", line) and len(line.split()) >= _MIN_SUB_QUERY_WORDS:
            # Bullet or plain-text fallback
            sub_queries.append(line.lstrip("-•* "))

    if not sub_queries:
        return [original]

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for q in sub_queries:
        key = q.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(q)

    return deduped if len(deduped) >= 2 else [original]


def merge_sub_answers(
    sub_queries: list[str],
    sub_answers: list[str],
    sources_per_query: list[list[dict]],
) -> tuple[str, list[dict]]:
    """Merge multiple sub-answers into a single coherent response.

    Args:
        sub_queries: The decomposed sub-query strings.
        sub_answers: The RAG-generated answer for each sub-query.
        sources_per_query: The source references for each sub-query's answer.

    Returns:
        (merged_answer, deduplicated_sources)
    """
    if len(sub_answers) == 0:
        return "", []
    if len(sub_answers) == 1:
        return sub_answers[0], sources_per_query[0] if sources_per_query else []

    parts: list[str] = []
    for i, (query, answer) in enumerate(zip(sub_queries, sub_answers), 1):
        heading = query.strip().rstrip("?").strip()
        heading = heading[0].upper() + heading[1:] if heading else f"Part {i}"
        parts.append(f"### {heading}\n\n{answer.strip()}")

    merged = "\n\n".join(parts)

    # Deduplicate sources across sub-queries
    seen_sources: set[tuple] = set()
    all_sources: list[dict] = []
    for src_list in sources_per_query:
        for src in src_list:
            key = (src.get("document_id", ""), src.get("section", ""))
            if key not in seen_sources:
                seen_sources.add(key)
                all_sources.append(src)

    return merged, all_sources
