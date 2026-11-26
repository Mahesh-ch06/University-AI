"""
Ingest a university FAQ DOCX into the RAG knowledge base.

Usage:
    # Drop your DOCX into data/ then run from the backend/ directory:
    .\\venv\\Scripts\\activate
    python scripts/ingest_university_doc.py --file ../data/your_university_doc.docx

    # Optional flags:
    --department "Student Services"   (defaults to section name)
    --dry-run                         (parse only, no DB/Chroma writes)
    --verbose                         (show each parsed Q&A entry)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend root is on sys.path when run directly
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from scripts.parse_university_docx import ParsedEntry, parse_university_docx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── ChromaDB metadata key for page URL ────────────────────────────────────────
CHROMA_PAGE_URL_KEY = "page_url"
CHROMA_SECTION_KEY = "section"
CHROMA_QUESTION_KEY = "question"


async def _clear_existing_inline_docs(db, collection) -> None:
    """Remove previous inline:docx documents from PostgreSQL and ChromaDB."""
    from sqlalchemy import select
    from app.models.document import Document, DocumentVersion

    ver_stmt = select(DocumentVersion).where(DocumentVersion.storage_location == "inline:docx")
    ver_res = await db.execute(ver_stmt)
    versions = ver_res.scalars().all()
    doc_ids = {v.document_id for v in versions}

    for v in versions:
        await db.delete(v)

    for doc_id in doc_ids:
        doc = await db.get(Document, doc_id)
        if doc:
            await db.delete(doc)
        if collection is not None:
            try:
                existing = collection.get(
                    where={"document_id": str(doc_id)},
                    include=["metadatas"],
                )
                chunk_ids = existing.get("ids", [])
                if chunk_ids:
                    collection.delete(ids=chunk_ids)
                    logger.info("Deleted %d existing chunks for doc_id=%s from ChromaDB", len(chunk_ids), doc_id)
            except Exception as e:
                logger.warning("Error clearing ChromaDB chunks for doc_id=%s: %s", doc_id, e)

    await db.commit()
    logger.info("Cleared %d existing inline docx records from database", len(doc_ids))


def _retired_sections() -> set[str]:
    """FAQ sections that are never indexed again (their answers come from elsewhere, e.g. fees from the fee
    engine): the titles auto_seed retires at start-up."""
    from app.services.auto_seed import _RETIRED_DOCUMENT_TITLES
    return {t.split("—", 1)[1].strip() for t in _RETIRED_DOCUMENT_TITLES if "—" in t}


def _norm(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _missing_or_changed(entries: list[ParsedEntry], collection) -> tuple[list[ParsedEntry], list[str]]:
    """What the additive update must do to make the FAQ index match the document.

    Returns (entries to index, chunk ids to remove AFTER the new ones are indexed):
      * an entry not in the index, or whose indexed text differs from the document now, is (re)indexed;
      * a chunk is removed when a newer text replaces it, when it duplicates an identical chunk, or when its
        (section, question) is no longer in the document at all (e.g. a question the old parser stored with its
        list number, "4. Does SRiX ...").
    Retired sections are never indexed. Nothing in the database is deleted; only derived index chunks."""
    existing = collection.get(where={"document_type": "faq"}, include=["metadatas", "documents"])
    # keyed by (section, question): the same question can be asked in two sections with different answers
    by_question: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for cid, meta, doc in zip(existing.get("ids", []), existing.get("metadatas", []), existing.get("documents", [])):
        key = (_norm((meta or {}).get(CHROMA_SECTION_KEY, "")), _norm((meta or {}).get(CHROMA_QUESTION_KEY, "")))
        by_question.setdefault(key, []).append((cid, _norm(doc)))
    retired = _retired_sections()
    to_add, stale, wanted = [], [], set()
    for entry in entries:
        if entry.section in retired:
            continue
        key = (_norm(entry.section), _norm(entry.question[:200]))
        wanted.add(key)
        indexed = by_question.get(key, [])
        current = _norm(entry.chunk_text)
        same = [cid for cid, text in indexed if text == current]
        if same:
            stale.extend(same[1:])                                          # identical duplicates
            stale.extend(cid for cid, text in indexed if text != current)  # older texts left by a failed run
            continue
        to_add.append(entry)
        stale.extend(cid for cid, _ in indexed)                             # replaced once the new one is in
    for key, chunks in by_question.items():
        if key not in wanted:
            stale.extend(cid for cid, _ in chunks)                          # no longer in the document
    return to_add, stale


async def _archive_documents_without_chunks(collection, document_ids: set[str]) -> int:
    """Documents whose index chunks were all replaced are archived (status inactive), never deleted."""
    if not document_ids:
        return 0
    from sqlalchemy import update
    from app.db.session import async_session_factory
    from app.models.document import Document, DocumentVersion
    empty = [d for d in document_ids if not collection.get(where={"document_id": d}, include=[]).get("ids")]
    if not empty:
        return 0
    async with async_session_factory() as db:
        ids = [uuid.UUID(d) for d in empty]
        await db.execute(update(Document).where(Document.id.in_(ids)).values(status="inactive"))
        await db.execute(update(DocumentVersion).where(DocumentVersion.document_id.in_(ids)).values(active=False))
        await db.commit()
    return len(empty)


async def _add_missing(entries: list[ParsedEntry], department_override: str | None) -> dict:
    """Additive, idempotent update of the FAQ index (see _missing_or_changed). The new chunks are indexed FIRST;
    superseded chunks are removed only after that succeeded, so a failed run (e.g. the embedding service is
    unavailable) leaves the previous knowledge in place and the next run finishes the job."""
    from app.db.chroma import get_chroma_client
    from app.services.rag_service import COLLECTION_NAME
    collection = get_chroma_client().get_or_create_collection(name=COLLECTION_NAME,
                                                               metadata={"hnsw:space": "cosine"})
    to_add, stale = _missing_or_changed(entries, collection)
    print(f"{len(to_add)} entries to add or update; {len(stale)} superseded index chunks to remove afterwards; "
          f"retired sections skipped: {sorted(_retired_sections())}")
    for e in to_add:
        print(f"  + [{e.section}] {e.question[:80]}")
    if to_add:
        await _ingest_entries(to_add, department_override)      # raises on failure: nothing is removed then
    archived = 0
    if stale:
        old = collection.get(ids=stale, include=["metadatas"])
        doc_ids = {(m or {}).get("document_id") for m in old.get("metadatas", []) if (m or {}).get("document_id")}
        collection.delete(ids=stale)
        archived = await _archive_documents_without_chunks(collection, doc_ids)
    result = {"added": len(to_add), "removed": len(stale), "archived_documents": archived,
              "faq_chunks": len(collection.get(where={"document_type": "faq"}, include=[]).get("ids", []))}
    print(f"Done: {result}")
    return result


async def _ingest_entries(
    entries: list[ParsedEntry],
    department_override: str | None,
    clear_existing: bool = False,
) -> None:
    """Embed and store parsed entries in ChromaDB + PostgreSQL."""
    import chromadb

    from app.config import settings
    from app.db.session import async_session_factory
    from app.models.document import Document, DocumentVersion
    from app.db.chroma import get_chroma_client
    from app.providers.factory import create_embedding_provider
    from app.services.rag_service import COLLECTION_NAME

    embedding_provider = create_embedding_provider()

    chroma_client = get_chroma_client()
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if clear_existing:
        async with async_session_factory() as db:
            await _clear_existing_inline_docs(db, collection)

    # Group entries by section so each section becomes one Document record
    sections: dict[str, list[ParsedEntry]] = {}
    for entry in entries:
        sections.setdefault(entry.section, []).append(entry)

    total_chunks = 0

    async with async_session_factory() as db:
        for section_name, section_entries in sections.items():
            department = department_override or section_name
            title = f"University FAQ — {section_name}"
            page_url = section_entries[0].page_url  # representative URL for the section

            logger.info(
                "Section [%s]: %d Q&A pairs → creating document record",
                section_name, len(section_entries),
            )

            # Create DB document record
            doc = Document(
                title=title,
                document_type="faq",
                department=department,
                status="processing",
            )
            db.add(doc)
            await db.flush()

            doc_version = DocumentVersion(
                document_id=doc.id,
                version=1,
                checksum=str(uuid.uuid4()),  # content hash not critical for FAQ entries
                effective_date=datetime.now(timezone.utc),
                storage_location="inline:docx",
            )
            db.add(doc_version)
            await db.flush()

            try:
                chunk_texts = [e.chunk_text for e in section_entries]
                embeddings = await embedding_provider.embed(chunk_texts)

                chunk_ids = [f"{doc.id}_{i}" for i in range(len(section_entries))]
                metadatas = [
                    {
                        "document_id": str(doc.id),
                        "version_id": str(doc_version.id),
                        "title": title,
                        "document_type": "faq",
                        "department": department,
                        CHROMA_SECTION_KEY: entry.section,
                        CHROMA_QUESTION_KEY: entry.question[:200],
                        CHROMA_PAGE_URL_KEY: entry.page_url or "",
                        "page": 1,
                        "effective_date": "",
                        "publication_date": "",
                    }
                    for entry in section_entries
                ]

                collection.add(
                    ids=chunk_ids,
                    embeddings=embeddings,
                    documents=chunk_texts,
                    metadatas=metadatas,
                )

                doc_version.chunk_count = len(section_entries)
                doc_version.indexed_at = datetime.now(timezone.utc)
                doc_version.active = True
                doc.status = "active"

                await db.commit()
                total_chunks += len(section_entries)
                logger.info(
                    "  [OK] doc_id=%s  chunks=%d  url=%s",
                    doc.id, len(section_entries), page_url or "(none)",
                )

            except Exception as exc:
                logger.error("Failed to ingest section [%s]: %s", section_name, exc, exc_info=True)
                doc.status = "error"
                doc_version.error_message = str(exc)
                await db.commit()
                raise

    await embedding_provider.close()
    logger.info("Done. Total chunks indexed: %d", total_chunks)


def _print_summary(entries: list[ParsedEntry]) -> None:
    from collections import Counter
    section_counts = Counter(e.section for e in entries)
    answered = len(entries)
    print(f"\n{'='*60}")
    print(f"  Parsed {answered} answered Q&A entries")
    print(f"{'='*60}")
    for section, count in section_counts.items():
        print(f"  {section:<40} {count:>4} entries")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a university FAQ DOCX into the knowledge base."
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to the university DOCX file (relative to project root or absolute).",
    )
    parser.add_argument(
        "--department", default=None,
        help="Override department name for all entries (default: section name).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse only — do not write to DB or ChromaDB.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print each parsed Q&A entry.",
    )
    parser.add_argument(
        "--clear-existing", action="store_true",
        help="Clear existing inline:docx records from DB and Chroma before ingestion.",
    )
    parser.add_argument(
        "--add-missing", action="store_true",
        help="Additive update: index only the entries missing from (or changed in) the search index; retired "
             "sections (e.g. Fee) are skipped; no database rows are deleted.",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        file_path = (Path.cwd() / args.file).resolve()
    if not file_path.exists():
        file_path = (_BACKEND_DIR.parent / args.file).resolve()

    if not file_path.exists():
        print(f"Error: file not found: {file_path}")
        sys.exit(1)

    print(f"\nParsing: {file_path}")
    entries = parse_university_docx(file_path)

    if not entries:
        print("No answerable Q&A entries found. Check your document format.")
        sys.exit(1)

    _print_summary(entries)

    if args.verbose:
        for i, e in enumerate(entries, 1):
            print(f"[{i}] [{e.section}]")
            print(f"     Q: {e.question}")
            print(f"     A: {e.answer[:120]}{'...' if len(e.answer) > 120 else ''}")
            print(f"     URL: {e.page_url or '(none)'}")
            print()

    if args.dry_run:
        print("[dry-run] Skipping DB/ChromaDB ingestion.")
        return

    if args.add_missing:
        print("Adding missing / changed entries to the knowledge base...")
        asyncio.run(_add_missing(entries, args.department))
        return
    print("Ingesting into knowledge base...")
    retired = _retired_sections()
    entries = [e for e in entries if e.section not in retired]   # never re-index a retired section
    asyncio.run(_ingest_entries(entries, args.department, clear_existing=args.clear_existing))
    print("\n[OK] University data ingested successfully!")


if __name__ == "__main__":
    main()
