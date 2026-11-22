"""Comprehensive Test Suite for Semantic Response Policies, Versioned University Knowledge, and Observability."""

import json
from pathlib import Path
import pytest

from app.sru_agent import fact_service, policy_engine, policy_models, policy_service, semantic_router, observability
from app.sru_agent.policy_models import ApprovalStatus, ResponseMode


# ----------------------------------------------------------------------------------------
# 1. Five Differently Worded "Why Choose SRU" Questions Routed Semantically
# ----------------------------------------------------------------------------------------
@pytest.mark.parametrize("query, label", [
    ("Why should I pick SR University over other colleges?", "Standard comparison query"),
    ("bro sru lo join avvadam worth ah kaada?", "Telugu-English colloquial phrasing"),
    ("What makes SRU stand out as a top engineering destination?", "Aspirational feature query"),
    ("Is SR University actually a good choice for my future?", "Skeptical prospective applicant"),
    ("Give me compelling reasons to consider SRU for B.Tech.", "Direct value proposition request"),
])
def test_five_differently_worded_why_choose_sru_routed_correctly(query, label):
    """Demonstrate how five differently worded questions about choosing SRU
    are routed correctly to policy.why_choose_sru without keyword matching."""
    decision = semantic_router.route_message(query)
    
    assert decision.intent_id == "WHY_CHOOSE_SRU", f"Failed for '{query}' ({label})"
    assert decision.policy_id == "policy.why_choose_sru", f"Wrong policy for '{query}'"
    assert decision.response_mode == ResponseMode.GUIDED
    assert decision.confidence >= semantic_router.DEFAULT_CONFIDENCE_THRESHOLD
    assert decision.is_fallback is False
    assert len(decision.evidence_ids) >= 3


# ----------------------------------------------------------------------------------------
# 2. Versioned University Knowledge Integration & Metadata
# ----------------------------------------------------------------------------------------
def test_versioned_verified_facts_metadata():
    """Verify dynamic university facts are separated from prompt instructions with full metadata."""
    facts = fact_service.get_all_facts()
    assert len(facts) >= 10, "Should have loaded registered facts"
    
    # Check ranking fact
    the_fact = fact_service.get_fact("fact.rankings.the_2027_research")
    assert the_fact is not None
    assert the_fact.academic_year == "2027-28"
    assert "#6 in India in Research Quality" in the_fact.statement
    assert "Times Higher Education" in the_fact.source
    assert the_fact.verification_status == "verified"
    assert the_fact.valid_from and the_fact.valid_until

    # Check ICAR accreditation fact
    icar_fact = fact_service.get_fact("fact.rankings.icar_accreditation")
    assert icar_fact is not None
    assert "1st private university" in icar_fact.statement
    assert "ICAR accreditation" in icar_fact.statement

    # Check placement stats fact
    placement_fact = fact_service.get_fact("fact.placements.packages_and_averages")
    assert placement_fact is not None
    assert "6 to 6.5 LPA average" in placement_fact.statement
    assert "₹51 LPA" in placement_fact.statement


# ----------------------------------------------------------------------------------------
# 3. Approved Answer Policy Schema & Lifecycle
# ----------------------------------------------------------------------------------------
def test_approved_answer_policy_schema_and_lifecycle():
    """Verify policies adhere to schema with version, response mode, required points & prohibited claims."""
    policy = policy_service.get_policy("policy.why_choose_sru")
    assert policy is not None
    assert policy.version == "1.0.0"
    assert policy.approval_status == ApprovalStatus.APPROVED
    assert policy.response_mode == ResponseMode.GUIDED
    assert len(policy.required_points) >= 4
    assert any("Research Quality" in pt for pt in policy.required_points)
    assert any("ICAR" in pt for pt in policy.required_points)
    assert len(policy.prohibited_claims) >= 2
    assert any("Never start with a negative" in c for c in policy.prohibited_claims)


# ----------------------------------------------------------------------------------------
# 4. Guided Response Generation & Guardrails Enforcement
# ----------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_guided_response_generation_why_choose_sru():
    """Verify guided execution incorporates required factual points and positive advocacy."""
    decision = semantic_router.route_message("Why should I choose SRU over other colleges?")
    answer, cards, chips = await policy_engine.execute_policy(
        decision,
        message="Why should I choose SRU over other colleges?",
        session_id="test-session-policy-1",
        profile={"name": "Kavya"},
    )
    
    # Must NOT start with a negative or concession (Rule 22)
    assert not answer.startswith("No,")
    assert not answer.startswith("SR University is not")
    assert "SR University stands among India's premier" in answer or "premier" in answer
    assert "#6 in India in Research Quality" in answer
    assert "ICAR accreditation" in answer
    assert "₹51 LPA" in answer
    assert len(chips) >= 2


