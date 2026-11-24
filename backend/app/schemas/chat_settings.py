"""Admin panel: chat behaviour settings (v4.12.0). See app/services/app_settings.py."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.services.app_settings import ChatAd, EventHighlight, VideoSettings, WelcomeTile


class ChatSettingsResponse(BaseModel):
    settings: dict
    descriptions: dict
    updated_at: Optional[str] = None


class ChatSettingsUpdate(BaseModel):
    """Only the settings sent are changed."""

    concession_picker: Optional[Literal["grouped", "table"]] = None
    connect_enabled: Optional[bool] = None
    ai_answers: Optional[bool] = None
    suggestion_chips: Optional[Literal["questions_only", "always"]] = None
    fee_questions: Optional[Literal["evaluate_first", "fee_card"]] = None
    welcome_tiles: Optional[list[WelcomeTile]] = Field(None, max_length=8)
    event_highlights: Optional[list[EventHighlight]] = Field(None, max_length=16)
    videos: Optional[VideoSettings] = None
    chat_ads: Optional[list[ChatAd]] = Field(None, max_length=6)
    ads_rotate_seconds: Optional[int] = Field(None, ge=4, le=60)
    connect_wait_seconds: Optional[int] = Field(None, ge=10, le=120)
    office_hours_start: Optional[str] = Field(None, max_length=5)
    office_hours_end: Optional[str] = Field(None, max_length=5)
    office_days: Optional[list[int]] = Field(None, max_length=7)
