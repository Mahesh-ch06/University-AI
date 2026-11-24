# 41. Ad image upload, the Student chats page, and the second audit (v4.15.1, 24 Nov 2026)

## 1. Upload a picture for an ad or an event card

Admin -> Campus media -> Ads (and Events): **Upload image** (or drop a picture on the box, or paste an https:// link
as before). The picture is made smaller in the browser (longest side 1,400 px, WebP, or JPEG where the browser can't
write WebP, under 400 KB), uploaded, and shown in the preview at once. Save to use it in the chat.

* Stored in the database, not on disk (Render's disk is wiped on every deploy): `user_memories`, session
  `system:media`, rows `media.<id>` (type, size, pieces) and `media.<id>#<i>` (base64 in 240-character pieces). No
  schema change. `<id>` = first 20 hex characters of the SHA-256, so the same picture is stored once.
* `POST /api/v1/admin/media` (admin key; multipart `file`): JPEG, PNG or WebP only, checked by the file's first bytes
  (no SVG or HTML, which could carry scripts); at most 450 KB. Returns `{id, url, type, size}`; `url` is
  `/api/v1/agent/media/<id>`, which is what goes in `image_url`. The request-size limit for this path is the upload
  limit (the general 256 KB limit would have refused normal pictures).
* `GET /api/v1/agent/media/<id>` (public, like the ad itself): the image, `Cache-Control: public, max-age=31536000,
  immutable`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'`. An image whose
  stored pieces don't match its hash is never served.
* `image_url` of an ad or event accepts an https:// link or `/api/v1/agent/media/<id>`; the widget makes the latter
  absolute with the API address (`mediaUrl` in `services/api.ts`).

## 2. Admin -> Student chats

* The list is an inbox: each chat shows the **student's name** (initials avatar), the time ("3:08 PM", "Yesterday",
  "Mon", "24 Nov"), the topic, a two-line preview, and tags: programme, marks, "Callback requested" / "Visit request",
  messages, helpful / not helpful. (It showed a session code and only the date.)
* The open chat starts with the student: name, **Call** and **WhatsApp** links, programme, marks, scholarship,
  request and lead status, then the topic, start time and message count. Two actions (Open as student, Copy chat)
  and **More** (copy link, print / PDF, JSON, copy ID, delete). The bubbles have initials and no side bars.
* API: `AdminConversationItem` and `AdminConversationDetailResponse` gain `student` (name, phone, program, marks,
  scholarship_percent, request, lead_status, is_parent), from the profile the chat saved and the leads (two queries
  per page). Additive; nothing removed.

## 3. Second audit

* 2,000 new students (seed 9001, not the seed the fixes were made against): **93.8%** passed every check;
  continuity, memory restoration, marks, eligibility, callback identity, fee completion, invalid marks,
  duplicates and programme changes 100%; 13,212 of 13,368 code-answered replies with no problem (98.8%); 5.1% of
  replies were the model's (stand-in here, not judged).
* Fixed: "tell me about BBA" / "b.des details" while the fee steps waited for the board only repeated the board
  question (now: the programme overview, then "Continue my fee estimate"); "Check my eligibility with my marks"
  after "which branches?" + "eligibility criteria for Civil" showed the general eligibility table (the programme
  discussed is now remembered); the request-size limit above.
* Backend 1,277 passed; browser journeys 32/32, 27/27, 19/19, 26/26, 16/16; upload journey 10/10 (laptop and
  phone); frontend type check, lint (no errors) and build clean.

## 4. Official videos (card and recommendations)

* 22 videos added from the official "SR University" YouTube channel (each checked by YouTube oEmbed: the channel is
  "SR University"): LUMINA 2026, JUNOON, SRU-MUN, Diwali, Bonalu, Navdhara, Convocation 2026, the 2025 recap,
  toppers, agriculture, the campus tour, AI / CS and placement stories. 75 videos in all
  (`backend/app/data/university_videos.json`). The LUMINA 2025 videos moved from "Hostels" to "Campus Life & Fests".
