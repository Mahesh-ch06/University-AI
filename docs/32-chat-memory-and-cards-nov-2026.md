# 32. Conversation memory, the welcome-back choice and chat cards (v4.8.0)

Base: v4.7.0 (`main`). Scope:
- conversation memory and resuming;
- "continue or start a new chat";
- the chat interface;
- every card shown inside a conversation.

No fee, scholarship, eligibility or placement logic or data was changed.

## 1. Root causes found

| # | Symptom | Root cause (where) |
|---|---|---|
| 1 | The "welcome back" question could appear right after a refresh, and on every visit; the student saw it only after typing a question | The page fetched the recovery context on every load and never checked inactivity there; the 30-minute check ran only for an open tab and reset its own timestamp on load (`ChatPage.tsx`) |
| 2 | "Start fresh" deleted the student's name and mobile number and all their details on the server | The frontend called `DELETE /agent/profile` before resetting (`handleStartNewConversation`) |
| 3 | The previous conversation lost its context after "Start fresh" | `reset_session_conversation` cleared that conversation's state and removed the marks from the profile, so reopening it later knew nothing |
| 4 | The wrong conversation could be offered, with the wrong "last active" time | Recovery chose the newest conversation by `updated_at`, which is never touched when messages are added (it stays the creation time) |
| 5 | With the database down, "continue" opened a conversation that did not exist | The memory fallback invented a random conversation id |
| 6 | The all-branch fee table never appeared after a personal fee answer, and a new chat could not show cards shown earlier | "Already shown" cards were remembered per browser session (not per conversation), and a card the agent dropped was still marked as shown |
| 7 | Card heading badges broke onto two lines (icon above the text) | The global `img, svg { display: block }` in `index.css` |
| 8 | Cards looked unrelated: coloured top / left stripes, different radii, buttons left / centred / spread | Per-card overrides on top of the shared `.rich-card` shell; three different footer layouts |
| 9 | Form options and buttons in cards used a different (system) font | Buttons and inputs do not inherit the page font by default |
| 10 | The placement card was about 2,000 px tall on a phone, with a clipped sideways strip | A carousel with fixed 180 px items and every offer listed |
| 11 | On phones the chat panel left a 32 px strip and cut off the close button | The phone layout set `width: 100vw` but kept the desktop `max-width: calc(100vw - 32px)` |
| 12 | Fee amounts in tables used a code font; the scholarship note's icon was squashed | `--font-mono` on amount cells; the icon had no fixed size |

## 2. Conversation memory: how it works now

| Situation | What the student sees |
|---|---|
| No earlier conversation | The normal welcome with quick actions |
| Refresh, or a chat link (`?chat=<id>`) | That conversation, as it was |
| Back within 30 minutes of the last message | The conversation simply continues (no question) |
| Back after 30 minutes, hours, or the next day | The **welcome-back panel**: when, the topic, the last question, the programme. Two buttons: **Continue chat** and **Start a new chat** |
| Typed a question before choosing | It is shown, and answered after the choice in the chosen conversation |
| Tab left open for 30+ minutes, then back | The same choice, once, at the end of the conversation |
| Chose "Start a new chat" earlier | That old conversation is never offered again; the new one continues |
| The conversation is gone | "That conversation is no longer available." Only "Start a new chat" is offered |
| Connection dropped while restoring | "I couldn't reach SRU Buddy…" and "Try again"; nothing is lost |
| Shared computer | "Not Asha?" forgets the name and number and starts a new chat |

- **Threshold:** `RECOVERY_RESUME_AFTER_MINUTES` (default 30, the value the app already used), on the server.
  `/recovery-context` returns `offer_choice`.
- **Continue:**
  - the saved messages are loaded;
  - the agent uses that conversation's history (from PostgreSQL after the 24-hour cache);
  - it uses that conversation's academic details (`journey.scope_profile`, with `saved_academic_conv` so they
    survive the cache);
  - a divider marks where it continues.
