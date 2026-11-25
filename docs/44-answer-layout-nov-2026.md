# 44. One answer layout for every chat answer (v4.17.0, 25 Nov 2026)

## Problem (seen in live Gemini answers)

Answers had a different shape on every turn:
* dense paragraphs;
* bold lines used as headings;
* no tables for comparisons;
* steps sometimes written as bullets.

Three causes:

1. **The chat agent's prompt** (`backend/app/sru_agent/prompt.py`) asked for "1–2 short paragraphs for
   explanations", "15–40 words" and "no [!NOTE] boxes".
2. **A per-turn "variant" engine** changed the layout at random.
3. **`system.md` §9** asked for headings and tables at the same time.

## The layout (`backend/prompts/answer_layout.md`, versioned)

One file, included at the end of the chat agent prompt and in `system.md` (`{{ANSWER_LAYOUT}}`). `rag.md` carries
the same rules in short.

| Content | Shape |
|---|---|
| Every answer | **Lead**: one sentence (≤ 30 words) answering the question; only its key figure bold |
| 3+ facts | 3–5 bullets `- **Label:** detail` (≤ 15 words) |
| A comparison (X vs Y, colleges, rooms, scholarship slabs) | A Markdown table, 2–3 columns, ≤ 6 rows, short cells |
| A process (apply, documents, next steps) | Numbered steps `1. **Step:** detail` |
| Two topics | `### Title` + 2–4 bullets each |
| A condition the student must act on | One `> [!NOTE]` (rare) |
| Close | At most one short question, on its own line |

Other rules:
* 50–130 words (≤ 170 with a table or steps).
* No emoji in headings, bullets or tables.
* Figures only from verified facts, the FEE POLICY block or tools.
* With a fee card, the text gives only the headline; the card has the semester table.

`VARIANT_ID` now changes only the tone, not the layout. The agent prompt is 9,961 characters; the size cap in the
tests was raised from 9,000 to 10,000.

## Rendering (`frontend/src/components/MarkdownContent.tsx` / `.css`)

* **Lead and follow-up:**
  * the first paragraph is the lead (slightly stronger);
  * a closing question is set apart by a hairline.
* **Bullets and steps:**
  * bullets have brand-coloured dot markers;
  * consecutive `1.` lines are one `<ol>` with numbered badges on a thin rail;
  * blank lines inside a list no longer split it.
* **Spacing:** one block gap; text measure capped at 68 characters on wide screens (ui-ux-pro-max: line length
  65–75, line-height 1.5–1.75).
* **Tables:**
  * a white card with brand-tinted uppercase headers; the first column names the row; numbers are tabular;
  * tables with 3+ columns are **stacked** (one block per row, each cell labelled with its column) on phones
    (≤ 480px) and always in the widget, so nothing is cut off or scrolls sideways.
* **Notes:** a quieter style labelled "Note". A `> [!NOTE]` whose text the model put on the next line is joined to
  it, so there is no empty box.
* **Bold titles:** a line that is bold from end to end (`**Hostel Facilities**`) renders as a section title.
* **Links:**
  * a link inside bold text renders as a link;
  * only `https://`, `http://`, `mailto:` and `tel:` links are clickable.
* **Widget colours:** `official-widget.css` and `ChatPage.css` force body colours with `!important`. They now let
  table headers, step numbers, note titles and the follow-up line keep their accent colours.

## Related fixes found while checking live answers

* **Comparison card:** when the answer already contains a comparison table, the generic "comparison" card is not
  added under it (`agent._HAS_MD_TABLE`).
* **Invented scores:** Gemini passed a percentage the student never gave to `compare_programs`. The table showed
  ₹2,80,000 / ₹11,44,000 (scholarship figures) instead of the standard ₹3,65,000 / ₹14,84,000.
  * `tools._student_scores` now uses a score only when it is on the student's saved details or appears in the
    student's own messages.
  * This applies to `calculate_fee`, `compare_programs` and `check_eligibility`.
  * An assumed score is never saved.
* **Stream questions:** `check_eligibility` without marks now returns the programme's required subjects and minimum.
  "I'm from BiPC, can I join CSE?" is answered (MPC required) instead of "what is your percentage?".

## Tests

* **`backend/tests/test_v417_answer_layout.py`:**
  * one spec file in both prompts, every content rule present, no fee figures;
  * no duplicate comparison card;
  * invented scores ignored and not saved; typed and saved scores used.
* **Updated prompt tests** assert the new layout instead of the old word ranges.
* **Live check:** 12 typical questions with live Gemini at 390px and laptop width; screenshots compared before and
  after.
* **Gemini compliance:** Gemini follows the layout in most but not all answers. In the runs, one answer started
  with steps without a lead, and one comparison was given as bullets. The layout is an instruction, not enforced
  by code.
