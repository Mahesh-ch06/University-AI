# SRU Buddy security assessment (Phase 1: as found, before fixes)

| | |
|---|---|
| Scope | Repository `Nikhil18N/University-AI`: FastAPI backend (`backend/`), React/Vite frontend and embeddable widget (`frontend/`), CI workflow, Docker files, example environment files |
| Base | Branch `claude/great-ptolemy-1x1q7k` at `1e16ced` (v4.6.0, PR #4, not merged). Hardening is on `claude/security-hardening` |
| Method | Manual source review of every route, dependency and storage path; secret scan of tracked files and git history; `pip-audit` and `npm audit`; local tests. No testing against live university infrastructure (Render, Vercel, Neon/PostgreSQL, Redis, Gemini) |
| Date | 23 November 2026 |
| Standards | OWASP Top 10 for LLM Applications 2026 (published 4 August 2026), OWASP ASVS / API Security Top 10, India DPDP Act 2023 and DPDP Rules 2025, CERT-In Directions of 28 April 2022 |

This document records what was found **before** any change, so each fix can be traced to a finding. Fixes, tests and
their status are in `SECURITY_IMPLEMENTATION.md` and `SECURITY_TEST_RESULTS.md`. What remains open is in
`SECURITY_REMAINING_RISKS.md`. Nothing here is a legal opinion; compliance needs confirmation by the university's
legal / privacy team.

## 1. System summary

SRU Buddy is an anonymous admissions chat for SR University.

- **Identity:** there is no login. The browser makes a random UUID (`crypto.randomUUID`, kept in `localStorage`
  `university_ai_session_id`). That **session ID is the only credential** for a student's profile (name, mobile
  number, marks), conversations and memory.
- **Staff:** use one shared admin key (`ADMIN_API_KEY`, sent as `X-Admin-Key`) for the admin dashboard: leads,
  conversations, exports, document upload and evaluations.
- **AI:** Gemini (Google `google-genai`) is called by an agent loop with tools (fee calculator, eligibility,
  knowledge search over ChromaDB, callback / campus visit requests). The tools that save leads store the student's
  name and mobile number in PostgreSQL.
- **Hosting (from repository files, not verified on the dashboards):** backend on Render (Docker, uvicorn);
  frontend on Vercel (`university-ai-companion.vercel.app`); PostgreSQL (Neon-style URL in the example file); Redis
  optional; ChromaDB embedded (`PersistentClient`) by default.

## 2. Attack surface inventory

### 2.1 Public HTTP endpoints (no authentication)

| Endpoint | Data | Credential | Abuse limits found |
|---|---|---|---|
| `POST /api/v1/agent/stream` | Chat turn (SSE), returns profile | session ID in body (1-64 chars) | 20 turns/min **per session ID** |
| `POST /api/v1/chat`, `POST /api/v1/chat/stream` | Legacy chat (RAG) | session ID in body | 20/min per session ID |
| `GET/PUT/DELETE /api/v1/agent/profile` | **Name, mobile, marks** | session ID in query (min 8) / body | none |
| `GET /api/v1/agent/recovery-context`, `POST /reset-session` | Last conversation context | session ID (min 1) | none |
| `GET /api/v1/conversations`, `GET/DELETE /conversations/{id}`, `GET /shared/{id}` | Chat transcripts | session ID in query (min 1) | none |
| `GET /api/v1/conversations/{id}` | as above, **plus an admin bypass** via `X-Admin-Key` header or `admin_key` **query parameter** | | |
| `POST /api/v1/feedback` | Rating; a thumbs-down prunes the verified exemplar for that `message_id` | session ID in body, **no ownership check** | none |
| `/api/v1/memory/*` (pending tasks, calculations, memory, summary) | Student memory | session ID in query | none |
| `POST /api/v1/leads` | Name, mobile (lead form) | none | 30/min per **first X-Forwarded-For entry** |
| `POST /api/v1/agent/calculate`, `GET /programs`, `GET /fee-config`, `POST /api/v1/finance/estimate` | Public fee data | none | none (no AI cost) |
| `GET /`, `/live`, `/health`, `/ready` | Service status | none | none |
| `GET /docs`, `/openapi.json` | API schema | none | exposed whenever `APP_DEBUG` is true (the default) |

### 2.2 Admin endpoints (`/api/v1/admin/*`, `X-Admin-Key`)

Agent runs, calculations, finance rules (read / **write**), document upload / list / **delete**, stats, feedback,
conversations list / export / view / **delete**, exemplar promotion, evaluations, leads list / stats / status / **export
(PII)**. All use `Depends(verify_admin_key)`. Failed keys are limited to 5 per minute per **first X-Forwarded-For
entry**.

