"""
routes/loans.py
────────────────
Full CRUD for the Loan resource.

All endpoints require a valid JWT.  Users can only access their own loans
(enforced by always scoping queries to current_user.id).

Endpoints
─────────
GET    /loans           → list all loans for current user
POST   /loans           → create a new loan
GET    /loans/{id}      → retrieve a single loan
PUT    /loans/{id}      → full replacement update
PATCH  /loans/{id}      → partial update (only supplied fields)
DELETE /loans/{id}      → delete a loan
GET    /loans/summary   → aggregate stats (total outstanding, monthly EMI burden)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.schemas import LoanCreate, LoanResponse, LoanUpdate
from app.services import loan_service

router = APIRouter(prefix="/loans", tags=["Loans"])


def _loan_or_404(loan, loan_id: int):
    """Raise 404 if loan is None — DRY helper used in every mutating route."""
    if loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Loan with id={loan_id} not found.",
        )
    return loan


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[LoanResponse], summary="List all loans")
async def list_loans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LoanResponse]:
    """Return every loan record belonging to the authenticated user."""
    return await loan_service.get_loans_for_user(db, current_user.id)  # type: ignore[return-value]


# ── Summary ───────────────────────────────────────────────────────────────────

@router.get("/summary", summary="Loan portfolio summary")
async def loan_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Aggregate view of the user's loan portfolio.

    Returns:
    - Total outstanding across all active loans
    - Combined monthly EMI outflow
    - Breakdown by loan type
    """
    loans = await loan_service.get_loans_for_user(db, current_user.id)
    active = [l for l in loans if l.status == "active"]

    total_outstanding = sum(float(l.outstanding_amount) for l in active)
    total_emi = sum(float(l.emi_amount) for l in active)

    by_type: dict[str, dict] = {}
    for loan in active:
        entry = by_type.setdefault(
            loan.loan_type,
            {"count": 0, "outstanding": 0.0, "monthly_emi": 0.0},
        )
        entry["count"] += 1
        entry["outstanding"] += float(loan.outstanding_amount)
        entry["monthly_emi"] += float(loan.emi_amount)

    return {
        "total_active_loans": len(active),
        "total_outstanding_inr": round(total_outstanding, 2),
        "total_monthly_emi_inr": round(total_emi, 2),
        "breakdown_by_type": by_type,
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new loan",
)
async def create_loan(
    payload: LoanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    """Create and persist a new loan for the authenticated user."""
    return await loan_service.create_loan(db, current_user.id, payload)  # type: ignore[return-value]


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{loan_id}", response_model=LoanResponse, summary="Get a single loan")
async def get_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    loan = await loan_service.get_loan_by_id(db, loan_id, current_user.id)
    return _loan_or_404(loan, loan_id)  # type: ignore[return-value]


# ── Full Update ───────────────────────────────────────────────────────────────

@router.put("/{loan_id}", response_model=LoanResponse, summary="Replace a loan record")
async def replace_loan(
    loan_id: int,
    payload: LoanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    """
    Full replacement update.  All fields are required in the request body.
    Use PATCH for partial updates.
    """
    loan = _loan_or_404(
        await loan_service.get_loan_by_id(db, loan_id, current_user.id), loan_id
    )
    update_payload = LoanUpdate(**payload.model_dump())
    return await loan_service.update_loan(db, loan, update_payload)  # type: ignore[return-value]


# ── Partial Update ────────────────────────────────────────────────────────────

@router.patch("/{loan_id}", response_model=LoanResponse, summary="Partially update a loan")
async def patch_loan(
    loan_id: int,
    payload: LoanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LoanResponse:
    """Only the fields present in the request body are updated."""
    loan = _loan_or_404(
        await loan_service.get_loan_by_id(db, loan_id, current_user.id), loan_id
    )
    return await loan_service.update_loan(db, loan, payload)  # type: ignore[return-value]


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete(
    "/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a loan",
)
async def delete_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    loan = _loan_or_404(
        await loan_service.get_loan_by_id(db, loan_id, current_user.id), loan_id
    )
    await loan_service.delete_loan(db, loan)
