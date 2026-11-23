# 33. Start afresh, fresh fact-based answers, relevant chips, concessions and the fee chart (v4.10.0)

Base: v4.9.0 (`claude/great-ptolemy-1x1q7k`). No fee, scholarship, eligibility or placement rule was changed. No
database schema was changed (the one new profile key is stored in the existing `user_memories` rows).

## 1. Root causes found

| # | Symptom | Root cause (where) |
|---|---|---|
| 1 | After "Start a new chat" SRU Buddy still knew the name, and old details could come back | The new chat kept the same session ID (`hooks/useSession.ts` was read once, never replaced), and the server keeps the profile, marks and pending steps per session (`memory`, `agent_profile_store`). The name was copied into every session from this browser (`syncStudentDetails`) |
| 2 | A reply still streaming for the old chat could appear in the new one | The stream callbacks in `ChatPage.tsx` had no way to tell that the conversation on screen had been replaced |
| 3 | The same question got the identical answer for hours, for everyone | A 6-hour answer cache keyed by the message text (`agent.py`, `memory.get_cached_answer`). It also outlived data updates |
| 4 | "Why SRU?" was always the same text | The production API calls the agent without a model client, so every `client is None` branch is a fixed text. "Why SRU" / "About SRU" used two fixed texts; the prompt also carried a fixed "WHY SRU" list |
| 5 | Facts in answers disagreed (9,300+ vs 8,900+ papers, 2,900+ vs 2,700+ patents; THE 2026 vs 2027) | Figures were copied into texts, the prompt, a card and handbook lines separately |
| 6 | "What is the hostel curfew?" after a research question answered research rankings | The "Research rankings" option of the clarification step matched any message containing "the" (`dialogue.py`, pattern `the\b`) |
| 7 | Chips under every answer, often unrelated | `followups.ensure_fixed_chips` padded every row to 4 with "Fee & Scholarship Info" and "Why Choose SRU?"; a completed callback got four generic chips |
| 8 | The special concessions answer was a long list; no table | The concessions card had no renderer in `Cards.tsx` (it was never shown), so the text carried the list |
| 9 | Two fee cards for one fee question | The "fee with hostel" intent added a generic CSE + hostel table next to the student's own calculation |
| 10 | "My percentage is 85" gave 0% scholarship; "98 percentile" was read as 98% | `_fee_args_from_message` read only "85%" / "85 percent", and "percent" matched the start of "percentile" |

## 2. Start afresh

- **New session:** "Start a new chat" (welcome-back panel and header button) gives this browser a new session ID
  (`startFreshSession`).
  - The server has no messages, marks, programme, eligibility, pending steps or confirmations for it, so nothing
    can be retrieved or injected.
  - The old conversation is not deleted. It stays saved under the old session (and opens from its link).
- **Late replies:** any stream or restore still running is cancelled. A late reply is dropped by a
  generation counter, so an old answer never lands in the new chat.
- **Contact details:** this browser keeps only the name and number used by the contact form.
  - They are copied to the new session marked `fresh_start`, so the contact form is not shown again and callbacks
    still have the number.
  - The conversation does not address the student by name, and the model does not see it (`address_by_name:
    false`).
  - If the student introduces themselves again, the name is used from then on.
- **Not {name}?:** forgets the name and number too.
- **Works offline:** the new chat starts even without a connection; filing the old chat's details on the server
  is best effort.

## 3. Facts, retrieval and answers

### Verified facts store

The drafts were broken into facts and stored as structured records in
`backend/app/sru_agent/knowledge_base/verified_facts.json` (version `2027-28.2`), not as raw text.

- **Fields:** each record has a category, statement, source, verification status, validity dates, a short
  student-facing line, tags and an aspect.
- **Statuses:**
  - **verified:** in an official SR University document; for rankings, also the ranking body's listing or press
    coverage.
  - **university_reported:** stated by SRU; answers say "as described by SRU".
  - **unverified:** not found in official materials; never used.

