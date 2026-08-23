from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.student_exams import get_current_student
from app.db.models import Exam, ExamSession, MonitoringEvent, Student
from app.db.session import get_db
from app.schemas.monitoring import MonitoringEventCreate, MonitoringEventResponse

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
) -> MonitoringEvent:
    _get_owned_active_session_or_404(payload.session_id, student, db)

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
    return event
