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


# ---------------------------------------------------------------------------
# Session-level aggregation
# ---------------------------------------------------------------------------


class MonitoringSessionSummary(BaseModel):
    """All monitoring activity for one student's exam session, combined.

    A presentation-layer rollup only: every underlying MonitoringEvent row
    (and its own Evidence) is left completely intact. Merging events into a
    single stored record would destroy the per-detection evidence this
    system exists to produce, so the grouping happens here in the query
    rather than in the database.

    The counts describe the events matching the caller's filters, not the
    session's lifetime totals -- filtering by severity=high reports each
    session's high-severity activity, which is what makes the filtered
    view readable.
    """

    session_id: int
    session_status: str
    started_at: datetime
    ended_at: datetime | None

    student_id: str
    student_full_name: str
    exam_id: int
    exam_title: str

    total_events: int
    pending_events: int
    confirmed_events: int
    ignored_events: int
    high_severity_events: int
    evidence_count: int

    first_detected_at: datetime
    last_detected_at: datetime

    # event_type -> count, e.g. {"FACE_ABSENT": 3, "MOBILE_PHONE": 2}.
    # Built by a second grouped query scoped to the current page's session
    # ids, so listing N sessions never costs N queries.
    events_by_type: dict[str, int]


class MonitoringSessionListResponse(BaseModel):
    items: list[MonitoringSessionSummary]
    page: int
    page_size: int
    total: int
    total_pages: int