| Draft claim | Checked against | Stored as |
|---|---|---|
| QS Asia 2027: 701–710 band, debut | 2027-28 fee card; Telangana Today, 5 Nov 2026 | verified |
| 19th among private universities in India (QS Asia 2027) | 2027-28 fee card | verified |
| "Ahead of nearly 60% of ranked Asian institutions" | Chancellor's statement only | not used in answers |
| THE World University Rankings: 801–1000 | THE profile (2026 and 2027); fee card (2027) | verified |
| 7th among private universities in India (THE) | Fee card (2027 edition); presentation (2026 edition) | verified |
| 6th in India in Research Quality (THE) | Presentation and handbook (they differ on the edition year, so no year is stated) | verified |
| NIRF 2025: 91st in Engineering; Top 100 four years running | Presentation, fee card, news; no NIRF 2026 listing found | verified (until the next edition is confirmed) |
| NBA Tier-I for all B.Tech programmes | Presentation: CSE, ECE, EEE, ME, CE | verified, with the five programmes named |
| ICAR, first private university in Telangana and Andhra Pradesh | Fee card, presentation | verified |
| Youngest private university in Telangana with national and global ranks | SRU's own description | university_reported |
| 8,900+ publications, 2,700+ patents | Handbook: 9,300+ papers; patents 2,700+ (news) or 2,900+ (one line) | 9,300+ papers, 2,700+ patents (the lower patent figure) |
| 171+ startups at SRiX | Presentation, handbook | verified |
| Highest ₹51 LPA (Microsoft); Amazon recruiter | Presentation | verified |
| **95% placement rate** | **Not in any official material** | **unverified: never used** |
| 80+ international collaborations | Presentation | verified |
| 170-acre campus, clubs, sports, hostels, fests | Handbook, presentation | verified |
| Industry-oriented curriculum, live projects, internships | Presentation (2,500+ internships, Batch 2026) | verified |

The 9,300+ / 2,700+ figures are now the same everywhere: the answer texts, the comparison card, the handbook lines
and the legacy RAG prompt.

### Retrieval

`fact_service.retrieve(question, exclude=…)` works in three steps:

1. **Identify the question:** detect its aspects (rankings, accreditation, placements, research, innovation,
   international, campus, academics, scholarships, about).
2. **Pick facts:** only active facts (not unverified, not expired) of those aspects. A broad question gets the
   strongest fact of each aspect. Keyword-similar facts of another aspect are not returned.
3. **Skip repeats:** facts already given in this conversation are skipped.

### Answers

- **Built from facts:** "Why SRU?", "About SRU", rankings, accreditation, research, startups, international links
  and challenges ("Is SRU bad?", "Is X better?") are answered from the retrieved facts (`responses.facts_reply`):
  - one framing line (several wordings);
  - 2–4 bullets;
  - one question back.
- **Asked again:** new facts ("a few more things worth knowing"). When everything relevant was said, it is
  framed as a recap.
- **Challenges:** lead with rankings, placements and accreditation (AGENTS.md rule 22).
- **No match:** when no fact matches, the answer says the information could not be verified.
- **With a model client:** the same facts go into the prompt as "VERIFIED FACTS FOR THIS QUESTION". The prompt's
  fixed WHY SRU list is gone (prompt `2026-11-23.3`).
- **Fixed overviews:** a programme, next-gen programmes, labs, canteen or evaluation overview is sent once per
  conversation. Asked again, the question goes to the model with the conversation.
- **Cache:** the answer cache is removed (`AGENT_ANSWER_CACHE_SECONDS` is no longer used).
- **Other routing fixes:**
  - a new question is no longer taken as an answer to the last clarification;
  - "why?" after an answer is about that answer, not "why choose SRU";
  - "EAPCET rank 40000" is not a rankings question.

## 4. Chips

- Only chips about the topic, at most 4. Nothing is added to fill the row.
- Yes / No for a yes / no question.
- No chips:
  - after a callback or visit request;
  - after "thanks" or "bye";
  - when the message has no topic to follow up on.