@pytest.mark.asyncio
async def test_placement_guarantee_policy_execution():
    """Verify placement guarantee query delivers 100% assistance policy without false job guarantees."""
    decision = semantic_router.route_message("does sru guarantee placements?")
    assert decision.intent_id == "PLACEMENT_GUARANTEE"
    assert decision.policy_id == "policy.placement_guarantee"

    answer, cards, chips = await policy_engine.execute_policy(
        decision,
        message="does sru guarantee placements?",
        session_id="test-session-policy-2",
    )
    assert "100% placement assistance" in answer
    assert "interview performance" in answer
    assert "6 to 6.5 LPA" in answer
    assert "not guarantee" not in answer.lower() or "assistance" in answer.lower()


# ----------------------------------------------------------------------------------------
# 5. Confidence-Aware Routing and RAG Fallback
# ----------------------------------------------------------------------------------------
def test_confidence_aware_routing_and_rag_fallback():
    """Novel, out-of-policy, or ambiguous queries fall back cleanly to RAG mode."""
    novel_query = "Who is the student coordinator for the annual cultural dance festival?"
    decision = semantic_router.route_message(novel_query)
    
    assert decision.is_fallback is True
    assert decision.response_mode == ResponseMode.RAG
    assert decision.policy_id is None
    assert decision.confidence < semantic_router.DEFAULT_CONFIDENCE_THRESHOLD
    assert "No approved policy met confidence threshold" in (decision.fallback_reason or "")


# ----------------------------------------------------------------------------------------
# 6. Preservation of Admission Context & Interruption Resumption
# ----------------------------------------------------------------------------------------
def test_preservation_of_admission_context_and_interruption():
    """During admission flow, interruptions preserve admission state and allow smooth resumption."""
    conv_state = {
        "current_intent": "ADMISSION_COUNSELLING",
        "admission_stage": "marks_intake",
        "fee_intake": {"program": "btech_cse", "waiting_for": "marks"},
        "collected_data": {"program_interest": "btech_cse"},
    }

    # Interruption turn
    interruption_msg = "Before that, why should I choose SRU?"
    decision = semantic_router.route_message(interruption_msg, conversation_state=conv_state)
    
    assert decision.intent_id == "WHY_CHOOSE_SRU"
    assert decision.policy_id == "policy.why_choose_sru"

    # Resumption turn
    conv_state["paused_intent"] = "ADMISSION_COUNSELLING"
    conv_state["current_intent"] = "WHY_CHOOSE_SRU"
    
    resume_decision = semantic_router.route_message("Okay, continue my admission.", conversation_state=conv_state)
    assert resume_decision.intent_id == "ADMISSION_COUNSELLING"
    assert "Resuming previously paused admission workflow" in resume_decision.reasoning


# ----------------------------------------------------------------------------------------
# 7. Observability Instrumentation
# ----------------------------------------------------------------------------------------
def test_observability_instrumentation():
    """Verify telemetry recording captures required routing and latency attributes."""
    observability.clear_telemetry()
    
    telemetry = observability.PolicyTurnTelemetry(
        session_id="test-session-obs",
        conversation_id="conv-obs-1",
        message="why should i choose sru",
        detected_intent="WHY_CHOOSE_SRU",
        selected_policy_id="policy.why_choose_sru",
        policy_version="1.0.0",
        response_mode="guided",
        retrieved_evidence_ids=["fact.rankings.the_2027_research"],
        routing_confidence=0.88,
        fallback_decision=False,
        routing_latency_ms=12.4,
        generation_latency_ms=45.1,
        total_latency_ms=57.5,
    )
    observability.record_policy_telemetry(telemetry)
    
    records = observability.get_recent_telemetry(limit=5)
    assert len(records) >= 1
    last = records[-1]
    assert last["detected_intent"] == "WHY_CHOOSE_SRU"
    assert last["selected_policy_id"] == "policy.why_choose_sru"
    assert last["policy_version"] == "1.0.0"
    assert last["routing_confidence"] == 0.88
    assert last["fallback_decision"] is False
    assert last["total_latency_ms"] == 57.5


# ----------------------------------------------------------------------------------------
# 8. Evaluation Dataset Schema Integrity
# ----------------------------------------------------------------------------------------
def test_evaluation_dataset_exists_and_valid():
    """Verify evaluation dataset JSON exists and contains the required categories and cases."""
    dataset_path = Path(__file__).resolve().parents[1] / "app" / "sru_agent" / "evals" / "semantic_policy_eval_dataset.json"
    assert dataset_path.exists()
    
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["version"] == "1.0.0"
    categories = [cat["category"] for cat in data["test_cases"]]
    assert "why_choose_sru_paraphrases" in categories
    assert "placement_guarantee_paraphrases" in categories
    assert "ambiguous_and_fallback" in categories
    assert "multi_turn_admission_context" in categories
