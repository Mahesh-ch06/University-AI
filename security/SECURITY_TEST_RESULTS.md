# Security test results

Run on 23 November 2026, branch `claude/security-hardening`, in a cloud container. The container has no
PostgreSQL, Redis, Gemini key, or access to Render / Vercel / Neon.

**Statuses:**
- **PASS:** verified by a test that ran here.
- **FAIL:** verified as not met.
- **PARTIAL:** part verified, part open.
- **BLOCKED:** needs dashboard / provider / institutional access.
- **NOT TESTED:** no test was possible.

Nothing is marked PASS on the strength of code alone.

## 1. Test suites

| Suite | Result | Command |
|---|---|---|
| `backend/tests/test_security_api.py` (new) | 34 passed | `cd backend && python -m pytest -q tests/test_security_api.py` |
| `backend/tests/test_security_ai.py` (new) | 27 passed | `... tests/test_security_ai.py` |
| `backend/tests/test_security_config.py` (new) | 12 passed | `... tests/test_security_config.py` |
| Full backend suite, before any change | 823 passed, 9 failed, 8 skipped | `python -m pytest -q` |
| Full backend suite, after all changes | **896 passed, 9 failed, 8 skipped** | same |
| `security/tests/frontend_security_ui.cjs` (Playwright, Chromium, Vite dev server) | 7 / 7 PASS. The export checks **fail on the previous code** (injected `<img>` and `<script>` were created), proving the test detects the bug | see file header |
| Frontend `npm run build`, `npm test` (3,477 fee checks, 11 effect checks) | Pass | |
| Frontend `npm run lint` | Same 4 warnings as before the change (none new) | |

**About the 9 failures.** They are the same 9 tests before and after:
- `test_api_endpoints` (2): need PostgreSQL;
- `test_context_and_course_selection` (3), `test_placement_guarantee`, `test_response_length_and_scannability`
  (career chips), `test_round3_features`, `test_v331_intelligence_and_context`: older follow-up-chip expectations
  already failing on v4.5.0.

None is related to security.

**Existing tests changed for the new rules** (not deleted):
- `test_pending_task_endpoints`, `test_round3_speed`, `test_exemplar_service`: session IDs shorter than 16
  characters, and feedback ownership;
- `test_round2_knowledge_and_profile`: the full mobile is no longer in the prompt;
- `test_response_length_and_scannability`: the new prompt version.

## 2. Abuse cases (`THREAT_MODEL.md` section 6)

| # | Case | Result | Evidence |
|---|---|---|---|
| 1 | Forged `X-Forwarded-For` rotation vs admin failed-key limit | PASS | `test_admin_brute_force_limit_survives_forged_ip_rotation`: 5 x 403, then 429 although the first XFF entry changed every time |
| 2 | `?admin_key=` grants nothing, no 500 | PASS | `test_admin_key_in_query_string_grants_nothing` (404, `is_admin=False`); wrong header gives 403 |
| 3 | Production refuses the placeholder key, hides `/docs` | PASS | `test_placeholder_admin_key_refused_in_production`, `..._over_http_on_render` (503), `test_docs_hidden_in_production_build`, `test_production_on_render_even_when_debug_was_forgotten` |
| 4 | Session rotation from one network is limited | PASS | `test_session_rotation_cannot_bypass_the_per_ip_limit` (8 sessions, limit 5, turns 6-8 refused); daily budget and per-IP daily tests; legacy `/chat` 429 |
| 5 | Weak session IDs rejected | PASS | `test_weak_or_malformed_session_ids_are_refused` (5 forms x 3 endpoints, 422) |
| 6 | Feedback on another student's message | PASS | `test_feedback_on_someone_elses_message_is_refused` (nothing stored, exemplar not pruned); route 404 |
| 7 | Oversized body | PASS | 413 before parsing; chunked body counted; upload path has its own limit |
| 8 | Poisoned passage | PASS | 5 injection forms dropped (title logged, not content); ordinary text kept; tool and handbook paths; provenance kept |
| 9 | Full mobile not in the prompt; callback still works | PASS | prompt shows "ending 3210"; `ON_FILE` / empty / masked use the saved number; a new number wins; invalid numbers rejected |
| 10 | Leaking answer replaced | PASS | 6 forms (Google key, DB URL, private key, GitHub token, 2 prompt markers) replaced; normal fee / contact answers unchanged |
| 11 | Exported chat with HTML | PASS | Browser test: no element created, text shown literally, bold kept |
| 12 | Message from a non-parent window | PASS | Browser test: self-post ignored; the embedding parent still opens the form |

