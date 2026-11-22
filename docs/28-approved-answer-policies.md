# Approved Answer Policies & Semantic Response Architecture

## 1. Overview & Architectural Goals

The **Semantic Response Policy System** replaces brittle regex/keyword intent matching with a structured, versioned, policy-driven response architecture for SRU Buddy.

### Why Semantic Response Policies?
Prior to this architecture, conversational intents and answers relied on:
- Brittle regex patterns prone to substring collisions (e.g. matching `"ac"` inside `"actually"`, or `"where is sru"` with `"what is sru"`).
- Static text strings scattered inside code files with duplicated or stale university statistics.
- Strict either/or routing that lacked confidence scoring and dynamic RAG fallback.

The Semantic Response Architecture introduces:
1. **Semantic Routing (`semantic_router.py`)**: Multi-turn context-aware routing combining colloquial normalizations (Telugu-English/Hinglish), interrogative pronoun alignment, content-word Jaccard, and F1 token overlap.
2. **Approved Answer Policies (`policy_models.py`, `approved_policies.json`)**: Machine-readable policies with versioning, required key facts, prohibited claims, response modes (`fixed`, `guided`, `rag`), evidence links, and approval states.
3. **Versioned Knowledge Store (`verified_facts.json`, `fact_service.py`)**: University facts isolated from prompts, with verified academic years, valid date ranges, and official citations.
4. **Confidence-Aware RAG Fallback**: Automatic threshold-based fallback ($< 0.52$) to standard RAG pipeline when no approved policy reliably matches.
5. **State Preservation**: Strict preservation of admission intake context (`fee_intake`, `current_intent`, `paused_intent`, `admission_stage`, `collected_data`, `pending_question`) across interruptions and resume signals.
6. **Telemetry & Observability (`observability.py`)**: Granular per-turn telemetry recording detected intent, policy ID, policy version, confidence score, evidence IDs, fallback decisions, and latencies.

---

## 2. Component Architecture

```
User Query
    │
    ▼
┌──────────────────────────────────────────────┐
│  SemanticRouter (confidence_threshold=0.52)   │
│  - Telugu-English colloquial normalization   │
│  - Context awareness (admission in progress) │
│  - Content word overlap + interrogative match│
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
[Confidence >= 0.52]         [Confidence < 0.52]
Approved Policy Match        Fallback Decision
         │                           │
         ▼                           ▼
┌──────────────────────┐    ┌──────────────────────┐
│  PolicyEngine        │    │ Standard RAG         │
│  Mode: FIXED         │    │ Vector Search +      │
│  Mode: GUIDED        │    │ Handbook Retrieval   │
│  Inject VerifiedFacts│    │ (Knowledge Base)     │
└──────────┬───────────┘    └──────────┬───────────┘
           │                           │
           └─────────────┬─────────────┘
                         ▼
        ┌──────────────────────────────────┐
        │ Observability & Telemetry Store  │
        │ - policy_id, version, confidence │
        │ - evidence_ids, latency, fallback│
        └──────────────────────────────────┘
```

---

## 3. Approved Answer Policy Schema

Each policy is defined in JSON and validated with Pydantic (`ApprovedAnswerPolicy`):

```json
{
  "policy_id": "policy.why_choose_sru",
  "intent_id": "WHY_CHOOSE_SRU",
  "description": "Questions asking why to choose SRU, what makes SRU special, or comparisons with other colleges.",
  "response_mode": "guided",
  "required_points": [
    "Times Higher Education (THE) 2027 ranks SRU #6 in India in Research Quality and #7 among private universities nationwide",
    "First private university in Telugu States (Telangana & Andhra Pradesh) with ICAR accreditation for Agricultural Sciences",
    "NIRF 2025 #91 in Engineering (Top 100 for 4 consecutive years) and Tier-1 NBA accreditation",
    "100% placement assistance with 6–6.5 LPA average package and peak packages up to ₹51 LPA (Microsoft)",
    "171+ startups incubated at DST-supported SRiX incubator with ₹76+ Cr funding"
  ],
  "prohibited_claims": [
    "Never start with a negative, concession, or blunt 'No' (e.g. 'No, SRU is not #1' or 'SR University is not ranked #1 overall')",
    "Never criticize or insult other universities or colleges",
    "Never guarantee 100% placement offers or confirm seats unconditionally"
  ],
  "preferred_tone": "Warm, encouraging, confident senior championing SR University's verified national leadership",
  "preferred_length": "40-80 words (or 80-120 words for detailed comparisons)",
  "evidence_requirements": [
    "fact.rankings.the_2027_research",
    "fact.rankings.icar_accreditation",
    "fact.rankings.nirf_engineering_2025",
    "fact.placements.packages_and_averages",
    "fact.infrastructure.srix_incubator"
  ],
  "semantic_anchors": [
    "why should i choose sru",
    "why should i choose sru over other colleges",
    "why sru",
    "what makes sru different",
    "is sru actually worth joining",
    "bro sru lo join avvadam worth ah kaada",
    "what makes sru stand out as a top engineering destination",
    "give me compelling reasons to consider sru for b tech"
  ],
  "suggested_chips": ["B.Tech CSE fees", "Placements at SRU", "Campus Life & Clubs", "Plan a campus visit"],
  "version": "1.0.0",
  "approval_status": "approved"
}
```

