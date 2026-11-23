# 35. Agentic features, admin switches and the awake schedule (v4.12.0)

Base: v4.11.0. No fee, scholarship, eligibility or concession amount was changed. **No database schema change**:
- the settings are rows in the existing `user_memories` table, under a reserved system key;
- the case summary goes in the existing `metadata` column of leads.

## 1. What was built

| # | Feature | Where |
|---|---|---|
| 0 | Server awake 06:00–01:00 India time, sleeping about 5 hours; a light `/ping` endpoint | `main.py`, `.github/workflows/keep-backend-awake.yml`, `docs/uptime-monitoring-setup.md` |
| 1 | **Admin switch** for how special concessions are shown: **Grouped** (default) or **Full table (19 rows)**. Both modes fully work everywhere | `services/app_settings.py`, admin → 🤖 Agent → Chat settings |
| 1 | Grouped concessions card: 5 folded groups, "None of these apply", private "Other circumstances" | `fee_plan.CONCESSION_GROUPS`, `FeePlanCards.tsx` |
| 2 | **"Lowest fee" agent** with a visible plan: compares board / EAPCET / JEE, concessions, cheapest room | `fee_journey.py` (goal `lowest`), `AgentCards.tsx` |
| 2 | **Self-check** of AI-written answers: scholarship % corrected, unknown ₹ amounts flagged | `sru_agent/answer_check.py` |
| 3 | **Counsellor copilot**: who to call first (with reasons) + a draft message; **case summary** saved with every callback | `services/copilot_service.py`, `sru_agent/case_summary.py`, admin → 🤖 Agent |
| 3b | **"Talk to a counsellor"**: rings the admin panel for 30 s (real), then "all counsellors are busy… we'll call you back on ******3210" | `services/live_connect.py`, `AgentCards.tsx`, admin banner |

## 2. Admin panel → 🤖 Agent

Open the admin console, then the **🤖 Agent** tab.

**Students waiting now**
- A student who asks to talk to a counsellor appears here, with a countdown and their case summary. A banner also
  rings on every other tab, and the browser tab title shows the count.
- **I'll call now** shows the number to call. The student sees "A counsellor will call you now on ******3210"
  (with your name if you typed it), and the lead is marked *contacted*.
- If nobody accepts in time, the student sees "All our counsellors are busy right now… our admissions team will
  call you back on ******3210". The callback request was already saved at the start, so nothing is lost if the
  student leaves.

**Counsellor copilot**
- **Who should I call first?** lists the open requests of the last 14 days, best first, each with a tier (hot /
  warm / later) and the reasons. For example: "asked to talk to a counsellor now · finished a fee summary · has a
  special concession pending · asked in the last 24 hours".
- **Draft a message** writes a short message from the student's case: course, scholarship, fee, and the
  concession proof reminder. You can edit it, copy it, or open it in WhatsApp. Nothing is sent automatically.

**Chat settings.** Each change applies to the next message students send: no code change, no redeploy.

| Setting | Values | Default |
|---|---|---|
| Special concessions: how they are shown | Grouped (recommended) / Full table (19 rows) | Grouped |
| "Talk to a counsellor" rings this panel | On / Off (off: the callback is arranged straight away) | On |
| Wait (seconds) | 10–120 | 30 |
| Office hours (India time) | from / until | 09:00–18:00 |
| Working days | Mon … Sun | Mon–Sat |

How the settings work:
- **Storage:** validated, stored in the database, and cached for at most 20 seconds per server.
- **Safety:** if the database cannot be reached, the last known values (or the defaults) are used, so the chat
  never breaks.
- **Audit:** every change is written to the audit log.

## 3. The two concession modes

| | Grouped (default) | Full table |
|---|---|---|
| Card | 5 groups (Your state · Family link to SRU · Parent in service or honoured · Sports or NCC · Other circumstances); one opens at a time | All 19 rows, highest amount first |
| "None of these apply" | A button inside the card (during a fee evaluation) | A chip under the answer |
| Sensitive categories | In "Other circumstances", with "Private: pick one only if it applies. You won't be asked about it." | In the table |
| After picking | Same in both: pending verification → proof → scholarship → hostel → final fee card | |

The mode applies to every place a concessions card appears:
- after the eligibility result;
- the Special Consideration tile;
- "what concessions are there?";
- cards made by the AI model.

Chats saved earlier keep showing what they showed.

