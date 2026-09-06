"""Schemas for the per-session case report.

The case report is the document an administrator attaches to a
disciplinary file, so its shape is driven by what has to be defensible
rather than by what is convenient to query: every flagged activity, the
evidence behind it, and the named administrator who decided what it meant.

Terminology follows CLAUDE.md section 18 throughout. Nothing here asserts
that a student cheated -- the report records that the system flagged an
activity and that a human reached a decision about it.
"""

from datetime import datetime

from pydantic import BaseModel


class ReportStudent(BaseModel):
    student_id: str
    full_name: str
    # "Program" and "section" in report terms; nullable on the model, so a
    # student with neither still produces a valid report.
    department: str | None
    class_name: str | None


class ReportExam(BaseModel):
    id: int
    title: str
    duration_minutes: int


class ReportSession(BaseModel):
    id: int
    status: str
    started_at: datetime
    ended_at: datetime | None
    score: int | None


class ReportDecision(BaseModel):
    """One administrator's review decision on one flagged activity.

    Multiple decisions per activity are expected and preserved in order:
    the audit trail is append-only, so a reversal adds an entry rather
    than replacing one.
    """

    id: int
    action: str
    reason: str | None
    admin_username: str
    created_at: datetime


class ReportEvent(BaseModel):
    id: int
    event_type: str
    severity: str
    confidence: float
    duration_seconds: float
    occurrences: int
    detected_at: datetime
    status: str
    source: str
    # Present when evidence was captured. The report embeds the image only
    # for CONFIRMED activities -- illustrating an activity an
    # administrator dismissed would misrepresent the record -- but the id
    # is exposed for every activity so the table can say whether evidence
    # exists at all.
    evidence_id: int | None
    decisions: list[ReportDecision]


class ReportEnforcement(BaseModel):
    id: int
    action_type: str
    reason: str
    status: str
    effective_status: str
    blocked_until: datetime | None
    created_at: datetime
    admin_username: str
    event_id: int | None


class SessionCaseReport(BaseModel):
    """Everything needed to render one session's case report."""

    # Provenance: a disciplinary document must say when it was produced and
    # by whom, since the underlying data keeps changing as reviews happen.
    generated_at: datetime
    generated_by: str

    student: ReportStudent
    exam: ReportExam
    session: ReportSession

    total_events: int
    confirmed_events: int
    ignored_events: int
    pending_events: int
    high_severity_events: int

    events: list[ReportEvent]
    enforcement_actions: list[ReportEnforcement]