### 2.3 Frontend and widget

- **Storage:**
  - `localStorage`: session ID, `sru_student_lead` (name and mobile number), chat UI state;
  - `sessionStorage`: `university_ai_admin_key` (the admin key) and `sru_staff_mode`.
- **Admin route:** a URL slug compiled into the bundle (`sru-ops-9f4a7c2e`, or `VITE_ADMIN_PATH`). It hides the
  page; it is not an access control. The backend key check is the control.
- **Widget:**
  - `public/widget.js` embeds the app in an iframe (`?mode=widget`) and checks message origins;
  - the app posts `sru-buddy:close` to `"*"`;
  - the app accepts `sru-buddy:register` from any sender.
- **Export to PDF** (`utils/exportChat.ts`) writes an HTML document into a new window with `document.write`.
- **Headers** (`vercel.json`): CSP with `script-src 'self'`, HSTS (preload), nosniff, frame-ancestors (incl.
  `https://*.vercel.app` and `http://localhost:*`), Permissions-Policy.

### 2.4 AI / RAG surfaces

- **System prompt** (`sru_agent/prompt.py`, versioned):
  - includes the student's known profile as `key=value` pairs, **including the full mobile number**;
  - has no rule saying that tool / document content is data, not instructions.
- **Tools** (`sru_agent/tools.py`): a fixed allowlist (`run_tool` refuses unknown names).
  - Write tools: lead save / update / cancel, profile memory.
  - Tool errors are stripped before the model sees them (`_error` popped in `agent.py`).
- **Retrieval:** `search_university_info` returns `title` and `text` only (no source / provenance), with no
  framing and no screening for embedded instructions.
- **Ingestion** (admin only):
  - extension allowlist `.pdf .txt .md .docx`;
  - random file names (no path traversal);
  - 50 MB limit (checked after the whole file is read into memory);
  - PDF parsed with PyMuPDF, DOCX with python-docx.
- **Input guard:** a regex for jailbreak / prompt-extraction / malware requests before the model is called.
- **Output:** no output-side check for leaked instructions or secret-shaped strings.

### 2.5 Infrastructure and supply chain

- **Backend container:** `Dockerfile` (python:3.12-slim) runs uvicorn **without** `--proxy-headers`, so the client
  IP is read by hand from `X-Forwarded-For`.
- **Python dependencies:** `requirements.txt` uses only `>=` ranges and has no lock file, so builds are not
  reproducible.
- **Frontend dependencies:** `package-lock.json` is present.
- **`docker-compose.yml` (development):** Postgres, Redis (no password) and Chroma are published on all interfaces.
- **GitHub workflow:** `.github/workflows/keep-backend-awake.yml` pings `/health` and has no `permissions:` block.
- **`start_tunnel.sh`:** exposes a local backend through a Cloudflare quick tunnel (developer tool).

## 3. Automated scan results

| Scan | Result |
|---|---|
| Secret scan of tracked files (Google API key, OpenAI / GitHub token, private key, cloud DB URL with password) | No real secret. One match in `backend/.env.production.example` is a placeholder (`username:password@ep-xyz...`). All `*KEY*` values in the three example files are placeholders |
| Same patterns over the whole git history (`git log --all -p`) | 0 Google keys, 0 tokens / private keys; 1 DB-URL match = the same placeholder |
| `pip-audit -r requirements.txt` (fresh resolution) | 1 package: **chromadb 1.5.9**: CVE-2026-45829, CVE-2026-45833, CVE-2026-45831, CVE-2026-45830 (all in the Chroma **server** HTTP API; no fixed version yet) |
| `pip-audit` of this container's environment (not the production image) | also old `pypdf`, `pillow`, `soupsieve`, `httplib2`, `pip`, `setuptools`, `wheel`. Not in `requirements.txt` directly; shows the risk of unpinned builds |
| `npm audit` (frontend) | 2 high: **vite 8.3.0-8.3.2** (dev-server / launch-editor advisories, GHSA-9jrq-w75r-8gcw and others) and **source-map-js < 1.2.2** (DoS in source-map parsing). Both build / dev time only; fixes available within the declared ranges |
| SQL injection sinks | None: SQLAlchemy ORM only; one `text("SELECT 1")` health check |
| Code execution / deserialisation (`eval`, `exec`, `pickle`, `yaml.load`, `subprocess`) | None in `app/` |
| SSRF | None: outbound URLs come from server configuration only (Gemini, OpenRouter, Ollama, leads API) |

## 4. Findings

