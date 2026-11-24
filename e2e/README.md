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

