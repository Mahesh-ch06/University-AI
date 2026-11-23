import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sru_agent import memory as agent_memory
from app.services import recovery_service
from app.schemas.chat import ConversationRecoveryContext


@pytest.mark.asyncio
async def test_recovery_no_previous_conversation():
    session_id = f"test-recovery-empty-{uuid.uuid4().hex[:8]}"
    ctx = await recovery_service.get_recovery_context(session_id)
    assert isinstance(ctx, ConversationRecoveryContext)
    assert ctx.has_resumable_conversation is False
    assert ctx.conversation_id is None
    assert ctx.assessment_status == "none"


@pytest.mark.asyncio
async def test_recovery_40_percent_scholarship():
    session_id = f"test-recovery-40-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Mahesh",
        program_interest="B.Tech Computer Science & Engineering",
        board_label="Telangana State Board (TSBIE)",
        stage_label="Intermediate 2nd Year (12th)",
        raw_marks=985,
        max_marks=1000,
        percent=98.5,
        scholarship_percent=40.0,
    )
    await agent_memory.append_history(
        session_id,
        "What is my scholarship for 985 marks?",
        "Congratulations! Based on your 98.5%, you qualify for a 40% Merit Scholarship.",
        conversation_id=conv_id,
    )
    await agent_memory.update_conversation_state(
        session_id,
        conv_id,
        waiting_for="done",
        active_program="B.Tech Computer Science & Engineering",
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.student_name == "Mahesh"
    assert ctx.assessment_status == "completed"
    assert ctx.scholarship_percent == 40.0
    assert "40% Merit Scholarship" in (ctx.scholarship_label or "")
    assert "highest available merit scholarship category (40% tuition fee waiver)" in ctx.welcome_message
    assert "Welcome back, Mahesh!" in ctx.welcome_message


@pytest.mark.asyncio
async def test_recovery_30_percent_scholarship():
    session_id = f"test-recovery-30-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Ananya",
        program_interest="B.Tech CSE",
        board_label="CBSE",
        stage_label="12th Completed",
        raw_marks=440,
        max_marks=470,
        percent=93.6,
        scholarship_percent=30.0,
    )
    await agent_memory.append_history(
        session_id,
        "Calculate my fee waiver",
        "You are eligible for a 30% Merit Scholarship.",
        conversation_id=conv_id,
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.student_name == "Ananya"
    assert ctx.assessment_status == "completed"
    assert ctx.scholarship_percent == 30.0
    assert "promising merit scholarship opportunity (30% fee waiver)" in ctx.welcome_message
    assert "Welcome back, Ananya!" in ctx.welcome_message


@pytest.mark.asyncio
async def test_recovery_25_percent_scholarship():
    session_id = f"test-recovery-25-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Rahul",
        program_interest="B.Tech ECE",
        percent=88.0,
        scholarship_percent=25.0,
    )
    await agent_memory.append_history(
        session_id,
        "Check my scholarship",
        "Your score qualifies for a 25% Merit Scholarship.",
        conversation_id=conv_id,
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.student_name == "Rahul"
    assert ctx.assessment_status == "completed"
    assert ctx.scholarship_percent == 25.0
    assert "eligible merit scholarship (25% fee waiver)" in ctx.welcome_message


@pytest.mark.asyncio
async def test_recovery_unmatched_scholarship():
    session_id = f"test-recovery-0-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Kiran",
        program_interest="B.Tech Mechanical",
        percent=62.0,
        scholarship_percent=0.0,
    )
    await agent_memory.append_history(
        session_id,
        "Can I get scholarship with 62%?",
        "Merit scholarships begin at 75%. While not matching merit scholarship, admissions are open.",
        conversation_id=conv_id,
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.assessment_status == "completed"
    assert ctx.scholarship_percent == 0.0
    assert "While it didn't match an available merit scholarship category" in ctx.welcome_message
    assert "explore other admission opportunities" in ctx.welcome_message


@pytest.mark.asyncio
async def test_recovery_incomplete_assessment():
    session_id = f"test-recovery-inc-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Pooja",
        program_interest="B.Tech CSE",
        board_label="Telangana Intermediate (TSBIE)",
    )
    await agent_memory.append_history(
        session_id,
        "I am from Telangana Intermediate board",
        "Are you in 1st year, 2nd year, or completed 12th?",
        conversation_id=conv_id,
    )
    await agent_memory.update_conversation_state(
        session_id,
        conv_id,
        counsellor_mode=True,
        waiting_for="stage",
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.student_name == "Pooja"
    assert ctx.assessment_status == "in_progress"
    assert ctx.workflow_step == "stage"
    assert "partway through your scholarship assessment" in ctx.welcome_message
    assert "Your academic details are saved" in ctx.welcome_message


@pytest.mark.asyncio
async def test_recovery_general_admission_inquiry():
    session_id = f"test-recovery-gen-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Mahesh",
    )
    await agent_memory.append_history(
        session_id,
        "What are the hostel rules and curfew timings?",
        "Hostel curfew is 9:00 PM with 24/7 security and biometric attendance.",
        conversation_id=conv_id,
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.student_name == "Mahesh"
    assert ctx.assessment_status == "none"
    assert "Welcome back, Mahesh!" in ctx.welcome_message
    assert "previous conversation" in ctx.welcome_message


@pytest.mark.asyncio
async def test_recovery_without_student_name():
    session_id = f"test-recovery-noname-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.append_history(
        session_id,
        "Tell me about B.Tech CSE placements",
        "SR University had ₹51 LPA highest package at Microsoft and 91% placement rate.",
        conversation_id=conv_id,
    )

    ctx = await recovery_service.get_recovery_context(session_id)
    assert ctx.has_resumable_conversation is True
    assert ctx.student_name is None
    assert ctx.welcome_message.startswith("Welcome back!")
    assert ", !" not in ctx.welcome_message


