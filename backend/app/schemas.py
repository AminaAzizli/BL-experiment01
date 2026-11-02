from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def create_assignment_default() -> dict[str, str]:
    return {"version": "A", "persona": "baseline"}


class StudyCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    study_code: str | None = None
    ethics_status: str = "not_obtained"
    preregistration_version: str = "v0"
    invitation_link: str | None = None
    default_language: str = "en"


class StudyRead(BaseModel):
    id: int
    name: str
    description: str
    study_code: str
    ethics_status: str
    preregistration_version: str
    invitation_link: str | None = None
    default_language: str = "en"

    model_config = ConfigDict(from_attributes=True)


class ParticipantCreate(BaseModel):
    recruitment_source: str = "unknown"
    ui_language: str = "en"
    background_questions: dict[str, Any] = Field(default_factory=dict)
    assignment: dict[str, str] = Field(default_factory=create_assignment_default)


class ParticipantRead(BaseModel):
    id: int
    study_id: int
    participant_id: str
    recruitment_source: str
    ui_language: str
    background_questions: dict[str, Any]
    assigned_version: str
    assigned_persona: str
    consent_status: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class SessionCreate(BaseModel):
    study_id: int
    participant_id: str
    ui_language: str = "en"
    assigned_version: str = "A"
    status: str = "in_progress"
    task_instructions: str = ""
    task_log: str = ""


class SessionRead(BaseModel):
    id: int
    session_id: str
    study_id: int
    participant_id: str
    assigned_version: str
    ui_language: str
    status: str
    task_instructions: str
    task_log: str
    seq_score: int | None = None
    sus_score: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ConsentUpdate(BaseModel):
    consent_status: str = "consented"
    consented_at: datetime | None = None


class ResearchEventCreate(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., min_length=1, max_length=96)
    task_id: str | None = Field(default=None, max_length=32)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)


class ResearchEventBatch(BaseModel):
    events: list[ResearchEventCreate] = Field(..., min_length=1, max_length=500)


class EventBatchResult(BaseModel):
    accepted: int
    duplicates: int


class TaskMetrics(BaseModel):
    event_count: int
    duration_seconds: int
    completed: bool
    success: bool | None = None


class SessionMetrics(BaseModel):
    session_id: str
    event_count: int
    event_types: dict[str, int]
    task_metrics: dict[str, TaskMetrics]


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str = "BehaviourLens"
    environment: str = "development"
