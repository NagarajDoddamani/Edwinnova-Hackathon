from fastapi import APIRouter

router = APIRouter()


@router.post("/recommend")
def generate_recommendation(payload: dict):
    user = payload.get("user_profile", {})
    finance = payload.get("financial_data", {})
    derived = payload.get("derived_metrics", {})
    preferences = payload.get("preferences", {})
    query_context = payload.get("query_context", {})

    income = float(finance.get("income", 0) or 0)
    expenses = float(finance.get("expenses", 0) or 0)
    savings = float(finance.get("savings", 0) or 0)
    debt = float(finance.get("debt", 0) or 0)
    emi = float(finance.get("emi", 0) or 0)

    monthly_surplus = income - expenses
    emergency_months = (savings / expenses) if expenses > 0 else 0
    high_debt = debt > 0 and emi > 0

    priority = "investments"
    summary = "You can consider investment options."

    if emergency_months < 3:
        priority = "emergency_fund"
        summary = "Build at least 3 months of emergency funds before investing."
    elif high_debt:
        priority = "emi_repayment"
        summary = "Prioritize debt and EMI repayment before increasing investments."

    return {
        "success": True,
        "user_profile": user,
        "financial_data": finance,
        "derived_metrics": {
            **derived,
            "monthly_surplus": monthly_surplus,
            "emergency_fund_months": emergency_months,
        },
        "preferences": preferences,
        "query_context": query_context,
        "recommendation": {
            "priority": priority,
            "summary": summary,
            "safe_to_invest": emergency_months >= 3 and not high_debt,
        },
    }
