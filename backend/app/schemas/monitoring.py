from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.monitoring_constants import ALLOWED_EVENT_TYPES, ALLOWED_SEVERITIES
from app.schemas.evidence import EvidenceResponse

EventType = Literal[
    "HEAD_LEFT",
    "HEAD_RIGHT",
    "HEAD_UP",
    "HEAD_DOWN",
    "LOOKING_AWAY",
    "FACE_ABSENT",
    "MULTIPLE_FACES",
    "MOBILE_PHONE",
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
    # Optional, defaulting to the value every caller relied on implicitly
    # before this field existed (the MonitoringEvent.source column default
    # -- see app/models/monitoring_event.py) so a request that omits it is
    # unchanged from before Milestone 6 Phase 2 Step 5. Added so the new
    # YOLOX mobile-phone-detection pipeline (Milestone 6) can identify
    # itself as "browser_yolox" instead of being mislabeled as MediaPipe.
    source: str = "browser_mediapipe"
    # Deliberately unconstrained (no max_length/format validation) at the
    # schema level: an invalid or oversized image must be rejected by the
    # route handler AFTER the event itself is created, never by failing
    # request validation for the whole payload. See
    # app/services/evidence_storage.py for the actual validation.
    evidence_image_base64: str | None = None


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
    evidence: EvidenceResponse | None = None


# The three states MonitoringEvent.status can hold: the AI-created default
# (PENDING_REVIEW) and the two admin decisions from the Phase 7A review
# endpoint (CONFIRMED / IGNORED). Kept separate from
# app.schemas.admin_action.ReviewAction, which models only the two values an
# admin may *submit* -- this type also needs to describe the pre-review
# default so it can be used as a listing filter.
EventStatus = Literal["PENDING_REVIEW", "CONFIRMED", "IGNORED"]


class MonitoringEventAdminResponse(BaseModel):
    """A single row of the admin monitoring-events review queue.

    Built manually from a joined query (see
    app/api/routes/monitoring.py::list_monitoring_events) rather than via
    from_attributes, since it combines fields from MonitoringEvent, Student,
    and Exam. Deliberately excludes Evidence.image_path.
    """

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
    evidence_id: int | None
    student_id: str
    student_full_name: str
    exam_id: int
    exam_title: str


class MonitoringEventListResponse(BaseModel):
    items: list[MonitoringEventAdminResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
