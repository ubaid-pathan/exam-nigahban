"""Voiding records, restricted to the system administrator.

Voiding is deliberately not deletion. This system's guarantee is an
append-only record, so a row that must stop having effect is marked rather
than removed: it disappears from every queue, count and report, but
survives with who voided it, when, and why. "What happened to event 412?"
stays answerable, which a DELETE would make impossible.

Three conditions guard every void:

  1. only the system administrator may perform one;
  2. the acting administrator must re-enter their own password, so a
     stolen or unattended session cannot do it;
  3. a record that an ACTIVE enforcement action depends on cannot be
     voided at all -- removing the evidence behind a punishment that is
     still in force would leave the institution unable to justify it.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_system_admin
from app.core.step_up import StepUpLockedError, step_up_verifier
from app.db.models import (
    EnforcementAction,
    Exam,
    ExamSession,
    MonitoringEvent,
    User,
)
from app.core.logging import log_event
from app.db.session import get_db
from app.schemas.void import (
    VoidedRecordListResponse,
    VoidedRecordResponse,
    VoidRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/void",
    tags=["void"],
    dependencies=[Depends(require_system_admin)],
)


def _confirm_password(admin: User, password: str) -> None:
    """Re-authenticates the acting administrator, or refuses.

    Lockout is checked before the comparison, so a locked-out caller learns
    nothing from the result or its timing. The password never reaches a log
    line or the stored record.
    """
    try:
        step_up_verifier.check_not_locked(admin.id)
    except StepUpLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        )

    if not step_up_verifier.verify(admin.id, password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password confirmation failed",
        )


def _reject_if_enforcement_depends_on_event(event_id: int, db: Session) -> None:
    """Refuses to void an event backing enforcement that is still in force.

    A completed or lifted action describes something already concluded; an
    ACTIVE one is a punishment currently being applied, and its
    justification must remain available while it is.
    """
    active = (
        db.query(EnforcementAction)
        .filter(
            EnforcementAction.event_id == event_id,
            EnforcementAction.status == "ACTIVE",
        )
        .first()
    )
    if active is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This violation supports an active enforcement action "
                f"(#{active.id}). Lift or complete that action first -- the "
                "evidence behind a punishment still in force cannot be removed."
            ),
        )


@router.post("/events/{event_id}", status_code=status.HTTP_200_OK)
def void_monitoring_event(
    event_id: int,
    payload: VoidRequest,
    current_admin: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Voids one monitoring event and, with it, its evidence.

    The evidence row is left in place rather than deleted: it is reached
    only through its event, which is now hidden everywhere, so voiding the
    event is sufficient to withdraw both from view while keeping the pair
    intact and explainable.
    """
    event = db.get(MonitoringEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring event not found",
        )
    if event.voided_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This violation has already been voided",
        )

    _confirm_password(current_admin, payload.password)
    _reject_if_enforcement_depends_on_event(event_id, db)

    event.voided_at = datetime.utcnow()
    event.voided_by_admin_id = current_admin.id
    event.void_reason = payload.reason.strip()
    db.commit()

    # A security-relevant event: something has left the visible audit
    # trail. The reason is recorded on the row; only the fact is logged.
    log_event(
        "record.voided",
        level=logging.WARNING,
        kind="monitoring_event",
        record_id=event_id,
        session_id=event.session_id,
        admin=current_admin.username,
    )

    return {
        "id": event_id,
        "kind": "monitoring_event",
        "voided_at": event.voided_at,
        "voided_by": current_admin.username,
    }


@router.post("/exams/{exam_id}", status_code=status.HTTP_200_OK)
def void_exam(
    exam_id: int,
    payload: VoidRequest,
    current_admin: User = Depends(require_system_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Voids one exam.

    Refused while any student has attempted it. An exam session chains on
    to answers, monitoring events, evidence and decisions, so withdrawing
    the exam would leave every one of those describing something that no
    longer appears to exist -- and would silently erase real attempts.
    Questions are not an obstacle: they belong to the exam and have no
    meaning without it.
    """
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    if exam.voided_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This exam has already been voided",
        )

    _confirm_password(current_admin, payload.password)

    session_count = (
        db.query(ExamSession).filter(ExamSession.exam_id == exam_id).count()
    )
    if session_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This exam has {session_count} student attempt"
                f"{'' if session_count == 1 else 's'} and cannot be voided. "
                "Voiding it would withdraw the attempts, their monitoring "
                "events and the decisions taken on them from view."
            ),
        )

    exam.voided_at = datetime.utcnow()
    exam.voided_by_admin_id = current_admin.id
    exam.void_reason = payload.reason.strip()
    db.commit()

    log_event(
        "record.voided",
        level=logging.WARNING,
        kind="exam",
        record_id=exam_id,
        admin=current_admin.username,
    )

    return {
        "id": exam_id,
        "kind": "exam",
        "voided_at": exam.voided_at,
        "voided_by": current_admin.username,
    }


@router.get("", response_model=VoidedRecordListResponse)
def list_voided_records(db: Session = Depends(get_db)) -> VoidedRecordListResponse:
    """Everything currently withdrawn from the visible record.

    The counterpart to voiding: records leave the queues and reports, but
    they do not leave the system unaccounted for. Without this view,
    voiding would be indistinguishable from deletion by anyone auditing it.
    """
    items: list[VoidedRecordResponse] = []

    event_rows = (
        db.query(MonitoringEvent, User.username)
        .join(User, User.id == MonitoringEvent.voided_by_admin_id)
        .filter(MonitoringEvent.voided_at.isnot(None))
        .order_by(MonitoringEvent.voided_at.desc())
        .all()
    )
    for event, username in event_rows:
        items.append(
            VoidedRecordResponse(
                id=event.id,
                kind="monitoring_event",
                label=f"{event.event_type} (session {event.session_id})",
                voided_at=event.voided_at,
                voided_by=username,
                void_reason=event.void_reason or "",
            )
        )

    exam_rows = (
        db.query(Exam, User.username)
        .join(User, User.id == Exam.voided_by_admin_id)
        .filter(Exam.voided_at.isnot(None))
        .order_by(Exam.voided_at.desc())
        .all()
    )
    for exam, username in exam_rows:
        items.append(
            VoidedRecordResponse(
                id=exam.id,
                kind="exam",
                label=exam.title,
                voided_at=exam.voided_at,
                voided_by=username,
                void_reason=exam.void_reason or "",
            )
        )

    items.sort(key=lambda item: item.voided_at, reverse=True)
    return VoidedRecordListResponse(items=items, total=len(items))
