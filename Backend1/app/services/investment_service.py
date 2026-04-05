"""
services/investment_service.py
────────────────────────────────
Data-access layer for Investment CRUD operations.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investment import Investment
from app.schemas.schemas import InvestmentCreate, InvestmentUpdate


async def get_investments_for_user(
    db: AsyncSession, user_id: int
) -> list[Investment]:
    """Return all investments for *user_id*, newest first."""
    result = await db.execute(
        select(Investment)
        .where(Investment.user_id == user_id)
        .order_by(Investment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_investment_by_id(
    db: AsyncSession, investment_id: int, user_id: int
) -> Investment | None:
    """Return a single Investment owned by *user_id*, or None."""
    result = await db.execute(
        select(Investment).where(
            Investment.id == investment_id, Investment.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_investment(
    db: AsyncSession, user_id: int, payload: InvestmentCreate
) -> Investment:
    """Persist a new Investment row and return it."""
    investment = Investment(user_id=user_id, **payload.model_dump())
    db.add(investment)
    await db.flush()
    return investment


async def update_investment(
    db: AsyncSession, investment: Investment, payload: InvestmentUpdate
) -> Investment:
    """Partial update — only touched fields are written."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(investment, field, value)
    await db.flush()
    return investment


async def delete_investment(db: AsyncSession, investment: Investment) -> None:
    """Hard-delete an Investment row."""
    await db.delete(investment)
    await db.flush()


async def get_referral_links(
    db: AsyncSession, user_id: int
) -> list[dict]:
    """
    Return active investments that have a referral link attached.

    Used by the /referrals endpoint to surface curated investment opportunities.
    """
    result = await db.execute(
        select(Investment).where(
            Investment.user_id == user_id,
            Investment.referral_link.isnot(None),
            Investment.status == "active",
        )
    )
    investments = result.scalars().all()
    return [
        {
            "investment_id": inv.id,
            "asset_name": inv.asset_name,
            "investment_type": inv.investment_type,
            "referral_link": inv.referral_link,
            "returns_percent": float(inv.returns_percent),
        }
        for inv in investments
    ]
