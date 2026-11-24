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
