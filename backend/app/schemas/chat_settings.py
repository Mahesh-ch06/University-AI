"""Admin panel: chat behaviour settings (v4.12.0). See app/services/app_settings.py."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.services.app_settings import WelcomeTile


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
    welcome_tiles: Optional[list[WelcomeTile]] = Field(None, max_length=8)
    connect_wait_seconds: Optional[int] = Field(None, ge=10, le=120)
    office_hours_start: Optional[str] = Field(None, max_length=5)
    office_hours_end: Optional[str] = Field(None, max_length=5)
    office_days: Optional[list[int]] = Field(None, max_length=7)
