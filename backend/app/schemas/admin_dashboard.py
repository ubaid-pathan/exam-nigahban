from datetime import datetime

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    """Aggregate counts for the admin dashboard's operational overview.

    Pure aggregate numbers only -- no student/user/evidence rows are ever
    embedded here, so there is nothing to leak (no password hashes, no
    filesystem paths). Recent-event detail is intentionally NOT duplicated
    here: the admin dashboard should call GET /api/monitoring/events
    (Phase 7B) for that, newest-first and already paginated/filterable.
    """

    active_exams: int
    active_sessions: int
    active_students: int
    total_events: int
    pending_review_events: int
    confirmed_events: int
    ignored_events: int
    high_severity_pending_events: int
    evidence_count: int
    # Count of AdminAction audit records representing review actions --
    # NOT the number of distinct reviewed events. AdminAction is an
    # append-only audit log (Phase 7A): reviewing the same MonitoringEvent
    # twice inserts a second AdminAction row, so this can exceed
    # confirmed_events + ignored_events. That is expected, not a bug.
    total_review_actions: int
    generated_at: datetime
