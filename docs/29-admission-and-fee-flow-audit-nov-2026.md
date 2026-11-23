# 29. Audit: admission and fee flows (23 Nov 2026, base v4.3.0)

Base: commit `ed85e79`. This is an audit only: **no code was changed**. It lists every admission and fee
flow in the project, shows how they overlap, and proposes one universal flow plus a migration plan.

How it was checked: by reading the code, and by running real student journeys through `run_agent` twice.
The first run used a production-like client (any use of the AI is recorded). The second used no client
(offline mode). The script is described in section 7. The existing fee and admission tests (116) all pass,
yet they do not catch the problems in section 3, because they run with mock clients, which take
different code paths from production.

## 1. Summary

A student who wants to know "what will I pay, and can I get in?" can land in **twelve different flows**.
Which one they get depends on the exact words they use, on whether the AI client is up, and on which
button they press. The flows ask different questions in a different order, show different cards and
end in different places.

| What the student does | What happens today (production) |
|---|---|
| "Calculate my scholarship" (welcome chip) | 6-step wizard: board → year of study → marks → entrance route → rank → programme (programme is asked **last**) |
| "CSE fee" | Fee worked out first, then the AI writes the answer, then one combined question |
| "What is the fee?" | Straight to the AI, no card |
| "Show me the fee structure" | Straight to the AI. Offline mode shows a school tree instead |
| "I want to join SRU" | School card. Tapping a school then goes to the AI with no card (**dead end**) |
| "I can't afford the fee" | Separate 2-step flow: marks, then special-category concession |
| "How do I apply for 2027-28?" (welcome chip) | Straight to the AI, no fixed answer or card |
| Header "Fee Calculator" button | Separate pop-up form in the browser with its own lead capture |
| Agent stream fails | The old chat endpoint runs a 4-step "Admission Wizard" with **wrong scholarship figures** |

## 2. Inventory of flows

### 2a. Agent (`/api/v1/agent/stream`, used by the website and the widget)

| # | Flow | Code | Started by | Questions, in order | Ends with |
|---|---|---|---|---|---|
| F1 | Scholarship "counsellor" wizard | `fee_intake.decide` (counsellor mode, `fee_intake.py:664-919`) | Any scholarship / waiver / "calculate my fee" wording that is not a general question | board → year of study → marks → entrance route → rank (skippable) → programme | `calculate_fee` card + counsellor assessment text |
| F2 | Standard fee intake | `fee_intake.decide` (form mode, `fee_intake.py:921+`) | Fee question with a programme ("CSE fee"), a bare score | Only what is missing, in one message | `fee_scholarship_form` card, then `calculate_fee` |
| F3 | School → course browse tree | `fee_flow.process_fee_flow` | Only when already in the tree, "explore / browse programs", **or a mock client** | school → programme → specialisation | `fee_structure_detailed` + `fee_scholarship_form` cards |
| F4 | Fixed fee pages per programme | `agent.py:2060-2186` (`FEE_TREE`, `BTECH_TREE`, `BTECH_CSE_FEE` … `DESIGN_FEE`) | Matching intent, **offline or mock client only** | none | Fixed text + fee card |
| F5 | Affordability / concessions | `affordability.process_affordability_flow` | "can't afford", "fees too high" | marks (+ programme), then concession category | Text; silently assumes State Board and B.Tech CSE when not told |
| F6 | Plain fee worked out before the AI | `agent.py:655+` | Fee question the code can work out by itself | none | AI-written text + `calculate_fee` card |
| F7 | AI with tools | `agent.py:2686+` | Everything else ("What is the fee?", "How do I apply?", "fee structure") | Whatever the AI decides | Free text; card only if the AI calls a tool |
| F8 | "Join SRU" | `agent.py:1890` (`JOIN_SRU_QUERY`) | "I want to join", "how to join" | school card | Tap goes to F7 (no state is saved, see P3) |

### 2b. Old chat endpoint (`/api/v1/chat/stream`, used when the agent stream fails before the first word)

| # | Flow | Code | Notes |
|---|---|---|---|
| F9 | "Admission Wizard" (4 steps: degree → branch → % → verdict) | `services/flow_service.py`, `chat_service.py:363, 798` | Hard-coded text, not from the fee card (see P2) |
| F10 | Finance estimate | `services/finance_service.py` | Reads `app/data/finance_rules.json`, which is **empty** (`fee_rules: []`), so it can never give a fee |

