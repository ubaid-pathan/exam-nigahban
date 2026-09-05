import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.routes.student_exams import get_current_student
from app.db.models import Evidence, Exam, ExamSession, MonitoringEvent, MonitoringRule, Student
from app.db.session import get_db
from app.schemas.evidence import EvidenceResponse
from app.schemas.monitoring import (
    EventStatus,
    EventType,
    MonitoringEventAdminResponse,
    MonitoringEventCreate,
    MonitoringEventListResponse,
    MonitoringEventResponse,
    Severity,
)
from app.services.evidence_storage import (
    EvidenceValidationError,
    decode_and_validate_image,
    delete_evidence_file,
    save_evidence_image,
)
from app.websocket.manager import manager as websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _validate_event_against_rule(
    payload: MonitoringEventCreate,
    db: Session,
) -> None:
    """Verify an incoming monitoring event satisfies its configured rule.

    Prevents spoofed or under-threshold events from being persisted.  If the
    event type has no rule or the rule is inactive, the request is rejected
    with a 422 so the backend cannot be used to create arbitrary/unconfigured
    events.
    """
    rule = (
        db.query(MonitoringRule)
        .filter(MonitoringRule.event_type == payload.event_type)
        .first()
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Monitoring rule for '{payload.event_type}' is not configured",
        )

    if not rule.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Monitoring rule for '{payload.event_type}' is currently disabled",
        )

    if payload.severity != rule.severity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Expected severity '{rule.severity}' for '{payload.event_type}', "
                f"got '{payload.severity}'"
            ),
        )

    if payload.confidence < rule.confidence_threshold:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Confidence {payload.confidence} is below the threshold "
                f"{rule.confidence_threshold} for '{payload.event_type}'"
            ),
        )

    if payload.duration_seconds < rule.min_duration_seconds:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Duration {payload.duration_seconds}s is below the minimum "
                f"{rule.min_duration_seconds}s for '{payload.event_type}'"
            ),
        )

    if payload.occurrences < rule.required_occurrences:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Occurrences {payload.occurrences} is below the required "
                f"{rule.required_occurrences} for '{payload.event_type}'"
            ),
        )


def _get_owned_active_session_or_404(
    session_id: int, student: Student, db: Session
) -> ExamSession:
    session_row = (
        db.query(ExamSession)
        .filter(ExamSession.id == session_id, ExamSession.student_id == student.id)
        .first()
    )
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )

    exam = db.get(Exam, session_row.exam_id)
    if session_row.status == "in_progress":
        deadline = session_row.started_at + timedelta(minutes=exam.duration_minutes)
        if datetime.utcnow() >= deadline:
            session_row.status = "expired"
            session_row.ended_at = deadline
            db.commit()
            db.refresh(session_row)

    if session_row.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Monitoring events can only be recorded for an active exam session",
        )

    return session_row