### Policy Response Modes
- **`fixed`**: Exact verified wording used only when legal, regulatory, or policy constraints prohibit alteration (e.g., curfew policies, future fee structure guarantees).
- **`guided`**: Dynamic, natural language responses generated with mandatory inclusion of verified factual points and strict adherence to prohibited claim guardrails (Rule 22).
- **`rag`**: Information retrieved dynamically from the university handbook and vector database.

---

## 4. Versioned University Knowledge Base

University facts are decoupled from prompt strings and stored in `backend/app/sru_agent/knowledge_base/verified_facts.json`:

```json
{
  "fact_id": "fact.rankings.the_2027_research",
  "category": "rankings",
  "statement": "Times Higher Education (THE) World University Rankings 2027 ranks SR University #6 in India in Research Quality and #7 among private universities nationwide.",
  "academic_year": "2027-28",
  "source": "Times Higher Education (THE) World University Rankings 2027",
  "verification_status": "verified",
  "verified_by": "Office of the Registrar / Institutional Research",
  "valid_from": "2026-06-01",
  "valid_until": "2027-05-31",
  "notes": "Verified national milestone. Always highlight Research Quality ranking."
}
```

The `FactService` provides:
- `get_fact(fact_id)`
- `get_facts_by_category(category)`
- `format_evidence_markdown(fact_ids)`: Injects verified citations directly into LLM prompt contexts.

---

## 5. Observability & Telemetry

Every turn instrumented with `PolicyTurnTelemetry`:
- `detected_intent`: Semantic intent ID detected.
- `selected_policy_id`: Matched policy ID (or `None` for fallback).
- `policy_version`: Version of matched policy (e.g. `1.0.0`).
- `response_mode`: `fixed`, `guided`, or `rag`.
- `retrieved_evidence_ids`: List of verified fact IDs injected.
- `routing_confidence`: Similarity score ($0.0 - 1.0$).
- `fallback_decision`: Boolean flag indicating if fallback was taken.
- `fallback_reason`: Description of fallback reason if triggered.
- `routing_latency_ms`: Time taken by semantic router ($< 2$ ms).
- `total_latency_ms`: Total agent turn execution time.

Recent telemetry can be inspected via `observability.get_recent_telemetry()`.

---

## 6. Administrator Guide: Policy Lifecycle Management

Administrators can manage policies via `app.sru_agent.policy_service`:

### Adding a New Policy
1. Define the policy JSON in `backend/app/sru_agent/policies/approved_policies.json` or call:
   ```python
   from app.sru_agent import policy_service
   from app.sru_agent.policy_models import ApprovedAnswerPolicy, ResponseMode, ApprovalStatus

   policy = ApprovedAnswerPolicy(
       policy_id="policy.sports_facilities",
       intent_id="SPORTS_FACILITIES",
       description="Inquiries regarding indoor and outdoor sports grounds",
       response_mode=ResponseMode.GUIDED,
       required_points=["Outdoor cricket ground with turf pitch", "Indoor badminton and basketball courts"],
       prohibited_claims=["Do not promise free personal coaching"],
       semantic_anchors=["what sports facilities are available", "are there sports grounds at sru"],
       evidence_requirements=["fact.infrastructure.sports_complex"],
       suggested_chips=["Hostel facilities", "Campus tour", "Student clubs"],
       version="1.0.0",
       approval_status=ApprovalStatus.DRAFT,
   )
   policy_service.register_policy(policy)
   ```

### Reviewing and Approving a Policy
Policies start in `ApprovalStatus.DRAFT`. To activate for production routing:
```python
policy_service.update_policy_status("policy.sports_facilities", ApprovalStatus.APPROVED)
```

### Updating a Policy
When updating facts, required points, or anchors:
1. Increment `version` (e.g., `1.0.0` $\to$ `1.1.0`).
2. Add or update linked facts in `verified_facts.json`.
3. Set status back to `DRAFT` for review, or `APPROVED` once validated against `test_semantic_response_policies.py`.

### Retiring a Policy
To discontinue a policy without deleting historical telemetry references:
```python
policy_service.update_policy_status("policy.legacy_feature", ApprovalStatus.RETIRED)
```
Retired policies are immediately excluded from production semantic routing and fall back to RAG.

---

## 7. Migration Plan for Remaining Canned Strings

| Phase | Target Area | Current State | Target State | Status |
|---|---|---|---|---|
| **Phase 1** | Core Institutional Queries (Overview, Why Choose SRU, Guarantees) | Hardcoded strings in `responses.py` | `policy.about_sru`, `policy.why_choose_sru`, `policy.placement_guarantee`, `policy.admission_guarantee` | **Completed** |
| **Phase 2** | Campus & Residential Living | Hardcoded in `responses.py` | `policy.hostel_info`, `policy.hostel_curfew`, `policy.lab_facilities` | **Completed** |
| **Phase 3** | Fees & Financial Policies | Hardcoded strings in `responses.py` | `policy.future_year_fee`, `policy.special_concessions`, `fact.fees.*` | **Completed** |
| **Phase 4** | Branch Guidance & Exploratory Paths | Canned branches | Migrate to guided policy with dynamic career alignment facts | Planned |
| **Phase 5** | Non-B.Tech Fee Queries (MBA, Agriculture, Design) | Static fee responses | Migrate to versioned catalog backed by `verified_facts.json` | Planned |
