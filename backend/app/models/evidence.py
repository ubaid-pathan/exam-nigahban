from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring_events.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    image_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Python attribute name avoids colliding with SQLAlchemy's reserved
    # Base.metadata; the actual database column is named "metadata" to
    # match the field name required by the project specification.
    metadata_json: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
