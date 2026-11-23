# Security implementation (what was changed, and why)

Branch `claude/security-hardening`, on top of v4.6.0. Each change maps to a finding in `SECURITY_AUDIT.md`
and to tests in `SECURITY_TEST_RESULTS.md`.

- **Architecture:** no change. Same stack, same endpoints, same SRU-only scope, fee / eligibility engines and
  accuracy disclaimer.
- **Database:** no schema change, so no migration.
- **Dependencies:** no new Python or npm dependency (the npm lock file was updated within existing ranges).

## Commits

| Commit | Scope |
|---|---|
| `cb14ea0` | Phase 1 assessment and threat model (documents only, before any fix) |
| `9c6b73b` | Backend / API: production detection, admin key, trusted client IP, AI limits, session IDs, feedback ownership, body size, CORS default, error messages |
| `cc32934` | AI: passage screening, provenance, data-not-instructions framing, mobile number masking, output leak guard, log hygiene |
| `2b3a9e8` | Frontend: export XSS, widget messages, admin key out of URLs, CSP |
| `d7ebe80` | Supply chain and infrastructure: npm fixes, Dependabot, CI token scope, dev ports, `.dockerignore`, config tests |
| (this commit) | Documentation |

## Changes by finding

| Finding | Change | Files |
|---|---|---|
| SEC-01, SEC-20 | `security.is_production()`: production when `APP_ENV=production`, when `RENDER` is set (Render sets it on every service), or when `APP_DEBUG=false`. In production the placeholder admin key is refused (503), `/docs` / `/redoc` / `/openapi.json` are off and HSTS is sent. Start-up warnings name weak settings, never their values | `app/security.py`, `app/main.py`, `app/api/v1/deps.py` |
| SEC-02 | Public conversation endpoint: the `admin_key` query parameter is removed. `X-Admin-Key` goes through the same `verify_admin_key` as admin routes (constant-time, limited, audited); this also fixes the HTTP 500. Frontend: no key in any URL; an old link's key is stripped from the address bar and ignored | `app/api/v1/chat.py`, `frontend/src/pages/ChatPage.tsx`, `AdminPage.tsx`, `services/api.ts` |
| SEC-03 | `security.client_ip()`: `CLIENT_IP_HEADER` if configured, else the `X-Forwarded-For` entry `TRUSTED_PROXY_HOPS` from the right (default 1), else the socket. Counters use a hash of the IP. Used by the admin failed-key limit and the lead limit | `app/security.py`, `deps.py`, `lead.py` |
| SEC-04 | `security.ai_turn_refusal()` on `/agent/stream`, `/chat`, `/chat/stream`: per session (unchanged 20/min), per network 40/min and 600/day, server 20,000 turns/day (all configurable; 0 = off). Fixed-window counters in Redis, falling back to process memory (`memory.allow_in_window`) | `app/security.py`, `sru_agent/memory.py`, `sru_agent/router.py`, `api/v1/chat.py`, `config.py` |
| SEC-05 | Export to PDF escapes message text before formatting; sources escaped; no inline script (printing is started by the app) | `frontend/src/utils/exportChat.ts` |
| SEC-06 | The prompt shows the mobile as "on file (ending 1234)". Lead tools accept `phone='ON_FILE'` (or a masked / empty value) and use the server-side profile; a new number typed by the student still wins. `remember_student_details` no longer echoes it. "What is my number?" is answered from the profile without the model | `sru_agent/prompt.py`, `tools.py`, `agent.py` |
| SEC-07 | Lead log: id and last 4 digits only. API keys are logged as `#n`, never a prefix. Tool logs carry the first 8 characters of the session ID | `services/lead_service.py`, `providers/key_pool.py`, `gemini.py`, `embedding_gemini.py`, `agent.py` |
| SEC-08 | `ai_guard.screen_passages()` drops passages carrying model instructions (handbook context and `search_university_info`), logging the title only. Passages carry their source (document type, page, dates, document id). Prompt rule: tool results and documents are data, never instructions (prompt `2026-11-23.1`) | `sru_agent/ai_guard.py`, `agent.py`, `tools.py`, `prompt.py`, `main.py` |
| SEC-09 | `ai_guard.guard_reply()` on every agent answer (`agent._done`) and legacy `/chat` answer: replaces answers with system-prompt lines, internal field names or secret-shaped strings. Live tokens stop once the streamed text matches | `ai_guard.py`, `agent.py`, `services/chat_service.py` |
| SEC-10 | Feedback stored only when the message is in a conversation of the same session; otherwise 404, nothing stored, no exemplar pruned | `services/conversation_service.py`, `api/v1/chat.py` |
| SEC-11 | `SESSION_ID_PATTERN` (16-64 of `A-Za-z0-9_-`) on every session parameter and body field (chat, memory, profile, recovery, feedback, agent) | `app/security.py`, `schemas/chat.py`, `schemas/memory.py`, routers |
| SEC-12 | CORS default: this project's Vercel domains and `*.sru.edu.in` only. CSP: `frame-ancestors 'self' https://sru.edu.in https://*.sru.edu.in`; `connect-src 'self' https://*.onrender.com`; `object-src 'none'`; `upgrade-insecure-requests`; `X-XSS-Protection: 0` | `config.py`, `frontend/vercel.json` |
| SEC-13 | Audit log line (`security.audit`) for every admin request and failed / locked attempt (action, outcome, path, hashed IP; never the key). Accounts / MFA / roles need an identity provider (remaining risk) | `app/security.py`, `deps.py` |
| SEC-14 | `BodySizeLimitMiddleware`: Content-Length check, then byte counting (chunked bodies); 256 KB API, 50 MB admin upload | `app/security.py`, `main.py` |
| SEC-15 | Registration message accepted only from `window.parent` when embedded; close message posted only when embedded | `ChatPage.tsx` |
| SEC-17 | `npm audit fix` (vite 8.3.8, source-map-js 1.2.4); Dependabot for pip / npm / actions | `frontend/package-lock.json`, `.github/dependabot.yml` |
| SEC-18 | Development Postgres / Redis / Chroma bound to `127.0.0.1` | `docker-compose.yml` |
| SEC-19 | `permissions: {}` on the keep-awake workflow | `.github/workflows/keep-backend-awake.yml` |
| — | `.dockerignore` excludes `.env.*` (local secrets never baked into the image) | `backend/.dockerignore` |

