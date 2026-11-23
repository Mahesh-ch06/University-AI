# API security

How each group of endpoints is protected after the hardening (v4.7.0). Contract details are in
`docs/12-api-specification.md`.

## Identity model

| Caller | Credential | Where it travels | Strength |
|---|---|---|---|
| Student / parent | `session_id`: a UUID made by the browser (`crypto.randomUUID`) | Query string (GET / DELETE) or JSON body | 122 random bits. The server accepts 16-64 URL-safe characters only. Anyone holding it can read that browser's profile and chats (bearer token) |
| Staff | `ADMIN_API_KEY` | `X-Admin-Key` header only | As strong as the configured key. A warning is logged if it is under 24 characters. Shared by all staff |

## Endpoint matrix

| Endpoints | Authorization | Abuse limits | Input validation |
|---|---|---|---|
| `POST /api/v1/agent/stream` | Session | 20/min/session; 40/min and 600/day per network; 20,000/day server | Pydantic: message 1-1,000 chars, session pattern, channel `^[a-z]+$`, typed form (Literal enums, numeric ranges) |
| `POST /api/v1/chat`, `/chat/stream` | Session | same as above (429) | message 1-4,000 chars, session pattern |
| `GET/PUT/DELETE /api/v1/agent/profile` | Session | none (no AI cost) | session pattern; name 80, phone 20 (validated as Indian mobile), programme 120 |
| `GET /api/v1/agent/recovery-context`, `POST /reset-session` | Session | none | session pattern |
| `GET /api/v1/conversations`, `GET/DELETE /conversations/{id}`, `GET /shared/{id}` | Session (owner filter in SQL); staff via `X-Admin-Key` on `GET /conversations/{id}` | admin failed-key limit applies to the header | UUID path, session pattern |
| `POST /api/v1/feedback` | Session **and** ownership of the conversation and message | none | rating -1..1, comment 1,000 |
| `/api/v1/memory/*` | Session (owner filter) | none | session pattern; memory key 64, value 255, consent required |
| `POST /api/v1/leads` | Public | 30/min per network (trusted IP) | `LeadCreate` schema |
| `POST /api/v1/agent/calculate`, `GET /programs`, `GET /fee-config`, `POST /api/v1/finance/estimate` | Public, read-only data | none (deterministic, no AI) | typed ranges |
| `/api/v1/admin/*` | `X-Admin-Key` (constant-time; placeholder refused in production) | 5 failed keys/min per network, then 429 | per route |
| `GET /`, `/live`, `/health`, `/ready` | Public | none | — |
| `/docs`, `/redoc`, `/openapi.json` | Development machine only | — | — |

## Cross-cutting controls

| Control | Implementation |
|---|---|
| Body size | `BodySizeLimitMiddleware`: 256 KB (API), 50 MB (`/api/v1/admin/documents`). Over the limit: 413 before parsing, including chunked bodies |
| CORS | Configured `CORS_ORIGINS` plus `CORS_ORIGIN_REGEX` (default: localhost for development, `university-ai-companion[-*].vercel.app`, `*.sru.edu.in`). `allow_credentials=False`, so no cookies or HTTP auth ride on cross-site requests |
| CSRF | Not applicable: no cookies or ambient credentials. Every credential is sent explicitly by the app |
| Client IP | `security.client_ip`: trusted header, else the X-Forwarded-For entry `TRUSTED_PROXY_HOPS` from the right, else the socket. Rate-limit keys use a SHA-256 prefix of the IP |
| Response headers (API) | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, HSTS in production |
| Errors | Global handler returns a generic message; production messages never name services, hosts or ports |
| Audit | `security.audit` logger (logger name `security.audit`): admin requests, failed / locked admin keys, AI limit refusals. Fields: action, outcome, method, path, hashed IP |
| Injection | SQLAlchemy ORM only; no shell, `eval`, unsafe YAML or pickle; outbound URLs only from configuration (no SSRF) |
| Uploads | Admin only; extension allowlist (`.pdf .txt .md .docx`); stored under a random UUID name (no path traversal); size limit before reading |

## Known limits

- The session ID is a bearer token in the query string of GET requests, so it appears in platform access logs.
  Moving it to a header (`X-Session-Id`) is recommended (`SECURITY_REMAINING_RISKS.md` R-05).
- Per-network limits can affect many students behind one NAT (school or college lab). The defaults are generous
  and configurable.
- Counters fall back to process memory without Redis: with several server processes and no Redis, each process
  counts separately.
