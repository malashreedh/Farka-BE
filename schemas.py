from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    data: T
    message: str = "success"


class ChatEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class ChatStartResponse(BaseModel):
    session_id: str
    message: str
    stage: str


class ChatMessageRequest(BaseModel):
    session_id: str
    content: str


class ChatMessageResponse(BaseModel):
    message: str
    stage: str
    profile_id: Optional[str] = None
    redirect: Optional[str] = None


class VoiceMessageResponse(ChatMessageResponse):
    transcript: str
    audio_base64: Optional[str] = None
    audio_mime_type: str = "audio/mpeg"


class AuthSessionRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class AuthSessionResponse(BaseModel):
    profile_id: str
    token: str


class ProfileBase(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    current_location: Optional[str] = None
    path: Optional[str] = None
    trade_category: Optional[str] = None
    years_experience: Optional[int] = None
    skills: Optional[list[str]] = None
    language_pref: Optional[str] = None
    district_target: Optional[str] = None
    has_savings: Optional[bool] = None
    savings_range: Optional[str] = None


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    id: str
    title: str
    org_name: str
    org_type: str
    district: str
    trade_category: str
    skill_tags: list[str]
    experience_level: str
    description: str
    salary_range: Optional[str] = None
    apply_url: str
    is_active: bool
    posted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobMatchRequest(BaseModel):
    profile_id: str


class JobMatchResponse(BaseModel):
    job: JobResponse
    match_score: float
    matched_tags: list[str]


class ChecklistItem(BaseModel):
    category: str
    week: int
    task: str
    done: bool = False


class ChecklistResponse(BaseModel):
    id: str
    profile_id: str
    trade: str
    district: str
    checklist_items: list[ChecklistItem]
    raw_ai_output: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChecklistGenerateRequest(BaseModel):
    profile_id: str


class ChecklistToggleRequest(BaseModel):
    checklist_id: str
    item_index: int
    done: bool


class AIProcessResult(BaseModel):
    reply: str
    extracted_data: dict[str, Any]
    next_stage: str
    redirect: Optional[str] = None