@pytest.mark.asyncio
async def test_reset_session_conversation_preserves_lead_identity():
    session_id = f"test-recovery-reset-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    # Set up profile with lead identity and temporary counselling marks
    await agent_memory.update_profile(
        session_id,
        name="Suresh Kumar",
        phone="9876543210",
        board_label="TSBIE",
        raw_marks=950,
        max_marks=1000,
        scholarship_percent=30.0,
    )
    await agent_memory.update_conversation_state(
        session_id,
        conv_id,
        counsellor_mode=True,
        waiting_for="done",
    )

    # Perform session conversation reset
    resp = await recovery_service.reset_session_conversation(session_id, conv_id)
    assert resp.status == "ok"
    assert resp.new_conversation_id is not None

    # Verify verified identity is preserved
    profile = await agent_memory.get_profile(session_id)
    assert profile.get("name") == "Suresh Kumar"
    assert profile.get("phone") == "9876543210"

    # Verify temporary marks were reset
    assert "raw_marks" not in profile
    assert "scholarship_percent" not in profile

    # The old conversation is NOT wiped (v4.8.0): it keeps its state, and the academic details are filed with
    # it, so continuing it later still knows what was discussed. The new conversation starts clean (above).
    state = await agent_memory.get_conversation_state(session_id, conv_id)
    assert state["waiting_for"] == "done" and state["counsellor_mode"] is True
    assert state["academic"]["raw_marks"] == 950


@pytest.mark.asyncio
async def test_recovery_endpoints_via_http():
    session_id = f"test-http-recovery-{uuid.uuid4().hex[:8]}"
    conv_id = str(uuid.uuid4())

    await agent_memory.update_profile(
        session_id,
        name="Divya",
        program_interest="B.Tech Data Science",
        scholarship_percent=40.0,
    )
    await agent_memory.append_history(
        session_id,
        "Hi, what is my scholarship?",
        "You get 40% scholarship!",
        conversation_id=conv_id,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test recovery-context endpoint
        res = await client.get(f"/api/v1/agent/recovery-context?session_id={session_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["has_resumable_conversation"] is True
        assert data["student_name"] == "Divya"
        assert data["scholarship_percent"] == 40.0
        assert "40% tuition fee waiver" in data["welcome_message"]

        # Test reset-session endpoint
        reset_res = await client.post(
            "/api/v1/agent/reset-session",
            json={"session_id": session_id, "conversation_id": conv_id},
        )
        assert reset_res.status_code == 200
        reset_data = reset_res.json()
        assert reset_data["status"] == "ok"
        assert reset_data["new_conversation_id"] is not None


@pytest.mark.asyncio
async def test_continue_conversation_preserves_collected_facts_without_duplicate_questions():
    """Verify Section 7: All collected fields are preserved so resuming never asks for previously provided info."""
    from app.sru_agent.fee_intake import decide

    profile = {
        "name": "Mahesh",
        "program_interest": "B.Tech Computer Science & Engineering",
        "board": "state_board",
        "board_key": "ts_state_board",
        "academic_stage": "inter_2nd",
        "stage_label": "Intermediate 2nd Year",
        "raw_marks": 965,
        "max_marks": 1000,
        "percent": 96.5,
    }
    intake = {
        "waiting_for": "route",
        "counsellor_mode": True,
        "turns": 2,
        **profile,
    }

    # Student returns, chooses 'Continue Conversation', and provides their rank
    res = decide("TG EAPCET rank 4500", intake, profile)

    # State must calculate and must NOT re-ask for board, stage, or marks
    assert res.get("action") == "calculate"
    assert "Which board did you study in" not in (res.get("ask") or "")
    assert "Are you in 1st year" not in (res.get("ask") or "")
    assert "How many marks did you score" not in (res.get("ask") or "")


