# AI security (OWASP Top 10 for LLM Applications 2026)

Reference: OWASP GenAI Security Project, *Top 10 for LLM Applications 2026* (published 4 August 2026). The list
covers the model as a component of an application; agent-specific risks are in OWASP's separate Agentic Top 10.

## How the model is used

- **Provider:** Gemini through `google-genai` (`sru_agent/agent.py`), behind the provider interface. The legacy
  `/chat` route uses `app/providers/*`.
- **Fees and eligibility are deterministic:** figures come from `fees.py` / `eligibility.py` and the official
  data file. The model explains them; it never produces fee figures on its own.
- **Tools:** a fixed allowlist in `tools.py`. Write tools (save / update / cancel a callback or visit request,
  remember details) act only on the caller's own session.

## Controls by risk

| Risk | Status | Controls in code | Tests |
|---|---|---|---|
| **LLM01 Prompt Injection** | PARTIAL | Direct: regex guard before the model (`intents.check_adversarial_guardrail`). Indirect: `ai_guard.screen_passages` drops knowledge / handbook passages that carry instructions; passages are labelled "reference data, not instructions"; prompt rule that tool results and documents are data (prompt `2026-11-23.1`) | `test_security_ai.py`: 5 injection forms dropped, ordinary text kept, tool and handbook paths |
| **LLM02 Sensitive Information Disclosure** | PARTIAL | Mobile number masked in the prompt (last 4 digits) and in tool results; tools resolve `ON_FILE` server-side; "what is my number" answered without the model; hidden profile keys; tools cannot read other sessions | prompt has no full number; `ON_FILE` / masked / new-number cases; remember tool masks |
| **LLM03 Excessive Agency** | PASS (code) | Tool allowlist (`unknown_tool`); lead tools need `consent=true` and a valid name and mobile; tools bound to the caller's session; no tool reads other students' data, exports or deletes; max 4 tool rounds | unknown tool refused; consent required |
| **LLM04 Supply Chain** | PARTIAL | npm audit clean; Dependabot; pip-audit shows chromadb server-API CVEs (embedded mode in the default configuration does not expose that API). Python dependencies unpinned (remaining risk R-07) | `SECURITY_TEST_RESULTS.md` section 3 |
| **LLM05 Data and Model Poisoning** | PARTIAL | Knowledge upload is admin-only, with an extension allowlist and size limit; poisoned passages screened at retrieval; feedback cannot prune exemplars of other students; exemplar promotion is admin-only | feedback ownership tests; passage screening |
| **LLM06 Unbounded Consumption** | PASS (code) / NOT VERIFIED (provider) | Per-session, per-network (minute / day) and server daily budget; message 1,000 chars; body 256 KB; 4 tool rounds; 900 output tokens; 25 s call timeout; 6 concurrent calls per process. Provider-side quota / billing alert: dashboard action | session rotation limited; daily budget; per-IP daily |
| **LLM07 Misinformation** | Existing controls | Deterministic fee / eligibility engines; "cannot verify" behaviour; required disclaimer "May contain inaccuracies. Verify with official university sources." Unchanged by this work | existing suites (conversation logic, factuality) |
| **LLM08 Hidden Context Exposure** | PARTIAL | Input guard for prompt-extraction requests; `ai_guard.guard_reply` replaces answers containing system-prompt lines or internal names; live tokens stop when the text matches | 6 leak forms replaced; normal answers unchanged |
| **LLM09 Vector and Embedding Weaknesses** | PARTIAL | Provenance on passages (document type, page, dates, document id); screening before use; Chroma embedded (not network-exposed) by default | provenance test |
| **LLM10 Improper Output Handling** | PASS (code) | React renders text (no `dangerouslySetInnerHTML`); export window escapes; CSP `script-src 'self'`; output guard for secret shapes | browser test of the export; config test for raw HTML sinks |

PASS (code) means the control is implemented and tested in code. It does not mean the risk is gone: no model
behaviour can be guaranteed.

## What these controls do not cover

- **Paraphrased leaks:** the regex screens and leak markers catch known phrasings. A model paraphrasing its
  instructions, or a cleverly worded injection, can get through. The prompt rules are the main defence there,
  and they are probabilistic.
- **Streamed text:** the guard replaces the final answer. The live stream stops when a marker appears, but text
  before the marker has already been shown.
- **Trust in uploaded documents:** admin uploads are trusted as university sources. A wrong document gives wrong
  answers; screening only removes instructions aimed at the model.
- **Live model runs:** no live Gemini call was made in this audit (no API key here). Model compliance with the new
  prompt rule is NOT TESTED; red-team the deployed model before relying on it (see `SECURITY_REMAINING_RISKS.md`).

## Operating rules

1. Change the system prompt only in `sru_agent/prompt.py` and bump `PROMPT_VERSION`.
2. Add a tool only with a session-bound context, typed parameters, and a consent step for anything that contacts
   or stores data about a person.
3. Upload only official, approved documents to the knowledge base, and record who approved them (see
   `SECURITY_REMAINING_RISKS.md` R-09).
4. Watch the `sru_agent.ai_guard` and `security.audit` loggers. Dropped passages and replaced answers are signals of
   attempted abuse or a poisoned document.
