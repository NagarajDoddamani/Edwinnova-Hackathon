"""
models/loan.py
──────────────
SQLAlchemy ORM model for the `loans` table.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Loan(Base):
    """
    Tracks an individual loan belonging to a user.

    Columns
    -------
    id              : Auto-incrementing PK.
    user_id         : FK → users.id.
    loan_type       : e.g. 'Home', 'Personal', 'Car', 'Education'.
    lender_name     : Bank / NBFC name.
    principal_amount: Original loan amount (INR).
    outstanding_amount: Remaining balance (INR).
    emi_amount      : Monthly instalment (INR).
    interest_rate   : Annual rate in percent (e.g. 8.5).
    start_date      : Loan disbursement date.
    end_date        : Scheduled closure date.
    status          : 'active' | 'closed' | 'overdue'.
    created_at      : Record creation timestamp.
    updated_at      : Last modification timestamp.
    """

    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    loan_type: Mapped[str] = mapped_column(String(100), nullable=False)
    lender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    emi_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    owner: Mapped["User"] = relationship("User", back_populates="loans")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Loan id={self.id} type={self.loan_type!r} user_id={self.user_id}>"
