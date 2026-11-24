# Implementation Changelog: Restoring Chatbot Quality on Main

**Branch:** `fix/restore-rollback-chat-quality`  
**Base Commit:** `948c1a74890d576a8ea72c8e30d21c002be20188`  
**Date:** November 11, 2026  

---

## 1. Overview of Changes

All modifications were implemented with minimal, surgical precision directly on top of `948c1a7` without discarding any newer features, schemas, or UI upgrades.

---

## 2. File-by-File Changelog

### `prompts/system.md`
- **Location:** Section 6 (Admission Guidance Flow & Student Skepticism).
- **Changes:**
  - Decoupled incoming prospective student lead inquiries ("I came through an ad", "Saw your post") from adversarial student skepticism handling.
  - Instructed the model to welcome ad visitors warmly and naturally ask for their program of interest and 12th/Intermediate percentage.
  - Softened anti-enthusiasm negative constraints while preserving strict factual accuracy against 2026-27 university regulations.
- **Why:** Restores the natural conversational lead qualification demonstrated in `rollback_resp.pdf`.

### `prompts/rag.md`
- **Location:** Rules & Directives section (lines 24–45).
- **Changes:**
  - Created a dedicated section for "Prospective Student & Ad Inquiries" instructing warm, direct welcome messaging.
  - Streamlined skepticism handling so the bot shares objective highlights without robotic or formulaic answers.
  - Re-emphasized celebrating qualifying student scores warmly.
- **Why:** Eliminates cognitive conflicts in LLM instructions and restores engaging senior-guide conversation.

### `backend/app/services/suggestion_service.py`
- **Location:** `CAMPUS_SUGGESTIONS`, `SRIX_SUGGESTIONS`, and lines 235–270.
- **Changes:**
  - Added dedicated exploratory suggestion sets: `CAMPUS_SUGGESTIONS` and `SRIX_SUGGESTIONS`.
  - Fixed false-positive bug where any response mentioning `"campus"` defaulted to `CAMPUS_VIDEO_OFFER_SUGGESTIONS` (`["🎥 Yes, watch video", "❌ No, thanks"]`).
  - Ensured binary video chips appear strictly when a video tour is actively offered in the assistant's answer.
- **Why:** Prevents trapping users in unintended binary Yes/No loops on non-video turns.

### `backend/app/services/card_service.py`
- **Location:** `generate_cards` function (lines 325–375).
- **Changes:**
  - Re-enabled strict single-category scoped fee cards (`TRANSPORT_FEE_CARD`, `HOSTEL_FEE_CARD`, `EXAM_FEE_CARD`, `ADMISSION_FEE_CARD`, `MERIT_SCHOLARSHIP_CARD`, `BTECH_CSE_FEE_CARD`, `BTECH_ACADEMIC_FEE_CARD`).
  - Preserved strict category isolation (never cross-contaminates hostel or transport fees into tuition cards).
- **Why:** Fixed 9 failing tests in `test_fee_scoping.py` and `test_admissions_accuracy.py` and restored structured fee cards.

### `backend/app/services/intent_service.py`
- **Location:** `UNIVERSITY_KEYWORDS`, `COMMON_UNIVERSITY_PHRASES`, and `FAST_PATTERNS`.
- **Changes:**
  - Added `"tech"`, `"engineering"`, and `"eligible"` to `UNIVERSITY_KEYWORDS`.
  - Added regex pattern for `"want/plan to join/apply"` to `COMMON_UNIVERSITY_PHRASES`.
  - Expanded `HELP` regex pattern to support `"what can you help me with"`.
- **Why:** Enables fast-path (<1ms) routing for core admission inquiries without falling back to slow LLM classification.

### `backend/tests/test_engagement_features.py`
- **Location:** Line 56 (`test_cards_fee_breakdown`).
- **Changes:**
  - Restored verification of scoped fee card attachment for comprehensive fee inquiries.
- **Why:** Aligns test suite with restored scoped fee card architecture.

### `backend/tests/test_rollback_behavioral_regression.py`
- **Location:** New file under `backend/tests/`.
- **Changes:**
  - Added 9 automated tests verifying:
    1. Greeting classification and warm time-aware salutations.
    2. "How are you" enthusiastic senior-mentor persona.
    3. Multi-turn follow-up greetings ("Hey again!").
    4. Thank-you and capabilities/help responses.
    5. Suggestion chip isolation (no binary video chips when no video is offered).
    6. Exploratory campus suggestion chips.
    7. Admission & eligibility fast classification.
    8. Affirmative follow-up context retention.
    9. Negative follow-up routing.
