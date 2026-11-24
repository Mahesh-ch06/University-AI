"""Recovery service — smart conversation recovery and personalized welcome context."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ConversationRecoveryContext, ResetSessionResponse
from app.sru_agent import config as agent_config, journey, memory as agent_memory

logger = logging.getLogger(__name__)


def generate_welcome_message(
    student_name: Optional[str],
    assessment_status: str,
    scholarship_percent: Optional[float] = None,
    topic: Optional[str] = None,
) -> str:
    """Generate context-aware personalized welcome messages adhering strictly to Section 4 specifications."""
    clean_name = (student_name or "").strip().strip(",").strip()
    if clean_name:   # the first name, as the student wrote it ("Mahesh", not "Mahesh kumar")
        clean_name = clean_name.split()[0]
        clean_name = clean_name[:1].upper() + clean_name[1:]
    name_part = f", {clean_name}" if clean_name else ""

    if assessment_status == 'completed':
        if scholarship_percent is not None and scholarship_percent >= 40:
            return (
                f'Welcome back{name_part}! Your previous scholarship assessment showed a strong result, '
                f'with the highest available merit scholarship category (40% tuition fee waiver). '
                f'Would you like to continue where you left off or start a fresh conversation?'
            )
        elif scholarship_percent is not None and scholarship_percent >= 30:
            return (
                f'Welcome back{name_part}! Your previous assessment identified a promising merit scholarship '
                f'opportunity (30% fee waiver). Shall we continue where we stopped?'
            )
        elif scholarship_percent is not None and scholarship_percent > 0:
            pct_val = int(scholarship_percent) if scholarship_percent.is_integer() else scholarship_percent
            return (
                f'Welcome back{name_part}! I found your previous scholarship assessment with an eligible merit '
                f'scholarship ({pct_val}% fee waiver). Would you like to review your result or explore your admission options?'
            )
        else:
            return (
                f"Welcome back{name_part}! I found your previous assessment. While it didn't match an available "
                f"merit scholarship category under the criteria applied, we can review your details or explore "
                f"other admission opportunities."
            )


    elif assessment_status == 'in_progress':
        return (
            f'Welcome back{name_part}! You were partway through your scholarship assessment. '
            f'Your academic details are saved. Would you like to continue from where you left off?'
        )

    else:
        topic_phrase = ''
        if topic and topic.strip() and topic.strip().lower() not in ('chat', 'new conversation', 'sru buddy', 'sru admissions'):
            topic_phrase = f' about {topic.strip()}'
        return (
            f'Welcome back{name_part}! I found your previous conversation{topic_phrase}. '
            f'Would you like to continue where you left off or start a fresh conversation?'
        )


async def get_recovery_context(
    session_id: str,
    db: Optional[AsyncSession] = None,
) -> ConversationRecoveryContext:
    """Inspect previous journey and return rich structured recovery context."""
    if not session_id or not session_id.strip():
        return ConversationRecoveryContext(has_resumable_conversation=False)

    session_id = session_id.strip()
    profile = await agent_memory.get_profile(session_id)
    student_name = profile.get('name') or None

    conv_id_str: Optional[str] = None
    messages_count = 0
    last_active_at: Optional[datetime] = None
    title: Optional[str] = None
    last_assistant_meta: dict = {}
    last_user_message: Optional[str] = None

    # 1. The conversation this student was most recently ACTIVE in: the one with the latest message.
    #    (conversations.updated_at is not touched when messages are added, so it cannot be used.)
    async def _inspect_db(session: AsyncSession):
        nonlocal conv_id_str, messages_count, last_active_at, title, last_assistant_meta, last_user_message
        latest = func.max(Message.created_at).label("latest")
        stmt = (
            select(Conversation.id, Conversation.title, latest, func.count(Message.id))
            .join(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.session_id == session_id)
            .group_by(Conversation.id, Conversation.title)
            .order_by(desc(latest))
            .limit(1)
        )
        row = (await session.execute(stmt)).first()
        if not row:
            return
        conv_uuid, title, last_active_at, messages_count = row[0], row[1], row[2], int(row[3] or 0)
        conv_id_str = str(conv_uuid)
        recent = (await session.execute(
            select(Message).where(Message.conversation_id == conv_uuid)
            .order_by(desc(Message.created_at)).limit(12))).scalars().all()
        for m in recent:
            if m.role == 'assistant' and m.metadata_ and not last_assistant_meta:
                last_assistant_meta = m.metadata_
            if m.role == 'user' and last_user_message is None and (m.content or '').strip():
                last_user_message = m.content.strip()[:120]

    if db is not None:
        try:
            await _inspect_db(db)
        except Exception as e:
            logger.warning('Database inspection failed in get_recovery_context: %s', e)
    else:
        try:
            async with async_session_factory() as local_db:
                await _inspect_db(local_db)
        except Exception as e:
            logger.warning('DB session factory unavailable for recovery context: %s', e)

    # 2. Database unavailable: a conversation still held in the agent's memory can be offered, but only with
    #    its REAL id (from the memory key). An id is never invented: continuing must reach the same chat.
    if not conv_id_str or messages_count == 0:
        prefix = f"sru:history:{session_id}:"
        for store in (getattr(agent_memory, "_hot", {}), getattr(agent_memory, "_local", {})):
            for k in list(store.keys()):
                if not k.startswith(prefix):
                    continue
                raw_val = store.get(k)
                val = raw_val[1] if isinstance(raw_val, tuple) and len(raw_val) > 1 else raw_val
                if isinstance(val, list) and val:
                    conv_id_str = k[len(prefix):]
                    messages_count = len(val)
                    first_user = next((h.get('text', '') for h in val if h.get('role') == 'user'), '')
                    title = title or (first_user[:45] or 'Chat')
                    last_user_message = next((h.get('text', '')[:120] for h in reversed(val)
                                              if h.get('role') == 'user'), None)
                    last_active_at = None  # unknown: the student is asked rather than guessed for
                    break
            if conv_id_str:
                break

    # If still no conversation or zero messages, check if there is an active profile/state
    if not conv_id_str or messages_count == 0:
        return ConversationRecoveryContext(has_resumable_conversation=False)

    # 3. Retrieve structured conversation state
    state = await agent_memory.get_conversation_state(session_id, conv_id_str)
    if not state and conv_id_str:
        # Also check without conv_id key
        state = await agent_memory.get_conversation_state(session_id)

    # 4. Determine assessment status and details
    fee_known = state.get('known', {})
    waiting_for = state.get('waiting_for')
    counsellor_mode = state.get('counsellor_mode', False)

    program_name = (
        profile.get('program_interest')
        or fee_known.get('program')
        or state.get('active_program')
    )
    if program_name:
        prog_key = str(program_name).lower().strip()
        PROGRAM_LABELS = {
            "btech_cse": "B.Tech Computer Science & Engineering",
            "btech_ai_ds": "B.Tech AI & Data Science",
            "btech_ece": "B.Tech Electronics & Communication",
            "btech_eee": "B.Tech Electrical & Electronics",
            "btech_mech": "B.Tech Mechanical Engineering",
            "btech_civil": "B.Tech Civil Engineering",
        }
        program_name = PROGRAM_LABELS.get(prog_key) or (
            str(program_name).replace("_", " ").title() if "_" in str(program_name) else str(program_name)
        )

    board_name = profile.get('board_label') or profile.get('board')
    if board_name:
        b_key = str(board_name).lower().strip()
        BOARD_LABELS = {
            "state_board": "Telangana / AP State Board",
            "ts_state_board": "Telangana State Board (TSBIE)",
            "bieap": "Andhra Pradesh (BIEAP)",
            "cbse": "CBSE",
            "icse": "ICSE / ISC",
            "ib": "International Baccalaureate (IB)",
        }
        board_name = BOARD_LABELS.get(b_key) or (
            str(board_name).replace("_", " ").title() if "_" in str(board_name) else str(board_name)
        )

    academic_stage = profile.get('stage_label') or profile.get('academic_stage')
    if academic_stage:
        s_key = str(academic_stage).lower().strip()
        STAGE_LABELS = {
            "inter_1st": "Intermediate 1st Year",
            "inter_2nd": "Intermediate 2nd Year",
            "1st_year": "Intermediate 1st Year",
            "2nd_year": "Intermediate 2nd Year",
            "completed": "Completed Intermediate",
        }
        academic_stage = STAGE_LABELS.get(s_key) or (
            str(academic_stage).replace("_", " ").title() if "_" in str(academic_stage) else str(academic_stage)
        )

    is_projected = bool(profile.get('is_projected'))

    # Compute formatted score text
    score_text = None
    raw_marks = profile.get('raw_marks') or fee_known.get('raw_marks')
    max_marks = profile.get('max_marks') or fee_known.get('max_marks')
    percent = profile.get('percent') or fee_known.get('percent')
    eapcet_rank = profile.get('eapcet_rank') or fee_known.get('eapcet_rank')
    jee_percentile = profile.get('jee_percentile') or fee_known.get('jee_percentile')

    def _n(v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return str(v)
        return str(int(f)) if f == int(f) else f'{f:g}'

    if raw_marks and max_marks:
        pct_display = f'{_n(round(float(percent), 1))}%' if percent else ''
        score_text = f'{_n(raw_marks)} / {_n(max_marks)} ({pct_display})' if pct_display else f'{_n(raw_marks)} / {_n(max_marks)}'
    elif percent:
        score_text = f'{percent:.1f}%' if isinstance(percent, float) else f'{percent}%'
    elif eapcet_rank:
        score_text = f'TG EAPCET Rank: {eapcet_rank:,}'
    elif jee_percentile:
        score_text = f'JEE Main: {jee_percentile}%ile'

    # Check for completed calculation result
    scholarship_percent: Optional[float] = None
    scholarship_label: Optional[str] = None
    assessment_status = 'none'

    if profile.get('scholarship_percent') is not None:
        try:
            scholarship_percent = float(profile['scholarship_percent'])
        except (ValueError, TypeError):
            pass

    # Check assistant metadata cards for fee calculation results
    cards = last_assistant_meta.get('cards') or []
    for c in cards:
        if c.get('type') in ('calculate_fee', 'counsellor_assessment'):
            c_data = c.get('data', {})
            if 'scholarship_percent' in c_data:
                try:
                    scholarship_percent = float(c_data['scholarship_percent'])
                except (ValueError, TypeError):
                    pass
            if c_data.get('program'):
                program_name = program_name or c_data.get('program')

    if scholarship_percent is not None or waiting_for == 'done' or any(c.get('type') in ('calculate_fee', 'counsellor_assessment') for c in cards):
        assessment_status = 'completed'
        if scholarship_percent is not None:
            if scholarship_percent >= 40:
                scholarship_label = '40% Merit Scholarship (Highest Tier)'
            elif scholarship_percent >= 30:
                scholarship_label = '30% Merit Scholarship'
            elif scholarship_percent >= 25:
                scholarship_label = '25% Merit Scholarship'
            elif scholarship_percent > 0:
                pct_val = int(scholarship_percent) if scholarship_percent.is_integer() else scholarship_percent
                scholarship_label = f'{pct_val}% Merit Scholarship'
            else:
                scholarship_label = 'No eligible scholarship slab found'
        else:
            scholarship_label = 'Scholarship Calculation Complete'

    elif counsellor_mode or waiting_for in ('board', 'stage', 'marks', 'route', 'program', 'calc') or (raw_marks and not scholarship_percent):
        assessment_status = 'in_progress'
        scholarship_label = 'Assessment in Progress'

    # Determine topic
    topic = None
    if assessment_status in ('completed', 'in_progress'):
        prog_display = program_name or 'B.Tech'
        topic = f'{prog_display} Scholarship Assessment'
    elif title and title not in ('New conversation', 'Chat', ''):
        topic = title
    else:
        topic = 'SR University Admissions'

    welcome_msg = generate_welcome_message(
        student_name=student_name,
        assessment_status=assessment_status,
        scholarship_percent=scholarship_percent,
        topic=topic,
    )

    threshold = max(1, int(agent_config.RECOVERY_RESUME_AFTER_MINUTES))
    inactive_minutes: Optional[float] = None
    if last_active_at is not None:
        stamp = last_active_at if last_active_at.tzinfo else last_active_at.replace(tzinfo=timezone.utc)
        inactive_minutes = max(0.0, (datetime.now(timezone.utc) - stamp).total_seconds() / 60.0)
    # Ask only after a real break; when the time is unknown, ask rather than assume.
    offer_choice = inactive_minutes is None or inactive_minutes >= threshold

    return ConversationRecoveryContext(
        has_resumable_conversation=True,
        conversation_id=conv_id_str,
        title=title or topic,
        last_active_at=last_active_at,
        inactive_minutes=round(inactive_minutes, 1) if inactive_minutes is not None else None,
        resume_after_minutes=threshold,
        offer_choice=offer_choice,
        last_user_message=last_user_message,
        student_name=student_name,
        topic=topic,
        program_name=program_name,
        board_name=board_name,
        academic_stage=academic_stage,
        score_text=score_text,
        assessment_status=assessment_status,
        scholarship_percent=scholarship_percent,
        scholarship_label=scholarship_label,
        is_projected=is_projected,
        welcome_message=welcome_msg,
        total_messages=messages_count,
        workflow_step=waiting_for,
    )


async def reset_session_conversation(
    session_id: str,
    conversation_id: Optional[str] = None,
) -> ResetSessionResponse:
    """The student chose "Start a new conversation".

    The new conversation starts clean, and nothing of the old one is destroyed:
      * the old conversation, its messages and its own state stay as they are, so it can be reopened later and
        still knows what was discussed;
      * the academic details (board, marks, group, entrance score...) are filed with the old conversation
        (journey.scope_profile) and kept as a one-tap "Use my saved details" offer, never applied by themselves;
      * the programme the old conversation was about is not carried into the new one;
      * the student's own identity (name, mobile number, saved callback requests) is kept: it is not
        conversation context, and "Forget my details" removes it when the student wants that.
    """
    if not session_id or not session_id.strip():
        return ResetSessionResponse(session_id='', active_conversation_id=None, new_conversation_id=None)

    session_id = session_id.strip()
    new_conv_id = str(uuid.uuid4())

    profile = await agent_memory.get_profile(session_id)
    if conversation_id and not profile.get('academic_conv') and journey.snapshot(profile):
        # Details collected before conversation scoping belong to the conversation being left.
        profile['academic_conv'] = str(conversation_id)
    if profile.get('program_interest'):
        owner = profile.get('academic_conv') or conversation_id
        if owner:
            await agent_memory.update_conversation_state(session_id, owner,
                                                         program_interest=profile.get('program_interest'))
        profile.pop('program_interest', None)
    await journey.scope_profile(session_id, new_conv_id, profile, {})
    agent_memory.seed_new_conversation(session_id, new_conv_id)

    return ResetSessionResponse(
        status='ok',
        session_id=session_id,
        active_conversation_id=conversation_id,
        new_conversation_id=new_conv_id,
    )