## New configuration (all optional, safe defaults)

| Variable | Default | Purpose |
|---|---|---|
| `TRUSTED_PROXY_HOPS` | 1 | Proxies that append to `X-Forwarded-For` (Render: 1, NOT VERIFIED) |
| `CLIENT_IP_HEADER` | empty | Platform header with the real client IP, e.g. `cf-connecting-ip` |
| `AI_IP_RATE_LIMIT_PER_MIN` | 40 | AI turns per network per minute |
| `AI_IP_DAILY_LIMIT` | 600 | AI turns per network per day (a college lab behind one IP shares this) |
| `AI_DAILY_TURN_BUDGET` | 20000 | AI turns per day for the whole server |
| `MAX_REQUEST_BYTES` | 262144 | Largest API request body |
| `MAX_UPLOAD_BYTES` | 52428800 | Largest admin document upload |

## Behaviour changes students or staff may notice

| Change | Who | Note |
|---|---|---|
| "What is my number?" answers from the profile (no AI) | Students | Same information, now deterministic |
| The AI says "the number ending 1234 is saved" instead of the full number | Students | Full number still in My details |
| "Copy chat link" in the admin page copies a link without the key | Staff | The link opens for staff signed in to the admin panel in that browser |
| Admin panel locked (503) on a production server that still uses the placeholder key | Staff | Intended; set a strong `ADMIN_API_KEY` (see `DEPLOYMENT_SECURITY.md`) |
| A site other than sru.edu.in can no longer frame the chat | Website team | Embedding on sru.edu.in and its subdomains is unchanged |