- Option rows that answer a question (board, programme, interests) keep all their options.

## 5. Special concessions

1. **The table:** "What concessions are there?" shows a one-line answer and the concessions table: 19 categories,
   per year, from the fee card, highest first.
   - It is shown every time it is asked.
   - Tapping a row selects it; "Apply to my fee" sends the exact category name.
   - The table then locks, so nothing is applied twice.
2. **Matching:** the exact fee-card name is matched first. "Students from Andhra Pradesh" is never confused with
   "Students from states other than Telangana and Andhra Pradesh".
3. **No programme yet:** SRU Buddy asks which programme, with four options.
4. **The result:** one card in a distinct (green) style:
   - tuition after the concession, per year and per semester;
   - the sum (tuition − concession);
   - the note "Applies only after you submit valid proof… verified by the Admissions Office";
   - with a merit scholarship, its effect and "whether it combines is confirmed by the Admissions Office" (the fee
     card does not say).
   - No second card.

## 6. Complete fee chart

- **The offer:**
  - after a fee with hostel or transport added, once per conversation, SRU Buddy asks "Shall I prepare your
    complete fee chart…?" with the chips "Yes, prepare my fee chart" / "No, thanks";
  - also available any time: "📋 Prepare my full fee chart".
- **The chart** (`fee_plan.full_fee_chart`, from `fees.calculate_fee`):
  - **Rows:** tuition, merit scholarship, other yearly fees, enrollment, hostel (with meals), transport.
  - **Totals:** the first-year total (equal to the calculator's), the regular semester total, and the application
    fee (paid when applying).
  - **Not included:** listed at the end.
  - **Concession:** a selected concession is shown as "if approved", separate from the total.
- **Sharing:** "Share" uses the phone's share sheet (or copies the chart). "WhatsApp" opens WhatsApp with the
  plain-text chart.

## 7. Tests

| Check | Result |
|---|---|
| `tests/test_v410_fresh_answers_and_fee_plan.py` (new, 28) | All pass. Covers: fact status and retrieval; expired and unverified facts excluded; fee-card ranking figures; why SRU twice with no repeated point; challenges; hostel question after research; bare "why?"; exam rank; overview once; chips; concessions table every time; exact category; programme asked; pending concession not captured later; merit note; chart offer, yes, no; chart sums; concession "if approved"; new session empty; fee message parsing |
| Updated tests | The old checks for fixed "Why SRU" texts, padded chips and the answer cache now check the new behaviour |
| Full backend suite | 955 passed, 3 failed. All 3 failed before this change: one needs a Gemini key, two are the older "scenario A" course tests |
| Browser journey `e2e/v410_journey.cjs` (real UI, API, PostgreSQL, Redis) at 390×844 and 1440×900 | 32 / 32 at both sizes: A start afresh (new ID, empty screen, in-flight reply dropped, no old marks or name, reload, no contact form); B why SRU twice; C ranking / NBA / curfew; D concessions table → AP → programme → one card → chart; fee with hostel → offer → chart; chips after callback and thanks |
| `e2e/memory_journey.cjs` (updated for the new session ID) | 25 / 25 |
| `e2e/cards_layout.cjs` with the new cards at 360, 390, 820, 1440 px | No overflow, no sideways scroll, no page errors |
| Frontend build, lint | Pass; 18 lint warnings before and after (none new) |

The review model has no Gemini key. The production path for the answers above does not use the model, so what was
tested is what students get. Answers that do go to the model (follow-ups, repeated overviews) were checked for
routing only, not for wording.

Screenshots: `docs/images/v4.10/`.

## 8. Known limits

- The step-by-step scholarship flow, once started, asks its steps first. A hostel named in a step answer is not
  carried into that estimate; ask for the hostel after it.
- Whether a special concession can be combined with a merit scholarship is not in the fee card. The card says the
  Admissions Office confirms it.
- Ranking positions should be re-checked when a new edition is published (NIRF 2026 was not found on 23 Nov 2026).
- The 95% placement rate from the draft needs an official placement report before it can be used.
