"""The university DOCX parser (v4.17.1): every question shape in the real document is recognised.

Built from an audit of data/SRU Agentic AI.docx: 113 questions there are Heading-3 paragraphs ("16. Who is the
Senior Director of Admissions and Marketing?") and the old parser turned every heading into a sub-section label,
so those questions and their answers were lost (78 entries -> 191 now).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

docx = pytest.importorskip("docx")

from scripts.parse_university_docx import parse_university_docx  # noqa: E402

DOCX = Path(__file__).resolve().parents[1] / "data" / "SRU Agentic AI.docx"


def _build(tmp_path, items):
    d = docx.Document()
    for kind, text in items:
        if kind == "title":
            d.add_paragraph(text, style="Title")
        elif kind == "h3":
            d.add_paragraph(text, style="Heading 3")
        elif kind == "bold":
            d.add_paragraph().add_run(text).bold = True
        elif kind == "mixed":                       # partly bold sentence
            p = d.add_paragraph()
            p.add_run(text[:10]).bold = True
            p.add_run(text[10:])
        else:
            d.add_paragraph(text)
    path = tmp_path / "t.docx"
    d.save(path)
    return path


def test_heading_questions_numbering_and_bold_answers(tmp_path):
    path = _build(tmp_path, [
        ("title", "Leadership"),
        ("h3", "16. Who is the Senior Director of Admissions and Marketing?"),
        ("mixed", "Admissions and marketing activities are led by Dr. A. B. Example, the Senior Director of "
                  "Admissions and Marketing."),
        ("h3", "17. Who is the Dean of Planning?"),
        ("bold", "The Dean of Planning is Dr. C. Example, who leads institutional planning."),
        ("title", "Admissions"),
        ("bold", "How do I apply?"),
        ("plain", "Follow these steps:"),
        ("plain", "1. Fill out the online application form."),
        ("plain", "2. Upload your documents."),
        ("plain", "https://sru.edu.in/admissions"),
        ("bold", "4. Does the university offer hostel?"),
        ("plain", "Yes, separate hostels for boys and girls are available on campus."),
    ])
    report = {}
    got = {e.question: e for e in parse_university_docx(path, report)}
    q16 = got["Who is the Senior Director of Admissions and Marketing?"]            # number stripped
    assert q16.section == "Leadership" and "Senior Director of Admissions and Marketing" in q16.answer
    assert "Dr. C. Example" in got["Who is the Dean of Planning?"].answer           # bold answer kept
    steps = got["How do I apply?"].answer
    assert "1. Fill out the online application form." in steps and "2. Upload your documents." in steps
    assert got["Does the university offer hostel?"].page_url == "https://sru.edu.in/admissions"
    assert report["unanswered"] == [] and report["orphans"] == []


def test_question_and_answer_in_one_paragraph_and_unanswered_questions(tmp_path):
    path = _build(tmp_path, [
        ("title", "Leadership"),
        ("h3", "Who is the Dean of PG Studies?\nThe Dean of PG Studies is Dr. D. Example, who oversees PG programs."),
        ("h3", "Who is the Dean of Research?"),
        ("h3", "Who is the Dean of Mentoring?"),
        ("plain", "The Dean of Mentoring is Dr. E. Example, who leads mentoring programmes."),
        ("title", "Library"),
        ("plain", "Is the library open today?"),
        ("bold", "Hostel Fees"),
        ("plain", "Sample text that belongs to no question."),
    ])
    report = {}
    got = {e.question: e.answer for e in parse_university_docx(path, report)}
    assert got["Who is the Dean of PG Studies?"].startswith("The Dean of PG Studies is Dr. D. Example")
    assert "Who is the Dean of Research?" not in got                       # no answer: skipped, and reported
    assert ("Leadership", "Who is the Dean of Research?") in report["unanswered"]
    assert ("Library", "Is the library open today?") in report["unanswered"]
    assert ("Library", "Sample text that belongs to no question.") in report["orphans"]


def test_answer_made_only_of_questions_is_not_knowledge(tmp_path):
    path = _build(tmp_path, [
        ("title", "Programs"),
        ("bold", "M.Tech, M.Sc and Agriculture?"),
        ("plain", "Which M.Tech specializations are available?"),
        ("plain", "Is GATE required?"),
        ("plain", "Ph.D."),
    ])
    report = {}
    assert parse_university_docx(path, report) == []
    assert ("Programs", "M.Tech, M.Sc and Agriculture?") in report["unanswered"]


@pytest.mark.skipif(not DOCX.exists(), reason="university document not present")
def test_real_document_recovers_the_heading_questions():
    entries = parse_university_docx(DOCX)
    assert len(entries) >= 190
    by_q = {e.question: e for e in entries}
    lead = by_q["Who is the Senior Director of Admissions and Marketing?"]
    assert lead.section == "Leadership"
    assert "Dr. Ram Raghotham Rao Deshmukh, the Senior Director of Admissions and Marketing" in lead.answer
    assert sum(1 for e in entries if e.section == "Campus Security") >= 40
    assert not any(e.question[:1].isdigit() and ". " in e.question[:5] for e in entries)   # no list numbers
