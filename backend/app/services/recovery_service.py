"""Recovery service — smart conversation recovery and personalized welcome context."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ConversationRecoveryContext, ResetSessionResponse
from app.sru_agent import memory as agent_memory

logger = logging.getLogger(__name__)


def generate_welcome_message(
    student_name: Optional[str],
    assessment_status: str,
    scholarship_percent: Optional[float] = None,
    topic: Optional[str] = None,
) -> str:
    """Generate context-aware personalized welcome messages adhering strictly to Section 4 specifications."""
    clean_name = (student_name or '').strip()
    name_part = f', {clean_name}' if clean_name else ''

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

    conv_row = None
    conv_id_str: Optional[str] = None
    messages_count = 0
    last_active_at: Optional[datetime] = None
    title: Optional[str] = None
    last_assistant_meta: dict = {}

    # 1. Try to fetch most recent conversation from PostgreSQL
    async def _inspect_db(session: AsyncSession):
        nonlocal conv_row, conv_id_str, messages_count, last_active_at, title, last_assistant_meta
        stmt = (
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(desc(Conversation.updated_at))
            .limit(1)
        )
        res = await session.execute(stmt)
        conv = res.scalar_one_or_none()
        if conv:
            conv_row = conv
            conv_id_str = str(conv.id)
            title = conv.title
            last_active_at = conv.updated_at or conv.created_at

            # Count messages
            msg_stmt = (
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(desc(Message.created_at))
            )
            msg_res = await session.execute(msg_stmt)
            all_msgs = msg_res.scalars().all()
            messages_count = len(all_msgs)

            # Find last assistant message metadata for calculation cards
            for m in all_msgs:
                if m.role == 'assistant' and m.metadata_:
                    last_assistant_meta = m.metadata_
                    break

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

    # 2. Fallback to in-memory / redis history if DB returned nothing or failed
    if not conv_id_str or messages_count == 0:
        history = await agent_memory.get_history(session_id)
        if history:
            messages_count = len(history)
            conv_id_str = conv_id_str or str(uuid.uuid4())
            title = title or (history[0].get('text', '')[:45] if history else 'Chat')
            last_active_at = datetime.now(timezone.utc)
        else:
            # Check in-memory stores for scoped conversations: sru:history:{session_id}:{conv_id}
            prefix = f"sru:history:{session_id}"
            found_key = None
            found_hist = None
            for store in (getattr(agent_memory, "_hot", {}), getattr(agent_memory, "_local", {})):
                for k in list(store.keys()):
                    if k.startswith(prefix) and store.get(k):
                        raw_val = store[k]
                        val = raw_val[1] if isinstance(raw_val, tuple) and len(raw_val) > 1 else raw_val
                        if isinstance(val, list) and len(val) > 0:
                            found_key = k
                            found_hist = val
                            break
                if found_key:
                    break
            if found_key and found_hist:
                parts = found_key.split(":")
                if len(parts) >= 4:
                    conv_id_str = parts[3]
                else:
                    conv_id_str = str(uuid.uuid4())
                messages_count = len(found_hist)
                title = title or (found_hist[0].get('text', '')[:45] if found_hist else 'Chat')
                last_active_at = datetime.now(timezone.utc)

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
    board_name = profile.get('board_label') or profile.get('board')
    academic_stage = profile.get('stage_label') or profile.get('academic_stage')
    is_projected = bool(profile.get('is_projected'))

    # Compute formatted score text
    score_text = None
    raw_marks = profile.get('raw_marks') or fee_known.get('raw_marks')
    max_marks = profile.get('max_marks') or fee_known.get('max_marks')
    percent = profile.get('percent') or fee_known.get('percent')
    eapcet_rank = profile.get('eapcet_rank') or fee_known.get('eapcet_rank')
    jee_percentile = profile.get('jee_percentile') or fee_known.get('jee_percentile')

    if raw_marks and max_marks:
        pct_display = f'{percent:.1f}%' if percent else ''
        score_text = f'{raw_marks} / {max_marks} ({pct_display})' if pct_display else f'{raw_marks} / {max_marks}'
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

    return ConversationRecoveryContext(
        has_resumable_conversation=True,
        conversation_id=conv_id_str,
        title=title or topic,
        last_active_at=last_active_at or datetime.now(timezone.utc),
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
    """Reset active conversation state for a fresh start while preserving verified identity & database records."""
    if not session_id or not session_id.strip():
        return ResetSessionResponse(session_id='', active_conversation_id=None, new_conversation_id=None)

    session_id = session_id.strip()

    # Clear active conversation state in memory & cache
    await agent_memory.clear_conversation_state(session_id, conversation_id)
    if conversation_id:
        await agent_memory.clear_conversation_state(session_id, None)

    # Remove temporary counselling progress keys while retaining verified lead identity (name, phone, email, city)
    await agent_memory.remove_profile_keys(
        session_id,
        'board',
        'board_label',
        'board_key',
        'academic_stage',
        'stage_label',
        'raw_marks',
        'max_marks',
        'is_projected',
        'admission_route',
        'route_label',
        'scholarship_percent',
    )

    new_conv_id = str(uuid.uuid4())
    agent_memory.seed_new_conversation(session_id, new_conv_id)

    return ResetSessionResponse(
        status='ok',
        session_id=session_id,
        active_conversation_id=None,
        new_conversation_id=new_conv_id,
    )
