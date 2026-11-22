"""Chat request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message."""

    conversation_id: UUID | None = Field(
        None, description="Existing conversation ID, or null to start a new one"
    )
    session_id: str = Field(
        ..., min_length=1, max_length=64, description="Browser-generated session UUID"
    )
    message: str = Field(
        ..., min_length=1, max_length=4000, description="User message text"
    )


class SourceReference(BaseModel):
    """A source citation returned with RAG answers."""

    document_id: str
    title: str
    section: str | None = None
    page: int | None = None
    page_url: str | None = None
    department: str | None = None
    effective_date: str | None = None


class ChatResponse(BaseModel):
    """Response to a chat message."""

    conversation_id: UUID
    message_id: UUID | None = None
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    cards: list[dict] = Field(default_factory=list)
    flow: dict | None = None
    agent: dict | None = None
    model: str | None = None


class MessageResponse(BaseModel):
    """A single message in a conversation."""

    id: UUID
    role: str
    content: str
    sources: list[SourceReference] | None = None
    suggestions: list[str] = Field(default_factory=list)
    cards: list[dict] = Field(default_factory=list)
    flow: dict | None = None
    agent: dict | None = None
    model: str | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Summary of a conversation for the sidebar."""

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    """Full conversation with all messages."""

    id: UUID
    title: str
    messages: list[MessageResponse]
    created_at: datetime


class FeedbackRequest(BaseModel):
    """Feedback on an assistant response."""

    session_id: str = Field(..., min_length=1, max_length=64)
    conversation_id: UUID
    message_id: UUID
    rating: int = Field(..., ge=-1, le=1, description="1 for thumbs up, -1 for thumbs down")
    comment: str | None = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Feedback submission confirmation."""

    id: UUID
    status: str = "received"


class ConversationRecoveryContext(BaseModel):
    """Structured information for recovering a previous student conversation."""

    has_resumable_conversation: bool
    conversation_id: str | None = None
    title: str | None = None
    last_active_at: datetime | None = None
    student_name: str | None = None
    topic: str | None = None
    program_name: str | None = None
    board_name: str | None = None
    academic_stage: str | None = None
    score_text: str | None = None
    assessment_status: str = "none"  # "completed" | "in_progress" | "none"
    scholarship_percent: float | None = None
    scholarship_label: str | None = None
    is_projected: bool = False
    welcome_message: str | None = None
    total_messages: int = 0
    workflow_step: str | None = None


class ResetSessionRequest(BaseModel):
    """Request to reset active conversation state while preserving identity and history."""

    session_id: str = Field(..., min_length=1, max_length=64)
    conversation_id: str | None = None


class ResetSessionResponse(BaseModel):
    """Response confirming session conversation reset."""

    status: str = "ok"
    session_id: str
    active_conversation_id: str | None = None
    new_conversation_id: str | None = None

