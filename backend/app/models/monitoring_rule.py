from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonitoringRule(Base):
    """Persistent temporal-rule configuration for AI monitoring events.

    Stores the baseline rules that mirror
    frontend/src/monitoring/constants.js so the backend has an authoritative
    copy, and validates incoming events against these thresholds.
    """

    __tablename__ = "monitoring_rules"

    __table_args__ = (
        UniqueConstraint("event_type", name="uq_monitoring_rule_event_type"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    min_duration_seconds: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    required_occurrences: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    confidence_threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
