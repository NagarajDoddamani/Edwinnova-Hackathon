"""
routes/health_report.py
────────────────────────
Financial health scoring endpoint.

GET /health-report  → merge stored snapshots → compute score → return HealthReport
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.schemas import HealthReport
from app.services.health_service import compute_health_report
from app.services.snapshot_service import get_merged_financial_data

router = APIRouter(prefix="/health-report", tags=["Financial Health"])


@router.get(
    "",
    response_model=HealthReport,
    summary="Get your financial health report",
    responses={
        200: {"description": "Health report computed successfully."},
        404: {
            "description": (
                "No financial documents have been processed yet. "
                "Upload at least one PDF via /documents/upload first."
            )
        },
    },
)
async def get_health_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HealthReport:
    """
    Compute and return a financial health report for the authenticated user.

    **How scoring works:**

    | Metric                | Weight | Ideal             |
    |----------------------|--------|-------------------|
    | Debt-to-Income ratio | 25 %   | < 40 %            |
    | Savings Rate         | 25 %   | > 20 %            |
    | CIBIL Score          | 25 %   | 750+              |
    | Credit Utilisation   | 15 %   | < 30 %            |
    | Income Growth (ITR)  | 10 %   | > 5 % YoY         |

    The overall **score** is 0–100; the **grade** follows standard A+/A/B/C/D/F scale.

    Missing documents reduce the score for their section rather than causing errors,
    so the report works even if only one PDF has been uploaded.
    """
    financial_data = await get_merged_financial_data(db, current_user.id)

    if financial_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No financial data found. "
                "Please upload your Bank Statement, IT Return, or CIBIL PDF first."
            ),
        )

    return compute_health_report(financial_data)
