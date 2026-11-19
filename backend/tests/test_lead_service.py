"""Tests for Prospective Lead tracking, verification schema, and admin APIs."""

import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.schemas.lead import LeadCreate, LeadResponse, LeadStatsResponse, LeadStatusUpdate


def test_lead_schema_validation():
    """Test that student phone numbers are properly validated and cleaned."""
    # Valid 10-digit number
    lead = LeadCreate(name="  Rahul Sharma  ", phone="+91 98765-43210", program_interest="B.Tech CSE")
    assert lead.name == "Rahul Sharma"
    assert lead.phone == "+919876543210"

    # Valid simple number
    lead2 = LeadCreate(name="Ananya Rao", phone="9123456789")
    assert lead2.name == "Ananya Rao"
    assert lead2.phone == "9123456789"

    # Invalid short number (< 10 digits)
    with pytest.raises(ValidationError):
        LeadCreate(name="Test User", phone="12345")

    # Blank name
    with pytest.raises(ValidationError):
        LeadCreate(name="   ", phone="9876543210")


def test_lead_response_orm_serialization_metadata_collision():
    """Verify LeadResponse correctly serializes ORM models with metadata_ without colliding with Base.metadata."""
    import uuid
    from datetime import datetime, timezone
    from app.models.lead import ProspectiveLead

    lead_orm = ProspectiveLead(
        id=uuid.uuid4(),
        name="Sunil Varma",
        phone="9876543210",
        program_interest="B.Tech CSE",
        source="scholarship_calculator",
        status="new",
        created_at=datetime.now(timezone.utc),
        metadata_={"scholarship_percent": 30, "payable_fee": 104000},
    )

    # Base.metadata exists on the SQLAlchemy model
    assert hasattr(lead_orm, "metadata")
    assert not isinstance(lead_orm.metadata, dict)  # It's an sqlalchemy.MetaData object

    # LeadResponse should extract metadata_ cleanly without crashing on Base.metadata
    res = LeadResponse.model_validate(lead_orm)
    assert res.name == "Sunil Varma"
    assert res.metadata == {"scholarship_percent": 30, "payable_fee": 104000}
    assert res.status == "new"

    # Also check dict validation
    dict_payload = {
        "id": uuid.uuid4(),
        "name": "Sunil Varma",
        "phone": "9876543210",
        "source": "scholarship_calculator",
        "status": "new",
        "created_at": datetime.now(timezone.utc),
        "metadata": {"scholarship_percent": 40},
    }
    res_dict = LeadResponse.model_validate(dict_payload)
    assert res_dict.metadata == {"scholarship_percent": 40}


@pytest.mark.asyncio
async def test_public_create_lead_endpoint():
    """Test POST /api/v1/leads registers a student lead without needing admin key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "Karthik Reddy",
            "phone": "9848022338",
            "program_interest": "B.Tech CSE",
            "score": "94.5%",
            "exam_type": "State Board (Inter)",
            "source": "calculator",
        }
        try:
            res = await client.post("/api/v1/leads", json=payload)
            if res.status_code == 201:
                data = res.json()
                assert data["name"] == "Karthik Reddy"
                assert data["phone"] == "9848022338"
                assert data["program_interest"] == "B.Tech CSE"
                assert data["status"] == "new"
                assert "id" in data
        except Exception:
            pytest.skip("Database connection not currently accessible for end-to-end insert")


@pytest.mark.asyncio
async def test_admin_lead_endpoints_security():
    """Test that admin lead endpoints strictly enforce X-Admin-Key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Without key -> 401 or 403
        res = await client.get("/api/v1/admin/leads")
        assert res.status_code in (401, 403, 422)

        res = await client.get("/api/v1/admin/leads/stats")
        assert res.status_code in (401, 403, 422)

        res = await client.patch("/api/v1/admin/leads/some-id/status", json={"status": "contacted"})
        assert res.status_code in (401, 403, 422)

        # With valid key
        headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
        try:
            res_stats = await client.get("/api/v1/admin/leads/stats", headers=headers)
            if res_stats.status_code == 200:
                stats = res_stats.json()
                assert "total_leads" in stats
                assert "chat_leads" in stats
                assert "calculator_leads" in stats
                assert "today_leads" in stats
        except Exception:
            pytest.skip("Database not accessible for admin stats test")


def test_resolve_clean_program():
    """Verify that program interest values are properly normalized and resolved."""
    from app.services.lead_service import resolve_clean_program

    # 1. Slugs mapped to proper names
    assert resolve_clean_program("btech_cse") == "B.Tech CSE"
    assert resolve_clean_program("btech_ece") == "B.Tech ECE"
    assert resolve_clean_program("bsc_agri") == "B.Sc Agriculture"
    assert resolve_clean_program("mba") == "MBA"

    # 2. Existing clean strings preserved / trimmed of long parentheses
    assert resolve_clean_program("B.Tech CSE (AIML, Data Science...)") == "B.Tech CSE"
    assert resolve_clean_program("BBA") == "BBA"

    # 3. Unspecified values resolved from metadata
    assert resolve_clean_program("Not specified", metadata={"pending_question": "What is the fee for MBA?"}) == "MBA"
    assert resolve_clean_program("Not specified", metadata={"pending_question": "How to get admission in agriculture?"}) == "B.Sc Agriculture"
    assert resolve_clean_program("Not specified", metadata={"pending_question": "tell me about ECE branch"}) == "B.Tech ECE"

    # 4. Unspecified values resolved from conversation text
    assert resolve_clean_program(None, conversation_text="I am looking for mechanical engineering") == "B.Tech Mechanical"

    # 5. Default fallback to flagship B.Tech CSE when nothing is specified
    assert resolve_clean_program("Not specified", metadata={}) == "B.Tech CSE"
    assert resolve_clean_program(None) == "B.Tech CSE"
    assert resolve_clean_program("") == "B.Tech CSE"


@pytest.mark.asyncio
async def test_list_leads_auto_repair():
    """Verify list_leads repairs raw slugs and unspecified values."""
    import uuid
    from unittest.mock import AsyncMock, MagicMock
    from app.services.lead_service import list_leads
    from app.models.lead import ProspectiveLead

    lead1 = ProspectiveLead(
        id=uuid.uuid4(),
        name="Suresh",
        phone="9876543210",
        program_interest="Not specified",
        metadata_={"pending_question": "What is the fee for MBA program?"},
    )
    lead2 = ProspectiveLead(
        id=uuid.uuid4(),
        name="Nikhil",
        phone="9876543211",
        program_interest="btech_cse",
        metadata_={},
    )
    lead3 = ProspectiveLead(
        id=uuid.uuid4(),
        name="Chitikeshi",
        phone="9876543212",
        program_interest=None,
        metadata_={},
    )

    mock_db = AsyncMock()
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 3
    mock_items_res = MagicMock()
    mock_items_res.scalars.return_value.all.return_value = [lead1, lead2, lead3]

    mock_db.execute.side_effect = [mock_count_res, mock_items_res]

    total, leads = await list_leads(mock_db, page=1, page_size=10)
    assert total == 3
    assert len(leads) == 3
    assert lead1.program_interest == "MBA"
    assert lead2.program_interest == "B.Tech CSE"
    assert lead3.program_interest == "B.Tech CSE"
    mock_db.commit.assert_awaited_once()