- **Why:** Guarantees future commits cannot silently regress conversational behavior.

---

## 3. Preserved Features Verification

The following newer features on `main` remain **100% active and untouched**:
- ✅ `ScholarshipCalculatorModal.tsx` & CSS (streamlined marks input, fee roadmap).
- ✅ `LeadAuthModal.tsx` & CSS (lead authentication modal).
- ✅ `AdminPage.tsx` & `admin_service.py` (admin analytics, lead management, export).
- ✅ `Icons.tsx` (minimalist executive university vector icons).
- ✅ `ThinkingIndicator.tsx` (5-stage thinking animation).
- ✅ Redis client connection pooling and response caching.
- ✅ Dynamic IST greeting calculation.
- ✅ Staff contact number sanitization (scrubbing personal mobiles).
- ✅ Async SQLAlchemy database pooler configurations.


---

## v2.7.0 (17 Nov 2026): agent audit and fixes

Full details: `docs/24-agent-audit-nov-2026.md`.

- **Fees:** one source of truth (`backend/app/sru_agent/fees_2027_28.json`, rebuilt from the official
  circular). The calculator, the fee cards and the agent all read it. Yearly increase is flat.
- **Agent actions:** callback and campus-visit requests are saved as soon as name and number are
  known; "don't call me" really cancels (lead status `do_not_contact`); the agent can no longer say
  "saved" or "cancelled" unless a tool did it.
- **New tools:** `get_program_info`, `compare_programs`, `get_special_concessions`,
  `cancel_contact_request`, `share_fee_estimate`.
- **Load:** all Gemini keys are used with rotation and retry, at most 6 model calls at once, prompt
  56% smaller, fee questions answered from the fee file when the model is unreachable.
- **Calculator:** rewritten on the fee table; understands "EAPCET 9000" whatever is selected; no
  lead on every keystroke; official hostel prices; first-year total includes other and exam fees.
- **Security:** placeholder admin key refused outside debug; public leads endpoint rate limited.
- **Kept:** every existing feature and all 360 earlier tests still pass.


---

## v2.8.0 (17 Nov 2026): audit round 2

Full details: `docs/25-audit-round-2-nov-2026.md`.

- **Fee card PDF:** fee file re-checked against the official 2027-28 fee card (19 concessions,
  AC electricity deposit, programme names, rankings). The handbook's fee pages are now generated
  from the fee file; the wrong "verified" fee facts and invented concessions are gone.
- **Knowledge without AI calls:** keyword search over the handbook files (`sru_agent/knowledge.py`);
  the vector index refreshes when handbook files change; new page of facts checked on sru.edu.in.
- **Free Gemini tier:** greetings 0 calls, fee and handbook questions 1 call, repeated first
  questions from a saved copy, daily limits recognised, a useful answer when no key is available.
- **Chat consistency:** question always above its answer (also for old chats), cards and
  suggestions restored on reopening, stable message ids, context read back after a restart.
- **My details:** one profile per student (`/api/v1/agent/profile`), a settings panel, and
  "change my number" in the chat updates the profile and the saved request.
- **Scholarship by score:** each score's own scholarship is reported (EAPCET rank above 20,000).
- **Videos:** matched by topic from their own keywords, no AI call.
- **Cards:** "requested" instead of "confirmed", one set of visit hours, official helpline.

## v2.9.0 (17 Nov 2026): production readiness

Full details: `docs/26-production-readiness-nov-2026.md`. Gemini API unchanged.

- **Staff-only admin console:** button hidden; open with `/#admin`.
- **No unconfirmed offers:** Early Bird card off by default (`SHOW_EARLY_BIRD_OFFER`); chip now
  "How to Apply for 2027-28".
- **Header and phone menu:** one Share menu, SVG icons, no overlap at any width; calculator first
  in the phone menu.
- **Input:** new quick actions, voice typing (en-IN) where supported, real send button, one
  disclaimer with the Admissions Office number.
- **Thinking indicator:** real tool step, timer, "waking up the server" note after 10 seconds.
- **Details form optional:** "Skip and see the answer" sends the question and is remembered for the
  session.
- **Campus visit:** a date in the sentence goes straight to the booking.
- **Security:** CORS by list or pattern without credentials, no origin echo on errors, security
  headers on server and site, sensible caching on Vercel.
