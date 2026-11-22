"""Fact Service: Retrieves versioned, verified university facts with provenance and validity metadata."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from app.sru_agent.policy_models import FactCategory, VerifiedFact

log = logging.getLogger("sru_agent.facts")
_FACTS_FILE = Path(__file__).parent / "knowledge_base" / "verified_facts.json"

_facts_registry: Dict[str, VerifiedFact] = {}
_version: str = "2027-28.1"
_academic_year: str = "2027-28"


def _load_facts() -> None:
    global _facts_registry, _version, _academic_year
    if not _FACTS_FILE.exists():
        log.warning("Verified facts file does not exist: %s", _FACTS_FILE)
        return
    try:
        with open(_FACTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _version = data.get("version", "2027-28.1")
        _academic_year = data.get("academic_year", "2027-28")
        raw_facts = data.get("facts", [])
        new_reg = {}
        for item in raw_facts:
            try:
                fact = VerifiedFact(**item)
                new_reg[fact.fact_id] = fact
            except Exception as e:
                log.error("Failed to parse fact: %s - %s", item.get("fact_id"), e)
        _facts_registry = new_reg
        log.info("Loaded %d verified university facts for year %s (version %s)", len(_facts_registry), _academic_year, _version)
    except Exception as exc:
        log.exception("Error loading verified facts: %s", exc)


def get_fact(fact_id: str) -> Optional[VerifiedFact]:
    """Retrieve an atomic verified fact by its identifier."""
    if not _facts_registry:
        _load_facts()
    return _facts_registry.get(fact_id)


def get_facts_by_ids(fact_ids: List[str]) -> List[VerifiedFact]:
    """Retrieve a list of verified facts by their IDs."""
    if not _facts_registry:
        _load_facts()
    results = []
    for fid in fact_ids:
        f = _facts_registry.get(fid)
        if f:
            results.append(f)
    return results


def get_facts_by_category(category: FactCategory | str) -> List[VerifiedFact]:
    """Retrieve all active verified facts belonging to a category."""
    if not _facts_registry:
        _load_facts()
    cat_str = category.value if isinstance(category, FactCategory) else str(category).lower()
    return [f for f in _facts_registry.values() if f.category.value == cat_str]


def get_all_facts() -> List[VerifiedFact]:
    """Return all registered verified facts."""
    if not _facts_registry:
        _load_facts()
    return list(_facts_registry.values())


def format_evidence_block(facts: List[VerifiedFact]) -> str:
    """Format verified facts into a clean markdown evidence block for guided prompts."""
    if not facts:
        return "No specific fact evidence specified."
    lines = []
    for idx, f in enumerate(facts, start=1):
        lines.append(f"[{f.fact_id}] ({f.academic_year} | Source: {f.source}):\n  {f.statement}")
    return "\n".join(lines)


# Preload on import
_load_facts()
