# 38. Conversational intelligence: the model writes, the code keeps the facts (v4.13.0)

Base: v4.13.0 (docs/37). No database schema change, no new dependency, no API contract change. The admin
settings gain one switch.

## 1. Root causes found

| # | Where | What it did |
|---|---|---|
| 1 | `agent.py`, ~30 branches gated `if client is None or _is_mock_or_test_client(client)` | Production calls `run_agent` **without** a client (`router.py`), so every one of these branches always sent its fixed text. The model-written alternative existed but only ran when code passed a client. **This is why answers felt scripted** |
| 2 | `_GREETING_ASK_NAME`, `_GREETING_WITH_NAME`, `_NAME_GIVEN_REPLIES`, `_SMALL_TALK_*`, `_QUESTION_ACK_*` | Greetings, thanks, "how are you" picked from lists by a hash (`_select_variation`): "hi", "hi again" got another line from the bank |
| 3 | 42 stored paragraphs (`responses.py`, `agent.py`) | One paragraph per keyword intent, whatever the question about that topic |
| 4 | Keyword routers (`fee_intake._COUNSELLOR_TRIGGER`, the dialogue manager) | "Discount" started the scholarship steps, even for "my brother studies at SRU, any discount?"; "closing cut-off rank" asked for the student's marks; "what is the eligibility?" asked for marks instead of giving the rule |
| 5 | Typos | "schorshipp", "placment" were not recognised (the patterns expected `schol…`, `placement`) |
| 6 | The old consolidated "Fee & Merit Scholarship Assessment Form" | Its marks field is a percentage: a student's Telangana marks (867 out of 1000) became "867%". "yes" to "did you mean 866 out of 1000?" went to the AI, which was out of quota in production |

## 2. What changed (architecture)

**Facts stay with the code; the words come from the model.**
- **Before:** a topic intent → `_say(STORED_TEXT)`.
- **Now:** `_reply(STORED_TEXT)`.
  - **Normal path:** one model call writes the answer to *this* message in *this* conversation. The stored text
    is given as **verified facts**, along with the history and the conversation state.
  - **Code keeps:** cards, chips, numbers and workflow steps.
  - **Fallback:** when the model can't be used, the verified text is sent as it is. That covers no key, every key
    resting after a rate limit, the admin switch off, test clients, and words that fail a check (an unverified
    ₹ amount, a prompt leak, an empty answer).

| Piece | File | Notes |
|---|---|---|
| `_use_model`, `_model_words`, `_reply`, `_small_talk_reply` | `sru_agent/agent.py` | One call, no tools, the existing key ring / model fallback / time budget. The self-check (`answer_check`) and the leak guard (`ai_guard`) on every model-written reply |
| Conversation state for the model | `agent._conversation_note` | Programme, details already given ("never ask again"), open step, selected concession (pending), topic, "already greeted". Used by the fact replies and the main model path |
| Prompt | `sru_agent/prompt.py` (version `2026-11-24.1`) | Continue the conversation (no re-welcome); follow-ups read the state; no filler endings ("How can I assist you today?"). Kept under the 9,000-character budget |
| Small talk | `agent._SMALL_TALK_BRIEFS` | A brief per kind (greeting, greeting + ask name, thanks, how are you, bye, who are you, name given, ask name first). The banks are deleted; one plain line each only when the model is unavailable |
| Admin switch | Admin → 🤖 Agent → **Answers written by the AI** (`ai_answers`) | **Off when first deployed** (not yet tested on the real model; more AI calls on the free quota). On = the model writes the answers from the verified facts. Off = the verified texts, no AI call for them. Cards, fees, workflows and every other fix in this document work either way |
| Meaning before keyword | `fee_plan.infer_concession`, `agent._CUTOFF_FACT`, `agent._ELIGIBILITY_RULE_Q`, `eligibility.rule_text` | See section 3 |
| Fee intake | `fee_intake.decide` wraps `_decide` | The old form card is never returned; the step card for the detail being asked is shown instead. Marks given before the board are kept (`pending_raw_marks`) |

**Unchanged by design:**
- **Deterministic:** fee calculations, eligibility, scholarship slabs, concessions, workflow transitions (the fee
  journey, connect, callbacks), the opening welcome card (no AI call on every widget open), the disclaimer (shown
  by the UI, outside the answer) and the university-only scope.
- **Fee calculation results:** "86.7% (867/1000) qualifies for a 25% scholarship…" is still worded by the code,
  from the calculation.

## 3. Understanding fixes (found by the student simulation and the production chat)

