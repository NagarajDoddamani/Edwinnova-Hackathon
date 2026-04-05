"""
services/loan_service.py
─────────────────────────
Data-access layer for Loan CRUD operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan
from app.schemas.schemas import LoanCreate, LoanUpdate


async def get_loans_for_user(db: AsyncSession, user_id: int) -> list[Loan]:
    """Return all loans belonging to *user_id*, newest first."""
    result = await db.execute(
        select(Loan)
        .where(Loan.user_id == user_id)
        .order_by(Loan.created_at.desc())
    )
    return list(result.scalars().all())


async def get_loan_by_id(db: AsyncSession, loan_id: int, user_id: int) -> Loan | None:
    """Return a single Loan owned by *user_id*, or None."""
    result = await db.execute(
        select(Loan).where(Loan.id == loan_id, Loan.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_loan(db: AsyncSession, user_id: int, payload: LoanCreate) -> Loan:
    """Persist a new Loan row and return it with its generated id."""
    loan = Loan(user_id=user_id, **payload.model_dump())
    db.add(loan)
    await db.flush()
    return loan


async def update_loan(
    db: AsyncSession, loan: Loan, payload: LoanUpdate
) -> Loan:
    """
    Apply a partial update to *loan*.
    Only fields explicitly set in the request body are changed (exclude_unset).
    """
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(loan, field, value)
    await db.flush()
    return loan


async def delete_loan(db: AsyncSession, loan: Loan) -> None:
    """Hard-delete a Loan row."""
    await db.delete(loan)
    await db.flush()
