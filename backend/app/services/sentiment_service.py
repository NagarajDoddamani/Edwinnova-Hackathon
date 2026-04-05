"""
app/services/sentiment_service.py
───────────────────────────────────
Scores financial sentiment based on extracted data.
Returns a sentiment mode that drives frontend UI.
"""

from dataclasses import dataclass


@dataclass
class SentimentResult:
    score: int           # 0-100
    mode: str            # "stabilization" | "balanced" | "growth" | "investment_pro"
    label: str           # Human readable label
    color: str           # UI color hint
    message: str


def score_sentiment(financial_data: dict, gatekeeper_risk: str) -> SentimentResult:
    score = 50  # base score

    income   = max(financial_data.get("monthly_income", [0]) or [0])
    expenses = max(financial_data.get("monthly_expenses", [0]) or [0])
    credit   = financial_data.get("credit_score") or 0
    assets   = sum(financial_data.get("total_assets", []) or [])

    # Income score (up to +20)
    if income > 100000:
        score += 20
    elif income > 50000:
        score += 10
    elif income > 25000:
        score += 5

    # Surplus score (up to +20)
    if income > 0:
        surplus_pct = ((income - expenses) / income) * 100
        if surplus_pct > 40:
            score += 20
        elif surplus_pct > 20:
            score += 10
        elif surplus_pct > 10:
            score += 5
        elif surplus_pct <= 0:
            score -= 20

    # Credit score (up to +15)
    if credit >= 750:
        score += 15
    elif credit >= 700:
        score += 10
    elif credit >= 650:
        score += 5
    elif 0 < credit < 600:
        score -= 15

    # Assets (up to +10)
    if assets > 1000000:
        score += 10
    elif assets > 500000:
        score += 5

    # Gatekeeper adjustment
    if gatekeeper_risk == "vulnerable":
        score -= 20
    elif gatekeeper_risk == "moderate":
        score -= 5

    # Clamp between 0-100
    score = max(0, min(100, score))

    # Determine mode
    if score < 30:
        return SentimentResult(
            score=score,
            mode="stabilization",
            label="Financial Stress",
            color="#ef4444",
            message="Focus on stabilizing finances before investing.",
        )
    elif score < 50:
        return SentimentResult(
            score=score,
            mode="balanced",
            label="Moderate Anxiety",
            color="#f97316",
            message="Build emergency fund and reduce debt first.",
        )
    elif score < 70:
        return SentimentResult(
            score=score,
            mode="growth",
            label="Stable",
            color="#eab308",
            message="Good foundation. Start with low-risk investments.",
        )
    else:
        return SentimentResult(
            score=score,
            mode="investment_pro",
            label="High Confidence",
            color="#22c55e",
            message="Strong financial health. Ready for diversified investments.",
        )