- **Start a new chat:**
  - the old conversation, its messages and its state are kept;
  - its academic details are filed with it and offered as "Use my saved details" (never applied by themselves);
  - the programme is not carried over;
  - name and mobile are kept;
  - the header's new-chat button does the same.
- **Ownership:** recovery, the restore request and the history loader all filter by the session ID. Another
  browser can neither see nor open the conversation, even with its link.

## 3. Chat interface and cards

- **One card system:** `components/ChatCards.css`, loaded after `Cards.css` and scoped to conversations.
  - **Design tokens:** radius, padding, inner-box background, border, shadow, title / text / label sizes.
  - **Shared rules:**
    - one card shell, with no stripes;
    - inline heading badges, with icons beside the text;
    - consistent section headings and inner boxes;
    - one footer;
    - one button family: primary, secondary, WhatsApp, and "show all".
  - **Layout:** cards adapt to the conversation's own width (container queries), so the 400 px desktop panel and
    phones get the same, correct layout.
- **Fee card:**
  - 2-column figures, down to very narrow widths;
  - tabular figures that never split;
  - the fee table's amounts in the chat typeface;
  - a fixed-size note icon.
- **Placement card:**
  - key numbers first (2 or 3 columns);
  - the three highest packages as a grid, not a clipped strip;
  - other offers folded behind "Show all 8 offers";
  - the data is unchanged.
- **Hostel card:** one column on phones, two in wider chats. Consistent item boxes and buttons.
- **Other cards** (curriculum, eligibility form, campus visit, faculty, contact, callback, videos): consistent
  shells, headings and buttons. Curriculum tabs keep their credits on one line. The videos card header wraps.
  The marks field placeholder fits.
- **Chat:**
  - a restored chat opens at the newest message;
  - a "Latest" button appears only when the student scrolls up;
  - full-width phone panel;
  - form controls use the chat typeface.

## 4. Tests

| Check | Result |
|---|---|
| `tests/test_conversation_memory.py` (new, 17; uses a real PostgreSQL where reachable) | All pass. Covers: the latest *active* conversation; offer at 31 min, 1 h, 3 h, 1 day, but not at 5 or 29 min; another student never offered; empty conversation not offered; real id in the memory fallback; a new chat isolated while the old one is kept; old details restored after cache expiry; no previous context in a new chat's prompt; history sent when continuing; cards per conversation; fee table after a personal fee |
| Browser journey (Playwright, real UI + backend + PostgreSQL + Redis; "time passing" done by moving saved message times back) | 24 / 24 checks pass: refresh; back after 10 min / 2 h / 1 day; typed question; continue; start new; reopen; offline then retry; another student |
| Cards and layout at 1440, 1280, 820, 390 and 360 px (12 card types, real backend output) | No element wider than the chat, no page sideways scroll, input always visible, no page errors |
| Full backend suite | 920 passed, 8 failed. The 8 are the known older suggestion-chip tests and one test that needs a Gemini key |
| Frontend build, fee calculator (3,477 checks), effects, lint | Pass; no new lint warnings (one fewer) |

The review model used here has no Gemini key. It reports how many earlier turns it received, which is how the
context checks are made visible; live AI wording was not tested.

Screenshots: `docs/images/v4.8/`.

## 5. Known limits

- A conversation's cached flow state (for example a half-answered question) lasts 24 hours in Redis. After that,
  continuing relies on the saved messages and the saved academic details.
- Only the most recent other conversation's details are kept for "Use my saved details".
- There is no conversation history list in the chat UI (the old `ConversationList` component is not used).
  Earlier conversations stay saved and can be opened by link.
- Feedback (thumbs up / down) on answers given live is not stored, because the browser does not receive the
  saved message ID. This was noted in `security/SECURITY_REMAINING_RISKS.md` R-15 and is unchanged here.
