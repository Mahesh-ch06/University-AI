"""Lead service — business logic for prospective student leads, inquiries, and conversion tracking."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import ProspectiveLead
from app.schemas.lead import LeadCreate

logger = logging.getLogger(__name__)


PROGRAM_SLUG_MAP = {
    "btech_cse": "B.Tech CSE",
    "btech_ai_robotics": "B.Tech AI & Robotics",
    "btech_ece": "B.Tech ECE",
    "btech_eee": "B.Tech EEE",
    "btech_mech": "B.Tech Mechanical",
    "btech_civil": "B.Tech Civil",
    "btech_biotech": "B.Tech Biotechnology",
    "btech_food_tech": "B.Tech Food Technology",
    "btech_engg_physics": "B.Tech Engineering Physics",
    "btech_iep": "B.Tech IEP (International)",
    "bsc_agri": "B.Sc Agriculture",
    "bdes": "B.Des (Design)",
    "bba": "BBA",
    "bsc_hospitality": "B.Sc Hospitality",
    "bba_specialised": "BBA (Specialised)",
    "bca": "BCA",
    "bsc_cs": "B.Sc Computer Science",
    "bsc_maths_ai": "B.Sc Mathematics & AI",
    "bcom": "B.Com",
    "bsc_physics": "B.Sc Physics",
    "bsc_chemistry": "B.Sc Chemistry",
    "mba": "MBA",
    "mba_agri": "MBA Agri Business",
    "mca": "MCA",
    "mtech": "M.Tech",
    "msc": "M.Sc",
}

UNSPECIFIED_VALUES = {"not specified", "unknown", "none", "null", "undefined", ""}


def resolve_clean_program(
    raw_program: str | None,
    metadata: dict | None = None,
    conversation_text: str | None = None,
) -> str:
    """Normalize program names to clean, readable titles (e.g. 'B.Tech CSE').

    Never returns 'Not specified' or raw database slugs.
    """
    raw = (raw_program or "").strip()
    lower = raw.lower()

    # 1. Exact slug match
    if lower in PROGRAM_SLUG_MAP:
        return PROGRAM_SLUG_MAP[lower]

    # 2. Existing valid human-readable string
    if raw and lower not in UNSPECIFIED_VALUES:
        if " (" in raw and raw.startswith("B.Tech"):
            return raw.split(" (")[0]
        return raw

    # 3. Check metadata for pending question, query, or explicit program field
    if metadata and isinstance(metadata, dict):
        for key in ("program_interest", "program", "program_name", "pending_question", "query"):
            candidate = metadata.get(key)
            if candidate and isinstance(candidate, str):
                c_str = candidate.strip()
                c_lower = c_str.lower()
                if c_lower in PROGRAM_SLUG_MAP:
                    return PROGRAM_SLUG_MAP[c_lower]
                if c_str and c_lower not in UNSPECIFIED_VALUES:
                    if len(c_str.split()) <= 4 and (
                        c_str.startswith("B.") or c_str.startswith("M.") or c_str in ("MBA", "BBA", "BCA", "MCA")
                    ):
                        return c_str
                    if not conversation_text:
                        conversation_text = c_str

    # 4. Analyze conversation text or inquiry query
    text = (conversation_text or "").lower()
    if text:
        try:
            from app.sru_agent import fees
            prog_key = fees.find_program(text)
            if prog_key and prog_key in PROGRAM_SLUG_MAP:
                return PROGRAM_SLUG_MAP[prog_key]
        except Exception:
            pass

        if "ai & robotics" in text or "ai and robotics" in text or "artificial intelligence and robotics" in text:
            return "B.Tech AI & Robotics"
        if "agri" in text or "agriculture" in text or "farming" in text:
            return "B.Sc Agriculture"
        if "ece" in text or "electronics" in text or "vlsi" in text:
            return "B.Tech ECE"
        if "eee" in text or "electrical" in text:
            return "B.Tech EEE"
        if "mech" in text or "mechanical" in text:
            return "B.Tech Mechanical"
        if "civil" in text or "construction" in text:
            return "B.Tech Civil"
        if "biotech" in text or "biotechnology" in text:
            return "B.Tech Biotechnology"
        if "food tech" in text or "food technology" in text:
            return "B.Tech Food Technology"
        if "mba" in text or "business administration" in text or "management" in text:
            return "MBA"
        if "bba" in text:
            return "BBA"
        if "bca" in text:
            return "BCA"
        if "mca" in text:
            return "MCA"
        if "mtech" in text or "m.tech" in text:
            return "M.Tech"
        if "msc" in text or "m.sc" in text:
            return "M.Sc"
        if "design" in text or "bdes" in text:
            return "B.Des (Design)"
        if "bcom" in text or "commerce" in text:
            return "B.Com"
        if (
            "cse" in text
            or "computer" in text
            or "software" in text
            or "data science" in text
            or "aiml" in text
            or "cyber" in text
            or "engineering" in text
            or "btech" in text
            or "b.tech" in text
        ):
            return "B.Tech CSE"

    return "B.Tech CSE"


async def create_lead(db: AsyncSession, data: LeadCreate) -> ProspectiveLead:
    """Register a new prospective student lead into the database."""
    clean_prog = resolve_clean_program(
        raw_program=data.program_interest,
        metadata=data.metadata,
    )
    lead = ProspectiveLead(
        name=data.name.strip(),
        phone=data.phone.strip(),
        email=data.email.strip() if data.email else None,
        program_interest=clean_prog,
        score=data.score.strip() if data.score else None,
        exam_type=data.exam_type.strip() if data.exam_type else None,
        source=data.source,
        conversation_id=data.conversation_id,
        metadata_=data.metadata,
        status="new",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    logger.info("Captured prospective lead: %s (%s) for %s from %s", lead.name, lead.phone, lead.program_interest, lead.source)
    return lead


async def list_leads(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    program: str | None = None,
    source: str | None = None,
    status: str | None = None,
) -> tuple[int, list[ProspectiveLead]]:
    """Retrieve paginated prospective leads with optional filtering and search."""
    stmt = select(ProspectiveLead)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            (ProspectiveLead.name.ilike(search_pattern))
            | (ProspectiveLead.phone.ilike(search_pattern))
            | (ProspectiveLead.email.ilike(search_pattern))
        )

    if program and program != "all":
        stmt = stmt.where(ProspectiveLead.program_interest.ilike(f"%{program.strip()}%"))

    if source and source != "all":
        if source in ("calculator", "scholarship_calculator"):
            stmt = stmt.where(ProspectiveLead.source.in_(["calculator", "scholarship_calculator"]))
        else:
            stmt = stmt.where(ProspectiveLead.source == source)

    if status and status != "all":
        stmt = stmt.where(ProspectiveLead.status == status)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate and order by newest first
    offset = (page - 1) * page_size
    stmt = stmt.order_by(ProspectiveLead.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(stmt)
    leads = list(result.scalars().all())

    # Auto-resolve conversation_id and program_interest for leads
    modified_leads = False
    for lead in leads:
        if not lead.conversation_id and lead.phone:
            clean_digits = "".join(filter(str.isdigit, lead.phone))
            if len(clean_digits) >= 10:
                last10 = clean_digits[-10:]
                try:
                    from app.models.message import Message
                    conv_q = (
                        select(Message.conversation_id)
                        .where(Message.content.contains(last10))
                        .order_by(Message.created_at.desc())
                        .limit(1)
                    )
                    res = await db.execute(conv_q)
                    conv_id = res.scalar_one_or_none()
                    if conv_id:
                        lead.conversation_id = conv_id
                        modified_leads = True
                except Exception:
                    pass

        # Check if program_interest is missing, 'Not specified', or raw slug
        raw_pi = (lead.program_interest or "").strip()
        is_unresolved = (
            not raw_pi
            or raw_pi.lower() in UNSPECIFIED_VALUES
            or raw_pi.lower() in PROGRAM_SLUG_MAP
            or raw_pi.startswith("btech_")
            or "_" in raw_pi
            or (raw_pi.startswith("B.Tech") and " (" in raw_pi)
        )

        if is_unresolved:
            conv_text = ""
            if lead.conversation_id:
                try:
                    from app.models.message import Message
                    msg_q = (
                        select(Message.content)
                        .where(Message.conversation_id == lead.conversation_id)
                        .where(Message.role == "user")
                        .order_by(Message.created_at.asc())
                        .limit(5)
                    )
                    msgs = (await db.execute(msg_q)).scalars().all()
                    conv_text = " ".join(m for m in msgs if m)
                except Exception:
                    conv_text = ""

            resolved = resolve_clean_program(
                raw_program=raw_pi,
                metadata=lead.metadata_ if isinstance(lead.metadata_, dict) else None,
                conversation_text=conv_text,
            )
            if resolved and resolved != lead.program_interest:
                lead.program_interest = resolved
                modified_leads = True

    if modified_leads:
        try:
            await db.commit()
        except Exception as e:
            logger.warning("Could not persist auto-resolved lead fields: %s", e)
            await db.rollback()

    return total, leads


async def get_lead_stats(db: AsyncSession) -> dict:
    """Aggregate KPI statistics on prospective student inquiries."""
    # Total
    total_q = select(func.count(ProspectiveLead.id))
    total = (await db.execute(total_q)).scalar() or 0

    # By source
    chat_q = select(func.count(ProspectiveLead.id)).where(ProspectiveLead.source == "chat_inquiry")
    chat_leads = (await db.execute(chat_q)).scalar() or 0

    calc_q = select(func.count(ProspectiveLead.id)).where(
        ProspectiveLead.source.in_(["calculator", "scholarship_calculator"])
    )
    calculator_leads = (await db.execute(calc_q)).scalar() or 0

    # Today's leads
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = select(func.count(ProspectiveLead.id)).where(ProspectiveLead.created_at >= today_start)
    today_leads = (await db.execute(today_q)).scalar() or 0

    # Enrolled conversions
    enrolled_q = select(func.count(ProspectiveLead.id)).where(ProspectiveLead.status == "enrolled")
    enrolled_leads = (await db.execute(enrolled_q)).scalar() or 0

    return {
        "total_leads": total,
        "chat_leads": chat_leads,
        "calculator_leads": calculator_leads,
        "today_leads": today_leads,
        "enrolled_leads": enrolled_leads,
    }


DO_NOT_CONTACT = "do_not_contact"


async def cancel_lead(db: AsyncSession, lead_id: UUID, reason: str = "") -> ProspectiveLead | None:
    """The student withdrew a callback / visit request: mark the lead so nobody phones them.

    The lead is kept (not deleted) so the admissions team can see that the request was withdrawn.
    """
    lead = await db.get(ProspectiveLead, lead_id)
    if not lead:
        return None
    lead.status = DO_NOT_CONTACT
    lead.metadata_ = {**(lead.metadata_ or {}), "consent": False,
                      "cancelled_at": datetime.now(timezone.utc).isoformat(),
                      "cancel_reason": (reason or "Student asked not to be contacted")[:200]}
    await db.commit()
    await db.refresh(lead)
    logger.info("Lead %s marked do-not-contact at the student's request", lead_id)
    return lead


async def update_lead_status(
    db: AsyncSession,
    lead_id: UUID,
    new_status: str,
) -> ProspectiveLead | None:
    """Update admissions status of a lead (interested, contacted, applied, enrolled, rejected)."""
    lead = await db.get(ProspectiveLead, lead_id)
    if not lead:
        return None

    lead.status = new_status
    await db.commit()
    await db.refresh(lead)
    logger.info("Updated lead %s status to %s", lead_id, new_status)
    return lead