### 2c. Frontend

| # | Flow | Code | Notes |
|---|---|---|---|
| F11 | Fee & Scholarship Calculator pop-up | `ScholarshipCalculatorModal.tsx`, opened from the header button, the widget button, or typing "open calculator" | Programme → exam/board → score → hostel; its own name + number form (lead source `scholarship_calculator`) |
| F12 | In-chat fee form | `FeeScholarshipFormCard` in `Cards.tsx` | A third way to enter the same details; keeps its own fallback list of programmes and tuition |

Name and number are collected in up to five places: the pre-chat form (`ChatLeadForm`), the Register
pop-up (`LeadAuthModal`), the agent's contact check (`require_contact_details`), the calculator pop-up
and callback requests. Most of them are pre-filled from saved details, so this is a smaller problem.

## 3. Problems, most serious first

**P1. PG scholarships use 12th marks (wrong answer).** "Calculate my scholarship for MBA" enters F1,
which asks for the Intermediate board, year of study, Intermediate marks and an EAPCET / JEE route. It
then calculates the MBA scholarship from the 12th marks. PG slabs use the degree percentage. By contrast,
"MBA fee" (F2) correctly asks only for the degree percentage. Measured:

```
Calculate my scholarship for MBA -> counsellor_board_selection
CBSE                             -> counsellor_stage_selection   ("Which year are you currently studying in?")
Completed Intermediate           -> counsellor_marks_input
75%                              -> counsellor_route_selection   (TG EAPCET / AP EAPCET / JEE Main ...)
Not decided yet                  -> calculate_fee
```

**P2. The old Admission Wizard states wrong figures.** `flow_service.py:216-252` says "with your score
you qualify for up to a **40% merit tuition waiver**" for any score of 90% or more. On the 2027-28 fee
card, 90% gives **25%** (State Board) or **30%** (CBSE), and 40% needs 98% (State) / 95% (CBSE). It also
says "50% minimum cutoff in 10+2 MPC" for every branch (the fee card says 55% for CSE / ECE, and
the website says 60%: see `fees_2027_28.json` → `needs_confirmation`). It also mentions "Vocational &
Certificate Tracks", which no verified source supports. This flow only runs when the agent stream fails,
which is when students are most likely to be confused already. It breaks AGENTS.md rule 5.

**P3. "I want to join SRU" is a dead end.** `JOIN_SRU_QUERY` shows the school card but does not set
`fee_flow_state`. In production, F3 only runs when that state is set, so tapping a school goes to the AI
with no card or next step.

**P4. The same question gets a different flow depending on the words.** See the table in section 1.
"Calculate my scholarship", "CSE fee", "What is the fee?" and "I can't afford it" are one need, but they
start four different flows with four question orders.

**P5. The question order disagrees between flows.**
- F1 asks **board first and programme last**. Its last step is titled "Which B.Tech programme…" and
  shows 7 programmes, while the fee card has 26 (B.Des, BCA, MCA, B.Com, M.Tech, M.Sc and the
  B.Sc courses are missing).
- In F1, the same programme card is labelled "Step 1" in one place and "Step 5" in another.
- F2, F3, F11 and the old wizard ask programme first. F5 asks marks first, then concession.

**P6. Production and tests take different paths.** F3 and F4 run only when the client is `None` or has
a mock class name (`_is_mock_or_test_client`, `agent.py:1563`). So the browse tree and the fixed fee
pages are tested but almost never reach a real student, and the paths students do reach (F1 for PG,
F8 → F7) are not covered.

**P7. Duplicated logic and data.**
- The fee-intake block in `agent.py` appears twice, nearly line for line (steps "1" and "3",
  `agent.py:2600-2683`).
- `agent.py` imports 38 templates from `responses.py` and then defines them again. 7 copies have
  drifted (`_BTECH_CSE_FEE_TEXT`, hostel texts, canteen, labs, placements). The `agent.py` copy wins.
- Tuition is written out by hand in `fee_flow.SCHOOLS_DATA`, `card_service` (programme card) and
  `Cards.tsx` (form fallback), as well as the fee card file. They all match today, but every fee
  change must be made in four places.
- There are three fee engines: `fees.py` (correct), `finance_service.py` (empty rules) and the browser
  calculator (reads the exported `feeConfig.json`).