@router.post(
    "/events",
    response_model=MonitoringEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_monitoring_event(
    payload: MonitoringEventCreate,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> MonitoringEventResponse:
    session = _get_owned_active_session_or_404(payload.session_id, student, db)
    _validate_event_against_rule(payload, db)

    # The event is created and committed first, independently of evidence.
    # Nothing below this point may ever cause the event itself to fail or
    # roll back -- evidence capture is strictly best-effort.
    event = MonitoringEvent(
        session_id=payload.session_id,
        event_type=payload.event_type,
        confidence=payload.confidence,
        duration_seconds=payload.duration_seconds,
        occurrences=payload.occurrences,
        severity=payload.severity,
        source=payload.source,
        detected_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    await _broadcast_monitoring_event(event)

    evidence_response = _try_attach_evidence(payload.evidence_image_base64, event, db)

    return MonitoringEventResponse(
        id=event.id,
        session_id=event.session_id,
        event_type=event.event_type,
        confidence=event.confidence,
        duration_seconds=event.duration_seconds,
        occurrences=event.occurrences,
        severity=event.severity,
        source=event.source,
        detected_at=event.detected_at,
        status=event.status,
        evidence=evidence_response,
    )


async def _broadcast_monitoring_event(event: MonitoringEvent) -> None:
    """Best-effort admin alert for an already-committed MonitoringEvent.

    Runs after the event is fully persisted (see create_monitoring_event)
    and must never affect the HTTP response: no connected admins, a
    disconnected socket, or any other broadcast failure is swallowed here
    exactly like _try_attach_evidence swallows evidence-capture failures.
    Only non-sensitive admin-alert metadata is sent -- no evidence image
    data, filesystem paths, or student/auth fields.
    """
    try:
        await websocket_manager.broadcast(
            {
                "type": "monitoring_event",
                "event_id": event.id,
                "session_id": event.session_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "status": event.status,
            }
        )
    except Exception:
        logger.exception(
            "Failed to broadcast monitoring event %s to admin WebSocket clients",
            event.id,
        )


def _try_attach_evidence(
    evidence_image_base64: str | None,
    event: MonitoringEvent,
    db: Session,
) -> EvidenceResponse | None:
    """Best-effort evidence capture for an already-committed event.

    Every failure path here is swallowed (logged, not raised): a missing,
    invalid, oversized, or unsaveable image must never affect the
    monitoring event that was already created above.
    """
    if not evidence_image_base64:
        return None

    try:
        image_bytes = decode_and_validate_image(evidence_image_base64)
    except EvidenceValidationError as exc:
        logger.warning("Rejected evidence image for event %s: %s", event.id, exc)
        return None

    captured_at = datetime.utcnow()
    try:
        relative_path = save_evidence_image(image_bytes, event.id, captured_at)
    except OSError:
        logger.exception("Failed to write evidence image for event %s", event.id)
        return None

    evidence = Evidence(
        event_id=event.id,
        image_path=relative_path,
        captured_at=captured_at,
        metadata_json={
            "content_type": "image/jpeg",
            "size_bytes": len(image_bytes),
            "image_base64": evidence_image_base64,
        },
    )
    try:
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
    except Exception:
        db.rollback()
        # The DB row never committed, so the file we just wrote would
        # otherwise be orphaned -- remove it to keep disk/DB consistent.
        delete_evidence_file(relative_path)
        logger.exception("Failed to save evidence record for event %s", event.id)
        return None

    return EvidenceResponse.model_validate(evidence)


@router.get(
    "/events",
    response_model=MonitoringEventListResponse,
    dependencies=[Depends(require_admin)],
)
def list_monitoring_events(
    event_status: EventStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = None,
    event_type: EventType | None = None,
    session_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> MonitoringEventListResponse:
    """Admin-only paginated/filterable monitoring-event review queue.

    Joins ExamSession -> Student -> Exam (none of these have ORM
    relationships defined between them, so the joins are explicit) to give
    the admin dashboard student/exam identity in one query, and
    left-joins Evidence only to expose whether/which evidence exists --
    Evidence.image_path is never selected or returned.
    """
    query = (
        db.query(
            MonitoringEvent,
            Student.student_id.label("student_code"),
            Student.full_name.label("student_full_name"),
            Exam.id.label("exam_id"),
            Exam.title.label("exam_title"),
            Evidence.id.label("evidence_id"),
        )
        .join(ExamSession, ExamSession.id == MonitoringEvent.session_id)
        .join(Student, Student.id == ExamSession.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .outerjoin(Evidence, Evidence.event_id == MonitoringEvent.id)
    )

    if event_status is not None:
        query = query.filter(MonitoringEvent.status == event_status)
    if severity is not None:
        query = query.filter(MonitoringEvent.severity == severity)
    if event_type is not None:
        query = query.filter(MonitoringEvent.event_type == event_type)
    if session_id is not None:
        query = query.filter(MonitoringEvent.session_id == session_id)

    total = query.count()

    rows = (
        query.order_by(MonitoringEvent.detected_at.desc(), MonitoringEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        MonitoringEventAdminResponse(
            id=event.id,
            session_id=event.session_id,
            event_type=event.event_type,
            confidence=event.confidence,
            duration_seconds=event.duration_seconds,
            occurrences=event.occurrences,
            severity=event.severity,
            source=event.source,
            detected_at=event.detected_at,
            status=event.status,
            evidence_id=evidence_id,
            student_id=student_code,
            student_full_name=student_full_name,
            exam_id=exam_id,
            exam_title=exam_title,
        )
        for event, student_code, student_full_name, exam_id, exam_title, evidence_id in rows
    ]

    total_pages = (total + page_size - 1) // page_size

    return MonitoringEventListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
