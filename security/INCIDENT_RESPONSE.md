# Incident response

A practical runbook for SRU Buddy. **Owners are TBD.** The university must name them (R-12). Legal reporting
duties must be confirmed by the university's legal team.

## 1. Reporting duties (to be confirmed by legal)

| Regime | Duty | Timeline |
|---|---|---|
| CERT-In Directions, 28 April 2022 (in force 27 June 2022) | Report specified cyber incidents to CERT-In (incident@cert-in.org.in). Keep ICT system logs for a rolling **180 days**, with a copy in India. Synchronise clocks to NTP sources specified by CERT-In | Within **6 hours** of noticing. Partial information is acceptable at first |
| DPDP Act 2023 / DPDP Rules 2025, Rule 7 (commences about May 2027) | Intimate a personal data breach to the Data Protection Board and to each affected person | Without delay. A detailed report to the Board within 72 hours (per the Rules; confirm) |

## 2. Roles (fill in)

| Role | Person | Contact |
|---|---|---|
| Incident lead | TBD | |
| Technical lead (Render / Vercel / database) | TBD | |
| Privacy / legal | TBD | |
| Communications (students, parents) | TBD | |

## 3. Severity

| Level | Examples |
|---|---|
| SEV-1 | Admin key or database credentials exposed; student PII exfiltrated; the knowledge base poisoned with false fee / eligibility facts and served to students |
| SEV-2 | Gemini key leaked; sustained denial of wallet; XSS on the production site |
| SEV-3 | Single-session abuse; prompt-injection attempt blocked by guards (log signal only) |

## 4. Playbooks

### 4.1 Admin key exposed (link shared, screenshot, log)

1. Render > service > Environment: set a new `ADMIN_API_KEY`. Generate it with
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Redeploy.
2. Tell staff to sign in to the admin panel again (the old key in `sessionStorage` stops working).
3. Review `security.audit` log lines (`admin_request`) for the exposure window: which paths were called, from which
   hashed IPs. Lead exports (`/admin/leads/export`) or conversation exports imply a personal-data breach (go to 4.3).

### 4.2 Gemini / OpenRouter API key leaked

1. Revoke the key in Google AI Studio / Google Cloud console (or OpenRouter), and create a new one.
2. Update `GEMINI_API_KEYS` on Render; redeploy.
3. Check billing / quota usage for the window.

### 4.3 Personal data breach (leads, profiles, transcripts)

1. Contain: rotate the admin key and database credentials (Neon / Render dashboard). Block the source if it is
   known.
2. Preserve evidence: export Render and Vercel logs for the window before they roll off.
3. Assess: what data, how many students, minors involved.
4. Report: CERT-In within 6 hours if it is a reportable incident. DPDP intimation (once in force) as advised by
   legal.
5. Notify affected students / parents as advised by legal.

### 4.4 Knowledge base poisoned / wrong answers

1. Admin > Documents: delete the document. Re-check answers for the affected topic.
2. Look at `sru_agent.ai_guard` warnings ("dropped a ... passage") for the document title.
3. Correct the official data file only through the normal reviewed change (it is the source for fees and
   eligibility).

### 4.5 Denial of wallet / abuse traffic

1. Check `security.audit` lines with `rate_limited_ip_*` / `daily_budget_reached`.
2. Lower `AI_IP_RATE_LIMIT_PER_MIN` / `AI_DAILY_TURN_BUDGET` on Render if needed, and set a provider quota cap.
3. If one network is abusive, block it at the platform level (Render / Cloudflare rules), if available.

## 5. Logging that exists today

| Logger | Content | Retention |
|---|---|---|
| `security.audit` | Admin requests, failed / locked admin keys, AI limit refusals (hashed IP, path, outcome) | Render log retention (plan-dependent, NOT VERIFIED). Likely less than 180 days: ship logs to a store kept 180 days in India (R-10) |
| `sru_agent.ai_guard` | Dropped passages (title), replaced answers (reason) | as above |
| Application logs | Errors, tool status, lead ids (no names / mobiles) | as above |
| Database | Leads, conversations, feedback, agent runs | Until deleted (no retention policy yet) |
