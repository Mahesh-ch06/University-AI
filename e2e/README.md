# Browser checks (Playwright)

End-to-end checks run against the real app: the Vite dev server, the full FastAPI backend, PostgreSQL and Redis.
Only the Gemini model is replaced (`review_server.py`), because these runs need no API key. The replacement says
plainly that it is a test model, and reports how many earlier turns of the conversation it received, which makes
restored context visible.

## Setup
```bash
docker compose up -d postgres redis          # or local PostgreSQL on 5433 and Redis on 6379
cd backend && alembic upgrade head && python ../e2e/review_server.py   # API on :8080
cd frontend && VITE_API_BASE_URL=http://localhost:8080 npx vite --port 5173
```
Playwright with Chromium must be installed (it is not a project dependency).

## Checks
| Script | What it checks |
|---|---|
| `memory_journey.cjs <outdir> 390x844` | Conversation memory: refresh; back after 10 min / 2 h / 1 day; a question typed before choosing; continue; start a new chat (a new session since v4.10.0); reopening; offline then retry; another student. "Time passing" is simulated by moving this session's saved message times back in PostgreSQL (`psql` must reach the database) |
| `cards_layout.cjs <outdir> <W>x<H> [portal\|widget]` | Sends messages that produce each card type and screenshots every answer. Reports elements wider than the chat, page sideways scroll, a hidden input and page errors (`MSGS="a\|b\|c"` overrides the messages) |
| `v410_journey.cjs <outdir> <W>x<H>` | v4.10.0 (`docs/33`): A start afresh (new session ID, in-flight reply dropped, no old marks / name, reload); B "why SRU" twice gives new points; C ranking / NBA / a new question after a clarification; D concessions table → pick → one fee-with-concession card → fee chart with Share; fee with hostel → chart offer → chart; chips after a callback and "thanks" |
| `v411_fee_agent.cjs <outdir> <W>x<H>` | v4.11.0 (`docs/34`): eligibility → concessions before any fee card → pick → pending → hostel (side question + continue) → final card (confirmed vs after approval, statuses, share); the Special Consideration tile → programme → proof → scholarship Yes → only missing steps → "thanks" offer → bus → final |
| `v412_agent.cjs <outdir> <W>x<H>` | v4.12.0 (`docs/35`), student and admin windows: admin switch to the full table and back (the chat follows at once); grouped card; lowest-fee plan; "talk to a counsellor" ring → accept → "will call you now"; ring → timeout → busy; copilot ranking and draft. Restores the default settings. `v410_journey.cjs` and `v411_fee_agent.cjs` switch to "Full table" for their run and back |
| `widget_on_official_site.cjs <outdir> [desktop\|mobile]` | v4.13.0 (`docs/37`): the widget injected into the live sru.edu.in (through the session proxy): closed bubble, open welcome, the two-step contact form, eligibility with concessions, grouped pick, pending, final fee card. `CDN_MIRROR=<dir>` serves the site's Bootstrap / Swiper from a local `npm pack` copy where cdn.jsdelivr.net is blocked |
| `python student_simulation.py <outdir> [--users 60] [--concurrency 4]` | v4.13.0 (`docs/38`): 60–100 students chatting the way real students do (short texts, typos, parents, Tenglish / Hinglish, repeated greetings, follow-ups, topic switches, journeys, concessions, callbacks, skeptics, off-topic, unpublished facts, multi-questions, Start Afresh). Every reply checked (errors, filler endings, re-welcomes, repeats, unverified ₹ amounts, length, known details asked again, cards, advocacy, scope); writes `report.md`, `results.json`, transcripts. With the real model: start the server with `REVIEW_MODEL=live` (and raise `AI_IP_RATE_LIMIT_PER_MIN` / `AGENT_RATE_LIMIT_PER_MIN` for one test IP) |


## 1,000-student simulation (v4.14.0)

```bash
AI_IP_RATE_LIMIT_PER_MIN=100000 AGENT_RATE_LIMIT_PER_MIN=100000 AI_IP_DAILY_LIMIT=1000000 \
  AI_DAILY_TURN_BUDGET=10000000 python e2e/review_server.py &
python e2e/student_simulation_1000.py /tmp/sim1000 --users 1000 --concurrency 12
```

Writes `report.md` (by topic, problems, examples), `results.json` and every transcript. All students come from one
IP, so the per-IP daily limit must be raised for the review server as above (never in production).

### 2,000-student simulation with checked outcomes (v4.15.0)

`student_simulation_2000.py`: 2,000 students, 20 personas, 7 writing styles (English, Telugu-English, Hindi-English,
short, typos, informal, long), 80% typing only and 20% also tapping the card and quick-reply buttons. Each student has
a journey with an outcome checked exactly: the full fee evaluation; 1-3 marks corrections (the profile on the server
and the final card must hold the LATEST marks, and the scholarship must be the official slab for them); impossible
marks; a side question or a "hi" in the middle; a programme change; "call me back" / the 30-second connect (the
student's name, never "Unknown", one lead per number); no name on file; Start fresh then a callback; and returning
minutes later (same server) or days later (a second server, `PORT=8081`, with the Redis keys removed so only the
database is left). The report gives the metrics (intent, relevance, facts, continuity, memory restoration, marks,
eligibility, callback identity, fee completion, quick replies, UI failures, repeats, overall) and the failures with
examples. Turns answered by the AI model are counted separately and not judged without a Gemini key.

```bash
for P in 8080 8081; do PORT=$P AI_IP_RATE_LIMIT_PER_MIN=100000 AGENT_RATE_LIMIT_PER_MIN=100000 \
  AI_IP_DAILY_LIMIT=1000000 AI_DAILY_TURN_BUDGET=10000000 python e2e/review_server.py & done
python e2e/student_simulation_2000.py /tmp/sim2000 --users 2000 --concurrency 16
```

It sets office hours to all day and the connect wait to 10 s for the run, and restores the settings afterwards.