**P8. Formatting.** The marks acknowledgement wraps an already bold score in bold again, so students
see `****92.0%****` (F1, after the marks step).

**P9. "How do I apply?" has no fixed answer.** It is a welcome chip and a follow-up chip after almost
every fee answer, but it always goes to the AI. A link and three verified steps would do.

## 4. Proposed universal flow: one Admission Journey

One engine, one state key and one set of cards. Every entry point (fee, scholarship, eligibility, join,
afford, calculator, apply) starts the same journey. The journey reads whatever the student has already
said or saved, and asks only what is still missing.

```
 Any entry ─▶ 1. PROGRAMME ─▶ 2. QUALIFYING SCORE ─▶ 3. ENTRANCE ─▶ 4. RESULT ─▶ 5. NEXT STEP
 (fee, scholarship,  skip if     UG: board (only if it    only B.Tech /   eligibility,     Apply online
  join, afford,      known       changes the slab) +      B.Sc Agri, and  tuition,         Add hostel
  calculator,                    marks, final or          only if it can  scholarship +    Special concessions
  apply, eligibility)            expected                 beat the marks  basis, sem-1     Talk to a counsellor
                                 PG: degree %             slab; skippable payable, next    Compare a programme
                                 IB: points                               slab
```

Rules:
1. **One state key**, `admission_journey = {step, programme, level, board, marks, marks_basis, entrance, result}`.
   It replaces `fee_intake`, `fee_flow_state`, `affordability_flow`, `admission_stage` and `fee_tree_step`.
2. **The programme decides the questions.** The level (UG / PG / IB) chooses step 2, and the programme
   chooses whether step 3 is asked at all. This fixes P1 by design.
3. **The year of study is not a separate step.** It becomes a toggle on the marks card ("final" /
   "expected (1st-year marks)").
4. **One collector.** `fee_intake.decide` already does most of this (asks each thing once, skips what
   is known, asks the board only when it changes the answer). It becomes the only collector. F1, F3, F5
   and F8 become entry points into it.
5. **One calculator.** Every result comes from `fees.calculate_fee`, in chat and in the pop-up
   (the pop-up already calls `/api/v1/agent/calculate`).
6. **One result card and the same next-step chips everywhere.** "I can't afford it" lands on the same
   result card with the special-concession step opened, instead of a separate flow.
7. **The same in every mode.** The `client is None` / mock-only branches are removed, so tests exercise
   what students see.
8. **The old endpoint does not run its own wizard.** On agent failure it answers fees from `fees.py`
   or points to the calculator, never with hard-coded figures.

What happens to each flow today:

| Today | In the universal flow |
|---|---|
| F1 counsellor wizard | Journey, with programme first and level-aware questions |
| F2 standard intake | Journey (it is already most of it) |
| F3 browse tree, F4 fixed fee pages | Step 1 card ("pick a programme"), then the journey |
| F5 affordability | Journey result + concession step |
| F6 / F7 plain fee via AI | Journey when details are missing; the AI only writes the wording around fee-card figures |
| F8 join | Journey, step 1 |
| F9 old wizard, F10 finance estimate | Removed; the old endpoint uses `fees.py` |
| F11 calculator pop-up | Same steps and cards as the journey; result can be sent into the chat |
| F12 in-chat form | Kept only as the "fill everything at once" view of the same journey |
| "How do I apply?" | Step 5: fixed answer with the apply link (`APPLY_URL`), plus the journey if no programme is known |

## 5. Migration plan (small, reviewable PRs)

| PR | Change | Risk |
|---|---|---|
| 1 | **Bug fixes only:** PG guard in F1 (P1); save state on "join" (P3); old wizard uses `fees.scholarship_for` and drops unverified claims (P2); double bold (P8). Journey tests with a production-like client. | Low |
| 2 | Single collector: route F1, F3, F5 and F8 into `fee_intake.decide`; one state key; remove the duplicated intake block (P4, P5, P7). | Medium |
| 3 | Frontend: one card set; calculator pop-up uses the same steps; remove the hand-written programme / tuition lists and read `/agent/fee-config` instead. | Medium |
| 4 | Old endpoint: remove the Admission Wizard and the empty finance engine, and answer from `fees.py`. | Low |
| 5 | Clean-up: remove the offline / mock-only branches and the duplicate templates in `agent.py`. | Low |

