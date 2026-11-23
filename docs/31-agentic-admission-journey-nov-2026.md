# 31. One admission journey: fees, unfinished messages, shared academic details and the form (v4.6.0)

Base: v4.5.0 (`main`). Starting point: a tested conversation where "I want to..." produced a hostel information dump,
"Fee details" produced every programme's fees plus an all-branch B.Tech table, and asking about the scholarship after
a completed eligibility check restarted with separate board, year, route and rank cards.

## 1. Root causes

| # | Symptom | Root cause (where) |
|---|---|---|
| 1 | "Fee details" -> all fees, specialisation fee, core branches | No rule for a fee question without a programme (it went to the AI), and `card_service.generate_cards` attached the all-branch B.Tech table to ANY message with "fee" + "details / structure / tuition", and to every "B.Tech fee" |
| 2 | "I want to..." -> hostel dump | Unfinished messages were not recognised, and any message that did not answer the pending question dropped it, so the hostel context was lost before the AI was called |
| 3 | Scholarship after eligibility restarted the questions | The scholarship flow asked board -> year -> marks -> route -> rank as separate cards; it reused only what happened to be on the profile, never showed one form, and made the entrance route a mandatory step |
| 4 | Details carried into a new chat | Academic details lived on the cross-conversation profile, so a new conversation silently inherited old marks |
| 5 | Form fields could not be submitted together | Cards could only send a chat text, so a multi-field form had no structured path to the agent |
| 6 | Course-pushing / unsupported wording | "Great choice!", branch guidance saying "strong academic foundation" for ANY marks (even 230) and "high campus recruitment" (no source) |
| 7 | Future-year fees | The reply stated "₹9,000 per year" as a universal rule (it is CSE's increase) and "scholarship kept with 7.5 CGPA and no backlogs" (the 7.5 CGPA is the placement rule; scholarship continuation is not in any official source) |
| 8 | Phone layout | Fee tables used four squeezed columns in the 400 px chat |

## 2. What changed

**Shared journey state** (`backend/app/sru_agent/journey.py`): academic details (board, status, marks, total,
confirmation, 10+2 group, entrance score) belong to one conversation. Every flow reads them from the same place, so
eligibility, scholarship and fee answers reuse them. A new conversation starts clean; the previous details are kept as
`saved_academic` and offered as "Use my saved details (...)". Switching back to an earlier chat restores its details.
Stored in the existing key-value profile rows (no schema change).

**Consolidated form** (`card_service.build_academic_details_form`, `AcademicDetailsFormCard` in `Cards.tsx`):
board -> current status -> marks (total filled from the board and status) -> 10+2 group (when the programme names
one) -> optional entrance score. Pre-filled with what is known; one submit button; live review line; after submit
it collapses to a one-line summary with "Edit details". Submitted as typed data (`form` on `/api/v1/agent/stream`,
Pydantic `AcademicForm`), validated again by the agent; a form with problems comes back with what was entered and
nothing is saved.

**Scholarship flow** (`fee_intake.py`): programme first; then 2+ of board / status / marks missing -> the form;
exactly one missing -> only that field; typed answers after the form continue field by field (no second form);
nothing missing -> the estimate at once. Entrance score is optional ("Add my EAPCET rank" / "Add my JEE Main
percentile" afterwards recalculates with everything else reused). Inside a journey, "What scholarships are
available?" / "I want to know about the scholarship" estimate for the chosen programme.

**Conversation manager** (`dialogue.py`): fee questions without a programme ask programme -> branch; unfinished
messages ask what the student means using the current topic (and keep the pending question); "I got my results"
asks how they did; a goal stated with the programme ("Check my eligibility for B.Tech CSE") is acted on; a programme
change midway keeps the marks; eligibility uses the form when marks and group are both missing.

**Agent** (`agent.py`): form handling and "Use my saved details"; the student's first name is passed to the flows
only when it reads naturally (not when one of the last two replies used it); the welcome no longer swallows a first
question; the all-branch fee table is attached only when the student asks to compare all branches.

**Wording**: neutral branch guidance (marks acknowledged, never judged); "Great choice" replaced; AI prompt rules
for fees, unfinished messages and neutral guidance; future-year reply rewritten from the sources (programme-specific
2027-28 figure when a programme is named); eligibility verdict shortened.

**UI**: the form; fee tables stack per row when the card is narrow (container query, works in the 400 px desktop
panel too); the required disclaimer stays under the input.

## 3. Tests

| Check | Result |
|---|---|
| New `tests/test_agentic_admission_journey.py` (29 tests: the 25 scenarios of the brief plus name use, results received, neutral wording), production code path | All pass |
| Full backend suite | 823 passed, 9 failed, 8 skipped. The 9 fail identically on v4.5.0 (no PostgreSQL / Redis / API key here, and older follow-up-chip tests) |
| Frontend: type check, build, lint (no new warnings), fee calculator 3,477 checks, effects | Pass |
| Real UI journey (Playwright, phone 390 px) against the real agent router with only the AI client replaced | Join -> B.Tech -> CSE -> eligibility form -> verdict -> scholarship estimate without re-asking; hostel -> "I want to" -> context kept; no page errors, no horizontal scroll |

Tests that described the old behaviour (board-first scholarship cards, school card for fee questions, all-branch
table for generic fee wording, "₹9,000 per year" for every programme) were rewritten for the new rules.

## 4. Limitations

- Live Gemini answers were not run (no API key here). AI-written answers are covered by what they receive (verified
  data, CURRENT FOCUS, prompt rules), not by a live run.
- Older chats keep their old cards; the old single-step cards are still used when exactly one field is missing.
- `saved_academic` is offered only for the most recent other conversation.
- Still for the Admissions Office (unchanged): 2027-28 minimum marks, whether B.Tech needs an entrance score,
  documents list, dates, and scholarship continuation rules.
