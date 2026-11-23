"""Fact Service: Retrieves versioned, verified university facts with provenance and validity metadata."""

from __future__ import annotations
import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional

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


# ---------------------------------------------------------------- question-aware retrieval
# Which part of the university a question is about. A question can touch several aspects ("rankings and
# placements"); a broad one ("why SRU?") touches none and gets the strongest facts across aspects.
ASPECT_WORDS: Dict[str, tuple] = {
    "rankings": ("rank", "nirf", "qs ", "qs asia", "times higher", "the world", "top 100", "top 1000",
                 "number one", "no.1", "no 1", "#1", "rated", "position", "best university", "global"),
    "accreditation": ("accredit", "nba", "icar", "ugc", "naac", "recogni", "approved", "valid degree",
                      "legit", "fake"),
    "placements": ("placement", "package", "lpa", "salary", "job", "recruit", "compan", "hire", "offer"),
    "research": ("research", "paper", "publication", "patent", "journal"),
    "innovation": ("startup", "start-up", "srix", "incubat", "innovation", "entrepreneur"),
    "international": ("international", "abroad", "foreign", "exchange", "collaborat", "partner universit",
                      "2+2", "3+1", "usa", "new zealand"),
    "campus": ("campus", "club", "sport", "fest", "event", "student life", "facilit", "lab", "green"),
    "academics": ("curriculum", "industry", "project", "internship", "teaching", "mentor", "skill"),
    "scholarships": ("scholarship", "concession", "discount", "waiver", "afford"),
    "about": ("youngest", "history", "established", "founded"),
}
_WORD = re.compile(r"[a-z0-9+#.]+")


def _is_active(fact: VerifiedFact, today: Optional[date] = None) -> bool:
    """Usable in an answer: not marked unverified, and within its validity window."""
    if fact.verification_status == "unverified":
        return False
    try:
        return date.fromisoformat(fact.valid_until) >= (today or date.today())
    except ValueError:
        return True


def detect_aspects(question: str) -> List[str]:
    """The aspects a question asks about, in the order they appear."""
    q = f" {(question or '').lower()} "
    found = []
    for aspect, words in ASPECT_WORDS.items():
        positions = [q.find(w) for w in words if w in q]
        if positions:
            found.append((min(positions), aspect))
    return [a for _, a in sorted(found)]


def retrieve(question: str, k: int = 4, exclude: Iterable[str] = (), aspects: Optional[List[str]] = None,
             today: Optional[date] = None) -> List[VerifiedFact]:
    """The verified facts that answer this question, best first.

    * only active facts (not unverified, not expired);
    * facts of the aspects asked about come first; a fact merely sharing a word with the question
      (keyword-similar but about something else) is not returned when the question names an aspect;
    * a broad question gets the highest-priority facts, one per aspect before any aspect repeats;
    * facts in `exclude` (already told in this conversation) are used only when nothing new is left.
    """
    if not _facts_registry:
        _load_facts()
    asked = aspects if aspects is not None else detect_aspects(question)
    words = set(_WORD.findall((question or "").lower()))
    seen = set(exclude or ())
    pool = [f for f in _facts_registry.values() if _is_active(f, today) and (f.metadata or {}).get("short")]

    def score(f: VerifiedFact) -> float:
        meta = f.metadata or {}
        tags = [t.lower() for t in meta.get("tags", [])]
        overlap = sum(1 for t in tags if t in words or (" " in t and t in (question or "").lower()))
        return overlap * 2 + float(meta.get("priority", 0)) / 10

    if asked:
        ranked = [f for f in pool if (f.metadata or {}).get("aspect") in asked]
        ranked.sort(key=lambda f: (asked.index(f.metadata["aspect"]) if len(asked) > 1 else 0, -score(f)))
        if len(asked) > 1:   # interleave the aspects so each one asked about is covered
            by_aspect = {a: [f for f in ranked if f.metadata["aspect"] == a] for a in asked}
            ranked = []
            while any(by_aspect.values()):
                for a in asked:
                    if by_aspect[a]:
                        ranked.append(by_aspect[a].pop(0))
    else:
        ordered = sorted(pool, key=lambda f: -score(f))
        ranked, used_aspects = [], set()
        for f in ordered:                       # one per aspect first ...
            if f.metadata["aspect"] not in used_aspects:
                ranked.append(f)
                used_aspects.add(f.metadata["aspect"])
        ranked += [f for f in ordered if f not in ranked]   # ... then the rest
    fresh = [f for f in ranked if f.fact_id not in seen]
    # New facts first; when only a few are left, top up with ones already told (at least 3 in all).
    told = [f for f in ranked if f.fact_id in seen]
    want = max(min(3, len(ranked)), len(fresh[:k]))
    return (fresh + told)[:max(want, 1) if fresh else k]


def format_facts_for_prompt(facts: List[VerifiedFact]) -> str:
    """Facts for the model, each with its status, so a university-reported claim is attributed."""
    lines = []
    for f in facts:
        label = "verified" if f.verification_status == "verified" else "as stated by SRU - attribute it"
        lines.append(f"- [{f.fact_id} | {label} | source: {f.source}] {f.statement}")
    return "\n".join(lines)


# Preload on import
_load_facts()
