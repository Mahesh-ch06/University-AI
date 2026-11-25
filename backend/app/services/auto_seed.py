"""Automatic background seeding for university documents when vector store is empty."""

import asyncio
import logging
from pathlib import Path

from app.config import settings
from app.db.chroma import get_chroma_client
from app.services.rag_service import COLLECTION_NAME

logger = logging.getLogger(__name__)


def _find_data_path(rel_path: str) -> Path | None:
    """Find a relative path within possible project data directories."""
    candidates = [
        Path.cwd() / "data" / rel_path,
        Path.cwd() / "backend" / "data" / rel_path,
        settings.PROJECT_ROOT / "data" / rel_path,
        settings.PROJECT_ROOT / "backend" / "data" / rel_path,
        Path(__file__).resolve().parent.parent.parent / "data" / rel_path,
        Path(__file__).resolve().parent.parent.parent.parent / "data" / rel_path,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _handbook_fingerprint(handbook_dir: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    for path in sorted(handbook_dir.glob("*.md")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


# Text that only the retired fee policy contained. A vector chunk carrying any of it is removed from the index
# (it is derived data: the handbook re-index adds the current text back), and the FAQ document whose fee answers
# predate the 2027-28 circular is archived, not deleted.
_OBSOLETE_FEE_MARKERS = ("Rs. 2,10,000", "Rs. 1,05,000", "aution deposit", "aundry per year", "fee card lists standard fees",
                         "60% in 10+2 PCM", "₹1,85,000", "₹1,80,000 / sem", "19 special", "Examination fee (first year)",
                         "60% aggregate", "60% and above", "60% cutoff", "970 out of 1000", "970+", "first-come, first-served")
_RETIRED_DOCUMENT_TITLES = ("University FAQ — Fee",)


def _norm(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9₹%]+", " ", (text or "").lower()).strip()


def _current_fee_pages() -> dict:
    """{handbook title: normalised current text} for the generated fee pages (08 and 09)."""
    try:
        from scripts.ingest_handbook_docs import HANDBOOK_DOCS
    except Exception:
        return {}
    out = {}
    for doc in HANDBOOK_DOCS:
        if doc["file"].startswith(("08_", "09_")):
            path = settings.DATA_DIR / "handbook" / doc["file"]
            if path.exists():
                out[doc["title"]] = _norm(path.read_text(encoding="utf-8"))
    return out


def _outdated_fee_page_chunk(title, text, current: dict) -> bool:
    """A chunk of a fee page whose text is no longer in the page (written from the retired fee policy)."""
    page = current.get(title)
    if not page:
        return False
    body = _norm(text)
    for prefix in ("section ", "source "):          # ingestion may prepend a short header line
        if body.startswith(prefix):
            body = body.split(" ", 12)[-1]
    probes = [body[i:i + 80] for i in range(0, max(len(body) - 80, 1), 200)] or [body]
    return any(p and p not in page for p in probes)


async def retire_obsolete_fee_knowledge() -> int:
    """Remove obsolete fee chunks from the vector index and archive retired fee documents. Returns chunks removed."""
    removed = 0
    try:
        collection = get_chroma_client().get_or_create_collection(name=COLLECTION_NAME,
                                                                  metadata={"hnsw:space": "cosine"})
        got = collection.get(include=["documents", "metadatas"])
        current = _current_fee_pages()
        stale = [cid for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"])
                 if (meta or {}).get("title") in _RETIRED_DOCUMENT_TITLES
                 or any(m in (text or "") for m in _OBSOLETE_FEE_MARKERS)
                 or _outdated_fee_page_chunk((meta or {}).get("title"), text, current)]
        if stale:
            collection.delete(ids=stale)
            removed = len(stale)
            logger.info("Removed %d obsolete fee chunks from the vector index.", removed)
    except Exception as err:
        logger.warning("Obsolete fee chunk clean-up skipped: %s", err)
    try:
        from sqlalchemy import update
        from app.db.session import async_session_factory
        from app.models.document import Document, DocumentVersion
        async with async_session_factory() as session:
            ids = (await session.execute(
                Document.__table__.select().with_only_columns(Document.id).where(
                    Document.title.in_(_RETIRED_DOCUMENT_TITLES), Document.status != "inactive"))).scalars().all()
            if ids:
                await session.execute(update(Document).where(Document.id.in_(ids)).values(status="inactive"))
                await session.execute(update(DocumentVersion).where(DocumentVersion.document_id.in_(ids))
                                      .values(active=False))
                await session.commit()
                logger.info("Archived %d retired fee document(s).", len(ids))
    except Exception as err:
        logger.warning("Retired fee document archiving skipped: %s", err)
    return removed


async def refresh_handbook_if_changed() -> bool:
    """Re-index the handbook when its files changed since the vector index was built.

    The vector index is only seeded when it is empty, so an edited handbook file used to leave the
    OLD text in the index for ever. A fingerprint of the handbook files is kept beside the index;
    when it no longer matches, the handbook documents are replaced. Best effort: if the embedding
    quota is exhausted the old index stays and this is retried on the next start. (The admissions
    agent does not depend on it: it reads the handbook files directly.)
    """
    handbook_dir = settings.DATA_DIR / "handbook"
    if not handbook_dir.is_dir():
        return False
    marker = Path(settings.CHROMA_PERSIST_DIR or "./chroma_data") / "handbook.sha256"
    fingerprint = _handbook_fingerprint(handbook_dir)
    try:
        if marker.exists() and marker.read_text(encoding="utf-8").strip() == fingerprint:
            return False
        logger.info("Handbook files changed since the last indexing; refreshing the vector index...")
        from scripts.ingest_handbook_docs import ingest_handbook
        await ingest_handbook()
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(fingerprint, encoding="utf-8")
        return True
    except Exception as err:
        logger.warning("Handbook re-index skipped (will retry on next start): %s", err)
        return False


async def ensure_documents_seeded() -> int:
    """Check if ChromaDB collection has documents; if empty, ingest automatically."""
    try:
        import sys
        backend_dir = Path(__file__).resolve().parent.parent.parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        scripts_dir = backend_dir / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))

        client = get_chroma_client()
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        count = collection.count()
        if count > 0:
            logger.info("ChromaDB '%s' collection has %d documents. No seeding needed.", COLLECTION_NAME, count)
            try:
                from app.services.video_service import sync_video_vectors
                await sync_video_vectors()
            except Exception as ve:
                logger.warning("Could not sync video vectors: %s", ve)
            return count

        logger.warning(
            "ChromaDB '%s' collection is empty (%d chunks). Starting automatic document ingestion...",
            COLLECTION_NAME,
            count,
        )

        docx_path = _find_data_path("SRU Agentic AI.docx")
        if docx_path:
            logger.info("Auto-seeding FAQ from: %s", docx_path)
            from scripts.parse_university_docx import parse_university_docx
            from scripts.ingest_university_doc import _ingest_entries

            entries = parse_university_docx(docx_path)
            if entries:
                await _ingest_entries(entries, department_override=None, clear_existing=False)
                logger.info("Auto-seeded %d FAQ entries from docx.", len(entries))

        handbook_dir = _find_data_path("handbook")
        if handbook_dir and handbook_dir.is_dir():
            logger.info("Auto-seeding student handbook from: %s", handbook_dir)
            from scripts.ingest_handbook_docs import ingest_handbook

            await ingest_handbook()
            logger.info("Auto-seeded handbook markdown documents.")
            try:  # remember which handbook text is in the index (see refresh_handbook_if_changed)
                marker = Path(settings.CHROMA_PERSIST_DIR or "./chroma_data") / "handbook.sha256"
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(_handbook_fingerprint(settings.DATA_DIR / "handbook"), encoding="utf-8")
            except Exception as marker_err:
                logger.warning("Could not record the handbook fingerprint: %s", marker_err)

        # Ensure semantic video vectors are synced in ChromaDB
        try:
            from app.services.video_service import sync_video_vectors
            await sync_video_vectors()
        except Exception as ve:
            logger.warning("Could not sync video vectors during auto-seed: %s", ve)

        new_count = collection.count()
        logger.info("Document auto-seeding completed. Total chunks in ChromaDB: %d", new_count)

        # Also ensure foundational verified exemplars are seeded
        await ensure_exemplars_seeded()

        return new_count

    except Exception as e:
        logger.error("Auto-seeding encountered an error: %s", e, exc_info=True)
        return 0


async def ensure_exemplars_seeded():
    """Seed foundational verified exemplars into ChromaDB if not already present."""
    try:
        from app.providers.factory import create_embedding_provider
        from app.services.exemplar_service import ExemplarService
        import uuid

        embed = create_embedding_provider()
        svc = ExemplarService(embed)
        collection = svc._get_collection()
        if not collection:
            return

        # Seeded answers older than the 2027-28 fee circular are retired (never kept as a fallback). Only
        # answers carrying an obsolete marker are removed, so an admin's own exemplar is never touched.
        obsolete = ("minimum of 50% aggregate marks in Mathematics", "fee card lists fees from 50%", "60% in PCM",
                    "laundry", "₹1,27,500 per semester", "3.70–3.90 lakh")

        async def _current(question: str):
            match = await svc.find_matching_exemplar(question, distance_threshold=0.20)
            if match and any(m in (match.get("answer") or "") for m in obsolete):
                try:
                    collection.delete(where={"answer": match["answer"]})
                    return None
                except Exception as exc:  # never block start-up on this
                    logger.warning("Could not retire an outdated exemplar: %s", exc)
            return match

        from app.sru_agent import fees as _fees

        # Foundational B.Tech eligibility exemplar (minimums from the 2027-28 fee circular)
        q1 = "What is the eligibility criteria and admission process for B.Tech?"
        if not await _current(q1):
            cse = _fees.load_data()["programs"]["btech_cse"]["min_percent"]
            other = _fees.load_data()["programs"]["btech_mech"]["min_percent"]
            ans1 = (
                "B.Tech needs 10+2 / Intermediate with Mathematics, Physics and Chemistry (MPC). The 2027-28 fee "
                f"circular lists a minimum of **{cse:g}%** for B.Tech CSE and ECE (and their specialisations) and "
                f"**{other:g}%** for the other branches. Meeting the minimum isn't a guarantee of admission; documents "
                "and seat availability decide it.\n\n"
                "To apply: register at https://apply.sru.edu.in, complete the application and upload documents, submit "
                "your JEE Main / EAPCET result where available, then accept the offer and pay the fee.\n\n"
                "Which branch are you interested in, and what are your 10+2 marks? I'll check your eligibility."
            )
            await svc.register_exemplar(uuid.uuid4(), q1, ans1)

        # Gold standard score & fee breakdown exemplar (878/1000 score), every figure from the fee engine
        q2 = "I scored 878/1000 in intermediate. What is my fee and scholarship?"
        if not await _current(q2):
            r = _fees.calculate_fee("btech_cse", percent=87.8)
            ans2 = (
                f"Nice score! 87.8% falls in the 80–91.9% band, so you'd get a **{r['scholarship_percent']}% merit "
                f"scholarship** on tuition. For B.Tech CSE that's {r['tuition_first_year_after_scholarship']} tuition a "
                f"year, split equally between the semesters, subject to marksheet verification.\n\n"
                f"• **Semester 1:** {r['sem1_total_payable']} (tuition + enrollment, other and Year-1 exam fees)\n"
                f"• **Semester 2:** {r['sem2_total_payable']}\n"
                f"• **First year:** {r['first_year_total_payable']} (application form {r['application_fee']} separately)\n\n"
                "Hostel and bus are optional extras. Which programme are you considering? I'll work out its exact fee."
            )
            await svc.register_exemplar(uuid.uuid4(), q2, ans2)
            logger.info("Auto-seeded gold standard merit scholarship verified exemplar.")
    except Exception as e:
        logger.warning("Could not auto-seed exemplars: %s", e)