## 3. Scans

| Scan | Before | After |
|---|---|---|
| Secrets in tracked files and full git history | None (placeholders only) | None. Now enforced by `test_no_secrets_in_tracked_files` |
| `npm audit` | 2 high (vite, source-map-js; dev / build time) | **0** |
| `pip-audit -r requirements.txt` | chromadb 1.5.9: 4 CVEs, no fixed version | Unchanged (no fix exists). Embedded mode does not expose the vulnerable server API; dev Chroma port now bound to localhost |

## 4. Acceptance criteria

| Area | Criterion | Status | Evidence / reason |
|---|---|---|---|
| Inventory | Attack surface and threat model before fixes | PASS | `SECURITY_AUDIT.md`, `THREAT_MODEL.md` (commit `cb14ea0`, before code changes) |
| Frontend | No XSS sinks; export escaped | PASS | browser test; config test (no `dangerouslySetInnerHTML`) |
| Frontend | CSP / headers tightened | PARTIAL | `vercel.json` tested statically; live headers on Vercel NOT VERIFIED (BLOCKED); `connect-src` still allows `*.onrender.com` until the API host is confirmed |
| Frontend | postMessage checks | PASS | browser test |
| Frontend | Browser storage minimised | PARTIAL | admin key out of URLs (PASS); name / mobile copy in `localStorage` accepted (R-06) |
| Backend | Object-level authorization (IDOR) | PASS | owner filters (existing) + feedback ownership (new tests) |
| Backend | Admin authentication hardening | PARTIAL | placeholder lockout, trusted-IP lockout, audit log: PASS. Individual accounts / MFA / RBAC: FAIL (R-01) |
| Backend | Rate limits incl. per IP / per session / AI budget | PASS (code) | tests; production proxy hop count NOT VERIFIED |
| Backend | Input / size validation | PASS | 413 and 422 tests |
| Backend | CORS / CSRF | PASS (code) / NOT VERIFIED (Render env) | CORS tests; no cookies |
| Backend | Injection / SSRF / path traversal | PASS | code review (section 3 of the audit); upload stored under a UUID name |
| Data | PII to the model minimised | PASS | prompt and tool tests |
| Data | PII out of logs | PASS (code) | log lines changed; existing platform logs not reviewed (BLOCKED) |
| Data | DPDP readiness | PARTIAL / BLOCKED | `DATA_PRIVACY.md`: notice, retention, minors, provider terms need the university |
| AI | OWASP LLM Top 10 2026 controls | PARTIAL | `AI_SECURITY.md`; live-model red-team NOT TESTED (no key) |
| Auth / admin | Strong production key, rotation | BLOCKED | Render dashboard (`DEPLOYMENT_SECURITY.md`) |
| Infrastructure | Production env settings verified | BLOCKED | no Render / Vercel / Neon access |
| Infrastructure | Container non-root | FAIL (documented) | not changed: needs a Render preview test (R-08) |
| Dependencies | Known-vulnerable packages addressed | PARTIAL | npm 0; chromadb has no fix; Python unpinned (R-07) |
| Logging / IR | Audit events, runbook | PARTIAL | `security.audit` logger + `INCIDENT_RESPONSE.md`; 180-day retention and owners BLOCKED |
| Tests | Automated security tests | PASS | 73 backend + 7 browser |
| Change mgmt | Small commits on a branch, PR, no deploy | PASS | 6 commits on `claude/security-hardening`; nothing merged or deployed |