Each PR keeps the existing tests passing. Tests that describe the old behaviour are rewritten for the
new behaviour, not deleted (as in round 27). `docs/06-conversation-design.md` and
`docs/12-api-specification.md` are updated in PR 2 and PR 3.

## 6. Decisions needed

1. **Programme first or board first?** Commit `dc3dfb0` (today) deliberately made the scholarship flow
   ask the board first. The universal flow proposes **programme first**, because the programme decides
   which questions make sense (no Intermediate board or EAPCET for MBA). A middle way: board first
   only once the student is known to be UG.
2. **Is the in-chat form (F12) kept** as a "fill everything at once" option, or replaced by the step cards?
3. **Should the calculator pop-up remain a separate entry point** (header button), or open the chat journey?
4. Still open with the Admissions Office (from round 27): the 2027-28 minimum marks (50 / 55 / 60%),
   the documents list, and the early-bird offer.

## 7. How the journeys were run

A script ran each journey as one multi-turn session through `run_agent`. In "production-like" mode
it used a client object that records any AI call. In offline mode it used no client.
Journeys: "What is the fee?", "CSE fee", "Calculate my scholarship", "I want to join SRU", "Show me the
fee structure", "I can't afford the fee", "How do I apply for 2027-28?", "start the admission wizard",
"Calculate my scholarship for MBA" and "MBA fee". Results are summarised in sections 1 and 3.

Existing tests: `test_course_fee_flow`, `test_fee_form_flow`, `test_fee_scoping`, `test_fee_single_source`,
`test_fees`, `test_scholarship_counselling_workflow`, `test_scholarship_eligibility_and_variants`,
`test_affordability_and_level_filtering`, `test_admissions_accuracy`: **116 passed**.

## 8. Fixes applied (v4.3.1, 23 Nov 2026)

From a live conversation review. The board-first order of the scholarship flow (commit `dc3dfb0`) is kept.

| Problem seen | Fix |
|---|---|
| "Which admission route… for B.Tech?" asked before the programme; programme asked last as "Which B.Tech programme" while MBA / BBA were offered | Scholarship flow is now board → year of study → marks → **programme** → route → rank. The route and rank are asked only for B.Tech and B.Sc Agriculture (the only programmes with EAPCET / JEE slabs); other UG programmes go straight to the result. Card labels are Step 4 (programme) and Step 5 (route) |
| PG scholarship worked out from 12th marks (P1) | A PG programme asks one question, the qualifying-degree %, with no board, year or entrance questions. Below 50% gets the ineligible reply worded for the degree. Choosing a PG programme after giving 12th marks also asks for the degree % |
| Marks compliment repeated, plus "Thanks! I already have your academic details" on a normal last step | The compliment is shown once, on the step right after the marks. "Thanks! I already have…" only appears when the assessment was already complete, or everything was known from the start |
| `****92.0%****`, `850/1000.0`, `₹170,000 per semester`, `45.0%` | Scores show as typed (`850/1000 (85%)`, `92%`); semester amounts use the Indian format (`₹1,70,000`) |
| 90%+ compliments promised the "highest tuition fee waiver" / "maximum merit scholarship" (90% State Board is 25%) | Wording no longer claims the top slab |
| Hostel table labelled "Merit Scholarship Alert" | The label is "Note" unless the note is about scholarships |
| Confetti on hostel and other answers, every time | The browser no longer reads reply text. Only the server's `eligible` flag counts, which is set only for an assessment that used the student's own score (not "CSE fee" or hostel answers). It plays once per chat session (`claimEligibilityCelebration`) |
| "Fee & Scholarship Info" / "Why Choose SRU?" chips in the middle of every question step, with only 2 of the step's answers | While a question is being asked, the chips are the answers to that question only (up to 4) |
| Four plain chips under the opening welcome | Replaced by four quick-action tiles, each with a verified incentive badge: Calculate My Scholarship (up to 40% off), Explore Programmes (NIRF #91), Placements & Careers (₹51 LPA), How to Apply (2027-28). The welcome text is unchanged |
| The same four options shown again after "hi" | The personal greeting ("Welcome to SR University, **Mahesh**!", name capitalised) no longer repeats the tiles; its chips are other topics (CSE fees, hostel, placements, campus visit) |

Not changed: "Would you like to schedule a campus visit…" after the hostel answer was written by the AI. The prompt
already forbids booking language, so this is a model slip, not fixed text.
