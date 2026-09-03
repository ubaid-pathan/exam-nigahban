from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# The two admin decisions AdminAction.action can hold -- mirrors
# app.schemas.admin_action.ReviewAction, kept as a separate name here since
# this module models the audit-log *read* side (Phase 7E), not the review
# *write* side (Phase 7A).
AuditAction = Literal["CONFIRMED", "IGNORED"]


class AuditLogEntryResponse(BaseModel):
    """A single row of the admin audit history (Phase 7E).

    Built manually from a joined query (see
    app/api/routes/audit.py::list_audit_log) rather than via
    from_attributes, since it combines fields from AdminAction, User,
    MonitoringEvent, ExamSession, Student, and Exam. Deliberately excludes
    User.password_hash and Evidence.image_path -- neither is ever selected
    by the query that builds this response.
    """

    id: int
    event_id: int
    admin_id: int
    admin_username: str
    action: AuditAction
    reason: str | None
    created_at: datetime
    event_type: str
    severity: str
    session_id: int
    student_id: str
    student_full_name: str
    exam_id: int
    exam_title: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