* Recommendations (`video_service.topic_videos`, `agent._with_topic_videos`): videos only for an informational
  answer on a visual topic (hostel, placements, fests, campus, a programme...), only from that topic, a named
  video first ("junoon", "lumina"), up to 2, once per topic per chat, never a video already shown. No videos on
  fee, eligibility, admission, location, safety or request questions, on a workflow step, or when the topic is
  unclear. Keywords are matched as whole words ("interview" is not "view"). When the AI asks the video tool for a
  topic with no official video, the tool now returns `no_match` (no card) instead of campus-tour videos.
* The card keeps its one row (two videos side by side, a third scrolls). Each video shows its **YouTube thumbnail
  as the preview**, with a small YouTube mark in the corner and no play button over the picture; a topic title
  ("Hostel life at SRU", "Placements & careers at SRU"); a clean title (the channel's repeated "| SR University |
  Best Private University…" tail removed); "SR University · YouTube". If a thumbnail can't load (a network that
  blocks YouTube images), a navy tile with the title shows instead of an empty box.

## 5. Unexpected questions (open-question audit)

248 questions students may ask in their own words (admissions, programmes, fees, scholarships, eligibility,
placements, hostel, food, academics, clubs, rankings, international, contacts, vague, off-topic, Telugu / Hindi,
multi-part, typos, rude, security, future dates, and 70 new phrasings), each in a fresh chat: **no errors, no
empty replies**. Answers fixed or added in `backend/app/sru_agent/quick_facts.py`, each from the 2027-28 fee card,
the verified handbook (`backend/data/handbook`), or saying plainly that it is not in the official sources and who
confirms it:

* Programmes SRU does not offer (pharmacy, MBBS, law, B.Arch, nursing, online) said plainly, with what SRU offers.
* Fee increase (the fee card's own words), "why is the fee so high", per semester, 4-year total, hostel not
  included, other charges, caution deposit, transport; instalments and education loans: not on the fee card ->
  the Admissions Office.
* Which programmes a stream allows (MPC / BiPC / commerce), from the fee card's eligibility notes only ("required
  subjects as per university norms" -> confirm with the Admissions Office); a named programme gets yes / no first.
* Leadership (Vice-Chancellor, Chancellor, Registrar..., from sru.edu.in/about), history (notified May 2020, from SR
  Engineering College; the group founded in 1976 by Sri A. Varada Reddy), international students (visa and
  settling-in support, ₹15,000 concession), B.Tech lateral entry (6 semesters; eligibility -> Admissions Office).
* Concessions recognised in more words: "sibling discount", "single girl child scholarship", "scholarship for army
  kids", "concession for lateral entry".
* Security: a request for keys or passwords, or for other students' details, gets a specific refusal.
* Food specifics not in the sources (spicy, Jain, outside food) are said to be unconfirmed, with what is known.

Questions with no verified answer in the sources are listed for the university to answer (the bot sends them to
the Admissions Office until then): NAAC grade, scholarship renewal rules, instalments, education loans,
admission dates and documents list, spot admission / management quota, lateral-entry eligibility, hostel Wi-Fi,
laundry details, parent visits, attendance rule, exam pattern, Sunday campus visits, starting a new club.

## 6. Crash fix and final checks

* Fixed a crash that is also on main: when the AI model failed (quota, "high demand", timeout) while a callback or
  campus visit was pending, the fallback read `is_other_fee_inquiry`, which only the skipped fee block set
  (`UnboundLocalError`, the reply errored). It is now set first. Test:
  `test_model_failure_during_a_pending_callback_or_visit_never_crashes` (fails without the fix).
* "is SRU ranked number one?" was taken for a phone-number question by the new contacts answer; "number one / 1"
  no longer counts as a phone number.
* Final checks: backend 1,326 passed; browser journeys v410 32/32, v411 27/27, v412 19/19, memory journey 26/26,
  memory flow 16/16, upload journey passed, video card on phone and laptop (real thumbnails, no page errors);
  248 unexpected questions with no errors; 2,000-student simulation (seed 4242): 93.1% of students passed every
  check, all critical metrics 100%, 1.3% of replies repeated earlier wording; frontend build clean.
* Not tested here: answers written by the AI model, for lack of API quota (free tier).
