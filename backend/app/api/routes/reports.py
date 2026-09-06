"""Report generation for administrators.

Read-only throughout: a report never changes what it describes.

Cost is four queries regardless of how much activity a session produced --
session context, flagged activities, the decisions on them, and enforcement
-- rather than one query per activity.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.routes.enforcement import _effective_status
from app.db.models import (
    AdminAction,
    EnforcementAction,
    Evidence,
    Exam,
    ExamSession,
    MonitoringEvent,
    Student,
    User,
)
from app.db.session import get_db
from app.schemas.report import (
    ReportDecision,
    ReportEnforcement,
    ReportEvent,
    ReportExam,
    ReportSession,
    ReportStudent,
    SessionCaseReport,
)

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"],
    dependencies=[Depends(require_admin)],
)


@router.get("/sessions/{session_id}", response_model=SessionCaseReport)
def get_session_case_report(
    session_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SessionCaseReport:
    """The complete record of one student's exam session.

    Combines the flagged activities, the evidence captured for them, every
    administrator decision, and every enforcement action into the single
    document a disciplinary process needs. Ordered chronologically, because
    a case is read as a sequence of events rather than as a set of counts.

    Nothing here asserts wrongdoing: the report states what the system
    flagged and what a named administrator decided about it.
    """
    row = (
        db.query(ExamSession, Student, Exam)
        .join(Student, Student.id == ExamSession.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .filter(ExamSession.id == session_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )

    session_row, student, exam = row

    # Evidence is unique per event, so this outer join cannot duplicate rows.
    event_rows = (
        db.query(MonitoringEvent, Evidence.id.label("evidence_id"))
        .outerjoin(Evidence, Evidence.event_id == MonitoringEvent.id)
        .filter(MonitoringEvent.session_id == session_id)
        .order_by(MonitoringEvent.detected_at, MonitoringEvent.id)
        .all()
    )
    event_ids = [event.id for event, _ in event_rows]

    decisions_by_event: dict[int, list[ReportDecision]] = {}
    if event_ids:
        decision_rows = (
            db.query(AdminAction, User.username)
            .join(User, User.id == AdminAction.admin_id)
            .filter(AdminAction.event_id.in_(event_ids))
            .order_by(AdminAction.created_at, AdminAction.id)
            .all()
        )
        for action, admin_username in decision_rows:
            decisions_by_event.setdefault(action.event_id, []).append(
                ReportDecision(
                    id=action.id,
                    action=action.action,
                    reason=action.reason,
                    admin_username=admin_username,
                    created_at=action.created_at,
                )
            )

    events = [
        ReportEvent(
            id=event.id,
            event_type=event.event_type,
            severity=event.severity,
            confidence=event.confidence,
            duration_seconds=event.duration_seconds,
            occurrences=event.occurrences,
            detected_at=event.detected_at,
            status=event.status,
            source=event.source,
            evidence_id=evidence_id,
            decisions=decisions_by_event.get(event.id, []),
        )
        for event, evidence_id in event_rows
    ]

    enforcement_rows = (
        db.query(EnforcementAction, User.username)
        .join(User, User.id == EnforcementAction.admin_id)
        .filter(EnforcementAction.session_id == session_id)
        .order_by(EnforcementAction.created_at, EnforcementAction.id)
        .all()
    )
    enforcement_actions = [
        ReportEnforcement(
            id=action.id,
            action_type=action.action_type,
            reason=action.reason,
            status=action.status,
            effective_status=_effective_status(action),
            blocked_until=action.blocked_until,
            created_at=action.created_at,
            admin_username=admin_username,
            event_id=action.event_id,
        )
        for action, admin_username in enforcement_rows
    ]

    return SessionCaseReport(
        generated_at=datetime.utcnow(),
        generated_by=current_admin.username,
        student=ReportStudent(
            student_id=student.student_id,
            full_name=student.full_name,
            department=student.department,
            class_name=student.class_name,
        ),
        exam=ReportExam(
            id=exam.id,
            title=exam.title,
            duration_minutes=exam.duration_minutes,
        ),
        session=ReportSession(
            id=session_row.id,
            status=session_row.status,
            started_at=session_row.started_at,
            ended_at=session_row.ended_at,
            score=session_row.score,
        ),
        total_events=len(events),
        confirmed_events=sum(1 for e in events if e.status == "CONFIRMED"),
        ignored_events=sum(1 for e in events if e.status == "IGNORED"),
        pending_events=sum(1 for e in events if e.status == "PENDING_REVIEW"),
        high_severity_events=sum(1 for e in events if e.severity == "high"),
        events=events,
        enforcement_actions=enforcement_actions,
    )
