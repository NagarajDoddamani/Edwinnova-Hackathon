"""
app/services/gatekeeper.py
───────────────────────────
Deterministic rules engine that checks financial health
before allowing AI to suggest investments.
"""

from dataclasses import dataclass


@dataclass
class GatekeeperResult:
    allowed: bool
    risk_level: str        # "safe" | "moderate" | "vulnerable"
    reason: str
    monthly_surplus: int
    safe_invest_amount: int


def run_gatekeeper(financial_data: dict) -> GatekeeperResult:
    income    = max(financial_data.get("monthly_income", [0]) or [0])
    expenses  = max(financial_data.get("monthly_expenses", [0]) or [0])
    credit    = financial_data.get("credit_score") or 0
    tax_paid  = sum(financial_data.get("tax_paid", []) or [])

    surplus = income - expenses

    # ── Rule 1: No income data ────────────────────────────────────────────────
    if income == 0:
        return GatekeeperResult(
            allowed=False,
            risk_level="unknown",
            reason="Cannot determine income from uploaded documents. Please upload a valid bank statement.",
            monthly_surplus=0,
            safe_invest_amount=0,
        )

    # ── Rule 2: Negative or zero surplus ─────────────────────────────────────
    if surplus <= 0:
        return GatekeeperResult(
            allowed=False,
            risk_level="vulnerable",
            reason=f"Your expenses (Rs.{expenses:,}) exceed your income (Rs.{income:,}). Focus on reducing expenses before investing.",
            monthly_surplus=surplus,
            safe_invest_amount=0,
        )

    # ── Rule 3: Surplus less than 10% of income ───────────────────────────────
    surplus_pct = (surplus / income) * 100
    if surplus_pct < 10:
        return GatekeeperResult(
            allowed=False,
            risk_level="vulnerable",
            reason=f"Your monthly surplus is only {surplus_pct:.1f}% of income. Build an emergency fund of at least 3 months expenses first.",
            monthly_surplus=surplus,
            safe_invest_amount=0,
        )

    # ── Rule 4: Low CIBIL score ───────────────────────────────────────────────
    if 0 < credit < 650:
        return GatekeeperResult(
            allowed=False,
            risk_level="vulnerable",
            reason=f"Your CIBIL score ({credit}) is too low for investment advice. Focus on clearing existing debts first.",
            monthly_surplus=surplus,
            safe_invest_amount=0,
        )

    # ── Rule 5: Moderate — can invest but conservatively ─────────────────────
    if surplus_pct < 20 or (0 < credit < 700):
        safe_amount = int(surplus * 0.3)
        return GatekeeperResult(
            allowed=True,
            risk_level="moderate",
            reason=f"Moderate financial health. Surplus: Rs.{surplus:,}/month. Recommended to invest conservatively.",
            monthly_surplus=surplus,
            safe_invest_amount=safe_amount,
        )

    # ── Rule 6: Healthy — full investment advice allowed ─────────────────────
    safe_amount = int(surplus * 0.5)
    return GatekeeperResult(
        allowed=True,
        risk_level="safe",
        reason=f"Good financial health. Surplus: Rs.{surplus:,}/month. You can invest up to Rs.{safe_amount:,}/month.",
        monthly_surplus=surplus,
        safe_invest_amount=safe_amount,
    )