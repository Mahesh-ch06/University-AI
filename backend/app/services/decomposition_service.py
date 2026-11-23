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

NON_SPLITTABLE_PHRASES: tuple[str, ...] = (
    "computer science & engineering", "computer science and engineering",
    "science & engineering", "science and engineering",
    "ai & robotics", "ai and robotics",
    "ai & ml", "ai and ml",
    "arts & science", "arts and science",
    "arts & sciences", "arts and sciences",
    "research & development", "research and development",
    "rules and regulations", "rules and timings", "terms and conditions",
    "fee and scholarship", "fees and scholarship", "fees and scholarships",
    "fee and scholarships", "living and learning", "boys and girls",
    "men and women", "sports and games", "food and mess", "mess and food",
    "ac and non-ac", "ac and non ac", "non-ac and ac",
)

# "also", "along with", "as well as", "besides", etc. are strong compound signals
_STRONG_COMPOUND_SIGNALS = re.compile(
    r"\b(also|along\s+with|as\s+well\s+as|besides|moreover|furthermore|in\s+addition|on\s+top\s+of\s+that|not\s+only|and\s+also)\b",
    re.IGNORECASE,
)

# Multiple question marks inside a single message
_MULTI_QUESTION_MARK = re.compile(r"\?.*\?")

_TOPIC_KEYWORD_PATTERN = re.compile(
    r"\b(sru|sr\s+university|cse|aiml|ece|eee|btech|mtech|mba|bba|hostel|hostels|fee|fees|"
    r"placement|placements|scholarship|scholarships|curfew|mess|food|admission|admissions|"
    r"eligibility|ranking|rankings|faculty|lab|labs|sports|club|clubs|campus|vs|versus|"
    r"compare|why\s+sru|why\s+choose|timings?|rules?|bus|transport)\b",
    re.IGNORECASE,
)

# Minimum meaningful sub-query length (tokens)
_MIN_SUB_QUERY_WORDS = 2
# Maximum sub-queries to process (avoid runaway fan-out)
MAX_SUB_QUERIES = 4


def _is_compound_query(message: str) -> bool:
    """Return True if the message likely contains more than one distinct question."""
    if not message or len(message.strip().split()) < 3:
        return False

    msg_clean = message.strip().lower()
    for phrase in NON_SPLITTABLE_PHRASES:
        msg_clean = msg_clean.replace(phrase, "___PHRASE___")

    # 1. Multiple question marks
    if msg_clean.count("?") >= 2:
        return True

    # 2. Numbered inline queries ("1) fees 2) hostel")
    if len(re.findall(r"\b\d+[.)]\s+\S", message)) >= 2:
        return True

    # 3. Strong compound signal words ("also", "along with", etc.)
    if _STRONG_COMPOUND_SIGNALS.search(msg_clean):
        return True

    # 4. Check for "and" / "&" / ";" separating two substantive topic clauses
    parts = re.split(r"\s*(?:;\s*|,\s*(?:and\s+)?|\s+(?:and|&)\s+)\s*", msg_clean)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        substantive = 0
        for p in parts:
            if p == "___phrase___":
                continue
            p_words = p.split()
            if (len(p_words) >= 2 and _TOPIC_KEYWORD_PATTERN.search(p)) or len(p_words) >= 3 or _TOPIC_KEYWORD_PATTERN.search(p):
                substantive += 1
        if substantive >= 2:
            return True

    return False


def _fast_split(message: str) -> list[str]:
    """Split a compound message heuristically into sub-queries without an LLM call."""
    masked = message
    placeholders = {}
    for i, phrase in enumerate(NON_SPLITTABLE_PHRASES):
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        for match in pattern.finditer(masked):
            token = f"___P{i}___"
            placeholders[token] = match.group(0)
            masked = masked[:match.start()] + token + masked[match.end():]

    # Strategy 1: Multiple "?" marks
    if masked.count("?") >= 2:
        parts = [p.strip() + "?" for p in masked.split("?") if p.strip()]
    # Strategy 2: Numbered inline queries
    elif len(re.findall(r"\b\d+[.)]\s+\S", masked)) >= 2:
        numbered = re.split(r"\s*\b\d+[.)]\s+", masked)
        parts = [p.strip() for p in numbered if p.strip()]
    # Strategy 3: Strong compound signals
    elif _STRONG_COMPOUND_SIGNALS.search(masked):
        parts = re.split(
            r"\s*(?:,\s*(?:also|plus)|;\s*|\b(?:also|along\s+with|as\s+well\s+as|besides|moreover|furthermore|in\s+addition|plus|and\s+also)\b)\s*",
            masked,
            flags=re.IGNORECASE,
        )
    # Strategy 4: Conjunction split on "and", "&", ";"
    else:
        parts = re.split(r"\s*(?:;\s*|,\s*(?:and\s+)?|\s+(?:and|&)\s+)\s*", masked, flags=re.IGNORECASE)

    # Restore placeholders and filter candidates
    unmasked = []
    for p in parts:
        p_clean = p.strip()
        for token, orig in placeholders.items():
            p_clean = p_clean.replace(token, orig)
        if p_clean and len(p_clean.split()) >= 1:
            unmasked.append(p_clean)

    if len(unmasked) >= 2:
        return unmasked[:MAX_SUB_QUERIES]

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
