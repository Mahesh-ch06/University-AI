# Remaining risks

SRU Buddy is not "100% secure", and no system is. These are the risks that remain after this hardening, with the
owner type and the next action. The risk ratings assume the deployment settings in `DEPLOYMENT_SECURITY.md` are
applied. Until they are, R-02 is **Critical**.

| ID | Risk | Rating | Why it remains | Next action | Owner |
|---|---|---|---|---|---|
| R-01 | One shared admin key: no per-person accounts, MFA, roles or per-person audit | High | Needs an identity provider decision | Put the admin panel behind university SSO (e.g. Google Workspace / Microsoft Entra) or an access proxy (Cloudflare Access); add roles (viewer / exporter / content admin) | University IT |
| R-02 | Production settings unverified (`APP_ENV`, `APP_DEBUG`, admin key strength, CORS override, proxy hops) | High (Critical if the placeholder key is in use) | No dashboard access | Apply `DEPLOYMENT_SECURITY.md` section 1; rotate `ADMIN_API_KEY` | DevOps |
| R-03 | Admin key may already be exposed (older versions put it in "Open live chat" / "Copy link" URLs) | High | Past links, browser history, logs | Rotate the key now | DevOps |
| R-04 | Prompt injection / hidden-context leaks by paraphrase | Medium | Pattern guards are backstops; model behaviour is probabilistic; no live-model red-team was possible | Red-team the deployed model with the OWASP LLM01 / LLM08 test set; monitor `sru_agent.ai_guard` logs | Engineering |
| R-05 | Session ID is a bearer token in GET query strings (in platform access logs) | Medium | Moving it to a header changes every client call | Accept `X-Session-Id` header and switch the frontend; restrict log access | Engineering |
| R-06 | Name / mobile in `localStorage` on shared computers | Low | The session ID in the same storage already opens the profile; "Forget my details" exists | Mention in the privacy notice; consider expiring the local copy | Engineering / Legal |
| R-07 | Unpinned Python dependencies; chromadb CVEs without a fix | Medium | Lock file must be produced for the production Python version | Generate and use a lock file; keep Chroma embedded / not network-exposed; update chromadb when fixed | Engineering |
| R-08 | Container runs as root; compilers in the final image | Low | A user change can break writes to a mounted disk on Render | Test the non-root user on a Render preview (`DEPLOYMENT_SECURITY.md` section 4) | DevOps |
| R-09 | No approval workflow or provenance record for knowledge-base uploads | Medium | Admin uploads are trusted | Record uploader, approver and source URL per document; review before ingestion | Admissions / Engineering |
| R-10 | Log retention below CERT-In's 180 days (likely, depends on plan) | Medium | Platform plan | Ship logs to a store with 180-day retention (copy in India) | DevOps |
| R-11 | DPDP: no privacy notice, retention schedule, minors' consent approach | High (from about May 2027) | Legal decisions | `DATA_PRIVACY.md` section 4 | Legal / Privacy |
| R-12 | Incident roles not named | Medium | Institutional | Fill `INCIDENT_RESPONSE.md` section 2 | University |
| R-13 | Per-network limits may affect many students behind one NAT | Low | Trade-off with denial of wallet | Tune `AI_IP_DAILY_LIMIT`; watch `rate_limited_ip_*` audit lines | DevOps |
| R-14 | Rate-limit counters are per process without Redis | Low | Deployment choice | Configure `REDIS_URL` (with password and TLS) when running more than one instance | DevOps |
| R-15 | Feedback on live agent answers is not stored (the client sends a browser-made message ID that the database does not know). Functional bug found during the audit, not a security issue | Low | Out of scope | Return the saved message ID in the agent `done` event | Engineering |
| R-16 | `connect-src` still allows any `*.onrender.com` host | Low | The exact production API host must be confirmed | Narrow it once `VITE_API_BASE_URL` is confirmed | DevOps |
| R-17 | Provider terms (Gemini data use / region) for student messages | Medium | Contractual | `DATA_PRIVACY.md` section 4 item 4 | Legal / IT |
