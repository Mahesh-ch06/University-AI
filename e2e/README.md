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
| `memory_journey.cjs <outdir> 390x844` | Conversation memory: refresh; back after 10 min / 2 h / 1 day; a question typed before choosing; continue; start a new chat; reopening; offline then retry; another student. "Time passing" is simulated by moving this session's saved message times back in PostgreSQL (`psql` must reach the database) |
| `cards_layout.cjs <outdir> <W>x<H> [portal\|widget]` | Sends messages that produce each card type and screenshots every answer. Reports elements wider than the chat, page sideways scroll, a hidden input and page errors (`MSGS="a\|b\|c"` overrides the messages) |
