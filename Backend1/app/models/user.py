"""
models/user.py
──────────────
SQLAlchemy ORM model for the `users` table.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """
    Represents a FinArmor end-user.

    Columns
    -------
    id           : Auto-incrementing PK.
    email        : Unique login identifier.
    full_name    : Display name.
    hashed_password : bcrypt hash — never store plain text.
    is_active    : Soft-disable accounts without deletion.
    created_at   : UTC timestamp of registration.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    loans: Mapped[list["Loan"]] = relationship(  # noqa: F821
        "Loan", back_populates="owner", cascade="all, delete-orphan", lazy="select"
    )
    investments: Mapped[list["Investment"]] = relationship(  # noqa: F821
        "Investment", back_populates="owner", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
