from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# Mirrors the two admin decisions MonitoringEvent.status can be moved to
# from PENDING_REVIEW by a human reviewer (see CLAUDE.md section 18 /
# PROJECT_SPEC.md: the AI never confirms cheating itself).
ReviewAction = Literal["CONFIRMED", "IGNORED"]


class EvidenceReviewRequest(BaseModel):
    action: ReviewAction
    reason: str | None = None


class AdminActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    admin_id: int
    action: str
    reason: str | None
    created_at: datetime


class EvidenceReviewResponse(BaseModel):
    evidence_id: int
    event_id: int
    status: str
    action: AdminActionResponse
