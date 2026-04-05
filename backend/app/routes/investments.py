"""
routes/investments.py
──────────────────────
Full CRUD for Investments + the Referrals sub-resource.

Endpoints
─────────
GET    /investments              → list user's investments
POST   /investments              → create investment
GET    /investments/referrals    → list active investments with referral links  ← referral API
GET    /investments/summary      → portfolio aggregate stats
GET    /investments/{id}         → single investment
PUT    /investments/{id}         → full update
PATCH  /investments/{id}         → partial update
DELETE /investments/{id}         → delete
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.schemas import InvestmentCreate, InvestmentResponse, InvestmentUpdate
from app.services import investment_service

router = APIRouter(prefix="/investments", tags=["Investments"])


def _inv_or_404(inv, inv_id: int):
    """Raise 404 if investment is None."""
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investment with id={inv_id} not found.",
        )
    return inv


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[InvestmentResponse], summary="List all investments")
async def list_investments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvestmentResponse]:
    return await investment_service.get_investments_for_user(db, current_user.id)  # type: ignore[return-value]


# ── Referrals (must come BEFORE /{id} to avoid route conflict) ────────────────

@router.get(
    "/referrals",
    summary="Get investment referral links",
    response_description="List of active investments that carry a referral / deep link.",
)
async def get_referrals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """
    Returns curated investment opportunities for the authenticated user.

    Each entry includes:
    - `asset_name` — name of the fund / scheme
    - `investment_type` — e.g. Mutual Fund, FD
    - `returns_percent` — historic or projected returns
    - `referral_link` — deep-link to the investment platform

    Only investments with a non-null `referral_link` and `status='active'` are returned.
    """
    return await investment_service.get_referral_links(db, current_user.id)


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", summary="Investment portfolio summary")
async def investment_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Aggregate view of the user's investment portfolio.

    Returns:
    - Total amount invested
    - Current portfolio value
    - Overall gain/loss in INR and percent
    - Breakdown by investment type
    """
    investments = await investment_service.get_investments_for_user(db, current_user.id)
    active = [i for i in investments if i.status == "active"]

    total_invested = sum(float(i.invested_amount) for i in active)
    total_current = sum(float(i.current_value) for i in active)
    gain_loss = total_current - total_invested
    gain_loss_pct = (gain_loss / total_invested * 100) if total_invested else 0.0

    by_type: dict[str, dict] = {}
    for inv in active:
        entry = by_type.setdefault(
            inv.investment_type,
            {"count": 0, "invested": 0.0, "current_value": 0.0},
        )
        entry["count"] += 1
        entry["invested"] += float(inv.invested_amount)
        entry["current_value"] += float(inv.current_value)

    return {
        "total_active_investments": len(active),
        "total_invested_inr": round(total_invested, 2),
        "total_current_value_inr": round(total_current, 2),
        "total_gain_loss_inr": round(gain_loss, 2),
        "total_gain_loss_percent": round(gain_loss_pct, 2),
        "breakdown_by_type": by_type,
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=InvestmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new investment",
)
async def create_investment(
    payload: InvestmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentResponse:
    return await investment_service.create_investment(db, current_user.id, payload)  # type: ignore[return-value]


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{investment_id}", response_model=InvestmentResponse, summary="Get single investment")
async def get_investment(
    investment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentResponse:
    inv = await investment_service.get_investment_by_id(db, investment_id, current_user.id)
    return _inv_or_404(inv, investment_id)  # type: ignore[return-value]


# ── Full Update ───────────────────────────────────────────────────────────────

@router.put("/{investment_id}", response_model=InvestmentResponse, summary="Replace investment")
async def replace_investment(
    investment_id: int,
    payload: InvestmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentResponse:
    inv = _inv_or_404(
        await investment_service.get_investment_by_id(db, investment_id, current_user.id),
        investment_id,
    )
    update_payload = InvestmentUpdate(**payload.model_dump())
    return await investment_service.update_investment(db, inv, update_payload)  # type: ignore[return-value]


# ── Partial Update ────────────────────────────────────────────────────────────

@router.patch("/{investment_id}", response_model=InvestmentResponse, summary="Partial update")
async def patch_investment(
    investment_id: int,
    payload: InvestmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvestmentResponse:
    inv = _inv_or_404(
        await investment_service.get_investment_by_id(db, investment_id, current_user.id),
        investment_id,
    )
    return await investment_service.update_investment(db, inv, payload)  # type: ignore[return-value]


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete(
    "/{investment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an investment",
)
async def delete_investment(
    investment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    inv = _inv_or_404(
        await investment_service.get_investment_by_id(db, investment_id, current_user.id),
        investment_id,
    )
    await investment_service.delete_investment(db, inv)
