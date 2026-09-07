import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import (
    EnforcementAction,
    Exam,
    ExamSession,
    MonitoringEvent,
    Student,
    User,
)
from app.core.logging import log_event
from app.db.session import get_db
from app.schemas.enforcement import (
    EnforcementActionListResponse,
    EnforcementActionResponse,
    EnforcementCreateRequest,
)
from app.websocket.manager import manager as websocket_manager
from app.websocket.session_manager import session_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/enforcement",
    tags=["enforcement"],
    dependencies=[Depends(require_admin)],
)


def get_active_block(session_id: int, db: Session) -> EnforcementAction | None:
    """Returns the newest BLOCK row still effectively active for a session.

    A stored status of ACTIVE is not enough: the row's blocked_until
    deadline is enforced lazily, so an expired block simply stops matching
    here -- its DB row is left untouched (append-only audit trail).  Shared
    with the student-exams routes so admin intent and student enforcement
    always read the same rule.
    """
    return (
        db.query(EnforcementAction)
        .filter(
            EnforcementAction.session_id == session_id,
            EnforcementAction.action_type == "BLOCK",
            EnforcementAction.status == "ACTIVE",
            EnforcementAction.blocked_until > datetime.utcnow(),
        )
        .order_by(EnforcementAction.id.desc())
        .first()
    )


def _effective_status(row: EnforcementAction) -> str:
    """ACTIVE if the row currently has effect, else the terminal label.

    A BLOCK past its deadline reports EXPIRED (its stored status stays
    ACTIVE forever, per the append-only audit rule).  LIFTED and COMPLETED
    rows report themselves.
    """
    if row.action_type == "BLOCK" and row.status == "ACTIVE":
        if row.blocked_until is None or row.blocked_until <= datetime.utcnow():
            return "EXPIRED"
    return row.status


def _to_response(row: EnforcementAction, db: Session) -> EnforcementActionResponse:
    """Builds the API view of one enforcement row, joining context lazily.

    Single-row lookups (after create/lift) use this; the list endpoint uses
    an explicit joined query instead so N rows don't cost N lookups.
    """
    admin_username = db.get(User, row.admin_id).username
    student = db.get(Student, row.student_id)
    session_row = db.get(ExamSession, row.session_id)
    exam = db.get(Exam, session_row.exam_id)
    return EnforcementActionResponse(
        id=row.id,
        session_id=row.session_id,
        student_id=row.student_id,
        admin_id=row.admin_id,
        event_id=row.event_id,
        action_type=row.action_type,
        reason=row.reason,
        status=row.status,
        blocked_until=row.blocked_until,
        created_at=row.created_at,
        admin_username=admin_username,
        student_full_name=student.full_name,
        exam_title=exam.title,
        effective_status=_effective_status(row),
    )


async def _broadcast_enforcement_action(row: EnforcementAction) -> None:
    """Best-effort admin alert for an enforcement action, mirroring
    _broadcast_monitoring_event in app/api/routes/monitoring.py: runs after
    the row is committed, sends only non-sensitive metadata, and never
    affects the HTTP response.
    """
    try:
        await websocket_manager.broadcast(
            {
                "type": "enforcement_action",
                "action_id": row.id,
                "session_id": row.session_id,
                "student_id": row.student_id,
                "action_type": row.action_type,
                "status": row.status,
            }
        )
    except Exception:
        logger.exception(
            "Failed to broadcast enforcement action %s to admin WebSocket clients",
            row.id,
        )


async def _notify_student_session(session_id: int) -> None:
    """Best-effort nudge telling the affected candidate to re-read their
    session, so a pause or cancellation shows up immediately instead of on
    their next poll.

    Deliberately carries no enforcement detail: the student client applies
    enforcement only from the authoritative GET /api/student/sessions/{id}
    response, so this cannot put anyone into a state the API did not grant.
    Like _broadcast_enforcement_action, it runs after the row is committed
    and never affects the HTTP response -- the student's polling fallback
    still delivers the change if this fails.
    """
    try:
        await session_manager.notify_session(session_id)
    except Exception:
        logger.exception(
            "Failed to notify student WebSocket clients for session %s",
            session_id,
        )


