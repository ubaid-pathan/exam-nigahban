import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_
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
    MonitoringSessionListResponse,
    MonitoringSessionSummary,
    Severity,
)
from app.services.evidence_storage import (
    EvidenceValidationError,
    decode_and_validate_image,
    delete_evidence_file,
    evidence_storage_is_durable,
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

    metadata_json: dict = {
        "content_type": "image/jpeg",
        "size_bytes": len(image_bytes),
    }
    if not evidence_storage_is_durable():
        # The local backend may live on an ephemeral filesystem (e.g.
        # Render), where files are lost on redeploy, so keep a base64 copy
        # in the DB row as a survival fallback. Durable object storage
        # needs no such copy -- embedding it would bloat every row by the
        # full image size for no benefit.
        metadata_json["image_base64"] = evidence_image_base64

    evidence = Evidence(
        event_id=event.id,
        image_path=relative_path,
        captured_at=captured_at,
        metadata_json=metadata_json,
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
        # Voided violations are withdrawn from the review queue. They are
        # not deleted -- see app/api/routes/void.py -- but they must not
        # appear anywhere an administrator acts on them.
        .filter(MonitoringEvent.voided_at.is_(None))
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


@router.get(
    "/sessions",
    response_model=MonitoringSessionListResponse,
    dependencies=[Depends(require_admin)],
)
def list_monitoring_sessions(
    event_status: EventStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = None,
    event_type: EventType | None = None,
    exam_id: int | None = None,
    session_id: int | None = None,
    session_status: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> MonitoringSessionListResponse:
    """Admin-only review queue rolled up to one row per student session.

    A student who triggers FACE_ABSENT three times and MOBILE_PHONE twice
    appears here once, with those counts, instead of as five separate rows
    -- while every underlying MonitoringEvent and its evidence stays
    exactly as it was.  Drill-down reuses the existing
    GET /api/monitoring/events?session_id=<id>; nothing about that endpoint
    or the evidence review flow changes.

    Filters restrict which events are aggregated (not merely which sessions
    appear), so a filtered listing's counts always describe precisely the
    events the caller asked about.  Sessions left with no matching events
    drop out of the results entirely.

    Cost is two queries regardless of page size: one grouped aggregate, and
    one per-type breakdown scoped to the session ids on the current page.
    """
    # Applied to both the aggregate and the per-type breakdown below, so
    # a voided violation is excluded from the counts as well as the rows.
    filters = [MonitoringEvent.voided_at.is_(None)]
    if event_status is not None:
        filters.append(MonitoringEvent.status == event_status)
    if severity is not None:
        filters.append(MonitoringEvent.severity == severity)
    if event_type is not None:
        filters.append(MonitoringEvent.event_type == event_type)
    if exam_id is not None:
        filters.append(Exam.id == exam_id)
    # Accepted so the admin UI's Session ID filter behaves identically in
    # the grouped and flat views rather than being silently ignored here.
    if session_id is not None:
        filters.append(MonitoringEvent.session_id == session_id)
    if session_status is not None:
        filters.append(ExamSession.status == session_status)
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Student.full_name.ilike(pattern),
                Student.student_id.ilike(pattern),
            )
        )

    # Grouped by every non-aggregated column that is selected, which
    # PostgreSQL requires and MySQL/SQLite accept -- so the same statement
    # runs unchanged on all three.
    group_columns = (
        MonitoringEvent.session_id,
        ExamSession.status,
        ExamSession.started_at,
        ExamSession.ended_at,
        Student.student_id,
        Student.full_name,
        Exam.id,
        Exam.title,
    )

    aggregate_query = (
        db.query(
            MonitoringEvent.session_id.label("session_id"),
            ExamSession.status.label("session_status"),
            ExamSession.started_at.label("started_at"),
            ExamSession.ended_at.label("ended_at"),
            Student.student_id.label("student_code"),
            Student.full_name.label("student_full_name"),
            Exam.id.label("exam_id"),
            Exam.title.label("exam_title"),
            func.count(func.distinct(MonitoringEvent.id)).label("total_events"),
            func.sum(
                case((MonitoringEvent.status == "PENDING_REVIEW", 1), else_=0)
            ).label("pending_events"),
            func.sum(case((MonitoringEvent.status == "CONFIRMED", 1), else_=0)).label(
                "confirmed_events"
            ),
            func.sum(case((MonitoringEvent.status == "IGNORED", 1), else_=0)).label(
                "ignored_events"
            ),
            func.sum(case((MonitoringEvent.severity == "high", 1), else_=0)).label(
                "high_severity_events"
            ),
            # Evidence is unique per event (see app/models/evidence.py), so
            # this outer join can never multiply the aggregated event rows.
            func.count(func.distinct(Evidence.id)).label("evidence_count"),
            func.min(MonitoringEvent.detected_at).label("first_detected_at"),
            func.max(MonitoringEvent.detected_at).label("last_detected_at"),
        )
        .join(ExamSession, ExamSession.id == MonitoringEvent.session_id)
        .join(Student, Student.id == ExamSession.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .outerjoin(Evidence, Evidence.event_id == MonitoringEvent.id)
        .filter(*filters)
        .group_by(*group_columns)
    )

    # One row per group, so the page count is the number of groups -- not
    # the number of underlying events.
    total = db.query(func.count()).select_from(aggregate_query.subquery()).scalar() or 0

    rows = (
        aggregate_query.order_by(func.max(MonitoringEvent.detected_at).desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    session_ids = [row.session_id for row in rows]
    events_by_type: dict[int, dict[str, int]] = {sid: {} for sid in session_ids}
    if session_ids:
        breakdown = (
            db.query(
                MonitoringEvent.session_id,
                MonitoringEvent.event_type,
                func.count(MonitoringEvent.id),
            )
            .join(ExamSession, ExamSession.id == MonitoringEvent.session_id)
            .join(Student, Student.id == ExamSession.student_id)
            .join(Exam, Exam.id == ExamSession.exam_id)
            .filter(MonitoringEvent.session_id.in_(session_ids), *filters)
            .group_by(MonitoringEvent.session_id, MonitoringEvent.event_type)
            .all()
        )
        for row_session_id, row_event_type, count in breakdown:
            events_by_type[row_session_id][row_event_type] = count

    items = [
        MonitoringSessionSummary(
            session_id=row.session_id,
            session_status=row.session_status,
            started_at=row.started_at,
            ended_at=row.ended_at,
            student_id=row.student_code,
            student_full_name=row.student_full_name,
            exam_id=row.exam_id,
            exam_title=row.exam_title,
            total_events=row.total_events,
            pending_events=int(row.pending_events or 0),
            confirmed_events=int(row.confirmed_events or 0),
            ignored_events=int(row.ignored_events or 0),
            high_severity_events=int(row.high_severity_events or 0),
            evidence_count=row.evidence_count,
            first_detected_at=row.first_detected_at,
            last_detected_at=row.last_detected_at,
            events_by_type=events_by_type.get(row.session_id, {}),
        )
        for row in rows
    ]

    total_pages = (total + page_size - 1) // page_size

    return MonitoringSessionListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
