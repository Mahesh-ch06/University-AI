# Security and Authorization Architecture

This document defines the production security standards, defense-in-depth architecture, and threat mitigation controls for **SRU Buddy – SR University AI Companion**.

## Roles & Access Control
- **STUDENT / PROSPECT**: Unauthenticated public visitors or prospective applicants identified via transient `session_id`. Can access public university knowledge, calculate fees, submit inquiries, and access exclusively their own conversation history.
- **ADMIN**: Authorized university admissions and IT staff. Authenticated via `X-Admin-Key` header with timing-safe comparison (`secrets.compare_digest`) and brute-force IP rate limiting. Can view student leads, conversation transcripts, ingest handbook documents, and monitor telemetry.

---

## OWASP Top 10 & API Security Compliance

### 1. Broken Object Level Authorization (IDOR) - OWASP API 1
- **Conversation Isolation**: All conversation endpoints (`/api/v1/conversations/{id}` and `/api/v1/shared/{id}`) strictly require `session_id` ownership verification. A user cannot read, update, or delete another student's conversation records.
- **Admin Access**: Administrative access to arbitrary conversations requires `X-Admin-Key` authentication via `/api/v1/admin/conversations/{id}`.

### 2. Broken Authentication & Brute-Force Protection - OWASP API 2
- **Admin Authentication**: All `/api/v1/admin/*` endpoints require the `X-Admin-Key` header.
- **Timing-Safe Verification**: Key verification uses `secrets.compare_digest` to prevent timing analysis attacks.
- **Brute-Force Rate Limiting**: Repeated failed admin authentication attempts are tracked per client IP using a sliding window in `deps.py`. Exceeding 5 failed attempts per minute triggers a temporary `HTTP 429 Too Many Requests` lockout.

### 3. Injection Prevention - OWASP Top 10 A03
- **SQL / NoSQL Injection**: All database queries are executed using SQLAlchemy parameterized queries (`select().where(...)`) with strict typing. Raw string concatenation in SQL queries is strictly prohibited.
- **DOM-based XSS in Widget (`widget.js`)**: All DOM construction in `widget.js` uses standard DOM APIs (`document.createElement`, `textContent`) avoiding `innerHTML`. Parameters (`data-color`, `data-app-url`) are strictly validated against hex color regex and URL scheme validators.
- **Iframe Sandboxing**: Embedded iframes enforce `sandbox="allow-scripts allow-same-origin allow-forms allow-popups"` to prevent top-level navigation and unpermitted DOM access.
- **Cross-Window Messaging**: `postMessage` targets are strictly constrained to the validated host origin (`base`) rather than wildcard `*`.

### 4. LLM Security & Guardrails - OWASP LLM01 / LLM06
- **Prompt Injection & Jailbreak Pre-screening**: The conversational agent stream (`/api/v1/agent/stream`) intercepts prompts before execution using `check_adversarial_guardrail` in `intents.py`.
- **Blocked Patterns**: Adversarial instructions ("ignore previous instructions", "act as DAN", "developer mode", system prompt disclosure requests, exploit/malware generation) receive an immediate deterministic refusal without invoking the LLM.
- **System Prompt Secrecy**: System prompts, tool implementation details, and internal credentials are never reflected to users (Rule 14).

### 5. Security Misconfiguration & HTTP Headers - OWASP Top 10 A05
- **Content-Security-Policy (CSP)**:
  - `default-src 'self'`
  - `script-src 'self'`
  - `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`
  - `font-src 'self' https://fonts.gstatic.com data:`
  - `img-src 'self' data: https: blob:`
  - `connect-src 'self' https://*.onrender.com https://*.vercel.app https://generativelanguage.googleapis.com`
  - `frame-ancestors 'self' https://*.vercel.app https://sru.edu.in https://*.sru.edu.in http://localhost:* http://127.0.0.1:*`
- **Transport Security**: HSTS enabled with `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`.
- **CORS Configuration**: Default whitelist allows `localhost`, `vercel.app`, and `sru.edu.in` (`https://(www\.)?sru\.edu\.in`). Credentials are disabled (`allow_credentials=False`).

### 6. Document Ingestion & File Upload Security
- **File Type Restrictions**: Ingestion endpoint restricts uploads to verified extensions: `.pdf`, `.txt`, `.md`, `.docx`.
- **Size Limit**: Maximum file upload size is strictly capped at 50MB.
- **Path Traversal Protection**: Uploaded files are stored using generated UUID4 filenames (`{uuid}{ext}`) rather than raw client filenames.

---

## Secret Management & Rotation Policy
1. **Never Commit Secrets**: Environment variables (`.env`, credentials) are strictly ignored in `.gitignore`.
2. **Historical Commits Advisory**: Any secrets that were historically present in git commit `51f8a99` must be rotated immediately in hosting provider configuration dashboards (Render, Neon, Vercel).
3. **Environment Isolation**: Production environments must provide independent, high-entropy secrets for `ADMIN_API_KEY`, `DATABASE_URL`, and `GEMINI_API_KEYS`.

