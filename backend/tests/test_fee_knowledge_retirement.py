"""Retired fee knowledge is never served: obsolete fee chunks leave the vector index, the FAQ fee document that
predates the 2027-28 circular is archived (not deleted), and cached RAG answers are keyed to the fee policy."""
import uuid

import chromadb
import pytest
from sqlalchemy import select

from app.config import settings
from app.services import auto_seed, cache_service


@pytest.fixture
def maker(monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    import app.db.session as db_session

    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(db_session, "async_session_factory", factory)
    return factory


@pytest.mark.asyncio
async def test_obsolete_fee_chunks_are_removed_and_the_old_faq_is_archived(tmp_path, monkeypatch, maker):
    from app.models.document import Document, DocumentVersion

    client = chromadb.PersistentClient(path=str(tmp_path))
    monkeypatch.setattr(auto_seed, "get_chroma_client", lambda: client)
    col = client.get_or_create_collection(name=auto_seed.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    col.add(ids=["old-faq", "old-handbook", "current"], embeddings=[[0.1, 0.2], [0.2, 0.1], [0.3, 0.3]],
            documents=["The annual tuition fee for B.Tech CSE is Rs. 2,10,000 plus other fees.",
                       "Hostel: caution deposit ₹5,000 and laundry per year ₹5,000.",
                       "B.Tech CSE tuition is ₹3,40,000 a year, split equally between the two semesters."],
            metadatas=[{"title": "University FAQ — Fee"}, {"title": "SRU Student Handbook"},
                       {"title": "SRU Student Handbook"}])

    doc_id = uuid.uuid4()
    async with maker() as s:
        s.add(Document(id=doc_id, title="University FAQ — Fee", document_type="faq", status="active"))
        s.add(DocumentVersion(document_id=doc_id, checksum="x" * 64, storage_location="inline:docx", active=True))
        await s.commit()
    try:
        assert await auto_seed.retire_obsolete_fee_knowledge() == 2
        assert col.get()["ids"] == ["current"]
        async with maker() as s:
            doc = (await s.execute(select(Document).where(Document.id == doc_id))).scalar_one()
            ver = (await s.execute(select(DocumentVersion).where(DocumentVersion.document_id == doc_id))).scalar_one()
            assert doc.status == "inactive" and ver.active is False        # archived, not deleted
        assert await auto_seed.retire_obsolete_fee_knowledge() == 0       # idempotent
    finally:
        async with maker() as s:
            for row in (await s.execute(select(DocumentVersion).where(DocumentVersion.document_id == doc_id))).scalars():
                await s.delete(row)
            await s.delete((await s.execute(select(Document).where(Document.id == doc_id))).scalar_one())
            await s.commit()


def test_rag_cache_keys_change_with_the_fee_policy():
    assert cache_service._knowledge_fingerprint() in cache_service.make_cache_key("what is the cse fee")
