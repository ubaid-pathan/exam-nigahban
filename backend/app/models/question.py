from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id"),
        nullable=False,
        index=True,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    option_a: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    option_b: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    option_c: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    option_d: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    correct_answer: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )