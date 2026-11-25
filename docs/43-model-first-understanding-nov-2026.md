# 43. Model-first understanding: no keyword routing for typed questions (v4.17.0, 25 Nov 2026)

## Why

Typed questions were routed by keyword and phrase rules before the language model ever saw them. Similar words
picked the wrong canned reply. Examples from a student chat:

* "standard fee of cse" → the saved-details prompt;
* "how is ru" and "im from delhi" → the scholarship text and fee summary sent again;
* "Placement record" → a false "couldn't verify amounts" note;
* "about sru" → the 19 special concessions.

When every Gemini key was resting after a rate limit, the fallback also chose a canned text by keyword:

* the programme / hostel / eligibility overviews;
* a fee parsed from the words;
* a handbook passage found by keyword search.

These were the "stale" answers. Most were about something else.

## How a message is handled now

`agent.run_agent` decides once per turn whether the turn is **structured** (`_structured_turn`). The decision uses
facts about the turn, never the topic words.

| Turn | Handled by |
|---|---|
| Typed question (the default) | **The model.** It gets the whole conversation, the student's saved details, the verified facts (`fact_service.retrieve`), the handbook passages, and the tools: fee engine, eligibility, programme info, faculty, callbacks, videos. |
| A chip, card option or tile the bot offered (`source: "button"`) | That button's fixed flow (fee steps, scholarship form, concession table, callback…). |
| A submitted form, or "use my saved details" | The fixed flow. |
| A typed answer that the open fee step's own parser accepts | The fee step continues. |
| A short reply (≤ 8 words, not a question) while the bot waits on its own question (a callback being arranged, "shall I prepare your fee chart?", a fee step, a "which aspect?" question) | That step. |
| A message with a phone number | The callback / number flow, so the number is saved exactly. |

A *question* typed during an open step goes to the model. The model sees the step in the conversation. The step
stays open, and its "continue" chip brings the student back. A stale "which aspect?" question or fee-chart offer
is closed when the student asks something else.

Unchanged:

* **Security:** the prompt-injection / adversarial guardrail runs before anything else, for every turn.
* **Fees:** amounts come only from the fee engine. The model calls `calculate_fee`. The answer self-check
  (`answer_check`) rejects any amount that is not an engine amount. For typed questions, no fee is pre-calculated
  from the words; the model asks the engine with the details it understood.
* **Honesty checks:** a reply about a callback / visit / cancellation must match what the tools actually did.

## When the model is unavailable (rate limit)

1. The key pool rotates to the next healthy key and retries (unchanged).
2. If every key is resting, or the model cannot be reached, the student gets an honest message. For example:
   *"I'm getting a lot of questions right now, so I couldn't read yours properly. Please send it again in a
   minute…"* It comes with buttons that work without the model:
   * **Open fee calculator** opens in the browser;
   * **Calculate my scholarship**, **Talk to a counsellor** and **Plan a campus visit** run fixed flows.

   The Admissions Office number is included.
3. No answer is guessed from the words of the question. These were removed:
   * the keyword-intent canned fallbacks (placements, hostel, programme overviews, eligibility…);
   * `_offline_fee_reply` (fee parsed from the words);
   * `_offline_knowledge_reply` (keyword handbook passage).
4. The one remaining fallback is a button or step whose fee the engine already calculated for that turn. It shows
   that calculation as it is: engine figures, nothing inferred from typed words.

## API

`POST /api/v1/agent/stream` accepts `source: "typed" | "button"` (default `typed`). The widget sends `button` for
suggestion chips, card selections, the welcome tiles and the calculator's "Ask SRU Buddy". It sends `typed` for
the text box. Internal callers of `run_agent` (tests, replays) that pass no `source` are treated as buttons, so the
fixed flows keep their own tests.

## Admin setting note

The admin "fee questions" setting (`evaluate_first` / `fee_card`) applies to the fee buttons and steps. A typed
fee question is understood by the model, which gives the engine's fee and offers the scholarship steps.

## Tests

* `backend/tests/test_v417_model_first.py` covers:
  * the routing rule;
  * the request schema;
  * ten typed questions from the student chat reaching the model with their own words;
  * history and verified facts in the prompt;
  * no keyword fee prefetch;
  * a button keeping its flow without a model call;
  * rate limit → honest reply, busy buttons, no ₹ amount, no cards.
* Tests that asserted the removed keyword fallbacks now assert the honest behaviour.