- **Chat titles** skip greetings.
- **Accessibility:** focus outlines, labels, tap targets ≥ 32 px (40 px on touch), text ≥ 11 px,
  zoom allowed, reduced motion.
- **Keep-awake GitHub Action** (needs the `BACKEND_URL` variable).
- Tests: 470 passed with PostgreSQL; 3,477 fee calculator checks.

## v3.0.0 (17 Nov 2026): admissions brief (fees, faculty, widget, visits, speed)

Full details: `docs/27-admissions-brief-nov-2026.md`. Gemini API unchanged; fee card unchanged.

- **Fee enquiries:** `sru_agent/fee_intake.py` asks for missing programme / branch, board, marks and
  JEE / EAPCET (only when they change the answer, each at most once, without an AI call), then
  calculates; answers point to sru.edu.in/fee-scholarship.
- **Follow-up chips:** `sru_agent/followups.py`, topic from the tool used and the question (not the
  answer); course-aware; never repeats the question.
- **Faculty:** 340 official profiles (`faculty_directory.json`), `find_faculty` tool, faculty card,
  refresh scripts `fetch_faculty_directory.py` and `build_faculty_directory.py`.
- **Strengths and formatting:** sourced "Why SRU" block, content-driven formatting, prompt 23% shorter;
  handbook page 12.
- **Widget:** `frontend/public/widget.js` + `?mode=widget` + `widget-demo.html`; messages tagged
  `channel` web / widget.
- **Campus visits:** never booked or confirmed; official contacts + optional callback request
  (`request_campus_visit_callback`); booking form, date confirmation and `book_campus_visit` removed.
- **Speed:** in-memory profile / context with background writes, parallel reads, no database trip
  to start a new chat, chat saved after the answer, Gemini streaming, MINIMAL thinking, shorter
  retries. Measured: first word for "hi" 2.9 s -> 0.9 s; 1-second AI answer complete 3.3 s -> 1.0 s.
- Tests: 511 passed with PostgreSQL; 3,477 fee calculator checks.

## v4.7.0 (23 Nov 2026): security audit and hardening

Full details: `security/` (assessment, threat model, implementation, test results, remaining risks).
No schema change; no new dependency; SRU-only scope, fee / eligibility engines and the accuracy disclaimer unchanged.

- **Admin:** placeholder key refused on any production server (APP_ENV / Render / debug off); `/docs` hidden there;
  admin key only in the `X-Admin-Key` header (never in URLs); brute-force limit on the trusted client IP; audit log.
- **Abuse limits:** per-network minute / day limits and a server daily budget for AI turns; 16-64 character session
  IDs; 413 for oversized bodies; feedback only on your own messages; CORS no longer open to every `*.vercel.app`.
- **AI:** knowledge passages with embedded instructions dropped; passages carry their source; prompt rule that
  documents are data (prompt `2026-11-23.1`); the model sees only the last 4 digits of the mobile; answers leaking
  prompt lines or secret-shaped strings replaced.
- **Frontend:** export-to-PDF XSS fixed; widget messages checked; stricter CSP.
- **Supply chain / infra:** npm audit clean, Dependabot, CI token scope, development services on localhost.
- Tests: 73 new backend security tests + 7 browser checks; full suite 896 passed (9 known environment failures).

## v4.8.0 (23 Nov 2026): conversation memory, welcome-back choice, chat cards

Full details: `docs/32-chat-memory-and-cards-nov-2026.md`. No fee / eligibility / placement logic or data changed.

