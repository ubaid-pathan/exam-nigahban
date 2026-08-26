from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import AdminAction, Evidence, MonitoringEvent, User
from app.db.session import get_db
from app.schemas.admin_action import (
    AdminActionResponse,
    EvidenceReviewRequest,
    EvidenceReviewResponse,
)
from app.schemas.evidence import EvidenceResponse
from app.services.evidence_storage import read_evidence_image

router = APIRouter(
    prefix="/api/evidence",
    tags=["evidence"],
    dependencies=[Depends(require_admin)],
)


def _get_evidence_or_404(evidence_id: int, db: Session) -> Evidence:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return evidence


@router.get("", response_model=list[EvidenceResponse])
def list_evidence(
    event_id: int | None = None,
    session_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Evidence]:
    query = db.query(Evidence)
    if event_id is not None:
        query = query.filter(Evidence.event_id == event_id)
    if session_id is not None:
        query = query.join(
            MonitoringEvent, MonitoringEvent.id == Evidence.event_id
        ).filter(MonitoringEvent.session_id == session_id)
    return query.order_by(Evidence.id).all()


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: int, db: Session = Depends(get_db)) -> Evidence:
    return _get_evidence_or_404(evidence_id, db)


@router.get("/{evidence_id}/image")
def get_evidence_image(evidence_id: int, db: Session = Depends(get_db)) -> Response:
    evidence = _get_evidence_or_404(evidence_id, db)
    try:
        image_bytes = read_evidence_image(evidence.image_path)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence image file not found",
        )
    return Response(content=image_bytes, media_type="image/jpeg")


@router.post("/{evidence_id}/review", response_model=EvidenceReviewResponse)
def review_evidence(
    evidence_id: int,
    payload: EvidenceReviewRequest,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EvidenceReviewResponse:
    """Records an admin's CONFIRMED/IGNORED decision on a piece of evidence.

    Updates the associated MonitoringEvent.status and inserts a new
    AdminAction audit row in the same transaction -- a repeat review is
    allowed (it simply appends another AdminAction and moves status again),
    but no existing AdminAction row is ever modified or deleted, so the
    audit history is preserved across any number of re-reviews.
    """
    evidence = _get_evidence_or_404(evidence_id, db)

    event = db.get(MonitoringEvent, evidence.event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring event not found for this evidence",
        )

    event.status = payload.action

    admin_action = AdminAction(
        event_id=event.id,
        admin_id=current_admin.id,
        action=payload.action,
        reason=payload.reason,
    )
    db.add(admin_action)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record the review decision",
        )

    db.refresh(event)
    db.refresh(admin_action)

    return EvidenceReviewResponse(
        evidence_id=evidence.id,
        event_id=event.id,
        status=event.status,
        action=AdminActionResponse.model_validate(admin_action),
    )