## 4. The "lowest fee" agent

**Trigger:** "Find me the lowest fee for CSE", "cheapest way to join", "maximum scholarship", "how can I pay less".

**What the agent does:**
- shows its plan (✓ done · ● now · ○ to do · – skipped) and updates it at every step;
- uses the existing step-by-step flow for any missing marks;
- asks for an EAPCET rank or JEE percentile (only for programmes that use them, and only when not already known);
- compares every route and uses the best one;
- offers the concessions;
- names the cheapest room;
- ends with the final fee card plus "how I got this":

```
✓ Done. Here's your lowest first-year fee. With your 40% scholarship (− ₹1,36,000), your first-year total …
• Scholarship: I compared Intermediate 72% → 20%, JEE Main 96 percentile → 40%, and used the best: 40%.
• 💡 A Non-AC, 4-sharing room would save ₹10,000 a year.        [Switch to Non-AC 4-sharing]
```

**Rules:**
- first-year amounts only;
- concessions stay "pending proof";
- the 4-year / full-course fee is never suggested; a test checks every chip for it.

## 5. Self-check of AI-written answers

Before an answer written by the AI model is sent, its numbers are checked against this turn's verified data:
- **Scholarship percentage:** a percentage next to the student's own fee calculation must match the calculator.
  If it doesn't, it is corrected.
- **Rupee amounts:** each one must appear in this turn's verified sources (the fee calculation, the cards, the
  passages) or in the official fee data. If one doesn't, a note is added: "I couldn't verify every amount above …
  please confirm with the Admissions Office."

Answers written by the code itself (all the flows above) come from the data and are not changed.

## 6. Fixes found while testing

- **First-message callback failed:** a callback or "talk to a counsellor" request sent as the **first message** of
  a new chat could fail with "I couldn't reach the admissions team". The lead was saved before the conversation's
  database row (written in the background) existed. The lead saver now waits for that row. This also fixes the
  older "call me" path.
- **Hidden countdown:** on phones the "Connecting…" card could sit below the fold. It now scrolls into view.

## 7. Tests

| Check | Result |
|---|---|
| `tests/test_v412_agentic_features.py` (new, 27) | All pass. Covers: settings defaults and validation; every concession in exactly one group; grouped and table cards; both modes finishing the fee flow; information question; model-made cards; admin settings API round trip (with the database); lowest-fee plan, route comparison, cheapest-room switch, entrance parsing; self-check; case summary on the lead and masked numbers; copilot ranking and draft; connect intent; ring → timeout → busy; accept (first wins, no duplicate); outside hours; switched off; no number; private status endpoint; no 4-year chip; `/ping` |
| Full backend suite | 1000 passed, 3 failed. All 3 failed before this change: one needs a Gemini key, two are the older "scenario A" course tests |
| `e2e/v412_agent.cjs` (student and admin windows) | 19 / 19 at 390×844 and 1440×900: admin switch to the table and back (the chat follows at once); grouped card; lowest-fee plan; ring → accept → "will call you now"; ring → timeout → busy; copilot list and draft |
| `e2e/v411_fee_agent.cjs`, `e2e/v410_journey.cjs` (now run in "Full table" mode) | 27 / 27 and 32 / 32 |
| `e2e/memory_journey.cjs` | 25 / 25 |
| `e2e/cards_layout.cjs` with the new cards at 360 and 1440 px | No overflow, no sideways scroll, no page errors |
| Frontend build, fee calculator (3,477 checks), effects, lint | Pass; 18 lint warnings before and after (none new) |

The review model has no Gemini key. The flows above are computed by code. The self-check was tested with a fake
model answer.

Screenshots: `docs/images/v4.12/`.

## 8. Notes and limits

- **Accepting a request:** "I'll call now" means a phone call. There is no chat takeover (as agreed).
- **Copilot:** it is rule-based (explainable reasons), not AI. Drafts are never sent automatically.
- **Live requests:** they live in the agent's short-term store (Redis) for a day. On the free Render plan a server
  restart during a 30-second wait can lose a ringing request; the callback lead is already saved, so the student
  is still called.
- **Not built (waiting for your decision):**
  - follow-up emails;
  - moving the website calculator's "4-Year Tuition" row behind a "Show later years" link.
- **cron-job.org:** this pinger must be set up once by you (see `docs/uptime-monitoring-setup.md`). The GitHub
  backup already runs on the new schedule once this is on `main`.
