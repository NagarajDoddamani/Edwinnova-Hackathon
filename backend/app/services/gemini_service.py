import re
import pdfplumber
from google import genai
from app.core.config import settings

_client = genai.Client(api_key=settings.GEMINI_API_KEY)


def extract_text(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def anonymize(text: str) -> str:
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '[PAN]', text)
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR]', text)
    text = re.sub(r'\b\d{9,18}\b', '[ACCOUNT]', text)
    text = re.sub(r'\b[6-9]\d{9}\b', '[PHONE]', text)
    text = re.sub(r'\S+@\S+\.\S+', '[EMAIL]', text)
    text = re.sub(r'\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b', '[NAME]', text)
    return text


def extract_financial_data(text: str) -> dict:
    def find_amounts(keywords):
        results = []
        for kw in keywords:
            matches = re.findall(
                rf'(?:{kw})[^\d]{{0,30}}?([\d,]+(?:\.\d{{1,2}})?)',
                text, re.IGNORECASE
            )
            for m in matches[:3]:
                try:
                    results.append(int(float(m.replace(',', ''))))
                except ValueError:
                    pass
        return results

    score_matches = re.findall(r'\b([3-9]\d{2})\b', text)
    credit_score = int(score_matches[0]) if score_matches else None

    return {
        "monthly_income":   find_amounts(["salary", "gross income", "net income", "total income", "credit"]),
        "monthly_expenses": find_amounts(["debit", "expense", "payment", "withdrawal"]),
        "tax_paid":         find_amounts(["tax paid", "TDS", "advance tax"]),
        "account_balance":  find_amounts(["closing balance", "available balance", "balance"]),
        "total_assets":     find_amounts(["total assets", "net worth", "investments"]),
        "credit_score":     credit_score,
    }


def _build_prompt(data: dict, query: str) -> str:
    def fmt(vals):
        if not vals:
            return "Not available"
        return f"Rs.{min(vals):,} - Rs.{max(vals):,} (avg Rs.{sum(vals)//len(vals):,})"

    return f"""
You are a certified financial advisor. Analyze the anonymized financial data below
and answer the user query with specific actionable investment suggestions.

ANONYMIZED FINANCIAL PROFILE:
Monthly Income    : {fmt(data.get('monthly_income', []))}
Monthly Expenses  : {fmt(data.get('monthly_expenses', []))}
Tax Paid (ITR)    : {fmt(data.get('tax_paid', []))}
Account Balance   : {fmt(data.get('account_balance', []))}
Total Assets      : {fmt(data.get('total_assets', []))}
CIBIL Score       : {data.get('credit_score') or 'Not found'}

USER QUERY: {query}

Based ONLY on the numeric data above, provide:
1. Top 3 investment options with expected returns
2. Recommended monthly investment amount
3. Projected growth for 1, 3, and 5 years
4. Risk level for this profile (Low/Medium/High)
5. Things to improve before investing (if any)

Keep response structured and India-specific.
""".strip()


async def get_investment_suggestions(financial_data: dict, query: str) -> dict:
    prompt = _build_prompt(financial_data, query)
    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )
    return {
        "suggestions": response.text,
        "financial_summary": financial_data,
    }