- **Memory:**
  - A student who comes back after 30 minutes (the existing threshold, now on the server) gets an inline
    "Continue chat / Start a new chat" choice. Sooner, the conversation simply continues.
  - Continue restores the messages and that conversation's context.
  - Start a new chat keeps the old conversation (no more deleting the student's details) and starts clean.
- **Backend:**
  - The latest *active* conversation is offered; ids are never invented.
  - The old conversation's details are filed with it and restored when the student goes back to it.
  - Cards already shown are remembered per conversation.
- **Cards:**
  - One card system (`ChatCards.css`): tokens, shell, badges, headings, buttons, container queries.
  - Fixed: fee figures; a shorter, clearer placement card; hostel, curriculum, videos and form cards; icon
    wrapping; control fonts.
- **Chat:** full-width phone panel, opening at the latest message, "Latest" button, resume divider.
- **Tests:**
  - backend: 17 new memory tests (real PostgreSQL);
  - browser: a 24-check memory journey, plus layout at 5 widths;
  - full suite: 920 passed (8 known failures).

## v4.9.0 (23 Nov 2026): shorter answers, step-by-step details, no repeated questions

- **Shorter answers:** `agent.py` held older, much longer copies of 33 response texts that silently replaced the
  condensed ones in `responses.py`; the copies are removed.
- **No boxes or pep talk:** no "Official Note / Recommendation / Important Notice" boxes, and no closing pep talk.
  The prompt asks for no caveats unless asked, varied wording and rare use of the student's name.
- **Placements:** "packages", "recruiters", "training", "internships" and "guarantee" each get a short answer
  (several wordings). A topic question ("What would you like to know about placements?") is asked once per
  conversation.
- **Scholarship details:** one small card per step (board -> status -> marks -> group), "Step n of N"; no large form.
  Asked again after an estimate: "use these details or change them?".
- **Fixes:**
  - a programme switch ("CSE to ECE") is applied to the fee calculation;
  - "add <concession> to my fee" gives tuition minus the concession;
  - "656%" is questioned;
  - a below-minimum result is not repeated word for word;
  - "Change my academic details" no longer opens the phone-number update;
  - Yes / No chips appear only for real yes / no questions.

## v4.10.0 (23 Nov 2026): start afresh, fresh fact-based answers, relevant chips, concessions table, fee chart

See `docs/33-fresh-answers-and-fee-plans-nov-2026.md`.

- **Start afresh:** a new session ID.
  - Nothing of the old chat (name use, programme, marks, eligibility, pending steps) can come back.
  - A reply still in flight is dropped.
  - The old chat stays saved.
  - The saved name and number are kept only for the contact form (`fresh_start`).
- **Fresh answers:**
  - the 6-hour answer cache is removed;
  - "Why SRU", "About SRU", rankings, accreditation, research, international links and challenges are built from
    the verified facts retrieved for the question, and skip facts already given;
  - fixed overviews are sent once per conversation;
  - the prompt's fixed WHY SRU list is replaced by the retrieved facts (prompt `2026-11-23.3`).
- **Knowledge:** the six drafts are broken into structured facts with sources and status (`verified_facts.json`
  2027-28.2).
  - Ranking claims were checked against the 2027-28 fee card, THE's profile and press reports.
  - The 95% placement rate is marked unverified and never used.
  - Research figures are consistent: 9,300+ papers, 2,700+ patents.
- **Chips:** relevant only (at most 4). None after a callback or visit request, "thanks" or "bye".
- **Special concessions:** a selectable table card, then one green "fee with concession" card with the proof note.
- **Fee chart:** offered after a fee with hostel or transport. A shareable first-year chart (Share, WhatsApp).
- **Fixes:**
  - the "Research rankings" option no longer captures any sentence with "the";
  - "my percentage is 85" and "98 percentile" are read correctly;
  - no generic fee table next to the student's own fee.

## v4.11.0 (23 Nov 2026): the fee evaluation agent

See `docs/34-fee-evaluation-agent-nov-2026.md`.

- **The flow:** eligibility result → qualification confirmed → special concessions offered (before any fee card)
  → special consideration evaluated as **pending** (proof ready / to be submitted) → academic scholarship from the
  existing rules (reused, never re-asked) → hostel / bus → final fee card.
- **Final fee card:** confirmed payable apart from the amount after pending approvals.
- **Planner:** `sru_agent/fee_journey.py` stores selections only; amounts are computed from `fees.calculate_fee`
  each time. It covers:
  - side questions with a "Continue my fee estimate" chip;
  - "how much will I pay…" from the current evaluation;
  - "thanks" with an unfinished estimate offers to finish it;
  - one concession at a time;
  - changing marks or hostel recalculates and keeps the other choices.
- **The 4th welcome tile:** "Special Consideration" (it was "How to Apply"; applying is still answered).
- **Concessions:** a picked concession is never applied straight away. "Prepare my fee chart" gives the final fee
  card.

## v4.12.0 (23 Nov 2026): agentic features, admin switches, awake schedule

See `docs/35-agentic-features-and-admin-switches-nov-2026.md`.

- **Admin → 🤖 Agent:**
  - chat settings: a concessions picker switch (Grouped / Full table), counsellor connect on/off, wait, office
    hours and days. Stored in the database and applied from the next message; no redeploy, no migration;
  - students waiting now: a ringing banner on every tab, and "I'll call now";
  - counsellor copilot: ranked leads with reasons, and draft messages.
- **Grouped concessions card:** 5 groups, "None of these apply", private "Other circumstances". Both modes work
  in every entry point.
- **"Lowest fee" agent:** a visible plan; compares board, EAPCET and JEE routes, concessions and the cheapest room;
  explains the result. First-year only; the 4-year fee is never suggested.
- **Self-check:** checks the numbers in AI-written answers before sending.
- **Case summary:** saved with every callback / visit lead.
- **"Talk to a counsellor":** callback saved first; rings the admin panel for 30 s in office hours; then "will call
  you now" or "all counsellors are busy… we'll call you back on ******3210".
- **Awake schedule:** `/ping`; awake 06:00–01:00 India time (GitHub backup on that schedule, cron-job.org guide);
  switch off with `KEEP_AWAKE=off`.
- **Fix:** a callback asked for in the first message of a new chat no longer fails (the lead waits for the
  conversation row).

## v4.12.1 (23 Nov 2026): understand what the student asks (fee agent)

See `docs/36-understanding-the-student-backlog.md` (standing priority).

- **Fee summary:** shows the programme as the student chose it ("B.Tech CSE", or "B.Tech CSE (Artificial
  Intelligence & Machine Learning)"), not the fee card's whole group of specialisations. "CSE with robotics" is
  read as the Robotics & Automation specialisation.
- **Questions about the student's own evaluation** are answered from their selections, then the open step
  continues:
  - "Documents needed for the concession": the selected category, what to submit, and the effect on their fee
    (₹2,80,000 → ₹2,65,000);
  - "is my concession approved?";
  - "how much is my scholarship?".
  They are no longer sent to the scholarship steps.
- **"Yes, I have the proof"** records the proof and updates the summary.
- **"Add hostel to my fee"** goes to the hostel question even when other steps are open.
- **Button-contract test:** every button the fee agent offers must get a relevant answer.


## v4.13.0 (24 Nov 2026): the official widget look; multi-question answers made safe

See `docs/37-official-widget-look-and-multi-questions-nov-2026.md`.

- **The widget looks like sru.edu.in:** logo blue `#194F90`, button blue `#297DE5`, black text, Inter, flat, small
  corners.
  - Covers the bubble, the REGISTER NOW button, the header, bubbles, tiles, chips, input, every card, the
    calculator, the confetti and the icons.
  - Only inside the widget (`html[data-surface="widget"]`, `styles/official-widget.css`); the full website is
    unchanged. Colours go through `--o-*` tokens (`frontend/scripts/official_tokens.py`).
- **Fixed:** the widget's Fee Calculator button opened the calculator behind the chat.
- **Nikhil's multi-question commits reviewed and kept, with safety rules** (`sru_agent/compound.py`):
  - **Never split:** messages with actions or the student's data (callbacks, marks, visits), button labels,
    single questions, and other programmes' fees.
  - **Verified parts only:** every part is answered from verified content. Fees without a programme ask which
    one.
  - **Fixed:** the wrong hand-written scholarship slabs, now written from the fee data; the "ai" in "detail" match;
    a pending dialogue answer being skipped.
- **Tests:** `tests/test_v413_compound_safety.py` (25); the 7 tests the commits had broken pass again.

### v4.13.0 (continued, 24 Nov 2026): conversational intelligence; the fee flow from a production chat

See `docs/38-conversational-intelligence-nov-2026.md`.

- **Root cause of the scripted feel:** production calls the agent without a client, so ~30 branches gated on
  `client is None` always sent their fixed text; greetings came from variation lists.
- **Now:**
  - the model writes the answer for this message and conversation from the same verified text, now its facts;
  - cards, numbers and workflows stay with the code;
  - fallback: the verified text when the model can't be used, or when its words fail a check;
  - the greeting banks are deleted;
  - the conversation state (programme, details, open step, concession) is given to the model;
  - admin switch **Answers written by the AI** (off when first deployed; turn it on in Admin → 🤖 Agent).
- **Understanding:**
  - a family-link discount question → the named concession;
  - cut-off / closing-rank questions → not published;
  - "what is the eligibility?" → the programme's rule from the data;
  - scholarship and placement typos are recognised.
- **Fee flow (production chat):**
  - the old consolidated form is no longer shown; the step cards are shown instead;
  - marks are read with the board's total (867 → 867/1000), and "yes" is handled by the code;
  - the agentic flow runs without an AI call.
- **e2e/student_simulation.py:** 60–100 students chatting, every reply checked.
- **Tests:** 34 new; suite 1108 passed (1 needs a Gemini key).
