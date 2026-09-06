import base64

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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
from app.schemas.evidence import EvidenceListResponse, EvidenceResponse
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


@router.get("", response_model=EvidenceListResponse)
def list_evidence(
    event_id: int | None = None,
    session_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> EvidenceListResponse:
    """Admin-only paginated evidence listing.

    Previously returned every row unbounded, and each row carried a full
    base64 copy of its JPEG inline under the local storage backend -- so a
    few hundred events produced a single response of tens of megabytes.
    Both halves of that are fixed: the page is bounded here, and
    EvidenceResponse no longer serializes the fallback image (the stored
    row still keeps it; GET /api/evidence/{id}/image still uses it).
    """
    query = db.query(Evidence)
    if event_id is not None:
        query = query.filter(Evidence.event_id == event_id)
    if session_id is not None:
        query = query.join(
            MonitoringEvent, MonitoringEvent.id == Evidence.event_id
        ).filter(MonitoringEvent.session_id == session_id)

    total = query.count()
    rows = (
        query.order_by(Evidence.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    total_pages = (total + page_size - 1) // page_size

    return EvidenceListResponse(
        items=[EvidenceResponse.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: int, db: Session = Depends(get_db)) -> Evidence:
    return _get_evidence_or_404(evidence_id, db)


@router.get("/{evidence_id}/image")
def get_evidence_image(evidence_id: int, db: Session = Depends(get_db)) -> Response:
    evidence = _get_evidence_or_404(evidence_id, db)
    try:
        image_bytes = read_evidence_image(evidence.image_path)
    except OSError:
        # Render's free filesystem is ephemeral: images are lost on redeploy.
        # We keep a base64 backup in the DB metadata so evidence survives.
        base64_image = evidence.metadata_json.get("image_base64")
        if not base64_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence image file not found",
            )
        try:
            image_bytes = base64.b64decode(base64_image, validate=True)
        except (ValueError, TypeError):
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
