from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"

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

    event_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    occurrences: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    severity: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="browser_mediapipe",
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING_REVIEW",
    )
