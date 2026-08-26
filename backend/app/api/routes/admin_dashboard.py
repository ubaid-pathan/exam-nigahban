from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import AdminAction, Evidence, Exam, ExamSession, MonitoringEvent
from app.db.session import get_db
from app.schemas.admin_dashboard import DashboardSummaryResponse

router = APIRouter(
    prefix="/api/admin/dashboard",
    tags=["admin-dashboard"],
    dependencies=[Depends(require_admin)],
)


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummaryResponse:
    """Read-only aggregate snapshot for the admin dashboard.

    Never mutates state: a session whose deadline has already passed but
    is still marked "in_progress" (lazy expiry -- see
    student_exams.py::_sync_expiry / monitoring.py::_get_owned_active_session_or_404)
    is excluded from the active counts below by re-checking the real
    deadline here, but its stored status is left untouched. Only a request
    that actually touches that session flips it to "expired".
    """
    active_exams = db.query(func.count(Exam.id)).filter(Exam.status == "active").scalar()

    in_progress_candidates = (
        db.query(ExamSession.student_id, ExamSession.started_at, Exam.duration_minutes)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .filter(ExamSession.status == "in_progress")
        .all()
    )
    now = datetime.utcnow()
    still_active_student_ids = [
        student_id
        for student_id, started_at, duration_minutes in in_progress_candidates
        if now < started_at + timedelta(minutes=duration_minutes)
    ]
    active_sessions = len(still_active_student_ids)
    active_students = len(set(still_active_student_ids))

    status_counts = dict(
        db.query(MonitoringEvent.status, func.count(MonitoringEvent.id))
        .group_by(MonitoringEvent.status)
        .all()
    )
    total_events = sum(status_counts.values())
    pending_review_events = status_counts.get("PENDING_REVIEW", 0)
    confirmed_events = status_counts.get("CONFIRMED", 0)
    ignored_events = status_counts.get("IGNORED", 0)

    high_severity_pending_events = (
        db.query(func.count(MonitoringEvent.id))
        .filter(
            MonitoringEvent.severity == "high",
            MonitoringEvent.status == "PENDING_REVIEW",
        )
        .scalar()
    )

    evidence_count = db.query(func.count(Evidence.id)).scalar()
    total_review_actions = db.query(func.count(AdminAction.id)).scalar()

    return DashboardSummaryResponse(
        active_exams=active_exams,
        active_sessions=active_sessions,
        active_students=active_students,
        total_events=total_events,
        pending_review_events=pending_review_events,
        confirmed_events=confirmed_events,
        ignored_events=ignored_events,
        high_severity_pending_events=high_severity_pending_events,
        evidence_count=evidence_count,
        total_review_actions=total_review_actions,
        generated_at=now,
    )
