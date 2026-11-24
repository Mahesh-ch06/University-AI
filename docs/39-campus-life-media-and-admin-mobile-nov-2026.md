# 39. Events, campus life, campus media and the admin dashboard on phones (v4.14.0, 24 Nov 2026)

## 1. What students get

| Question | Answer | Cards |
| --- | --- | --- |
| "what events happen at SRU", "fests?" | 50+ events a year, the highlights by name and date, "Which event…?" | Event photo cards (carousel) |
| "tell me about Lumina", "hostel night", "sparkrill", "navadhara", "freshers party", "project expo", "hackathons", "convocation" | That event: description and date ("Last held" once the date has passed), "See the other events?" (a "yes" shows them) | That event's photo card with its "Watch video" link |
| "how is campus life", "is campus life boring" | Events, clubs, sports, SRiX, living, support | Event cards |
| "what clubs are there", "is there a dance club", "tech clubs", "is there a chess club" | 39 clubs by group; one club with its official description; a club not on the list is said to be not on it | – |
| "how is the hostel food", "mess timings", "non veg?" | Dining hall, 4 meals, timings, cafeteria and kiosks, veg and non-veg | The official food video |
| "how is hostel life", "is the hostel good" | Rooms, food, services, safety (first-years in by 8:30 PM), Lumina | Lumina card + 2 hostel videos |
| "sports facilities", "is there a gym" | Sports complex, gym, Sports Day, clubs | Sports Day card |
| "stress", "is there a doctor" | Medical, counselling, career guidance | – |

* Facts: only those the admissions team approved on 24 Nov 2026 (checklist), from sru.edu.in (Events, Campus Life,
  Clubs & Organisations), the admissions presentation of 30 Oct 2026, the hostel rules document and the official
  YouTube channel. Lumina is the title of the Hostel Night / Hostel Hawa (confirmed by the team and the official
  "LUMINA 2025" Girls' and Boys' Hostel Night videos). No source links are shown to students.
* Not taken over: fees, scholarships, rules, curfew, safety, room types, quotas ("sports quota"), admissions,
  placements, several questions in one message (compound), an answer to a pending step ("sports" for a concession),
  general-knowledge questions ("who won the cricket world cup?").
* With "Answers written by the AI" on, the model words the same facts (agent `_reply`); otherwise the verified text.
* Code: `backend/app/sru_agent/campus_life.py` (topic, answers, the 39 clubs), wired in `agent.run_agent` before the
  broad-topic clarification. Handbook page `backend/data/handbook/15_events_clubs_and_student_life_nov2026.md` (RAG).
* Corrected: the curfew text now gives first-years 8:30 PM and seniors 9:00 / 9:30 PM (as the verified hostel
  fact); `fact.campus.life` now says 39 clubs and names Lumina.

## 2. Videos: 2 at a time, not the same every time

`video_service.get_keyword_videos` picks `limit` (2) videos **at random** among all videos about as relevant as the
best one (its topic), and skips videos already shown in the conversation when others are left. Hidden videos are
never shown (`create_video_card` filters them, whichever search found them).

## 3. Admin -> Campus media (new tab)

| Section | What the team can do | Setting |
| --- | --- | --- |
| Events | Add, edit, reorder, show/hide (max 16): title, when, description, image link (https), YouTube video, other names students use. Live preview. | `event_highlights` |
| YouTube videos | See all 53 official videos (+ added ones) by topic with counts, search, change a video's topic, hide/show, add a video by its link (title, topic, video/short, words). | `videos` = `{hidden, topics, added}` |
| Ads | Small ad above the message box (max 6): cover image, highlight, line under it, tag, button text and link (https), show/hide, seconds per ad. Live preview. Shown ads take turns; a student can close them for the visit. | `chat_ads`, `ads_rotate_seconds` |

Stored like the other chat settings (`user_memories`, `system:app-settings`, long values in pieces): **no
migration**. Validation: https links only, no `<`/`>`, YouTube ids checked, an ad switched on needs a link. The one
sample ad ("Admissions open for 2027-28") ships switched off.

## 4. API

| Method | Path | Auth | Returns |
| --- | --- | --- | --- |
| GET | `/api/v1/agent/chat-ads` | public | `{rotate_seconds, items:[{id,title,subtitle,tag,image_url,cta_text,link_url}]}` (switched-on ads) |
| GET | `/api/v1/agent/videos` | public | `{items:[video]}` (the videos the chat may show) |
| GET | `/api/v1/admin/videos` | X-Admin-Key | `{builtin:[video], topics:[…], changes:{hidden,topics,added}}` |
| PUT | `/api/v1/admin/settings` | X-Admin-Key | accepts `event_highlights`, `videos`, `chat_ads`, `ads_rotate_seconds` |

