import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.student_exams import get_current_student
from app.db.models import Evidence, Exam, ExamSession, MonitoringEvent, Student
from app.db.session import get_db
from app.schemas.evidence import EvidenceResponse
from app.schemas.monitoring import MonitoringEventCreate, MonitoringEventResponse
from app.services.evidence_storage import (
    EvidenceValidationError,
    decode_and_validate_image,
    delete_evidence_file,
    save_evidence_image,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


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
def create_monitoring_event(
    payload: MonitoringEventCreate,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> MonitoringEventResponse:
    _get_owned_active_session_or_404(payload.session_id, student, db)

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
        detected_at=datetime.utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

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
        metadata_json={"content_type": "image/jpeg", "size_bytes": len(image_bytes)},
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
