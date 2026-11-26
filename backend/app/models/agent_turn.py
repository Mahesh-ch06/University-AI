"""A private receipt for an admissions-agent submission and its optional edit checkpoint."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentTurn(Base):
    __tablename__ = "agent_turns"

    request_id: Mapped[UUID] = mapped_column(primary_key=True)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    user_message_id: Mapped[UUID | None]
    answer_id: Mapped[UUID | None]
    effect_started: Mapped[bool] = mapped_column(default=False)
    snapshot: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
