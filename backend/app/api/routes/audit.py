from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import AdminAction, Exam, ExamSession, MonitoringEvent, Student, User
from app.db.session import get_db
from app.schemas.audit import AuditAction, AuditLogEntryResponse, AuditLogListResponse

router = APIRouter(
    prefix="/api/audit",
    tags=["audit"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AuditLogListResponse)
def list_audit_log(
    action: AuditAction | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    """Admin-only paginated/filterable audit history of review decisions.

    AdminAction is the root table and is treated as an append-only audit
    log (Phase 7A design): a repeat review of the same MonitoringEvent
    inserts a second row rather than overwriting the first, so this
    listing can show every decision ever made, in order.

    None of AdminAction/MonitoringEvent/ExamSession/Student/Exam/User have
    ORM relationships defined between them, so the joins below are
    explicit -- matching the exact pattern already used by
    GET /api/monitoring/events (see app/api/routes/monitoring.py). Only
    User.username is selected (never password_hash), and
    Evidence.image_path is never selected at all.
    """
    query = (
        db.query(
            AdminAction,
            User.username.label("admin_username"),
            MonitoringEvent.event_type.label("event_type"),
            MonitoringEvent.severity.label("severity"),
            MonitoringEvent.session_id.label("session_id"),
            Student.student_id.label("student_code"),
            Student.full_name.label("student_full_name"),
            Exam.id.label("exam_id"),
            Exam.title.label("exam_title"),
        )
        .join(User, User.id == AdminAction.admin_id)
        .join(MonitoringEvent, MonitoringEvent.id == AdminAction.event_id)
        .join(ExamSession, ExamSession.id == MonitoringEvent.session_id)
        .join(Student, Student.id == ExamSession.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
    )

    if action is not None:
        query = query.filter(AdminAction.action == action)

    total = query.count()

    rows = (
        query.order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        AuditLogEntryResponse(
            id=admin_action.id,
            event_id=admin_action.event_id,
            admin_id=admin_action.admin_id,
            admin_username=admin_username,
            action=admin_action.action,
            reason=admin_action.reason,
            created_at=admin_action.created_at,
            event_type=event_type,
            severity=severity,
            session_id=session_id,
            student_id=student_code,
            student_full_name=student_full_name,
            exam_id=exam_id,
            exam_title=exam_title,
        )
        for (
            admin_action,
            admin_username,
            event_type,
            severity,
            session_id,
            student_code,
            student_full_name,
            exam_id,
            exam_title,
        ) in rows
    ]

    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
