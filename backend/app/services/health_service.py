"""
services/health_service.py
──────────────────────────
Financial health scoring engine.

Computes a weighted composite score (0–100) from:
  • Debt-to-Income ratio      (25 %)
  • Savings rate              (25 %)
  • CIBIL score               (25 %)
  • Credit utilisation        (15 %)
  • Income growth (ITR)       (10 %)
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.financial_data import FinancialData
from app.schemas.schemas import HealthMetrics, HealthReport

# ── Weights (must sum to 1.0) ─────────────────────────────────────────────────
_WEIGHTS = {
    "debt_to_income": 0.25,
    "savings_rate": 0.25,
    "cibil": 0.25,
    "credit_utilisation": 0.15,
    "income_growth": 0.10,
}


def compute_health_report(financial_data: FinancialData) -> HealthReport:
    """
    Compute a HealthReport from a FinancialData envelope.

    Any missing document simply contributes the section's neutral/worst value
    so the overall score degrades gracefully.
    """
    metrics = _compute_metrics(financial_data)
    score = _weighted_score(metrics)
    grade = _grade(score)
    summary = _narrative(score, grade, metrics)
    recommendations = _recommendations(metrics)

    return HealthReport(
        user_id=financial_data.user_id,
        overall_score=round(score, 1),
        grade=grade,
        summary=summary,
        metrics=metrics,
        recommendations=recommendations,
        generated_at=datetime.now(timezone.utc),
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _compute_metrics(fd: FinancialData) -> HealthMetrics:
    """Compute raw sub-metrics from available financial data."""

    # 1. Debt-to-income ratio (monthly EMI / avg monthly income × 100)
    dti = 0.0
    if fd.bank_statement:
        monthly_income = float(fd.bank_statement.average_monthly_credit or Decimal("1"))
        monthly_emi = sum(
            float(t.amount) for t in fd.bank_statement.emi_transactions
        ) / 6  # spread over 6 months
        dti = (monthly_emi / monthly_income * 100) if monthly_income else 0.0

    # 2. Savings rate ((income − expenses) / income × 100)
    savings_rate = 0.0
    if fd.bank_statement:
        income = float(fd.bank_statement.average_monthly_credit or Decimal("1"))
        expenses = float(fd.bank_statement.average_monthly_debit or Decimal("0"))
        savings_rate = max(0.0, (income - expenses) / income * 100) if income else 0.0

    # 3. CIBIL score — normalise 300–900 → 0–100
    cibil_normalised = 0.0
    if fd.cibil:
        cibil_normalised = (fd.cibil.cibil_score - 300) / 600 * 100

    # 4. Credit utilisation (lower is better; >80% is bad)
    credit_util = 0.0
    if fd.cibil and fd.cibil.accounts:
        total_limit = sum(
            float(a.credit_limit_or_sanction or Decimal("0"))
            for a in fd.cibil.accounts
        )
        total_used = sum(float(a.current_balance) for a in fd.cibil.accounts)
        if total_limit > 0:
            credit_util = total_used / total_limit * 100

    # 5. Income growth (YoY from ITR)
    income_growth = 0.0
    if fd.it_return and len(fd.it_return.years) >= 2:
        sorted_years = sorted(fd.it_return.years, key=lambda y: y.assessment_year)
        old_income = float(sorted_years[-2].gross_total_income or Decimal("1"))
        new_income = float(sorted_years[-1].gross_total_income or Decimal("0"))
        income_growth = (new_income - old_income) / old_income * 100 if old_income else 0.0

    return HealthMetrics(
        debt_to_income_ratio=round(dti, 2),
        savings_rate=round(savings_rate, 2),
        credit_utilisation=round(credit_util, 2),
        cibil_score_normalised=round(cibil_normalised, 2),
        income_growth_rate=round(income_growth, 2),
    )


def _weighted_score(m: HealthMetrics) -> float:
    """
    Convert raw metrics to a 0–100 weighted composite score.
    Each sub-metric is first mapped to a 0–100 component score.
    """
    # DTI: 0–20% → 100 pts; 20–50% linear decay; >50% → 0 pts
    dti_score = max(0.0, min(100.0, (50.0 - m.debt_to_income_ratio) / 50.0 * 100))

    # Savings rate: 0% → 0 pts; 30%+ → 100 pts (linear)
    savings_score = min(100.0, m.savings_rate / 30.0 * 100)

    # CIBIL normalised is already 0–100
    cibil_score = m.cibil_score_normalised

    # Utilisation: 0% → 100 pts; 100% → 0 pts
    util_score = max(0.0, 100.0 - m.credit_utilisation)

    # Income growth: >15% → 100; 0% → 50; negative → 0
    growth_score = min(100.0, max(0.0, (m.income_growth_rate + 15.0) / 30.0 * 100))

    composite = (
        dti_score * _WEIGHTS["debt_to_income"]
        + savings_score * _WEIGHTS["savings_rate"]
        + cibil_score * _WEIGHTS["cibil"]
        + util_score * _WEIGHTS["credit_utilisation"]
        + growth_score * _WEIGHTS["income_growth"]
    )
    return composite


def _grade(score: float) -> str:
    """Map numeric score to letter grade."""
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _narrative(score: float, grade: str, m: HealthMetrics) -> str:
    """Generate a human-readable 2-line summary for the dashboard."""
    if score >= 80:
        tone = "Your finances are in excellent shape."
    elif score >= 60:
        tone = "Your finances are reasonably healthy with room to improve."
    else:
        tone = "Your finances need attention in several areas."

    highlights = []
    if m.debt_to_income_ratio > 40:
        highlights.append("high EMI burden")
    if m.savings_rate < 10:
        highlights.append("low savings rate")
    if m.cibil_score_normalised < 50:
        highlights.append("below-average credit score")

    detail = (
        f" Key concerns: {', '.join(highlights)}." if highlights else " Keep up the good work!"
    )
    return f"{tone}{detail} Overall Grade: {grade}."


def _recommendations(m: HealthMetrics) -> list[str]:
    """Return prioritised, actionable recommendations."""
    recs: list[tuple[int, str]] = []

    if m.debt_to_income_ratio > 40:
        recs.append((10, "Reduce EMI burden: aim for DTI below 40% by prepaying high-interest loans."))
    if m.savings_rate < 20:
        recs.append((9, "Increase your savings rate to at least 20% of income through SIPs or RDs."))
    if m.cibil_score_normalised < 60:
        recs.append((8, "Improve CIBIL score: pay all dues on time and reduce credit card utilisation."))
    if m.credit_utilisation > 30:
        recs.append((7, "Keep credit card utilisation below 30% to protect your credit score."))
    if m.income_growth_rate < 5:
        recs.append((6, "Focus on income growth: upskilling, side income, or salary negotiations."))

    # Always-on advice
    recs.append((3, "Build an emergency fund covering 6 months of expenses."))
    recs.append((2, "Diversify investments across equity, debt, and gold."))

    # Sort highest priority first
    return [r for _, r in sorted(recs, reverse=True)]
