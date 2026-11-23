# 30. Conversation logic audit and correction (23 Nov 2026, v4.4.0)

Base: v4.3.1. Scope: admission eligibility, broad versus specific questions, incomplete messages, context across
turns, programme relevance, and the university data behind them. Everything below was implemented and tested.

## 1. Root causes found

| # | Problem seen | Root cause (where) |
|---|---|---|
| 1 | "230 marks (~23.0%) ... you meet the official 50% minimum" | `fee_intake.py`: when raw marks gave no scholarship, the reply claimed eligibility **without comparing the percentage at all**; it also assumed the total was 1000 |
| 2 | Same score, different eligibility answers | Thresholds written in 9 places: `responses.py` (B.Tech **60%**), `prompts/system.md` (line 126: 60%; line 192: "strictly 50%, NOT 60%"), `prompts/rag.md` ("50% or above: answer YES, fully eligible"), `verified_facts.json`, handbook page 09, `fee_intake` (hardcoded 50), `flow_service.py` (hardcoded 50, "40% at 90%+"), `agent.format_counsellor_assessment` (hardcoded 50), `auto_seed.py` |
| 3 | Disputed minimums stated as fact | The data file records that the 2027-28 fee card (50%; CSE/ECE fees from 55%) and the 2026-27 programme pages (60% PCM for B.Tech, 55-60% for others) disagree, but the prompts hid this |
| 4 | Scholarship confused with admission | Marks compliments said "you are eligible for admission" before the programme was known; the AI answered "Am I eligible?" with a scholarship waiver |
| 5 | `check_eligibility` with no marks said "not eligible" | `tools.py` defaulted the percentage to 0 |
| 6 | Rounding could pass a failing score | Parsed percentages were rounded to 2 decimals before comparison (499.99/1000 -> 50.0) |
| 7 | B.Tech eligibility without the subject check | The fee card requires MPC, but no flow asked for it |
| 8 | Information dumps for broad questions | "Tell me about the hostel" / "B.Tech" returned long fixed texts; "CSE", "placements", "admissions", "transport"... went straight to the AI with no clarification |
| 9 | "I want to join" led nowhere useful | It showed a school card whose taps were not continued in production; "I'm interested" and "I want to join B.Tech CSE" went to the AI |
| 10 | Short follow-ups lost context | "Placements" / "fees" after choosing a programme were not tied to it; the AI was not told which programme was being discussed |
| 11 | The first question after sign-up was ignored | The one-time welcome greeting replied to any first message |
| 12 | Unverified claims | "Extra 10% scholarship for PG" (website-only offer), "10% to 50%" scholarships (fee card max 40%), Early Bird offer in the legacy prompt, "alternative diploma / lateral entry" for below-minimum students |
| 13 | Required disclaimer not shown | `MarkdownContent` strips "May contain inaccuracies..." from every message and it was shown nowhere else |

## 2. What was implemented

**One eligibility engine** (`backend/app/sru_agent/eligibility.py`), used by every flow: the journey, fee intake,
scholarship counselling, the AI's `check_eligibility` and `calculate_fee` tools, the old chat endpoint's wizard and
the eligibility overview.
- Source of truth: `fees_2027_28.json` (fee card minimum, fee-card fee band, programme-page minimum).
- Below the lowest documented minimum -> `below_minimum`; at or above the highest -> `meets_minimum`; in between ->
  `needs_confirmation` (both values shown, Admissions Office confirms; never called eligible or not eligible).
- Exact maths (marks / total x 100, unrounded), inclusive minimums, total asked when missing.
- 10+2 subjects (MPC for B.Tech, BiPC for B.Sc Agriculture) asked once before eligibility is confirmed.
- No alternative pathways are offered (none are documented).
- `calculate_fee` results now carry `admission_eligibility`; below the minimum the fee is not presented as payable.

**Conversation manager** (`backend/app/sru_agent/dialogue.py`), run before every other route, no AI call:
- Broad topics (hostel, placements, admissions, scholarships, transport, campus, faculty, labs, internships,
  research, student life, events, departments) -> one "which aspect?" question with chips -> the chosen aspect
  becomes a specific question.
- Broad programmes -> branch (if needed) -> aspect, answered for that programme only.
- Journey: programme -> branch -> goal (eligibility / process / fees) -> marks -> subjects -> verdict.
- Short follow-ups and "this branch" resolve to the programme being discussed; "what about hostel?" right after
  a fee answer means hostel fees; "skip" ends a pending question; anything else drops it and is answered as new.
- Specific questions, branch guidance, school-card taps and replies to an open fee intake are left to their routes.
- The programme is stored as `active_program` and given to the AI as a CURRENT FOCUS line.

**Data**: the eligibility overview is generated from the data file; the handbook fact page, `verified_facts.json`,
the seeded FAQ (the old one is retired on start-up) and the legacy prompts now state the conflict instead of one
value; the unverified PG / Early Bird / 50% claims were removed. The factuality benchmark flags any single
disputed value presented as the confirmed cutoff.

**Frontend**: the required disclaimer is shown once under the input; the calculator's below-minimum note says
clearly that the student does not meet the minimum.

## 3. Tests

| Check | Result |
|---|---|
| New suite `tests/test_conversation_logic_audit.py` (production code path, 63 tests: every case in the brief, boundaries, spelling, interruptions, topic changes, follow-ups) | All pass |
| Full backend suite | 793 passed, 9 failed, 8 skipped. The 9 also fail on v4.3.1 (no PostgreSQL / Redis / API key here, and older follow-up-chip tests). None of them is new |
| Frontend build, lint (no new warnings), fee calculator (3,477 checks), effects tests | Pass |

Tests that described the old behaviour (fixed 50% cutoff, assumed totals, "eligible" compliments, B.Tech dumps)
were rewritten for the new rules, not deleted.

Not tested here: the real Gemini model (no API key in this environment). AI-written answers are covered by the
data they receive (verified fee data, eligibility verdicts, CURRENT FOCUS) and by the prompt rules, not by a live run.

## 4. For the Admissions Office to confirm

1. The 2027-28 minimum marks: fee card 50% (CSE / ECE fees from 55%) versus programme pages 60% PCM for B.Tech,
   55% for B.Sc Agriculture / B.Des / MBA / M.Tech / M.Sc, 60% for BCA / MCA / B.Sc CS. Once confirmed, update
   `fees_2027_28.json` and the "needs confirmation" range disappears automatically.
2. Whether an entrance score (JEE Main / EAPCET) is required for B.Tech in 2027-28 (the programme pages say so).
3. Whether a percentage minimum applies to PCM subject marks or to the aggregate.
4. The documents list, important dates and refund policy (not in any official source; SRU Buddy says so).
5. The welcome line "Top Private University in Telangana & AP" has no official source by itself (see doc 27); it
   was kept as instructed.
