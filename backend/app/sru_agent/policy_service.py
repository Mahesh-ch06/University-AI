"""Policy Service: Manages versioned, approved answer policies for SRU Buddy."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.sru_agent.policy_models import ApprovalStatus, ApprovedAnswerPolicy, ResponseMode

log = logging.getLogger("sru_agent.policies")
_POLICIES_FILE = Path(__file__).parent / "policies" / "approved_policies.json"

_policy_registry: Dict[str, ApprovedAnswerPolicy] = {}
_intent_to_policy: Dict[str, ApprovedAnswerPolicy] = {}
_version: str = "1.0.0"


def _load_policies() -> None:
    global _policy_registry, _intent_to_policy, _version
    if not _POLICIES_FILE.exists():
        log.warning("Approved policies file does not exist: %s", _POLICIES_FILE)
        return
    try:
        with open(_POLICIES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _version = data.get("version", "1.0.0")
        raw_policies = data.get("policies", [])
        new_reg = {}
        new_intent_map = {}
        for item in raw_policies:
            try:
                pol = ApprovedAnswerPolicy(**item)
                new_reg[pol.policy_id] = pol
                if pol.approval_status == ApprovalStatus.APPROVED:
                    new_intent_map[pol.intent_id] = pol
            except Exception as e:
                log.error("Failed to parse policy: %s - %s", item.get("policy_id"), e)
        _policy_registry = new_reg
        _intent_to_policy = new_intent_map
        log.info("Loaded %d approved answer policies (version %s)", len(_policy_registry), _version)
    except Exception as exc:
        log.exception("Error loading approved policies: %s", exc)


def get_policy(policy_id: str) -> Optional[ApprovedAnswerPolicy]:
    """Retrieve an approved policy by its ID."""
    if not _policy_registry:
        _load_policies()
    return _policy_registry.get(policy_id)


def get_policy_by_intent(intent_id: str) -> Optional[ApprovedAnswerPolicy]:
    """Retrieve the approved active policy for an intent identifier."""
    if not _policy_registry:
        _load_policies()
    return _intent_to_policy.get(intent_id)


def get_all_policies(status: Optional[ApprovalStatus] = None) -> List[ApprovedAnswerPolicy]:
    """Return all policies, optionally filtered by approval status."""
    if not _policy_registry:
        _load_policies()
    if status is None:
        return list(_policy_registry.values())
    return [p for p in _policy_registry.values() if p.approval_status == status]


def register_policy(policy: ApprovedAnswerPolicy) -> None:
    """Register or update a policy dynamically in memory."""
    if not _policy_registry:
        _load_policies()
    _policy_registry[policy.policy_id] = policy
    if policy.approval_status == ApprovalStatus.APPROVED:
        _intent_to_policy[policy.intent_id] = policy
    elif policy.intent_id in _intent_to_policy and _intent_to_policy[policy.intent_id].policy_id == policy.policy_id:
        _intent_to_policy.pop(policy.intent_id, None)


# Preload on import
_load_policies()
