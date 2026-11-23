# Data privacy

**Not legal advice.** This maps what the code does to the Digital Personal Data Protection Act, 2023 (DPDP Act)
and the DPDP Rules, 2025. Compliance must be confirmed by SR University's authorised legal / privacy team. Every
legal item below is **NOT VERIFIED** until they do.

## 1. Commencement (checked 23 November 2026)

The DPDP Rules, 2025 were notified in mid-November 2025. Secondary sources differ by one day (13 or 14 November);
confirm against the Gazette.

| Phase | Provisions | Date |
|---|---|---|
| On notification | Rules 1, 2, 17-21 (definitions, Data Protection Board) | November 2025 |
| +12 months | Rule 4 (consent managers) | about 13-14 November 2026 |
| +18 months | Rules 3, 5-16, 22, 23 (notice, security safeguards, breach intimation, retention, rights, children's data) | about 13-14 May 2027 |

The core duties therefore apply from about **May 2027**. The DPDP Act's definitions already apply, and the IT Act
2000 / SPDI Rules 2011 continue in the meantime.

## 2. Personal data inventory

| Data | Where stored | Purpose | Who can read it |
|---|---|---|---|
| Name, mobile number | Agent profile (PostgreSQL `agent profile` rows; Redis cache), leads table, browser `localStorage` (`sru_student_lead`) | Callback / campus-visit requests; personalisation | The browser holding the session ID; staff with the admin key |
| Marks, board, stream, entrance rank | Agent profile (conversation-scoped `academic_conv`, `saved_academic`) | Eligibility and scholarship estimates | Same |
| Chat transcripts | `conversations` / `messages` tables | Continuity; staff review | Same |
| Session ID | Browser `localStorage`; database rows; platform access logs (query strings) | Pseudonymous identifier (also the access key) | Browser; platform log readers |
| IP address | Not stored by the application; hashed in rate-limit counter keys and audit log lines | Abuse prevention | Platform logs (Render / Vercel) hold raw IPs: NOT VERIFIED |
| Data sent to Gemini | Messages, recent history, profile **without** the full mobile number, passages | Answers | Google, under its API terms: NOT VERIFIED (data residency / retention) |

Students are mostly 12th-standard applicants. **Many are under 18** (children under the DPDP Act: verifiable
parental consent, no tracking or targeted advertising). The application has no age or guardian-consent step.
This is a legal decision for the university (R-11).

## 3. What the code does now

| DPDP theme | Implemented | Status |
|---|---|---|
| Data minimisation | Full mobile not sent to the model; not echoed by tools; not written to application logs; API keys and session IDs truncated in logs | PASS (code) |
| Purpose-limited contact | Callback / visit requests need explicit consent in the chat (`consent=true`); "don't call me" cancels; the lead form is separate | PASS (code), wording NOT VERIFIED by legal |
| Erasure | "Forget my details" (`DELETE /api/v1/agent/profile`) clears the profile; chats can be deleted by the student. Leads stay with the Admissions Office | PARTIAL: no erasure for leads; no request workflow |
| Access / correction | Settings > My details shows and edits name, mobile, programme | PARTIAL |
| Security safeguards | This hardening (access control, limits, logging hygiene, encryption in transit via HTTPS / HSTS) | PARTIAL: encryption at rest and backups are provider settings, NOT VERIFIED |
| Notice | No privacy notice text in the app | FAIL / BLOCKED (legal text needed) |
| Retention | No retention schedule; data kept indefinitely | FAIL / BLOCKED (policy decision) |
| Breach intimation | Procedure in `INCIDENT_RESPONSE.md` | PARTIAL (needs named owners) |
| Children's data | No age check or parental consent | BLOCKED (legal decision) |

## 4. Actions for the university (cannot be done in code alone)

1. Approve a **privacy notice** (what is collected, why, retention, rights, grievance officer contact), and show it
   in the chat before name / mobile are collected. The UI slot can be added once the text exists.
2. Decide **retention periods**, e.g. chats N days, leads M months after the admission cycle. Then implement a
   scheduled deletion job (needs a migration-free script plus a schedule).
3. Decide the approach for **applicants under 18** (parental consent wording or age gate).
4. Confirm Google Gemini API **data-use, retention and region** terms for student messages. Use a paid tier if the
   free tier allows prompts to be used for product improvement.
5. Confirm Neon / Render / Vercel **regions, encryption at rest and backup retention**. CERT-In requires logs to
   be retained (a copy in India), see `INCIDENT_RESPONSE.md`.
6. Name a **grievance / data protection contact** and add it to the notice.

## 5. Browser storage

`localStorage` keeps the session ID and, for convenience, the name and mobile number (`sru_student_lead`).
The server copy is authoritative; "Forget my details" clears both. On shared computers, anyone using the same
browser profile can see them. Removing the local copy would not help on its own, because the session ID in the
same storage opens the server profile. Mitigation: privacy notice advice and the "Forget my details" control.
Accepted as a residual risk (R-06).
