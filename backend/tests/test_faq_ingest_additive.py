"""The FAQ ingest's additive mode and the start-up fee clean-up (v4.17.0).

* --add-missing indexes only entries missing from (or changed in) the search index, matched by SECTION and
  question (the same question can be in two sections), never a retired section (Fee), and deletes no database row.
* The start-up clean-up checks only the ANSWER of a Q&A chunk for retired fee phrases: a student's question such as
  "Is it 60% and above?" does not make its corrected answer obsolete.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.auto_seed import _OBSOLETE_FEE_MARKERS, _answer_part  # noqa: E402
from scripts.ingest_university_doc import _missing_or_changed, _retired_sections  # noqa: E402
from scripts.parse_university_docx import ParsedEntry  # noqa: E402


def _entry(section, question, answer):
    return ParsedEntry(section=section, sub_section=section, page_url="", question=question, answer=answer)


class FakeCollection:
    def __init__(self, chunks):
        self.chunks = chunks          # [(id, metadata, document)]

    def get(self, where=None, include=None):
        rows = [c for c in self.chunks if (c[1] or {}).get("document_type") == "faq"]
        return {"ids": [c[0] for c in rows], "metadatas": [c[1] for c in rows], "documents": [c[2] for c in rows]}


def test_same_question_in_two_sections_is_two_entries():
    adm = _entry("Admissions", "What is the last date to apply?", "Apply early.")
    sch = _entry("Scholarship", "What is the last date to apply?", "Slabs are fixed.")
    col = FakeCollection([("a1", {"document_type": "faq", "section": "Admissions",
                                  "question": adm.question}, adm.chunk_text)])
    to_add, stale = _missing_or_changed([adm, sch], col)
    assert [e.section for e in to_add] == ["Scholarship"] and stale == []      # the Admissions one is kept


def test_changed_answer_replaces_only_its_own_chunk():
    old = _entry("Programs", "Is it 60% and above?", "Yes, 60% is the cutoff.")
    new = _entry("Programs", "Is it 60% and above?", "Not quite: 55% for CSE and ECE, 50% for others.")
    col = FakeCollection([("p1", {"document_type": "faq", "section": "Programs", "question": old.question},
                           old.chunk_text)])
    to_add, stale = _missing_or_changed([new], col)
    assert to_add == [new] and stale == ["p1"]
    assert _missing_or_changed([old], col) == ([], [])                         # unchanged: nothing to do


def test_retired_sections_are_never_indexed():
    assert "Fee" in _retired_sections()
    fee = _entry("Fee", "How much fee do I need to pay?", "See the fee card.")
    assert _missing_or_changed([fee], FakeCollection([])) == ([], [])


def test_retired_phrase_in_the_question_does_not_retire_a_corrected_answer():
    corrected = "Section: Eligibility\nQ: Is it 60% and above?\nA: Not quite: 55% for CSE and ECE."
    assert not any(m in _answer_part(corrected) for m in _OBSOLETE_FEE_MARKERS)
    outdated = "Section: Eligibility\nQ: What is the cutoff?\nA: 60% and above in Intermediate."
    assert any(m in _answer_part(outdated) for m in _OBSOLETE_FEE_MARKERS)
    assert _answer_part("Fees: 60% aggregate required") == "Fees: 60% aggregate required"   # not a Q&A chunk