New chat card: `{"type": "event_highlights", "title", "items": [{id,title,when,summary,image_url,video_url}]}`.

## 5. Admin dashboard on phones (`frontend/src/pages/AdminMobile.css`)

* Header on one line (badge and "Live" hidden on phones), tabs one scrollable row with the active tab scrolled into view.
* Numbers two per row; every table (leads, documents, feedback) becomes one card per row with labelled values.
* Student chats: the list, or the open conversation with "← All chats" (not both one under the other); the
  transcript buttons in two columns.
* Campus media: one column below 960px, the Save bar sticks to the bottom only when there are changes.
* Checked at 390 x 844 and 1366 x 800: no sideways scrolling on any tab.

## 6. Tests

* `backend/tests/test_v414_campus_life.py` (55): topics and not-ours, answers, clubs, past dates, admin events used
  at once, validation, hidden / moved / added videos, random picks, ads validation, public ads and admin video list,
  chat flows (events -> Lumina -> "yes"; food video; hostel fee untouched).
* Updated vehicles (their messages are now answered from the approved facts): `test_agent_actions` and
  `test_v412_agentic_features` use a library question for the model path; `test_hostel_flow` checks the new food
  answer and the 8:30 PM first-year in-time.

## 7. The 1,000-student test (`e2e/student_simulation_1000.py`)

1,000 generated students, 18 mindsets (anxious parent, topper, low scorer, budget, fun-seeker, skeptic, confused,
impatient texter, Telugu-English, Hindi-English, hostel-focused, sports person, safety-conscious, comparison shopper,
rude, wanderer, day scholar, outstation), 3-7 questions each about SR University only, ~30 topics with varied
wording, typos and follow-ups. 800 only type; 200 also tap the quick-response buttons (a reply to a button is checked
against the button's words). Each reply is checked: error, empty, filler ending, welcomed again, repeated answer,
unverified rupee amount, length, and that it is about what was asked.

Replies the code cannot give itself go to the language model; without a Gemini key here the review server's
stand-in answers them, so those turns (22.6%: safety, location, curfew, room fees, off-topic) are counted apart.

| Round | Replies | Checked (code) | No problem | No problem, not counting "same facts as an earlier reply" |
|---|---|---|---|---|
| 1 (before fixes) | 5,441 | 4,098 | 79.4% | 95.4% |
| 2 | 5,452 | 4,220 | 86.8% | 96.9% |
| 3 | 5,463 | 4,230 | 88.2% | 96.7% |
| Final | 5,463 | 4,230 | 88.5% | 97.0% |

Median reply 103 ms, 90th percentile 175 ms (code path, local).

**Found and fixed** (each with a test in `tests/test_v414_side_questions.py`):

* **The fee steps captured every next message.** After "B.Tech CSE fees" asked "which board did you study under?",
  "how are the placements?", "fests in sru", "what is the AC room fee", "tech clubs" all got the board question
  again. Now a question about something else (`agent._side_question`) is answered; the steps stay saved and the
  reply offers "Continue my fee estimate". A fee question or an answer to the step still continues the steps.
* **"Just show the B.Tech CSE fee"** (the button) was read as an answer to a pending question ("which kind of
  events?" matched "Tech"). It now closes the steps and gives the standard fee, whatever was waiting.
* **"What scholarships does SRU give?"** started the steps; it now gets the merit scholarship slabs from the fee data.
* **Placement questions** ("how are the placements?", "highest package", "jobs after BBA") get the verified placement
  answer at once; a bare "placements" / "what about placements?" still asks which aspect; a guarantee question keeps
  its approved answer.
* **The same step question again** now says why it is asked again and offers "Just show the … fee".
* **A campus topic asked again** gets a short recap instead of the same block; specific questions get their own
  answer: mess timings, canteen, non-veg, a gym, a listed sport (cricket…) or an unlisted one (swimming: not listed,
  the Admissions team can confirm).
* **"tell me about B.Tech AI & ML"** now says "B.Tech CSE (AI & ML)" (AI & ML is a CSE specialisation in the fee data).
* **"hi" after earlier answers** no longer brings the first-visit welcome back.

Remaining flags are mostly the simulated student asking the same question twice and getting the same facts, and
scholarship savings the fee engine computed (the checker only whitelists amounts shown in a fee card).
