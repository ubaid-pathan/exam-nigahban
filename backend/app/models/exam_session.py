from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"),
        nullable=False,
        index=True,
    )

    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
    )

    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )