from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="student",
    )

    status: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Nullable, added for the Users consolidation feature. Students already
    # have an authoritative full_name on the Student profile table -- this
    # column is only ever populated for admin accounts (which have no
    # separate profile table of their own). email is shared by both roles,
    # since neither previously had anywhere to store one.
    full_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    student = relationship(
        "Student",
        back_populates="user",
        uselist=False,
    )