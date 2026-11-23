# 34. The fee evaluation agent: eligibility, special consideration, scholarship, final fee (v4.11.0)

Base: v4.10.0. The existing pieces are reused, not replaced:
- the step-by-step scholarship flow (`fee_intake`);
- the eligibility engine (`eligibility.assess`);
- the fee calculator (`fees.calculate_fee`);
- the fee card's 19 special concessions;
- the concessions table card.

No fee, scholarship or eligibility rule or amount was changed. No database schema was changed.

## 1. What the student experiences

```
Calculate my scholarship  →  board → status → marks → group      (existing steps)
        ↓
"Congratulations! … you qualify for this programme."  + the scholarship result
"Before we finalise your fee, there may be additional concessions or special considerations…"
        [concessions table]   [None of these apply]   [Show my final fee]        ← no fee card yet
        ↓ (picks a category)
"Noted: Students from Andhra Pradesh — ₹15,000 a year. This isn't applied yet: … evaluated once you submit proof"
"Do you have the supporting document…?"            [Yes, I have it] [Not yet]
        ↓
(academic scholarship: already known from the marks → not asked again)
"Will you stay in the university hostel?"           [AC 4-sharing (₹1,25,000)] … [No hostel, I'm a day scholar]
        ↓ (day scholar)  "Will you use the university bus?"  [Yes, add the bus] [No, I'll manage]
        ↓
Final fee card: payable now (confirmed) · after pending approvals (estimate) · each item with its status
```

### The "Special Consideration" tile

The fourth welcome tile was "How to Apply". It is now **Special Consideration**; "How to apply" is still answered
when asked, and is offered as a chip.

1. **Start:** the tile explains that the request will be evaluated, then shows the categories.
2. **Programme:** asked only if it is not known yet.
3. **Proof:** "Do you have the supporting document?"
4. **Academic scholarship:** "Would you also like to check whether your 10+2 / Intermediate marks give you an
   academic scholarship?" with Yes / No.
5. **Yes, with no marks yet:** the existing step-by-step flow asks only what is missing. The programme is not
   asked again. Its result comes back into the evaluation, and the concessions are not offered a second time.
6. **Then:** hostel, bus and the final card.

## 2. How it works (`backend/app/sru_agent/fee_journey.py`)

A planner, not a script.

- **State:** the conversation state `fee_eval` keeps only the student's choices:
  - programme;
  - chosen concession, and whether its proof is ready;
  - whether to check the scholarship;
  - hostel and bus;
  - the question last asked.
- **Next step:** `next_step()` looks at those choices and the profile (marks), and asks the first open question.
- **Amounts:** `evaluate()` computes every amount when it is shown, from `fees.calculate_fee`:
  - **A change of marks, programme or hostel** shows up in the next card. Nothing stale is kept.
  - **Nothing is counted twice.**
  - **Tests** check that the confirmed payable equals the calculator's first-year total for the same inputs.

| Rule | How |
|---|---|
| A special concession is never approved here | It is "Pending verification" (proof ready / to be submitted). It is shown apart from the confirmed fee: the confirmed payable excludes it; "after pending approvals" includes it |
| Academic scholarship only from the fee-card rules | The existing calculator with the student's marks. Final marks: **applied**, in the confirmed fee. Projected marks (exam not finished): **estimate**, outside the confirmed fee. No marks: **not evaluated**. Skipped: **not checked** |
| No duplicate concession | One at a time. The same one again: "counted once". Another one replaces it, and says so |
| No duplicate scholarship | Deducted once, from one calculation |
| Changing one thing keeps the rest | New marks (via "Change my academic details") update the scholarship and keep the hostel, bus and concession. "Change hostel", "remove the concession" and "change concession" each change only that |
| Final card not shown too early | Shown when the steps are done, or when the student asks ("show my final fee", "how much will I pay…", "give me the final fee card"). If steps are still open, they are listed on the card |
| Merit + concession together | The fee card does not say whether they combine, so the card says the Admissions Office confirms it |

### Agentic behaviour

- **Where the student is:** each reply asks the first open question. Details already given (marks, programme,
  hostel from a previous fee question) are reused, never asked again.
- **Side questions:** "what is the hostel curfew?" in the middle is answered normally. The progress is kept, and a
  **"↩️ Continue my fee estimate"** chip brings the student back to the exact step.
- **Answers are matched to the question:** a bare "yes" counts only if the fee agent asked the last question. A
  "yes" to another question in between is not taken as a fee answer.
- **"How much will I pay after the scholarship?":** answered from the current evaluation, with the card.
- **Winding down:** "thanks" while the estimate is unfinished gets "Before you go — your fee estimate is almost
  ready", the next question, and "Show my final fee".
- **Coming back:** the selections live in the conversation state, so a returning student resumes at the same
  step.
- **Below the minimum marks:** the existing explanation is unchanged; no evaluation starts.

### Final fee card (`fee_summary`)

Shows:
- the course (as named on the fee card) and the admission category (merit slab with its basis, or the standard
  fee);
- **payable now (confirmed)**, and **after pending approvals** (as an estimate, when something is pending);
- the items: tuition, the academic scholarship (with an **Applied** or **Estimate** tag), the special
  consideration (with a **Pending verification** tag), other fees, enrollment, hostel (meals included) and bus;
- approved concessions in total;
- the status of the scholarship and of the special consideration;
- **Still open:** the pending evaluations;
- the "combined with merit?" note;
- the application fee, and what is not included;
- **Share** (share sheet or copy) and **WhatsApp**.

## 3. Older paths, now joined to the agent

- **A picked or asked-for concession** ("add the sibling concession to my fee") enters the evaluation as
  pending. The v4.10 green "fee with concession" card is no longer produced (old chats still show it).
- **"Prepare my full fee chart"** and "yes" to the fee chart offer now give the final fee card (the v4.10 chart
  card still shows in old chats).
- **The concessions table** button reads "Check my fee with this" (it was "Apply to my fee"), and the table says
  each concession is approved only after the proof is verified.
- **"What special category concessions are there?"** is still an information question: the table, without
  starting an evaluation.

## 4. Tests

| Check | Result |
|---|---|
| `tests/test_v411_fee_evaluation_agent.py` (new, 18) | All pass. Covers: qualification and concessions before any fee card; full flow with the concession pending and out of the confirmed fee; none apply → no hostel → no bus; tile starts an evaluation; only missing details collected and the flow resumed after the steps; known marks reused; information question shows only the table; side question and continue; "how much will I pay" mid-flow; changing marks recalculates and keeps the hostel; same concession counted once, another replaces it; remove; "thanks" offers to finish; a bare "yes" to another question ignored; below minimum unchanged; projected marks; unknown programme; all amounts equal the calculator's |
| v4.10 tests updated for the new behaviour | 28 pass |
| Full backend suite | 973 passed, 3 failed. All 3 failed before this change: one needs a Gemini key, two are the older "scenario A" course tests |
| `e2e/v411_fee_agent.cjs` (real UI, API, PostgreSQL, Redis) | 27 / 27 at 390×844 and at 1440×900 |
| `e2e/v410_journey.cjs` (updated for evaluated concessions) | 32 / 32 |
| `e2e/memory_journey.cjs` | 25 / 25 |
| `e2e/cards_layout.cjs`: special consideration → final card, at 360, 390, 820 and 1440 px | No overflow, no sideways scroll, no page errors |
| Frontend build, fee calculator (3,477 checks), effects, lint | Pass; 18 lint warnings before and after (none new) |

The browser runs use the review model (no Gemini key). Everything in this flow is computed by the code, not the
model; only the side questions went to the model, and those were checked for routing only.

Screenshots: `docs/images/v4.11/`.

## 5. Known limits

- **Proof:** the agent records whether the student says the proof is ready; it does not receive or check
  documents. Approval is always the Admissions Office's.
- **One concession:** only one special concession is evaluated at a time. The fee card does not say whether two
  can be combined.
- **Started steps:** once the step-by-step scholarship flow has started, a hostel named inside a step answer is
  not picked up. The hostel question comes after the steps.
