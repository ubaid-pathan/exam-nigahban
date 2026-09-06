from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# The three proportionate enforcement actions an admin may take after
# reviewing evidence.  Ordered by severity: BLOCK (reversible pause) <
# CANCEL_EXAM (terminal, score voided) < UFM_CASE (formal academic record).
EnforcementType = Literal["BLOCK", "CANCEL_EXAM", "UFM_CASE"]


class EnforcementCreateRequest(BaseModel):
    session_id: int
    action_type: EnforcementType
    # A defensible reason is mandatory for every enforcement action --
    # these rows back disciplinary decisions and must be audit-ready.
    reason: str = Field(min_length=3, max_length=1000)
    event_id: int | None = None
    # Required when action_type == BLOCK (validated in the route handler so
    # the error can say what's missing, rather than a generic schema error).
    block_minutes: int | None = Field(default=None, ge=1, le=60)


class ActiveBlockInfo(BaseModel):
    """The write-block currently enforced on a session, if any.

    Returned inside SessionResponse so the student client's periodic resync
    can render the pause overlay without a second request.
    """

    blocked_until: datetime
    reason: str


class EnforcementActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    student_id: int
    admin_id: int
    event_id: int | None
    action_type: str
    reason: str
    status: str
    blocked_until: datetime | None
    created_at: datetime

    # Joined context (explicit joins in the list endpoint, direct lookups
    # in the create endpoint) so the admin UI never needs extra requests.
    admin_username: str
    student_full_name: str
    exam_title: str

    # Computed, not stored: a BLOCK is only effectively active while its
    # deadline hasn't passed -- expired blocks keep status="ACTIVE" in the
    # DB (append-only audit) but report "EXPIRED" here.
    effective_status: str


class EnforcementActionListResponse(BaseModel):
    items: list[EnforcementActionResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