| Student | Before | Now |
|---|---|---|
| "my elder brother is studying at SRU, any discount for me?" | "Which programme would you like the scholarship details for?" | "The Sibling … concession (₹15,000 a year) looks like it fits…" + the concessions card (also: parent works at SRU, SR Junior College, army, police, single parent, NCC, sports, disability…) |
| "What was the closing EAPCET cutoff rank for CSE last year?" | "What were your Intermediate marks?" | Not published; the Admissions Office confirms (833 100 3030) |
| "What is the eligibility?" after choosing B.Tech CSE | Asks for marks | The CSE eligibility rule from the data (every documented minimum where sources differ), then "Check my eligibility with my marks" |
| "Eligibility." as the answer to "check eligibility, process or fees?" / "Am I eligible?" | The check | The check (unchanged) |
| "any merit schorshipp" | The AI, a generic answer, a fee card | The step-by-step scholarship flow |
| "867" (no board yet) | "Out of how many marks?" + the old % form | "Noted: 867 marks. Step 1 of 4: which board?" → Telangana → 86.7% |
| "… Telangana State Board with 866% marks" | "866% isn't possible" | 866 out of 1000 |
| "yes" to "Did you mean 866 out of 1000?" | The AI (out of quota) | Handled by the code |

The reported production conversation now runs the whole agentic flow without an AI call:
- the steps (new cards only);
- 86.7%, 25%;
- concessions → proof → hostel;
- the final fee summary: ₹4,60,000 payable, ₹4,45,000 after approval, as in the report.

## 4. The student simulation (`e2e/student_simulation.py`)

60–100 simulated students, several at a time, through the real API (the widget's lead form first). Kinds of
students and conversations:
- short texters, typos, parents, Telugu and Hindi mixed with English;
- repeated greetings, pronoun follow-ups, topic switches and returns;
- the admission and scholarship journeys, concessions, callbacks;
- skeptics, off-topic asks, unpublished facts, multi-questions;
- Start Afresh, odd inputs, a repeated question.

Every reply is checked:
- no error, not empty, no filler ending;
- not welcomed again mid-chat, no repeated self-introduction, opening or answer;
- every ₹ amount verified, not over-long, the disclaimer not inside the answer, no 4-year fee chip;
- plus each turn's own expectations (topic covered, known programme not asked again, the right card, positive
  advocacy, scope).

**Runs here:**
- **Without a key (fallback mode):** this showed the routing bugs in section 3, all now fixed. Most remaining
  flags in that mode are replies that need the real model; the review sandbox's stand-in model marks them.
- **With the real model:** `REVIEW_MODEL=live python e2e/review_server.py`, then
  `python e2e/student_simulation.py <out> --users 60`. **Not run yet: this environment has no Gemini key**
  (see section 6).

## 5. Tests

| Check | Result |
|---|---|
| `tests/test_v413_dynamic_replies.py` (new, 14) | No greeting bank left; greeting / "hi again" / thanks / who-are-you written by the model with their brief and the history; model down → one plain line, not re-welcomed; a topic answer written from its verified facts; an invented ₹ amount or a leak → the verified text; cards still from the code; switch off and keys resting → no model call; the conversation state lists what is known; a follow-up gets the programme from the state |
| `tests/test_v413_understanding.py` (new, 11) | Family-link categories → the official concession (label and amount from the data); no category → no guess; the concessions card instead of the scholarship steps; cut-off → unpublished; the eligibility rule from the data; with the programme already chosen; a bare "Eligibility." choice and "am I eligible?" still check |
| `tests/test_v413_fee_flow_transcript.py` (new, 9) | The reported conversation end to end (new cards only, 867 kept, 86.7%, the flow continues, final 4,60,000 / 4,45,000); typos start the flow; 866% with the board known; "yes" handled; the old form never returned; a board without a fixed total still asks "out of how many?" |
| Full backend suite | 1108 passed, 1 failed: `test_feedback_submission`, which needs a Gemini key (as before) |
| Browser journeys `v412_agent`, `v411_fee_agent`, `v410_journey`, `memory_journey` | 19/19, 27/27, 32/32, 25/25 |
| The reported conversation in the widget (390 px) | Only the new step cards, "Noted: 867 marks", no old form, no page errors |
| Frontend build, lint | Pass; 18 lint warnings, as before |

The older tests run with the switch off, so they keep checking the verified texts (the facts and the fallback).

## 6. Limits and what is next

- **Real-model runs not done here:** this environment has no Gemini key. The model-written replies are tested
  with a recording fake model; their quality on Gemini is not measured yet. To run the 60-student simulation on
  the real model, add the key to the environment: Network secrets, host `generativelanguage.googleapis.com`,
  header `x-goog-api-key`.
- **Quota:**
  - the production chat already showed "The free AI limit has been reached";
  - model-written answers use more calls: one per topic answer and greeting, where the old texts used none;
  - when every key is resting, or the admin switch is off, the verified texts are used. Consider the paid
    plan, or turn the switch off on busy days.
- **Latency:** a model-written reply appears when it is complete (it is checked before it is shown), about 1–3 s
  on flash-lite. The main model path (questions without a stored answer) still streams as before.
- **Code-worded parts:** the fee calculation and summary sentences and the workflow step questions are still
  worded by the code, by design (exact numbers, the button contract).
- **Old intake code:** the old form intake in `fee_intake._decide` still runs underneath for its logic; only its
  card is replaced. The `FeeScholarshipFormCard` component stays in the frontend for chats saved earlier.