Severity: Critical / High / Medium / Low / Info. "Prod" says whether the production state could be checked from
here. Nothing on Render / Vercel / the database could be checked (no access), so those are **NOT VERIFIED**.

| ID | Sev. | Finding | Evidence | Prod |
|---|---|---|---|---|
| SEC-01 | **Critical** (if production lacks `APP_DEBUG=false`) | **Insecure defaults:** `APP_DEBUG=True` and `ADMIN_API_KEY="change-me-in-production"` by default. The placeholder key (public in the repository) is refused only when `APP_DEBUG` is false. A deployment that forgets `APP_DEBUG=false` gives full admin access (all leads with mobile numbers, all transcripts, exports, deletes, knowledge-base upload) to anyone, and exposes `/docs` | `config.py`, `deps.py:71` | NOT VERIFIED |
| SEC-02 | High | **Admin key in URLs.** "Open live chat" and "Copy shareable chat link" in the admin page build `/?chat=<id>&admin_key=<KEY>`; the chat page reads it and sends it as a query parameter. The key ends up in the clipboard, browser history, Vercel / Render access logs and any link that is shared. The public endpoint compares with `==` against `settings.ADMIN_KEY`, which does not exist (any key gives HTTP 500) | `AdminPage.tsx:441,452`, `ChatPage.tsx:131`, `api.ts:421`, `chat.py:124` | n/a |
| SEC-03 | High | **Spoofable client IP:** the admin brute-force limiter and the lead limiter use the **first** `X-Forwarded-For` value, which the caller controls. A new fake IP per request bypasses both | `deps.py:66`, `lead.py` | NOT VERIFIED (depends on Render's proxy) |
| SEC-04 | High | **Denial of wallet / unbounded consumption (LLM06:2026):** the only chat limit is per session ID, and the caller chooses the session ID. A new ID per request gives unlimited Gemini calls. No per-IP limit, no daily budget | `router.py:122`, `chat.py` | n/a |
| SEC-05 | Medium | **XSS in "Export to PDF":** message text is written into the print window without HTML escaping (only titles and sources are escaped). A message or AI answer containing HTML runs in a same-origin window that can read `localStorage` (session ID, name, mobile) and `sessionStorage` (admin key). The production CSP should be inherited by the `about:blank` window and block inline handlers, but this is browser-dependent | `exportChat.ts:85-89,288` | partly mitigated by CSP (NOT VERIFIED per browser) |
| SEC-06 | Medium | **PII sent to the model (LLM02:2026, DPDP minimisation):** the full mobile number is in the system prompt on every turn and is echoed back by `remember_student_details` | `prompt.py:80`, `tools.py:339` | n/a |
| SEC-07 | Medium | **PII and key fragments in logs:** each lead logs name and full mobile at INFO; Gemini embedding timeouts log the first 8 characters of the API key | `lead_service.py:167`, `embedding_gemini.py:123,176` | n/a |
| SEC-08 | Medium | **Indirect prompt injection (LLM01 / LLM05 / LLM09):** retrieved passages go to the model with no "data, not instructions" framing, no screening and no provenance. The prompt has no rule against following instructions found in documents or tool results | `tools.py:317-330`, `main.py:agent_knowledge_search`, `prompt.py` | n/a |
| SEC-09 | Medium | **No output check (LLM08 Hidden Context Exposure / LLM10):** nothing stops a reply that quotes internal instructions or a secret-shaped string | `agent.py` | n/a |
| SEC-10 | Medium | **Feedback without ownership:** any caller can store feedback against any conversation / message ID, and a thumbs-down removes the verified exemplar with that `message_id` (integrity of the curated answer store) | `conversation_service.create_feedback` | n/a |
| SEC-11 | Medium | **Weak session-ID rules:** endpoints accept 1-character session IDs (8 for the profile) and take them in query strings (kept in access logs). The session ID is the only key to a student's name and mobile | `chat.py`, `memory.py`, `router.py` | n/a |
| SEC-12 | Medium | **Broad origins:** CORS accepts any `https://*.vercel.app` (anyone can host a page there); CSP `frame-ancestors` allows any `*.vercel.app` and `http://localhost:*` (clickjacking frame); `connect-src` allows any `*.vercel.app` and the Gemini API host (the browser never calls Gemini) | `config.py` CORS regex, `vercel.json` | NOT VERIFIED (Render env may override) |
| SEC-13 | Medium | **Single shared admin key:** no per-person accounts, MFA, roles, rotation or audit trail of admin actions (lead exports, deletes, knowledge-base uploads). Key kept in `sessionStorage` | `deps.py`, `AdminPage.tsx:363` | NOT VERIFIED |
| SEC-14 | Low | **No request body size limit:** JSON bodies are fully read before validation; uploads are read completely (up to and beyond 50 MB) before the size check | `main.py`, `admin.py:136` | Render limits NOT VERIFIED |
| SEC-15 | Low | **postMessage:** the app accepts `sru-buddy:register` from any window (it only opens the registration form) and posts `sru-buddy:close` to `"*"` (no data) | `ChatPage.tsx:35,364` | n/a |
| SEC-16 | Low | **PII in browser storage:** name and mobile kept in `localStorage` with no expiry (shared / lab computers) | `studentProfile.ts:52` | n/a |
| SEC-17 | Medium | **Supply chain (LLM04):** unpinned Python dependencies; chromadb server-API CVEs (embedded mode in the default config is not exposed); vite / source-map-js advisories (dev / build only); no Dependabot | section 3 | production image NOT VERIFIED |
| SEC-18 | Low | **Development compose** publishes Postgres / Redis / Chroma on all interfaces with development passwords (Redis without one) | `docker-compose.yml` | dev only |
| SEC-19 | Low | **CI workflow** has no `permissions:` block (inherits the repository default token scope) | `keep-backend-awake.yml` | n/a |
| SEC-20 | Low | **API docs and debug:** `/docs`, `/openapi.json` exposed while `APP_DEBUG` is true; HSTS only when debug is off | `main.py` | NOT VERIFIED |
| SEC-21 | Info | **Logging / retention:** no documented log retention, no security event log, no incident procedure. CERT-In expects ICT logs kept for a rolling 180 days (a copy in India) and incidents reported within 6 hours | — | BLOCKED (institutional) |
| SEC-22 | Info | **DPDP:** no privacy notice text, retention schedule or erasure path beyond "Forget my details" (profile only). DPDP Rules 2025 core duties (notice, security safeguards, breach intimation, retention) commence on about 13-14 May 2027 (18 months after notification). Consent managers: about 13-14 November 2026 | — | BLOCKED (legal) |

### Controls that are already in place (verified in code)

| Area | Evidence |
|---|---|
| Ownership by session | Conversations, memory and profile queries filter by `session_id`. `get_or_create_conversation` never attaches a turn to another session's conversation |
| Typed request schemas | Pydantic models with length limits for messages (1,000 chars), names, phones and form fields (Literal choices) |
| Admin key comparison | `secrets.compare_digest`; placeholder refused outside debug |
| Generic error handler | No stack traces to clients |
| Tool allowlist and consent | Unknown tools refused. Leads require `consent=true` and a valid 10-digit mobile |
| Upload handling | Extension allowlist; random stored file names; admin only |
| Browser hardening | CSP `script-src 'self'` (no inline scripts); `X-Frame-Options DENY` on the API; nosniff; Referrer-Policy |
| CORS | Credentials not allowed (`allow_credentials=False`) |
| Widget | Checks the origin of `sru-buddy:close` messages |
| Model resource limits | 4 tool rounds, 25 s call timeout, 6 concurrent calls per process, message length cap |
| No SQL injection / SSRF / unsafe deserialisation sinks | See section 3 |

## 5. Prioritised plan

| Order | Findings | Change (code, with tests) |
|---|---|---|
| 1 | SEC-01, SEC-20 | Production detection (`APP_ENV=production` or Render's `RENDER` variable or debug off); placeholder key always refused there; no `/docs` there; startup warning for weak keys |
| 2 | SEC-02, SEC-03, SEC-13 | Remove the query-parameter admin bypass; validate the header with the same check as admin routes; trusted-proxy client-IP helper; audit log line for admin actions; frontend stops putting the key in URLs |
| 3 | SEC-04, SEC-11, SEC-14 | Per-IP minute and daily limits on AI endpoints, global daily turn budget, session-ID format rule, request body size limit |
| 4 | SEC-10 | Feedback only for the caller's own conversation and message |
| 5 | SEC-06, SEC-07, SEC-08, SEC-09 | Mask the mobile number to the model; retrieved passages framed, screened and given provenance; prompt security rules; output leak guard; PII-free logs |
| 6 | SEC-05, SEC-12, SEC-15, SEC-16 | Escape the export; narrow CSP and CORS; postMessage source / origin checks; shorter browser storage of contact details |
| 7 | SEC-17, SEC-18, SEC-19 | Update vite / source-map-js in the lock file; Dependabot; bind dev services to localhost; workflow `permissions: {}` |
| — | SEC-13 (accounts / MFA), SEC-21, SEC-22, production settings | Documented actions for the hosting dashboards and the university (cannot be done from the repository) |
