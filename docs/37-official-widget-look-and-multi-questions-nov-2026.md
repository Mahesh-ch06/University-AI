# 37. The official widget look, and multi-question answers made safe (v4.13.0)

Base: v4.12.1 plus Nikhil's three commits on `main` (multi-question decomposition, PR #20).
- No fee, scholarship, eligibility or concession amount was changed.
- No database schema change. No API contract change.

## 1. The widget looks like sru.edu.in

The widget is the bubble added to the official site (`public/widget.js`); it opens this app at `/?mode=widget`.

**Where:** only inside the widget. `main.tsx` marks the page (`html[data-surface="widget"]`) before the first render,
and `src/styles/official-widget.css` holds the look. The full website keeps its own look; a pixel comparison of the
cards before and after the colour tokens showed no change outside the widget.

**Taken from sru.edu.in:**

| | Official site | Widget now |
|---|---|---|
| Brand blue (logo) | `#194F90` | header, chat bubbles of the student, labels, icons |
| Button blue ("APPLY NOW") | `#297DE5`, white text, 4 px corners | REGISTER NOW, send, Continue, Calculate, primary card buttons |
| Text | black `#0F0F11`, grey `#5D5E6C` | all text |
| Light blue | `#EFF8FF`, `#C1E3FC` | icon boxes, information notes |
| Font | Inter | Inter (the bubble uses the host page's Inter, else the system font) |
| Style | flat, white, thin grey lines, small corners | same: no gradients, almost no shadows, 4–10 px corners |

**What changed on screen:**
- **Bubble on the page:** flat logo blue with a calm pulse; REGISTER NOW like the site's APPLY NOW; a small square
  "Ask SRU Buddy" label; greeting and panel with small corners.
- **Header:** flat logo blue. The version pill moved out of the header (the version stays in the footer).
- **Conversation:** plain white (no dot pattern); flat grey answer bubbles; flat blue student bubbles.
- **Quick start tiles:** one official style (white, thin line, blue icon, blue label) instead of green / blue /
  purple / amber.
- **Buttons under answers:** outlined, blue text, 6 px corners.
- **Input:** a rectangular field with a blue focus ring, and a square blue send button.
- **Cards:** every card takes the official palette. The indigo, sky, purple and emerald accents became the two
  official blues.
  - WhatsApp buttons are plain (white with a thin line), like the site's top bar.
  - In the fee summary, the "Pending verification" label stays amber, because it is a status. The "Still open"
    note is an official blue information box.
- **Confetti** (eligibility): official blues and black.
- **Built-in icons** drawn in amber or emerald: official blues.

**Fixed (existed before):**
- **Fee Calculator button hidden:** in the widget, the header's Fee Calculator button opened the calculator *behind*
  the chat, so nothing seemed to happen. On narrow screens the chat container took the top layer. Inside the widget
  it is now the base layer, so the calculator and "My details" open in front.

**How every card follows** (`frontend/scripts/official_tokens.py`):
- The chat's stylesheets now write their colours as `var(--o-<token>, <the old colour>)`, for 1,119 colours.
- The full website defines no `--o-*` token, so it keeps every colour.
- The widget defines the tokens with the official values.
- The script is idempotent (a second run changes nothing).
- To give the full website the same look later, set `data-surface="widget"` there too: one line.

Screenshots (the widget on the live sru.edu.in): `docs/images/v4.13/`.

## 2. Nikhil's multi-question commits: review

What they add: when one message asks two things ("about sru and about hostels", "cse vs aiml and why sru"), each
part is answered.

**Kept:**
- the decomposition service and its 29 tests;
- the versioned prompt `prompts/decomposition.md`;
- per-part retrieval with sources kept, in the fallback chat path (`chat_service.py`);
- the comparison guard in the intent classifier;
- his answer texts for CSE vs AI & ML, hostel and placements (checked against our data).

**Problems found, all fixed:** the agent split *every* message that looked like two questions, before the flows
that understand it. Seven existing tests failed.

| Student message | Before the commits | After the commits | Now |
|---|---|---|---|
| "please call me, Priya Sharma 98765…. also is hostel available for girls?" | callback saved + answer | **callback lost** (the phone number was dropped) | callback saved + answer |
| "i got 85% and want cse" | marks remembered, fee calculated | **nothing calculated** (cut in two) | as before |
| "can my parents also come for the campus visit and what are the timings?" | campus visit answer | **hostel curfew rules** | as before |
| "Fee & scholarships" button after AI & Robotics | AI & Robotics fees | **B.Tech CSE fees** (always CSE) | as before |
| "What are all the programs and courses…", canteen, "How big is the campus and…" | their own cards | generic text | as before |
| "What are the fees and hostel timings?" | one part answered | **CSE fees assumed** + timings | "Which programme?" + hostel timings |
| "Tell me about SR University in detail" | About SRU | lost ("ai" matched inside "detail") | About SRU |
| A reply to our own question ("Which branch?" → "CSE and AIML") | read as the answer | **ignored** | read as the answer |

**Wrong scholarship slabs:** the new hand-written scholarship text did not match the official fee data. The overview
is now written from the fee data, so it always matches the calculator.

| Intermediate (state board) | Hand-written text | Official |
|---|---|---|
| 95–97.9% | 40% | 30% |
| 90–91.9% | 30% | 25% |
| 80–89.9% | 20% | 25% |
| 70–79.9% | 10% | 20% |
| 60–69.9% | missing | 10–15% |

**The rules now** (`app/sru_agent/compound.py`). A message is split only when all of these hold:
1. **No action and none of the student's own data:** no digits (marks, ranks, phone numbers); no callback,
   counsellor, visit, apply or booking request; no "I got / I want / my marks…".
2. **Every part is a verified topic:** SRU overview, why SRU, CSE vs AI & ML, hostel (rules and timings, mess, fee,
   safety, facilities), fees, placements, scholarships.
   - "Timings" counts as hostel only when the message is about the hostel.
   - A part that isn't one of these: no split.
3. **At least two different topics.** "Food stalls and food options" is one topic.
4. **Fees:**
   - for B.Tech CSE (named or already chosen): the CSE fee card;
   - with no programme known: the part asks which programme (never assumes CSE);
   - another programme named: no split, because the fee flow knows every programme.
5. **Continue button:** a multi-question message during an unfinished fee evaluation keeps the "Continue my fee
   estimate" button.
6. **Button labels are not split:** "Fee & scholarships", "Placements & Careers" and the like.
7. **Pending question:** an answer to our own question is still read as that answer.

## 3. Tests

| Check | Result |
|---|---|
| `tests/test_v413_compound_safety.py` (new, 25) | All pass. Covers: genuine multi-questions split; actions, marks, visits, button labels, single questions and other programmes not split; comparison and timings rules; the scholarship overview equals the fee data; fees without a programme ask which one; CSE fees and placements; marks still go to the agent; the pending dialogue answer; "in detail"; the continue button |
| Nikhil's tests (`test_decomposition_service.py`, `test_agent_compound_queries.py`) | All pass |
| Full backend suite | 1074 passed, 1 failed (`test_feedback_submission` needs a Gemini key, as before). The two older "scenario A" failures are fixed by Nikhil's commit |
| `e2e/v412_agent.cjs`, `v411_fee_agent.cjs`, `v410_journey.cjs`, `memory_journey.cjs` | 19/19, 27/27, 32/32, 25/25 |
| `e2e/cards_layout.cjs` (widget, 360 and 1440 px, incl. multi-question answers) | No page errors |
| `e2e/widget_on_official_site.cjs` (new) | The widget on the live sru.edu.in, desktop and phone: closed, open, contact form, eligibility, concessions, final fee card |
| Pop-ups in the widget | Fee Calculator and My details open in front of the chat, at 420 and 390 px |
| Frontend build, fee calculator (3,477 checks), effects (11), lint | Pass; 18 lint warnings before and after |

## 4. Notes

- **Review sandbox:** `cdn.jsdelivr.net` (the site's Bootstrap) is blocked here. The harness can serve it from a
  local copy (`CDN_MIRROR`). Without it, the official page lays out wider than a phone, and the bubble ends up
  off-screen. On the real site Bootstrap loads normally.
- **Bubble on a site:** the bubble keeps its `data-color` option. The default is now the logo blue `#194F90`.
