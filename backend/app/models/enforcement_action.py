from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EnforcementAction(Base):
    """A disciplinary action an admin takes against a violating student.

    Three proportionate action types (BLOCK < CANCEL_EXAM < UFM_CASE):
    - BLOCK pauses the student's exam session for a limited time and is
      reversible (auto-expires at blocked_until, or is lifted early).
    - CANCEL_EXAM voids the session (score 0) and is terminal.
    - UFM_CASE files a formal Unfair Means case against the student.

    Rows are append-only: apart from the status transitions on a BLOCK
    (ACTIVE -> LIFTED), no row is ever modified or deleted, so the audit
    trail stays immutable.  student_id is denormalized from the session so
    student-level UFM history can be queried without joining.
    """

    __tablename__ = "enforcement_actions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("exam_sessions.id"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"),
        nullable=False,
        index=True,
    )

    admin_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Optional link to the MonitoringEvent whose evidence justified the
    # action; enforcement is also valid without a specific event.
    event_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_events.id"),
        nullable=True,
        index=True,
    )

    # BLOCK | CANCEL_EXAM | UFM_CASE
    action_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # ACTIVE | LIFTED | COMPLETED.  A BLOCK starts ACTIVE and may move to
    # LIFTED; CANCEL_EXAM / UFM_CASE rows are COMPLETED at creation.
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        index=True,
    )

    # BLOCK only: the write-block is enforced lazily against this deadline.
    blocked_until: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
