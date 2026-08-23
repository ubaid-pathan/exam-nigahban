from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.monitoring_constants import ALLOWED_EVENT_TYPES, ALLOWED_SEVERITIES

EventType = Literal[
    "HEAD_LEFT",
    "HEAD_RIGHT",
    "HEAD_UP",
    "HEAD_DOWN",
    "LOOKING_AWAY",
    "FACE_ABSENT",
    "MULTIPLE_FACES",
]
Severity = Literal["low", "medium", "high"]

assert set(EventType.__args__) == ALLOWED_EVENT_TYPES
assert set(Severity.__args__) == ALLOWED_SEVERITIES


class MonitoringEventCreate(BaseModel):
    session_id: int
    event_type: EventType
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    duration_seconds: float = Field(ge=0.0)
    occurrences: int = Field(ge=1)


class MonitoringEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    event_type: str
    confidence: float
    duration_seconds: float
    occurrences: int
    severity: str
    source: str
    detected_at: datetime
    status: str
