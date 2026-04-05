"""
models/snapshot.py
──────────────────
ORM model for `financial_snapshots` — stores parsed PDF data as JSON.
One row per (user_id, document_type).  Re-uploads overwrite the existing row.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FinancialSnapshot(Base):
    """
    Persists the JSON output of pdf_service for later health-score computation.

    Columns
    -------
    id            : PK.
    user_id       : FK → users.id.
    document_type : 'bank_statement' | 'it_return' | 'cibil'.
    data          : JSON string (FinancialData model serialised).
    created_at    : First upload timestamp.
    updated_at    : Last re-upload timestamp.
    """

    __tablename__ = "financial_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "document_type", name="uq_user_doc_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)

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

    owner: Mapped["User"] = relationship("User")  # noqa: F821

    def __repr__(self) -> str:
        return f"<FinancialSnapshot user_id={self.user_id} type={self.document_type!r}>"
