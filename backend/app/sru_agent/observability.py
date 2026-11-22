"""Observability & Telemetry Service for Semantic Routing and Approved Answer Policies."""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("sru_agent.observability")


@dataclass
class PolicyTurnTelemetry:
    session_id: str
    conversation_id: Optional[str]
    message: str
    detected_intent: str
    selected_policy_id: Optional[str] = None
    policy_version: Optional[str] = None
    response_mode: str = "rag"
    retrieved_evidence_ids: List[str] = field(default_factory=list)
    routing_confidence: float = 0.0
    fallback_decision: bool = False
    fallback_reason: Optional[str] = None
    routing_latency_ms: float = 0.0
    generation_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    evaluation_score: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_recent_telemetry: List[PolicyTurnTelemetry] = []
_MAX_TELEMETRY_LOG = 500


def record_policy_telemetry(telemetry: PolicyTurnTelemetry) -> None:
    """Record a policy routing and execution telemetry event."""
    global _recent_telemetry
    _recent_telemetry.append(telemetry)
    if len(_recent_telemetry) > _MAX_TELEMETRY_LOG:
        _recent_telemetry = _recent_telemetry[-_MAX_TELEMETRY_LOG:]

    log.info(
        "POLICY_TELEMETRY: intent=%s policy=%s conf=%.2f mode=%s fallback=%s lat=%.1fms ev_ids=%s",
        telemetry.detected_intent,
        telemetry.selected_policy_id,
        telemetry.routing_confidence,
        telemetry.response_mode,
        telemetry.fallback_decision,
        telemetry.total_latency_ms,
        telemetry.retrieved_evidence_ids,
    )


def get_recent_telemetry(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent policy execution telemetry records."""
    return [t.to_dict() for t in _recent_telemetry[-limit:]]


def clear_telemetry() -> None:
    global _recent_telemetry
    _recent_telemetry.clear()
