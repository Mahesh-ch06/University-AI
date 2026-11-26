"""
Parser for the SRU university data DOCX.

Actual document structure observed:
  - style='Title'     → top-level section heading (e.g. "Admissions", "Notifications")
  - style='Normal', bold=True, short text → question (or sub-section label)
  - style='Normal', bold=False → answer paragraph (may be multi-paragraph)
  - Bare URL line     → page URL associated with the preceding block of questions

A "question" is a bold Normal paragraph that reads like a question
(contains "?" or is clearly interrogative). Bold Normal paragraphs
without "?" are treated as sub-section labels.

Entries with blank/empty answers are skipped.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_RE_URL = re.compile(r"^https?://\S+$", re.IGNORECASE)
_BLANK_MARKERS = {"", "n/a", "not available", "tbd", "to be updated", "-", "\u2013", "none"}


@dataclass
class ParsedEntry:
    section: str
    sub_section: str
    page_url: str | None
    question: str
    answer: str
    chunk_text: str = field(init=False)

    def __post_init__(self) -> None:
        label = self.sub_section or self.section
        parts = [f"Section: {label}"]
        if self.page_url:
            parts.append(f"Source URL: {self.page_url}")
        parts.append(f"Q: {self.question}")
        parts.append(f"A: {self.answer}")
        self.chunk_text = "\n".join(parts)


def _is_blank(text: str) -> bool:
    return text.strip().lower() in _BLANK_MARKERS


_RE_NUMBERED = re.compile(r"^\s*\d{1,3}[.)]\s+(?=\S)")
_STARTERS = ("what", "when", "where", "who", "whom", "whose", "how", "why", "can", "is", "are", "am", "do", "does",
             "did", "will", "which", "should", "could", "would", "has", "have", "may")


def _strip_number(text: str) -> str:
    """"16. Who is the Senior Director...?" -> "Who is the Senior Director...?" (the number is list position only)."""
    return _RE_NUMBERED.sub("", text, count=1).strip()


def _looks_like_question(text: str) -> bool:
    """A paragraph that asks something: it has a question mark, or it starts with a question word and is not a
    full sentence (no closing full stop). Numbering ("12. ...") is ignored."""
    text = _strip_number(text)
    if not text:
        return False
    if "?" in text:
        return True
    first = text.lower().split()[0].strip(",:;")
    return first in _STARTERS and not text.rstrip().endswith((".", "!"))


def _is_label(text: str) -> bool:
    """A short heading-like line ("Hostel Fees", "Mess Timings") rather than a sentence of an answer."""
    t = _strip_number(text)
    return bool(t) and len(t.split()) <= 6 and not t.rstrip().endswith((".", "!", ":", ";", ","))


def _para_is_bold(para) -> bool:
    """True if ALL non-empty runs in the paragraph are bold."""
    runs = [r for r in para.runs if r.text.strip()]
    return bool(runs) and all(r.bold for r in runs)


def parse_university_docx(file_path: Path, report: dict | None = None) -> list[ParsedEntry]:
    """
    Parse the SRU university DOCX and return ParsedEntry objects.

    Rules (v4.17.1, from an audit of the whole document):
      * Title paragraphs start a section.
      * A Heading paragraph that is a question ("16. Who is the Senior Director of Admissions and Marketing?") is a
        QUESTION; only other headings are sub-section labels. (Earlier every heading was a label, so all 113
        Heading-3 questions and their answers were lost.)
      * A bold Normal paragraph that is a question, or a numbered bold item in a list of questions
        ("12. Mess Timings"), is a question; its list number is not part of the question.
      * Everything else under a question is its answer, kept in order with line breaks (numbered steps inside an
        answer stay in the answer). Bold sentences inside an answer do not end it; only a short bold label does.
      * A bare URL line is the source page for the entries that follow.
      * Questions with no answer are skipped and listed in `report["unanswered"]`; paragraphs that belong to no
        question are listed in `report["orphans"]` (nothing is dropped silently).
    """
    try:
        from docx import Document as DocxDocument
    except ImportError as e:
        raise ImportError("python-docx is required: pip install python-docx") from e

    doc = DocxDocument(str(file_path))
    entries: list[ParsedEntry] = []
    report = report if report is not None else {}
    report.setdefault("unanswered", [])
    report.setdefault("orphans", [])

    current_section = "General"
    current_sub_section = ""
    current_page_url: str | None = None

    pending_question: str | None = None
    answer_lines: list[str] = []

    def _flush() -> None:
        nonlocal pending_question, answer_lines
        if pending_question is None:
            return
        answer_text = "\n".join(l for l in answer_lines if l).strip()
        # An "answer" made only of further questions and labels (a list of unanswered questions) is no answer.
        substantive = [l for l in answer_lines
                       if l.strip() and not _looks_like_question(l) and len(l.split()) >= 4]
        if not _is_blank(answer_text) and substantive:
            entries.append(ParsedEntry(
                section=current_section,
                sub_section=current_sub_section,
                page_url=current_page_url,
                question=pending_question,
                answer=answer_text,
            ))
        else:
            report["unanswered"].append((current_section, pending_question))
            logger.debug("Skipping unanswered Q in [%s > %s]: %s",
                         current_section, current_sub_section, pending_question[:80])
        pending_question = None
        answer_lines = []

    def _start_question(text: str) -> None:
        nonlocal pending_question, answer_lines
        _flush()
        # A question and its answer in one paragraph, split by a line break
        # ("Who is the Dean of PG Studies?\nThe Dean of PG Studies is ..."): the first line is the question.
        first, _, rest = text.partition("\n")
        pending_question = _strip_number(first if rest.strip() and "?" in first else text)
        answer_lines = [l.strip() for l in rest.splitlines() if l.strip()] if rest.strip() and "?" in first else []

    for para in doc.paragraphs:
        raw = para.text.strip()
        if not raw:
            continue
        style_name = para.style.name or ""

        # ── Top-level section (Title style) ───────────────────────────────
        if style_name == "Title":
            _flush()
            current_section = raw
            current_sub_section = ""
            current_page_url = None
            continue

        # ── Heading styles: a question, or a sub-section label ─────────────
        if "Heading" in style_name:
            if _looks_like_question(raw) or _RE_NUMBERED.match(raw):
                _start_question(raw)
            else:
                _flush()
                current_sub_section = raw
                current_page_url = None
            continue

        # ── Bare URL line: the source page of what follows ────────────────
        if _RE_URL.match(raw):
            current_page_url = raw.rstrip(".,;)")
            continue

        is_bold = _para_is_bold(para)
        if is_bold and _looks_like_question(raw):
            _start_question(raw)
            continue
        if is_bold and _RE_NUMBERED.match(raw) and _is_label(raw):
            # a numbered topic item in a list of questions ("12. Mess Timings"): asked as a topic
            _start_question(raw)
            continue
        if is_bold and _is_label(raw):
            _flush()
            current_sub_section = raw
            continue

        # ── Answer text (plain or bold sentences, numbered steps) ─────────
        if pending_question is not None:
            answer_lines.append(raw)
        elif _looks_like_question(raw):
            report["unanswered"].append((current_section, _strip_number(raw)))   # a question with no answer
        else:
            report["orphans"].append((current_section, raw))   # sample prompts / example dialogue, not facts

    _flush()

    logger.info("Parsed %d answerable Q&A entries from '%s' (%d unanswered, %d orphan paragraphs)",
                len(entries), file_path.name, len(report["unanswered"]), len(report["orphans"]))
    return entries
