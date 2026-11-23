"""Pydantic schemas and types for the Approved Answer Policy and Semantic Routing system."""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResponseMode(str, Enum):
    FIXED = "fixed"      # Verbatim template required (legal notices, statutory disclaimers, date)
    GUIDED = "guided"    # LLM-guided generation constrained by required points & prohibited claims
    RAG = "rag"          # Standard vector retrieval & grounding fallback


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    DRAFT = "draft"
    RETIRED = "retired"


class FactCategory(str, Enum):
    RANKINGS = "rankings"
    PLACEMENTS = "placements"
    FEES = "fees"
    SCHOLARSHIPS = "scholarships"
    HOSTEL = "hostel"
    INFRASTRUCTURE = "infrastructure"
    ADMISSIONS = "admissions"
    LEADERSHIP = "leadership"
    GENERAL = "general"
    ABOUT = "about"
    RESEARCH = "research"
    INTERNATIONAL = "international"
    CAMPUS_LIFE = "campus_life"


class VerifiedFact(BaseModel):
    """Atomic, versioned university fact with audit trail and validity window."""
    fact_id: str = Field(description="Unique identifier, e.g. 'fact.rankings.the_2027_research'")
    category: FactCategory
    academic_year: str = Field(default="2027-28")
    statement: str = Field(description="Verified ground-truth factual statement")
    source: str = Field(description="Official circular, gazette, or university office")
    verification_status: str = Field(default="verified")
    valid_from: str = Field(default="2026-11-01")
    valid_until: str = Field(default="2027-10-31")
    last_audited: str = Field(default="2026-11-22")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovedAnswerPolicy(BaseModel):
    """Versioned Approved Answer Policy for an intent or conversational domain."""
    policy_id: str = Field(description="Unique policy identifier, e.g. 'policy.why_choose_sru'")
    intent_id: str = Field(description="Intent name, e.g. 'WHY_CHOOSE_SRU'")
    description: str = Field(description="What questions this policy answers")
    response_mode: ResponseMode = Field(default=ResponseMode.GUIDED)
    fixed_template: Optional[str] = Field(default=None, description="Exact text for fixed response mode")
    fixed_template_variants: Optional[List[str]] = Field(default=None, description="Rotating fixed templates")
    required_points: List[str] = Field(default_factory=list, description="Factual points that MUST be included")
    prohibited_claims: List[str] = Field(default_factory=list, description="Forbidden claims or negative concessions")
    preferred_tone: str = Field(default="Warm, encouraging, confident senior")
    preferred_length: str = Field(default="40-80 words")
    evidence_requirements: List[str] = Field(default_factory=list, description="List of fact_ids needed as evidence")
    version: str = Field(default="1.0.0")
    approval_status: ApprovalStatus = Field(default=ApprovalStatus.APPROVED)
    semantic_anchors: List[str] = Field(
        default_factory=list,
        description="Representative user phrases, paraphrases, and multilingual queries for semantic routing",
    )
    suggested_chips: List[str] = Field(default_factory=list, description="Follow-up quick suggestions")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    """Result of semantic intent classification and policy selection."""
    intent_id: str
    policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    response_mode: ResponseMode = Field(default=ResponseMode.RAG)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ids: List[str] = Field(default_factory=list)
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    reasoning: str = ""
    matched_anchor: Optional[str] = None