@router.post("/actions", response_model=EnforcementActionResponse, status_code=status.HTTP_201_CREATED)
async def create_enforcement_action(
    payload: EnforcementCreateRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EnforcementActionResponse:
    """Records an admin enforcement action against a violating student.

    BLOCK pauses the session's write access for a bounded time (server-side,
    enforced in the student routes); CANCEL_EXAM voids the session's result
    (score 0) in the same transaction; UFM_CASE files a formal academic
    record against the student.  Every action requires a defensible reason.
    """
    session_row = db.get(ExamSession, payload.session_id)
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )

    if payload.event_id is not None:
        event = db.get(MonitoringEvent, payload.event_id)
        if event is None or event.session_id != session_row.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="event_id does not reference an event in this session",
            )

    blocked_until = None
    if payload.action_type == "BLOCK":
        if payload.block_minutes is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="block_minutes is required for BLOCK actions",
            )
        if session_row.status != "in_progress":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only an in-progress session can be blocked",
            )
        blocked_until = datetime.utcnow() + timedelta(minutes=payload.block_minutes)

    elif payload.action_type == "CANCEL_EXAM":
        if session_row.status not in ("in_progress", "submitted"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Only an in-progress or submitted session can be cancelled "
                    f"(current status: {session_row.status})"
                ),
            )

    # UFM_CASE needs no session-state check: it files a student-level record
    # regardless of what happened to the exam session.

    row = EnforcementAction(
        session_id=session_row.id,
        student_id=session_row.student_id,
        admin_id=current_admin.id,
        event_id=payload.event_id,
        action_type=payload.action_type,
        reason=payload.reason,
        status="ACTIVE" if payload.action_type == "BLOCK" else "COMPLETED",
        blocked_until=blocked_until,
    )
    db.add(row)

    if payload.action_type == "CANCEL_EXAM":
        session_row.status = "cancelled"
        session_row.score = 0
        if session_row.ended_at is None:
            session_row.ended_at = datetime.utcnow()

    db.commit()
    db.refresh(row)

    log_event(
        "enforcement.action.created",
        action_id=row.id,
        session_id=row.session_id,
        student_id=row.student_id,
        admin=current_admin.username,
        action_type=row.action_type,
        blocked_until=row.blocked_until,
    )

    await _broadcast_enforcement_action(row)
    await _notify_student_session(row.session_id)

    return _to_response(row, db)


@router.get("/actions", response_model=EnforcementActionListResponse)
def list_enforcement_actions(
    action_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    session_id: int | None = None,
    student_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EnforcementActionListResponse:
    """Paginated, filterable enforcement-action history for admins.

    Joins ExamSession -> Student -> Exam (no ORM relationships between
    these, so the joins are explicit, mirroring list_monitoring_events) and
    joins the acting admin's username for a self-contained review table.
    The status filter matches the EFFECTIVE status the API reports (an
    expired BLOCK counts as EXPIRED, not ACTIVE), so the filter options
    line up with what the admin UI table displays.
    """
    query = (
        db.query(
            EnforcementAction,
            Student.full_name.label("student_full_name"),
            Exam.title.label("exam_title"),
            User.username.label("admin_username"),
        )
        .join(ExamSession, ExamSession.id == EnforcementAction.session_id)
        .join(Student, Student.id == EnforcementAction.student_id)
        .join(Exam, Exam.id == ExamSession.exam_id)
        .join(User, User.id == EnforcementAction.admin_id)
    )

    if action_type is not None:
        query = query.filter(EnforcementAction.action_type == action_type)
    if status_filter is not None:
        # ACTIVE/EXPIRED are computed from blocked_until (the stored status
        # of an expired block stays ACTIVE forever, per the append-only
        # audit rule); LIFTED/COMPLETED map straight onto the stored value.
        now = datetime.utcnow()
        if status_filter == "ACTIVE":
            query = query.filter(
                EnforcementAction.action_type == "BLOCK",
                EnforcementAction.status == "ACTIVE",
                EnforcementAction.blocked_until > now,
            )
        elif status_filter == "EXPIRED":
            query = query.filter(
                EnforcementAction.action_type == "BLOCK",
                EnforcementAction.status == "ACTIVE",
                or_(
                    EnforcementAction.blocked_until <= now,
                    EnforcementAction.blocked_until.is_(None),
                ),
            )
        else:
            query = query.filter(EnforcementAction.status == status_filter)
    if session_id is not None:
        query = query.filter(EnforcementAction.session_id == session_id)
    if student_id is not None:
        query = query.filter(EnforcementAction.student_id == student_id)

    total = query.count()
    rows = (
        query.order_by(EnforcementAction.created_at.desc(), EnforcementAction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        EnforcementActionResponse(
            id=row.id,
            session_id=row.session_id,
            student_id=row.student_id,
            admin_id=row.admin_id,
            event_id=row.event_id,
            action_type=row.action_type,
            reason=row.reason,
            status=row.status,
            blocked_until=row.blocked_until,
            created_at=row.created_at,
            admin_username=admin_username,
            student_full_name=student_full_name,
            exam_title=exam_title,
            effective_status=_effective_status(row),
        )
        for row, student_full_name, exam_title, admin_username in rows
    ]

    total_pages = (total + page_size - 1) // page_size
    return EnforcementActionListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.post("/actions/{action_id}/lift", response_model=EnforcementActionResponse)
async def lift_enforcement_action(
    action_id: int,
    db: Session = Depends(get_db),
) -> EnforcementActionResponse:
    """Lifts an active BLOCK early, restoring the student's write access.

    Only BLOCK rows can be lifted: CANCEL_EXAM and UFM_CASE are terminal by
    design -- reversing one is a new disciplinary decision, not an edit.
    """
    row = db.get(EnforcementAction, action_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enforcement action not found",
        )

    if row.action_type != "BLOCK":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only BLOCK actions can be lifted",
        )

    if row.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This block is already {row.status.lower()}",
        )

    if row.blocked_until is not None and row.blocked_until <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This block has already expired",
        )

    row.status = "LIFTED"
    db.commit()
    db.refresh(row)

    log_event(
        "enforcement.action.lifted",
        action_id=row.id,
        session_id=row.session_id,
    )

    # An early lift restores the candidate's write access, so they must be
    # told at once rather than sitting behind a pause overlay that is no
    # longer in force.
    await _notify_student_session(row.session_id)

    return _to_response(row, db)
