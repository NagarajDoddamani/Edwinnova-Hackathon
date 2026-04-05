"""
schemas/schemas.py
──────────────────
Pydantic v2 request/response schemas for all CRUD resources.

Convention:
    *Create  — used as request body for POST endpoints.
    *Update  — used as request body for PUT/PATCH endpoints (all fields optional).
    *Response — returned by the API (includes DB-generated fields like id, timestamps).
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════════════════════════════════════

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, description="Min 8 characters")


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ═══════════════════════════════════════════════════════════════════════════════
# Loan
# ═══════════════════════════════════════════════════════════════════════════════

class LoanCreate(BaseModel):
    loan_type: str = Field(..., min_length=2, max_length=100, examples=["Home Loan"])
    lender_name: str = Field(..., min_length=2, max_length=255)
    principal_amount: Decimal = Field(..., gt=0)
    outstanding_amount: Decimal = Field(..., ge=0)
    emi_amount: Decimal = Field(..., gt=0)
    interest_rate: Decimal = Field(..., gt=0, le=100)
    start_date: date
    end_date: date
    status: str = Field("active", pattern="^(active|closed|overdue)$")

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class LoanUpdate(BaseModel):
    """All fields optional — send only what changed."""

    loan_type: str | None = None
    lender_name: str | None = None
    outstanding_amount: Decimal | None = None
    emi_amount: Decimal | None = None
    interest_rate: Decimal | None = None
    end_date: date | None = None
    status: str | None = Field(None, pattern="^(active|closed|overdue)$")


class LoanResponse(BaseModel):
    id: int
    user_id: int
    loan_type: str
    lender_name: str
    principal_amount: Decimal
    outstanding_amount: Decimal
    emi_amount: Decimal
    interest_rate: Decimal
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Investment
# ═══════════════════════════════════════════════════════════════════════════════

class InvestmentCreate(BaseModel):
    investment_type: str = Field(..., min_length=2, max_length=100, examples=["Mutual Fund"])
    asset_name: str = Field(..., min_length=2, max_length=255)
    invested_amount: Decimal = Field(..., gt=0)
    current_value: Decimal = Field(..., ge=0)
    returns_percent: Decimal = Field(Decimal("0.00"))
    start_date: date
    maturity_date: date | None = None
    status: str = Field("active", pattern="^(active|redeemed|matured)$")
    referral_link: str | None = None


class InvestmentUpdate(BaseModel):
    current_value: Decimal | None = None
    returns_percent: Decimal | None = None
    maturity_date: date | None = None
    status: str | None = Field(None, pattern="^(active|redeemed|matured)$")
    referral_link: str | None = None


class InvestmentResponse(BaseModel):
    id: int
    user_id: int
    investment_type: str
    asset_name: str
    invested_amount: Decimal
    current_value: Decimal
    returns_percent: Decimal
    start_date: date
    maturity_date: date | None
    status: str
    referral_link: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Financial Health Report (returned by /health endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

class HealthMetrics(BaseModel):
    """Numeric breakdown of the financial health score."""

    debt_to_income_ratio: float = Field(..., description="Total EMI / Monthly income × 100")
    savings_rate: float = Field(..., description="(Income − Expenses) / Income × 100")
    credit_utilisation: float = Field(..., description="Used credit / Limit × 100 (from CIBIL)")
    cibil_score_normalised: float = Field(..., description="CIBIL score mapped to 0–100 scale")
    income_growth_rate: float = Field(..., description="YoY income growth % (from ITR)")


class HealthReport(BaseModel):
    """
    Composite financial health report.

    overall_score : Weighted average of all sub-metrics (0–100).
    grade         : Letter grade — A+, A, B, C, D, F.
    summary       : Human-readable 2–3 line narrative for the UI.
    metrics       : Raw sub-scores for charting.
    recommendations: Actionable suggestions ranked by impact.
    """

    user_id: int
    overall_score: float = Field(..., ge=0, le=100)
    grade: str
    summary: str
    metrics: HealthMetrics
    recommendations: list[str]
    generated_at: datetime
