"""
models/investment.py
────────────────────
SQLAlchemy ORM model for the `investments` table.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Investment(Base):
    """
    Tracks an individual investment belonging to a user.

    Columns
    -------
    id              : Auto-incrementing PK.
    user_id         : FK → users.id.
    investment_type : e.g. 'Mutual Fund', 'Stocks', 'FD', 'PPF', 'NPS'.
    asset_name      : Specific fund / stock / scheme name.
    invested_amount : Total capital deployed (INR).
    current_value   : Current market value (INR).
    returns_percent : XIRR / CAGR in percent (e.g. 14.3).
    start_date      : Date of first investment.
    maturity_date   : Expected maturity (nullable for open-ended).
    status          : 'active' | 'redeemed' | 'matured'.
    referral_link   : Deep-link to invest more (optional).
    created_at / updated_at : Audit timestamps.
    """

    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    investment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    returns_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    referral_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)

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
    owner: Mapped["User"] = relationship("User", back_populates="investments")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<Investment id={self.id} type={self.investment_type!r} user_id={self.user_id}>"
        )
