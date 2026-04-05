import json
import os
import uuid
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
from fastapi import FastAPI, HTTPException, Depends, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from pymongo import MongoClient
from jose import jwt
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import certifi
from typing import List
import re
from google import genai
from google.genai import types
import traceback



# Load .env file
load_dotenv()

# ================= CONFIG =================

SECRET_KEY = os.getenv("SECRET_KEY", "finarmor_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is required. Please set it in your .env file.")

# ================= DB =================

mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["finarmor"]

users = db["users"]
finance = db["finance"]
queries = db["queries"]
goals = db["goals"]
QUERY_PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent / "prompts" / "query_ai_prompt.txt"

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "20"))
ALLOWED_DOC_TYPES = {"bank_statement", "it_return", "cibil"}

_TXN_DATE_RE = re.compile(r"(\d{2}-\d{2}-\d{4})")
_AMOUNT_RE = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})(?!\d)")
_SALARY_RE = re.compile(r"\b(salary|sal|payroll|stipend)\b", re.IGNORECASE)
_EMI_RE = re.compile(r"\b(emi|loan|repay|equated|installment|instalment)\b", re.IGNORECASE)
_CHARGE_RE = re.compile(r"\b(charge|fee|bounce|penalty|gst|service charges?)\b", re.IGNORECASE)
_CASH_RE = re.compile(r"\b(cash withdrawal|atm wdl|cash-bna-self)\b", re.IGNORECASE)
_TRANSFER_RE = re.compile(r"\b(neft|imps|rtgs|upi|transfer|trf|clg|clearing)\b", re.IGNORECASE)


def _to_decimal(value: str | None) -> Decimal:
    if not value:
        return Decimal("0")

    cleaned = value.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _quantize_two(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _extract_pdf_text(file_path: Path) -> str:
    pages: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _classify_transaction(description: str, txn_type: str) -> str:
    lowered = description.lower()

    if txn_type == "credit":
        if _SALARY_RE.search(lowered):
            return "salary"
        return "other_income"

    if _EMI_RE.search(lowered):
        return "emi"
    if _CHARGE_RE.search(lowered):
        return "charges"
    if _CASH_RE.search(lowered):
        return "cash"
    if _TRANSFER_RE.search(lowered):
        return "transfer"
    return "other_expense"


def _estimate_month_count(text: str, transaction_dates: list[datetime]) -> int:
    months = {(date.year, date.month) for date in transaction_dates}
    if months:
        return max(len(months), 1)

    range_match = re.search(
        r"From\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s+To\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
        text,
        re.IGNORECASE,
    )
    if range_match:
        start = datetime.strptime(range_match.group(1), "%d %b %Y")
        end = datetime.strptime(range_match.group(2), "%d %b %Y")
        months_apart = (end.year - start.year) * 12 + (end.month - start.month) + 1
        return max(months_apart, 1)

    return 1


def _build_finance_payload_from_pdf(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    categories = defaultdict(Decimal)
    transaction_dates: list[datetime] = []
    previous_balance: Decimal | None = None
    transactions_count = 0

    for line in lines:
        date_match = _TXN_DATE_RE.search(line)
        if not date_match:
            continue

        amount_strings = _AMOUNT_RE.findall(line)
        if len(amount_strings) < 2:
            continue

        transaction_amount = _to_decimal(amount_strings[-2])
        current_balance = _to_decimal(amount_strings[-1])

        try:
            txn_date = datetime.strptime(date_match.group(1), "%d-%m-%Y")
            transaction_dates.append(txn_date)
        except ValueError:
            pass

        txn_type = None
        if previous_balance is not None:
            delta = current_balance - previous_balance
            if delta > 0:
                txn_type = "credit"
            elif delta < 0:
                txn_type = "debit"

        if txn_type is None:
            if _SALARY_RE.search(line) or re.search(r"\bcr\b|credit", line, re.IGNORECASE):
                txn_type = "credit"
            else:
                txn_type = "debit"

        category = _classify_transaction(line, txn_type)
        categories[category] += transaction_amount
        previous_balance = current_balance
        transactions_count += 1

    months = _estimate_month_count(text, transaction_dates)

    income_total = categories["salary"] + categories["other_income"]
    expense_total = (
        categories["emi"]
        + categories["cash"]
        + categories["transfer"]
        + categories["charges"]
        + categories["other_expense"]
    )
    liability_total = categories["emi"]

    monthly_income_total = _quantize_two(income_total / Decimal(months))
    monthly_expense_total = _quantize_two(expense_total / Decimal(months))
    monthly_liability_total = _quantize_two(liability_total / Decimal(months))
    monthly_savings_total = _quantize_two(monthly_income_total - monthly_expense_total)

    def monthly(amount: Decimal) -> float:
        return float(_quantize_two(amount / Decimal(months)))

    income_items = []
    if categories["salary"] > 0:
        income_items.append({"name": "Salary (PDF)", "amount": monthly(categories["salary"]), "type": "fixed"})
    if categories["other_income"] > 0:
        income_items.append({"name": "Other Income (PDF)", "amount": monthly(categories["other_income"]), "type": "variable"})
    if not income_items and income_total > 0:
        income_items.append({"name": "Bank Credits (PDF)", "amount": float(monthly_income_total), "type": "fixed"})

    expense_items = []
    for label, key, item_type in (
        ("Loan EMI (PDF)", "emi", "fixed"),
        ("Cash Withdrawal (PDF)", "cash", "variable"),
        ("Transfers / Payments (PDF)", "transfer", "variable"),
        ("Bank Charges (PDF)", "charges", "variable"),
        ("Other Expenses (PDF)", "other_expense", "variable"),
    ):
        if categories[key] > 0:
            expense_items.append({"name": label, "amount": monthly(categories[key]), "type": item_type})

    if not expense_items and expense_total > 0:
        expense_items.append({"name": "Bank Debits (PDF)", "amount": float(monthly_expense_total), "type": "variable"})

    liability_items = []
    if categories["emi"] > 0:
        liability_items.append({"name": "EMI / Loan Obligation (PDF)", "amount": float(monthly_liability_total), "type": "fixed"})

    savings_items = [{"name": "Net Savings (PDF)", "amount": float(monthly_savings_total), "type": "fixed"}]

    return {
        "income": income_items or [{"name": "Bank Credits (PDF)", "amount": 0.0, "type": "fixed"}],
        "expenses": expense_items or [{"name": "Bank Debits (PDF)", "amount": 0.0, "type": "variable"}],
        "savings": savings_items,
        "liabilities": liability_items,
        "summary": {
            "transactions": transactions_count,
            "months": months,
            "totals": {
                "income": float(monthly_income_total),
                "expenses": float(monthly_expense_total),
                "savings": float(monthly_savings_total),
                "liabilities": float(monthly_liability_total),
            },
            "categories": {
                key: float(_quantize_two(value))
                for key, value in categories.items()
                if value > 0
            },
        },
    }


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_VERSION = os.getenv("GEMINI_API_VERSION", "v1beta")
GEMINI_TEXT_DISABLED = False
try:
    gemini_client = (
        genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(
                api_version=GEMINI_API_VERSION,
                client_args={"trust_env": False},
            ),
        )
        if GEMINI_API_KEY
        else None
    )
except Exception as e:
    print("GEMINI CLIENT INIT ERROR:", e)
    gemini_client = None

# ================= APP =================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ðŸ”¥ for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= AUTH =================

security = HTTPBearer()

def create_token(data: dict):
    data["exp"] = datetime.utcnow() + timedelta(days=1)
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(401, "Invalid token")

# ================= MODELS =================

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class Item(BaseModel):
    name: str
    amount: float
    type: str  # fixed / variable

class FinanceData(BaseModel):
    income: List[Item]
    expenses: List[Item]
    savings: List[Item]
    liabilities: List[Item] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleUser(BaseModel):
    name: str
    email: EmailStr

class UpdateUser(BaseModel):
    name: str | None = None
    age: int | None = None
    employment_type: str | None = None
    location: str | None = None

class FinanceInput(BaseModel):
    income: float
    expenses: float
    savings: float
    debt: float
    emi: float

class QueryInput(BaseModel):
    question: str

class GoalInput(BaseModel):
    title: str
    target_amount: float
    saved_amount: float = 0
    target_date: str | None = None
    monthly_target: float | None = None

# ================= ROOT =================

@app.get("/")
def root():
    return {"message": "FinArmor backend running"}

# ================= AUTH =================

@app.post("/auth/register")
def register(user: UserRegister):

    if users.find_one({"email": user.email}):
        raise HTTPException(400, "User already exists")

    users.insert_one({
        "name": user.name,
        "email": user.email,
        "password": user.password,  # âœ… plain password
        "created_at": datetime.utcnow()
    })

    token = create_token({"email": user.email})

    return {"access_token": token}


@app.post("/auth/login")
def login(user: UserLogin):

    db_user = users.find_one({"email": user.email})

    if not db_user:
        raise HTTPException(400, "User not found")

    if user.password != db_user["password"]:
        raise HTTPException(400, "Invalid password")

    token = create_token({"email": user.email})

    return {"access_token": token}


@app.post("/auth/google")
def google_login(user: GoogleUser):

    db_user = users.find_one({"email": user.email})

    if not db_user:
        users.insert_one({
            "name": user.name,
            "email": user.email,
            "password": None,
            "created_at": datetime.utcnow()
        })

    token = create_token({"email": user.email})

    return {"access_token": token}

# ================= USER =================

@app.get("/user/me")
def get_me(data=Depends(verify_token)):

    user = users.find_one(
        {"email": data["email"]},
        {"_id": 0, "password": 0}
    )

    if not user:
        raise HTTPException(404, "User not found")

    return user


@app.put("/user/update")
def update_user(update: UpdateUser, data=Depends(verify_token)):

    users.update_one(
        {"email": data["email"]},
        {"$set": {k: v for k, v in update.dict().items() if v is not None}}
    )

    return {"message": "updated"}

# ================= FINANCE =================

@app.post("/finance/update")
def update_finance(fin: FinanceInput, data=Depends(verify_token)):

    finance.update_one(
        {"email": data["email"]},
        {
            "$set": {
                "email": data["email"],
                "income": fin.income,
                "expenses": fin.expenses,
                "savings": fin.savings,
                "debt": fin.debt,
                "emi": fin.emi,
                "updated_at": datetime.utcnow()
            }
        },
        upsert=True
    )

    return {"message": "finance updated"}


@app.post("/documents/upload")
def upload_document(
    document_type: str = Form("bank_statement"),
    file: UploadFile = File(...),
    data=Depends(verify_token),
):
    if document_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            400,
            f"document_type must be one of: {', '.join(sorted(ALLOWED_DOC_TYPES))}",
        )

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(400, "Invalid file type. Please upload a PDF.")

    content = file.file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {MAX_FILE_MB} MB.")

    dest_dir = Path(UPLOAD_DIR) / data["email"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4()}.pdf"
    dest.write_bytes(content)

    try:
        if document_type != "bank_statement":
            return {
                "message": "Document uploaded successfully.",
                "document_type": document_type,
                "filename": filename,
                "status": "stored",
                "income": [],
                "expenses": [],
                "savings": [],
                "liabilities": [],
                "summary": {
                    "transactions": 0,
                    "months": 0,
                    "totals": {
                        "income": 0.0,
                        "expenses": 0.0,
                        "savings": 0.0,
                        "liabilities": 0.0,
                    },
                    "categories": {},
                },
            }

        text = _extract_pdf_text(dest)
        parsed = _build_finance_payload_from_pdf(text)

        finance.update_one(
            {"email": data["email"]},
            {
                "$set": {
                    "email": data["email"],
                    "income": parsed["income"],
                    "expenses": parsed["expenses"],
                    "savings": parsed["savings"],
                    "liabilities": parsed["liabilities"],
                    "totals": parsed["summary"]["totals"],
                    "last_pdf_upload": {
                        "document_type": document_type,
                        "filename": filename,
                        "stored_path": str(dest),
                        "updated_at": datetime.utcnow(),
                    },
                }
            },
            upsert=True,
        )

        parsed["message"] = "Document uploaded and parsed successfully."
        parsed["document_type"] = document_type
        parsed["filename"] = filename
        parsed["status"] = "parsed"
        return parsed
    except Exception as exc:
        raise HTTPException(500, f"Failed to process PDF: {exc}") from exc

# ================= QUERY =================

@app.post("/query/ask")
def ask_query(q: QueryInput, data=Depends(verify_token)):

    answer = f"AI Response: {q.question}"

    queries.insert_one({
        "email": data["email"],
        "question": q.question,
        "answer": answer,
        "timestamp": datetime.utcnow()
    })

    return {"answer": answer}

@app.post("/finance/submit")
def submit_finance(data: FinanceData, user=Depends(verify_token)):

    # ðŸ”¥ VALIDATION
    if len(data.income) == 0:
        raise HTTPException(400, "At least 1 income required")

    if len(data.expenses) == 0:
        raise HTTPException(400, "At least 1 expense required")

    if len(data.savings) == 0:
        raise HTTPException(400, "At least 1 saving required")

    # âœ… CALCULATE TOTALS
    total_income = sum(float(i.amount) for i in data.income)
    total_expenses = sum(float(i.amount) for i in data.expenses)
    total_savings = sum(float(i.amount) for i in data.savings)
    total_liabilities = sum(float(i.amount) for i in data.liabilities)

    # âœ… STORE IN MONGO
    finance.update_one(
        {"email": user["email"]},
        {
            "$set": {
                "email": user["email"],

                "income": [i.dict() for i in data.income],
                "expenses": [i.dict() for i in data.expenses],
                "savings": [i.dict() for i in data.savings],
                "liabilities": [i.dict() for i in data.liabilities],

                "totals": {
                    "income": total_income,
                    "expenses": total_expenses,
                    "savings": total_savings,
                    "liabilities": total_liabilities,
                },
            }
        },
        upsert=True,
    )

    return {"message": "Finance saved successfully"}

def _sum_item_amounts(items) -> float:
    if not isinstance(items, list):
        return 0.0

    total = 0.0
    for item in items:
        if isinstance(item, dict):
            total += float(item.get("amount", 0) or 0)
    return total


def _extract_profile_completion(value) -> int:
    if value is None:
        return 0

    text = str(value).strip().replace("%", "")
    try:
        return max(0, min(int(float(text)), 100))
    except (TypeError, ValueError):
        return 0


def _load_finance_snapshot(email: str) -> dict:
    doc = finance.find_one({"email": email}) or {}
    totals = doc.get("totals") or {}

    if totals:
        income = float(totals.get("income", 0) or 0)
        expenses = float(totals.get("expenses", 0) or 0)
        raw_savings = totals.get("savings")
        savings = float(raw_savings if raw_savings is not None else max(income - expenses, 0))
        debt = float(totals.get("debt", doc.get("debt", 0) or 0) or 0)
        emi = float(totals.get("emi", doc.get("emi", 0) or 0) or 0)
    else:
        income_raw = doc.get("income", 0)
        expenses_raw = doc.get("expenses", 0)
        savings_raw = doc.get("savings")

        income = _sum_item_amounts(income_raw) if isinstance(income_raw, list) else float(income_raw or 0)
        expenses = _sum_item_amounts(expenses_raw) if isinstance(expenses_raw, list) else float(expenses_raw or 0)

        if isinstance(savings_raw, list):
          savings = _sum_item_amounts(savings_raw)
        else:
          savings = float(savings_raw if savings_raw is not None else max(income - expenses, 0))

        debt = float(doc.get("debt", 0) or 0)
        emi = float(doc.get("emi", 0) or 0)
        liabilities_total = _sum_item_amounts(doc.get("liabilities"))
        if debt <= 0 and liabilities_total > 0:
            debt = liabilities_total

    has_data = bool(totals) or any(
        doc.get(key) is not None for key in ("income", "expenses", "savings", "debt", "emi", "liabilities")
    )

    return {
        "doc": doc,
        "totals": totals,
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "debt": debt,
        "emi": emi,
        "has_data": has_data,
    }


def _load_goals(email: str) -> list[dict]:
    return list(
        goals.find({"email": email}, {"_id": 0})
        .sort([("created_at", -1), ("updated_at", -1)])
    )


def _serialize_goal(goal: dict) -> dict:
    target_amount = float(goal.get("target_amount", 0) or 0)
    saved_amount = float(goal.get("saved_amount", 0) or 0)
    monthly_target = float(goal.get("monthly_target", 0) or 0)
    progress = round(min((saved_amount / target_amount) * 100, 100), 2) if target_amount > 0 else 0

    return {
        "goal_id": goal.get("goal_id"),
        "title": goal.get("title"),
        "target_amount": target_amount,
        "saved_amount": saved_amount,
        "monthly_target": monthly_target,
        "target_date": goal.get("target_date"),
        "status": goal.get("status", "active"),
        "created_at": goal.get("created_at"),
        "updated_at": goal.get("updated_at"),
        "progress": progress,
        "remaining_amount": max(target_amount - saved_amount, 0),
    }


def _grade_from_score(score: int) -> str:
    if score >= 90:
        return "A+"
    if score >= 80:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    if score >= 45:
        return "D"
    return "F"


def _clamp_score(value: float) -> int:
    return max(min(int(round(value)), 25), 0)


def _build_analysis_scores(snapshot: dict, goal_docs: list[dict]) -> dict:
    income = float(snapshot["income"] or 0)
    expenses = float(snapshot["expenses"] or 0)
    savings = float(snapshot["savings"] or 0)
    debt = float(snapshot["debt"] or 0)
    emi = float(snapshot["emi"] or 0)

    profile_source = 90 if snapshot["totals"] else (80 if snapshot["has_data"] else 20)
    profile_score = round(profile_source / 100 * 25)

    savings_rate = (savings / income * 100) if income > 0 else 0
    if income <= 0:
        context_score = 0
    elif savings_rate >= 25:
        context_score = 25
    elif savings_rate >= 15:
        context_score = 20
    elif savings_rate >= 8:
        context_score = 15
    elif savings_rate >= 0:
        context_score = 10
    else:
        context_score = 6

    debt_pressure = ((debt + emi) / income * 100) if income > 0 else 100
    if debt_pressure <= 10:
        behavior_score = 25
    elif debt_pressure <= 20:
        behavior_score = 20
    elif debt_pressure <= 35:
        behavior_score = 15
    elif debt_pressure <= 50:
        behavior_score = 10
    else:
        behavior_score = 5

    goal_count = len(goal_docs)
    if goal_count == 0:
        goal_score = 5
    else:
        goal_score = min(25, 8 + goal_count * 6)

    total_score = max(min(profile_score + context_score + behavior_score + goal_score, 100), 0)

    recommendations = []
    if profile_source < 80:
        recommendations.append("Complete your profile to sharpen the score.")
    if savings_rate < 10 and income > 0:
        recommendations.append("Try to keep at least 10% of income as monthly savings.")
    if debt_pressure > 25 and income > 0:
        recommendations.append("Reduce debt pressure before taking on new commitments.")
    if goal_count == 0:
        recommendations.append("Set one upcoming savings goal to keep the plan focused.")
    if not recommendations:
        recommendations.append("Your habits look steady. Keep reviewing the plan monthly.")

    active_goal = goal_docs[0] if goal_docs else None
    financial_goal = active_goal.get("title") if active_goal else "No active goal"

    if savings_rate >= 25 and debt_pressure <= 10:
        recommendation = "Strong position. Keep the surplus focused on your current goal."
    elif debt_pressure > 25:
        recommendation = "Prioritize debt control and keep new spending conservative."
    elif savings_rate < 10:
        recommendation = "Increase monthly savings before scaling investments."
    else:
        recommendation = "Stay consistent and review the plan on a monthly cadence."

    return {
        "total_score": total_score,
        "grade": _grade_from_score(total_score),
        "score_breakdown": {
            "profile_score": profile_score,
            "context_score": context_score,
            "behavior_score": behavior_score,
            "goal_score": goal_score,
        },
        "recommendation": recommendation,
        "recommendations": recommendations,
        "financial_goals": financial_goal,
        "goal_count": goal_count,
        "active_goal": _serialize_goal(active_goal) if active_goal else None,
        "savings_rate": round(savings_rate, 2),
        "debt_pressure": round(debt_pressure, 2),
    }


def _build_dashboard_fallback(snapshot: dict, goal_docs: list[dict], recent_queries: list[dict]) -> dict:
    income = float(snapshot["income"] or 0)
    savings = float(snapshot["savings"] or 0)
    debt = float(snapshot["debt"] or 0)
    emi = float(snapshot["emi"] or 0)
    goal_count = len(goal_docs)
    query_count = len(recent_queries)
    savings_rate = (savings / income * 100) if income > 0 else 0
    debt_pressure = ((debt + emi) / income * 100) if income > 0 else 100

    if savings_rate >= 20 and debt_pressure <= 10:
        sentiment = {"label": "Confident", "score": 82, "reason": "Savings are healthy and debt pressure is low."}
    elif debt_pressure > 25:
        sentiment = {"label": "Stressed", "score": 48, "reason": "Debt pressure is high, so the plan should stay conservative."}
    elif savings_rate < 10:
        sentiment = {"label": "Cautious", "score": 58, "reason": "There is room to improve savings before expanding risk."}
    else:
        sentiment = {"label": "Balanced", "score": 70, "reason": "Your money flow looks steady and manageable."}

    if goal_count > 0 and savings_rate >= 15:
        behavior = {"label": "Goal-oriented", "score": 80, "reason": "You already have a savings goal and a workable surplus."}
    elif query_count > 4:
        behavior = {"label": "Active Planner", "score": 72, "reason": "You are asking regular questions and checking the plan often."}
    elif debt_pressure > 20:
        behavior = {"label": "Reactive", "score": 52, "reason": "Debt pressure is pushing the plan toward short-term fixes."}
    else:
        behavior = {"label": "Early Stage", "score": 60, "reason": "The profile is still building, so focus on simple habits."}

    risk_level = "Low" if savings_rate >= 20 and debt_pressure <= 10 else "Moderate" if debt_pressure <= 25 else "High"

    highlights = [
        f"{query_count} recent questions logged",
        f"{goal_count} active goals",
        f"Savings rate around {round(savings_rate, 1)}%",
    ]

    recommendations = []
    if goal_count == 0:
        recommendations.append("Set one upcoming savings goal and track it weekly.")
    if savings_rate < 12 and income > 0:
        recommendations.append("Raise monthly savings to at least 12% of income.")
    if debt_pressure > 20 and income > 0:
        recommendations.append("Trim debt pressure before adding new spending.")
    if not recommendations:
        recommendations.append("Keep the current plan and review it at month-end.")

    active_goal = goal_docs[0] if goal_docs else None
    goal_focus = {
        "title": active_goal.get("title") if active_goal else "Emergency fund",
        "target_amount": int(active_goal.get("target_amount", 0) or 50000) if active_goal else 50000,
        "reason": "A near-term savings target keeps the dashboard focused.",
    }
    if active_goal:
        goal_focus["reason"] = "The most recent goal should stay on top of your plan."

    notification = {
        "title": "FinArmor check-in",
        "message": "Your dashboard is ready with a fresh behavior and goal review.",
    }

    next_action = (
        "Keep saving into the active goal and review debt pressure each month."
        if goal_count
        else "Create one upcoming savings goal before taking new risks."
    )

    return {
        "sentiment": sentiment,
        "behavior": behavior,
        "risk": {"level": risk_level, "reason": "Based on savings rate, debt pressure, and recent questions."},
        "highlights": highlights,
        "recommendations": recommendations,
        "goal_focus": goal_focus,
        "next_action": next_action,
        "notification": notification,
    }

@app.get("/finance/analysis")
def get_analysis(user=Depends(verify_token)):
    snapshot = _load_finance_snapshot(user["email"])
    goal_docs = _load_goals(user["email"])

    if not snapshot["has_data"]:
        return {
            "income": 0,
            "expenses": 0,
            "savings": 0,
            "debt": 0,
            "emi": 0,
            "goals": 0,
            "goal_count": 0,
            "profile_completion": "20%",
            "total_score": 0,
            "grade": "F",
            "score_breakdown": {
                "profile_score": 0,
                "context_score": 0,
                "behavior_score": 0,
                "goal_score": 0,
            },
            "recommendation": "Complete your profile",
            "recommendations": ["Complete your profile to unlock the full score."],
            "financial_goals": "No active goal",
            "active_goal": None,
            "savings_rate": 0,
            "debt_pressure": 0,
        }

    profile_completion = "90%" if snapshot["totals"] else "80%"
    scores = _build_analysis_scores(snapshot, goal_docs)

    return {
        "income": snapshot["income"],
        "expenses": snapshot["expenses"],
        "savings": snapshot["savings"],
        "debt": snapshot["debt"],
        "emi": snapshot["emi"],
        "goals": len(goal_docs),
        "goal_count": len(goal_docs),
        "profile_completion": profile_completion,
        "total_score": scores["total_score"],
        "grade": scores["grade"],
        "score_breakdown": scores["score_breakdown"],
        "recommendation": scores["recommendation"],
        "recommendations": scores["recommendations"],
        "financial_goals": scores["financial_goals"],
        "active_goal": scores["active_goal"],
        "savings_rate": scores["savings_rate"],
        "debt_pressure": scores["debt_pressure"],
    }

# ==============AI part===========
def extract_user_question(payload: dict) -> str:
    """
    Accept both a raw question and the full prompt produced by the UI.
    """
    raw = (payload.get("question") or payload.get("prompt") or payload.get("query") or "").strip()

    if "User Question:" in raw:
        segment = raw.split("User Question:", 1)[1]
        if "Instructions:" in segment:
            segment = segment.split("Instructions:", 1)[0]
        return segment.strip().strip('"').strip()

    return raw


def extract_requested_amount(question: str, fallback: float) -> float:
    """
    Prefer an explicit amount mentioned by the user, otherwise fall back to the available balance.
    """
    text = question.lower().replace(",", "")

    matches = list(re.finditer(r"(?:â‚¹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)(?:\s*(k|m|l|lac|lakh|crore|cr))?", text))
    if not matches:
        return max(float(fallback), 0.0)

    amount = matches[-1].group(1)
    suffix = (matches[-1].group(2) or "").lower()

    value = float(amount)
    if suffix in {"k"}:
        value *= 1_000
    elif suffix in {"m"}:
        value *= 1_000_000
    elif suffix in {"l", "lac", "lakh"}:
        value *= 100_000
    elif suffix in {"crore", "cr"}:
        value *= 10_000_000

    return max(value, 0.0)


def extract_requested_amount_safe(question: str) -> float:
    text = (question or "").lower().replace(",", "")
    matches = list(
        re.finditer(r"(?:rs\.?|inr|rupees?)?\s*(\d+(?:\.\d+)?)(?:\s*(k|m|l|lac|lakh|crore|cr))?", text)
    )
    if not matches:
        return 0.0

    amount = matches[-1].group(1)
    suffix = (matches[-1].group(2) or "").lower()

    value = float(amount)
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    elif suffix in {"l", "lac", "lakh"}:
        value *= 100_000
    elif suffix in {"crore", "cr"}:
        value *= 10_000_000

    return max(value, 0.0)


def format_currency(amount: float) -> str:
    return f"Rs. {max(int(round(amount)), 0):,}"


QUERY_INTENT_KEYWORDS = {
    "debt": [
        "emi",
        "loan",
        "debt",
        "credit card",
        "repay",
        "repayment",
        "interest",
        "overdue",
        "installment",
        "instalment",
    ],
    "purchase": [
        "buy",
        "purchase",
        "laptop",
        "phone",
        "mobile",
        "car",
        "bike",
        "watch",
        "tv",
        "television",
        "camera",
        "home",
        "house",
        "property",
        "furniture",
        "appliance",
        "vacation",
        "trip",
    ],
    "investment": [
        "invest",
        "investment",
        "sip",
        "stock",
        "stocks",
        "equity",
        "share",
        "shares",
        "mutual fund",
        "mutual funds",
        "fd",
        "fixed deposit",
        "rd",
        "recurring deposit",
        "gold",
        "real estate",
        "portfolio",
        "etf",
        "bond",
    ],
    "savings": [
        "save",
        "savings",
        "emergency fund",
        "buffer",
        "budget",
    ],
    "goal": [
        "goal",
        "goals",
        "target",
        "milestone",
        "reach my goal",
        "achieve my goal",
        "financial goal",
        "goal plan",
    ],
}

ASSET_ALIAS_MAP = {
    "SIP": ["sip", "systematic investment plan"],
    "Stocks": ["stock", "stocks", "equity", "shares", "share market"],
    "FD": ["fd", "fixed deposit", "bank fd", "bank deposit"],
    "RD": ["rd", "recurring deposit"],
    "Gold": ["gold", "gold etf", "sovereign gold"],
    "Mutual Fund": ["mutual fund", "mutual funds", "mf", "index fund", "index funds"],
    "Real Estate": ["real estate", "property", "land", "house property"],
    "Laptop": ["laptop", "notebook", "macbook"],
    "Phone": ["phone", "mobile", "smartphone"],
    "Car": ["car", "vehicle", "automobile"],
}

RAG_KNOWLEDGE_BASE = [
    {
        "id": "debt_first",
        "intents": ["debt", "purchase", "investment"],
        "keywords": ["debt", "emi", "loan", "credit card", "interest", "repayment"],
        "title": "Debt comes first",
        "content": "If EMI or debt pressure is high, recommend debt repayment before a new purchase or a new investment. Keep the emergency buffer untouched.",
    },
    {
        "id": "emergency_buffer",
        "intents": ["purchase", "investment", "savings"],
        "keywords": ["emergency fund", "buffer", "reserve", "cash buffer"],
        "title": "Emergency buffer rule",
        "content": "Keep at least 3 months of essential expenses in reserve before discretionary spending or aggressive investing.",
    },
    {
        "id": "goal_completion",
        "intents": ["goal", "savings", "mixed"],
        "keywords": ["goal", "target", "milestone", "progress", "monthly target", "remaining amount"],
        "title": "Goal completion",
        "content": "Use the active goal, remaining gap, and monthly target to decide whether to save first, invest later, or split the surplus.",
    },
    {
        "id": "goal_priority",
        "intents": ["goal", "investment", "purchase"],
        "keywords": ["goal first", "goal management", "reach my goal", "complete goal"],
        "title": "Goal priority",
        "content": "If the goal is near-term or underfunded, direct surplus to the goal before riskier investments. Keep the emergency buffer intact.",
    },
    {
        "id": "purchase_affordability",
        "intents": ["purchase"],
        "keywords": ["buy", "purchase", "laptop", "phone", "car", "bike", "house", "home", "property", "furniture"],
        "title": "Purchase affordability",
        "content": "For a big purchase, compare the price with savings, monthly surplus, and the emergency buffer. If the purchase drains the buffer or leaves debt pressure high, recommend wait or downsize.",
    },
    {
        "id": "low_risk_investing",
        "intents": ["investment"],
        "keywords": ["fd", "rd", "gold", "low risk", "capital safety", "safe"],
        "title": "Low risk investing",
        "content": "Low-risk choices include FD, RD, and gold. Use them when capital safety matters more than growth or when debt is still elevated.",
    },
    {
        "id": "balanced_investing",
        "intents": ["investment"],
        "keywords": ["sip", "mutual fund", "balanced", "diversified", "index fund"],
        "title": "Balanced investing",
        "content": "Balanced plans usually mix SIPs in diversified mutual funds with a cash-like reserve. This suits moderate risk and disciplined monthly investing.",
    },
    {
        "id": "growth_investing",
        "intents": ["investment"],
        "keywords": ["stock", "stocks", "real estate", "property", "high risk"],
        "title": "Growth investing",
        "content": "Higher risk options like direct stocks and real estate should be reserved for stronger cashflow, lower debt pressure, and a healthy emergency buffer.",
    },
    {
        "id": "asset_mix",
        "intents": ["investment"],
        "keywords": ["sip", "stock", "fd", "rd", "gold", "mutual fund", "real estate"],
        "title": "Asset mix guidance",
        "content": "If the user asks for specific assets, explain them by risk: FD and RD for safety, gold for stability, SIPs and mutual funds for growth with diversification, and stocks or real estate for higher risk or long-term growth.",
    },
]


def _normalize_query_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _extract_asset_mentions(question: str) -> list[str]:
    normalized = _normalize_query_text(question)
    mentions: list[str] = []

    for asset_name, phrases in ASSET_ALIAS_MAP.items():
        if any(phrase in normalized for phrase in phrases):
            mentions.append(asset_name)

    return mentions


def _classify_query_intent(question: str) -> dict:
    normalized = _normalize_query_text(question)
    scores = {intent: 0 for intent in QUERY_INTENT_KEYWORDS}

    for intent, phrases in QUERY_INTENT_KEYWORDS.items():
        for phrase in phrases:
            if phrase in normalized:
                scores[intent] += 2 if " " in phrase else 1

    asset_mentions = _extract_asset_mentions(question)
    if any(asset in {"Laptop", "Phone", "Car"} for asset in asset_mentions):
        scores["purchase"] += 4
    if any(asset in {"SIP", "Stocks", "FD", "RD", "Gold", "Mutual Fund", "Real Estate"} for asset in asset_mentions):
        scores["investment"] += 3

    priority = ["debt", "purchase", "goal", "investment", "savings"]
    primary = "general"
    best_score = 0
    for intent in priority:
        score = scores[intent]
        if score > best_score:
            primary = intent
            best_score = score

    secondary = [
        intent
        for intent, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if score > 0 and intent != primary
    ]

    return {
        "primary": primary,
        "secondary": secondary,
        "scores": scores,
        "asset_mentions": asset_mentions,
    }


def _build_financial_context(snapshot: dict, requested_amount: float) -> dict:
    income = max(float(snapshot.get("income", 0) or 0), 0.0)
    expenses = max(float(snapshot.get("expenses", 0) or 0), 0.0)
    savings = max(float(snapshot.get("savings", 0) or 0), 0.0)
    debt = max(float(snapshot.get("debt", 0) or 0), 0.0)
    emi = max(float(snapshot.get("emi", 0) or 0), 0.0)
    monthly_surplus = max(income - expenses, 0.0)

    savings_rate = round((savings / income) * 100, 2) if income > 0 else 0.0
    debt_to_income = round(((debt + emi) / income) * 100, 2) if income > 0 else 0.0
    emi_to_income = round((emi / income) * 100, 2) if income > 0 else 0.0
    buffer_months = round((savings / expenses), 2) if expenses > 0 else 0.0
    available_capacity = max(savings + (monthly_surplus * 3), 0.0)

    risk_bucket = "low"
    if debt_to_income >= 35 or buffer_months < 3:
        risk_bucket = "high"
    elif debt_to_income >= 20 or savings_rate < 15:
        risk_bucket = "medium"

    return {
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "debt": debt,
        "emi": emi,
        "monthly_surplus": round(monthly_surplus, 2),
        "savings_rate_pct": savings_rate,
        "debt_to_income_pct": debt_to_income,
        "emi_to_income_pct": emi_to_income,
        "emergency_buffer_months": buffer_months,
        "available_capacity": round(available_capacity, 2),
        "requested_amount": _to_int_amount(requested_amount),
        "risk_bucket": risk_bucket,
    }


def _build_goal_context(goal_docs: list[dict], financial_context: dict) -> dict:
    monthly_surplus = float(financial_context.get("monthly_surplus", 0) or 0)
    active_goal = _serialize_goal(goal_docs[0]) if goal_docs else None

    if not active_goal:
        suggested_monthly = int(round(max(monthly_surplus * 0.4, 0)))
        return {
            "goal_count": len(goal_docs),
            "has_active_goal": False,
            "active_goal": None,
            "title": "No active goal",
            "target_amount": 0,
            "saved_amount": 0,
            "remaining_amount": 0,
            "monthly_target": suggested_monthly,
            "recommended_monthly_contribution": suggested_monthly,
            "progress": 0,
            "status": "no_goal",
            "reason": "Create one clear goal so the surplus has a target.",
            "next_step": "Set one goal and choose a monthly contribution.",
            "top_goals": [],
        }

    target_amount = max(float(active_goal.get("target_amount", 0) or 0), 0.0)
    saved_amount = max(float(active_goal.get("saved_amount", 0) or 0), 0.0)
    monthly_target = max(float(active_goal.get("monthly_target", 0) or 0), 0.0)
    remaining_amount = max(target_amount - saved_amount, 0.0)
    progress = round(min((saved_amount / target_amount) * 100, 100), 2) if target_amount > 0 else 0.0

    if remaining_amount <= 0:
        status = "completed"
        reason = "The goal is already fully funded."
        recommended_monthly = 0
        next_step = "Move surplus to the next priority."
    elif monthly_target > 0 and monthly_surplus >= monthly_target:
        status = "on_track"
        reason = "The goal fits the current monthly surplus."
        recommended_monthly = int(round(monthly_target))
        next_step = "Keep the monthly contribution steady."
    elif progress >= 80:
        status = "almost_there"
        reason = "The goal is close, so keep the pace steady."
        recommended_monthly = int(round(monthly_target or max(monthly_surplus * 0.5, remaining_amount / 12 if remaining_amount > 0 else 0)))
        next_step = "Finish the goal before adding new risk."
    else:
        status = "catch_up"
        reason = "The goal needs a more consistent monthly contribution."
        recommended_monthly = int(round(monthly_target or max(monthly_surplus * 0.5, remaining_amount / 12 if remaining_amount > 0 else 0)))
        next_step = "Direct surplus to the goal before riskier investing."

    top_goals = [
        {
            "title": goal.get("title"),
            "target_amount": float(goal.get("target_amount", 0) or 0),
            "saved_amount": float(goal.get("saved_amount", 0) or 0),
            "progress": goal.get("progress", 0),
        }
        for goal in goal_docs[:3]
    ]

    return {
        "goal_count": len(goal_docs),
        "has_active_goal": True,
        "active_goal": active_goal,
        "title": active_goal.get("title") or "Goal",
        "target_amount": int(round(target_amount)),
        "saved_amount": int(round(saved_amount)),
        "remaining_amount": int(round(remaining_amount)),
        "monthly_target": int(round(monthly_target)),
        "recommended_monthly_contribution": max(recommended_monthly, 0),
        "progress": progress,
        "status": status,
        "reason": reason,
        "next_step": next_step,
        "top_goals": top_goals,
    }


def _build_decision_hint(
    intent: str,
    financial_context: dict,
    asset_mentions: list[str],
    goal_context: dict | None = None,
) -> str:
    income = float(financial_context.get("income", 0) or 0)
    monthly_surplus = float(financial_context.get("monthly_surplus", 0) or 0)
    savings_rate = float(financial_context.get("savings_rate_pct", 0) or 0)
    debt_ratio = float(financial_context.get("debt_to_income_pct", 0) or 0)
    buffer_months = float(financial_context.get("emergency_buffer_months", 0) or 0)
    requested_amount = float(financial_context.get("requested_amount", 0) or 0)
    goal_context = goal_context or {}

    if intent == "purchase":
        if debt_ratio >= 35 or buffer_months < 3:
            return "Purchase intent. Recommend wait and clear debt pressure or rebuild the emergency buffer first."
        if requested_amount > financial_context.get("available_capacity", 0):
            return "Purchase intent. The price is above the safe capacity, so recommend wait, downsize, or save more."
        return "Purchase intent. If the purchase is essential, it can be considered while preserving the emergency buffer."

    if intent == "investment":
        if debt_ratio >= 35 or buffer_months < 3:
            return "Investment intent. Use low-risk options only and prioritize debt repayment before higher-risk investing."
        if savings_rate >= 20 and monthly_surplus > 0:
            return "Investment intent. A balanced mix is suitable, with a tilt toward SIPs and diversified mutual funds."
        return "Investment intent. Keep the mix conservative and spread across low to medium risk options."

    if intent == "debt":
        return "Debt intent. Focus on EMI and loan repayment first, then revisit purchases or investing."

    if intent == "savings":
        return "Savings intent. Build the emergency buffer and keep the goal simple and liquid."

    if intent == "goal":
        if not goal_context.get("has_active_goal"):
            return "Goal intent. Create one clear target before choosing a split."
        goal_title = goal_context.get("title") or "the goal"
        goal_status = (goal_context.get("status") or "").lower()
        if goal_status == "completed":
            return f"Goal intent. {goal_title} is already funded, so move surplus to the next priority."
        if debt_ratio >= 35 or buffer_months < 3:
            return f"Goal intent. Protect the emergency buffer before pushing {goal_title} faster."
        if goal_status == "on_track":
            return f"Goal intent. {goal_title} is on track, so keep the monthly pace steady."
        return f"Goal intent. Direct surplus to {goal_title} before riskier investing."

    if goal_context.get("has_active_goal"):
        goal_title = goal_context.get("title") or "the goal"
        return f"General intent. Keep {goal_title} and the emergency buffer in front of new spending."

    if asset_mentions:
        return "Mixed intent. Use the financial constraints to rank the assets by risk and keep debt pressure in front of new commitments."

    return "General intent. Use the numeric financial profile to keep the answer conservative and specific."


def _rag_score_text(text: str, doc: dict, intent: str, asset_mentions: list[str]) -> int:
    score = 0
    normalized = _normalize_query_text(text)

    if intent != "general" and intent in doc.get("intents", []):
        score += 4

    for keyword in doc.get("keywords", []):
        if keyword in normalized:
            score += 2 if " " in keyword else 1

    title = _normalize_query_text(doc.get("title", ""))
    if title and title in normalized:
        score += 2

    for asset in asset_mentions:
        if asset.lower() in normalized:
            score += 2

    return score


def _retrieve_rag_context(question: str, intent: str, asset_mentions: list[str]) -> list[dict]:
    selected = []

    for doc in RAG_KNOWLEDGE_BASE:
        score = _rag_score_text(question, doc, intent, asset_mentions)
        if score <= 0:
            continue

        selected.append(
            {
                "id": doc["id"],
                "title": doc["title"],
                "content": doc["content"],
                "score": score,
            }
        )

    selected.sort(key=lambda item: (-item["score"], item["title"]))
    return selected[:4]


def _summarize_recent_queries(recent_queries: list[dict]) -> dict:
    counts = Counter()

    for item in recent_queries:
        question = item.get("question", "")
        intent = _classify_query_intent(question)["primary"]
        counts[intent] += 1

    return {
        "count": len(recent_queries),
        "intent_counts": dict(counts),
    }


def _build_query_context(snapshot: dict, user_query: str, goal_docs: list[dict]) -> dict:
    intent_info = _classify_query_intent(user_query)
    explicit_amount = extract_requested_amount_safe(user_query)
    financial_context = _build_financial_context(snapshot, explicit_amount)
    goal_context = _build_goal_context(goal_docs, financial_context)
    amount_source = "explicit" if explicit_amount > 0 else "estimated"
    financial_context["explicit_amount"] = _to_int_amount(explicit_amount)

    if explicit_amount <= 0:
        if intent_info["primary"] == "purchase":
            financial_context["requested_amount"] = _to_int_amount(
                max(financial_context["available_capacity"], financial_context["monthly_surplus"] * 3)
            )
        elif intent_info["primary"] == "goal":
            financial_context["requested_amount"] = _to_int_amount(
                goal_context.get("remaining_amount")
                or max(financial_context["monthly_surplus"] * 12, financial_context["savings"])
            )
        elif intent_info["primary"] == "investment":
            financial_context["requested_amount"] = _to_int_amount(
                max(financial_context["available_capacity"], financial_context["monthly_surplus"])
            )
        else:
            financial_context["requested_amount"] = _to_int_amount(
                max(financial_context["monthly_surplus"], financial_context["savings"])
            )
    financial_context["suggested_amount"] = _to_int_amount(financial_context["requested_amount"])
    financial_context["amount_source"] = amount_source

    decision_hint = _build_decision_hint(
        intent_info["primary"],
        financial_context,
        intent_info["asset_mentions"],
        goal_context,
    )

    rag_context = _retrieve_rag_context(
        user_query,
        intent_info["primary"],
        intent_info["asset_mentions"],
    )

    chart_blueprint = {
        "purchase": ["Emergency Fund", "Debt / EMI", "Savings Buffer", "Purchase Budget"],
        "investment_high": ["Emergency Fund", "Debt / EMI", "FD", "RD", "Gold"],
        "investment_medium": ["Emergency Fund", "Debt / EMI", "SIP", "Mutual Fund", "Gold"],
        "investment_low": ["Emergency Fund", "Debt / EMI", "SIP", "Mutual Fund", "Stocks", "Real Estate"],
        "goal": ["Emergency Fund", "Debt / EMI", "Goal Fund", "Growth Bucket"],
        "debt": ["Emergency Fund", "Debt / EMI", "Savings", "Debt Paydown"],
        "savings": ["Emergency Fund", "Debt / EMI", "Savings", "Goal Buffer"],
        "general": ["Emergency Fund", "Debt / EMI", "Savings", "Investment"],
    }

    if intent_info["primary"] == "investment":
        if intent_info["asset_mentions"]:
            chart_labels = ["Emergency Fund", "Debt / EMI"] + intent_info["asset_mentions"][:2]
        elif financial_context["risk_bucket"] == "high":
            chart_labels = chart_blueprint["investment_high"]
        elif financial_context["risk_bucket"] == "medium":
            chart_labels = chart_blueprint["investment_medium"]
        else:
            chart_labels = chart_blueprint["investment_low"]
    elif intent_info["primary"] == "purchase":
        purchase_label = "Purchase Budget"
        if intent_info["asset_mentions"]:
            purchase_label = f'{intent_info["asset_mentions"][0]} Budget'
        chart_labels = ["Emergency Fund", "Debt / EMI", "Savings Buffer", purchase_label]
    elif intent_info["primary"] == "goal":
        chart_labels = chart_blueprint["goal"]
    else:
        chart_labels = chart_blueprint.get(intent_info["primary"], chart_blueprint["general"])

    return {
        "question": user_query,
        "intent": intent_info["primary"],
        "secondary_intents": intent_info["secondary"],
        "asset_mentions": intent_info["asset_mentions"],
        "financial": financial_context,
        "goal_context": goal_context,
        "decision_hint": decision_hint,
        "chart_blueprint": chart_labels,
        "rag_context": rag_context,
    }


QUERY_AI_PACKET_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "intent": {"type": "string"},
        "decision": {"type": "string"},
        "recommended_assets": {
            "type": "array",
            "items": {"type": "string"},
        },
        "readiness_label": {"type": "string"},
        "readiness_reason": {"type": "string"},
        "risk_level": {"type": "string"},
        "risk_reason": {"type": "string"},
        "why": {
            "type": "array",
            "items": {"type": "string"},
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_step": {"type": "string"},
        "goal_focus": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "target_amount": {"type": "integer"},
                "saved_amount": {"type": "integer"},
                "remaining_amount": {"type": "integer"},
                "monthly_target": {"type": "integer"},
                "progress": {"type": "number"},
                "reason": {"type": "string"},
                "next_step": {"type": "string"},
            },
        },
    },
    "required": [
        "summary",
        "intent",
        "decision",
        "recommended_assets",
        "readiness_label",
        "readiness_reason",
        "risk_level",
        "risk_reason",
        "why",
        "warnings",
        "next_step",
    ],
}

DASHBOARD_AI_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["label", "score", "reason"],
        },
        "behavior": {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["label", "score", "reason"],
        },
        "risk": {
            "type": "object",
            "properties": {
                "level": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["level", "reason"],
        },
        "highlights": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "goal_focus": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "target_amount": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["title", "target_amount", "reason"],
        },
        "next_action": {"type": "string"},
        "notification": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["title", "message"],
        },
    },
    "required": [
        "sentiment",
        "behavior",
        "risk",
        "highlights",
        "recommendations",
        "goal_focus",
        "next_action",
        "notification",
    ],
}


def _to_int_amount(value) -> int:
    try:
        return max(int(round(float(value or 0))), 0)
    except (TypeError, ValueError):
        return 0


def _build_split_payload(total: int, emergency_pct: float, debt_pct: float, savings_pct: float) -> dict:
    total = max(int(total), 0)
    emergency = int(total * emergency_pct)
    debt_alloc = int(total * debt_pct)
    savings_alloc = int(total * savings_pct)
    investment = max(total - emergency - debt_alloc - savings_alloc, 0)
    return {
        "requested_amount": total,
        "emergency_fund": emergency,
        "debt_emi": debt_alloc,
        "savings": savings_alloc,
        "investment": investment,
    }


def build_fallback_response(query_context: dict) -> dict:
    financial = query_context["financial"]
    goal_context = query_context.get("goal_context") or {}
    intent = (query_context.get("intent") or "mixed").strip().lower()

    requested_amount = _to_int_amount(financial.get("requested_amount", 0))
    income = max(float(financial.get("income", 0) or 0), 0.0)
    expenses = max(float(financial.get("expenses", 0) or 0), 0.0)
    savings = max(float(financial.get("savings", 0) or 0), 0.0)
    debt = max(float(financial.get("debt", 0) or 0), 0.0)
    emi = max(float(financial.get("emi", 0) or 0), 0.0)
    debt_pressure = debt + emi
    savings_rate = (savings / income) * 100 if income > 0 else 0.0
    buffer_months = (savings / expenses) if expenses > 0 else 0.0
    monthly_surplus = max(income - expenses, 0.0)

    if requested_amount <= 0 or income <= 0:
        readiness = {
            "label": "Not Ready",
            "reason": "No usable amount yet. Stabilize cashflow first.",
        }
        risk = {
            "level": "High",
            "reason": "Cashflow is tight, so avoid aggressive investing.",
        }
        split = _build_split_payload(0, 0.0, 0.0, 0.0)
        why = [
            "Low emergency buffer",
            "Unstable cashflow",
            "High EMI pressure",
        ]
        warnings = ["Avoid investing aggressively due to high EMI"]
        next_step = "Build an emergency fund first."
    elif intent == "goal" or (intent == "general" and goal_context.get("has_active_goal")):
        goal_title = goal_context.get("title") or "your goal"
        goal_status = str(goal_context.get("status") or "no_goal").lower()
        monthly_contribution = _to_int_amount(goal_context.get("recommended_monthly_contribution", 0))

        if not goal_context.get("has_active_goal"):
            readiness = {
                "label": "Set Goal",
                "reason": "Create a goal before splitting the surplus.",
            }
            risk = {
                "level": "Moderate",
                "reason": "A clear target helps the money work better.",
            }
            split = _build_split_payload(requested_amount, 0.25, 0.0 if debt_pressure <= 0 else 0.10, 0.35)
            why = [
                "No active goal",
                "Surplus needs direction",
                "Buffer stays protected",
            ]
            warnings = []
            next_step = "Set one clear goal and a monthly contribution."
        elif goal_status == "completed":
            readiness = {
                "label": "Goal Complete",
                "reason": "The current goal is already funded.",
            }
            risk = {
                "level": "Low",
                "reason": "The target is done, so shift to the next priority.",
            }
            split = _build_split_payload(requested_amount, 0.20, 0.0 if debt_pressure <= 0 else 0.10, 0.25)
            why = [
                "Goal is funded",
                "Surplus can move forward",
                "Buffer stays intact",
            ]
            warnings = []
            next_step = f"Move the surplus from {goal_title} to the next goal or investment."
        elif goal_status in {"catch_up", "building"} or debt_pressure > income * 0.35 or savings_rate < 15 or (monthly_contribution > 0 and buffer_months < 3):
            readiness = {
                "label": "Goal First",
                "reason": "The goal needs funding before risky investing.",
            }
            risk = {
                "level": "Moderate",
                "reason": "Keep the goal pace steady until the buffer improves.",
            }
            split = _build_split_payload(requested_amount, 0.30, 0.10 if debt_pressure > 0 else 0.0, 0.35)
            why = [
                "Goal needs funding",
                "Protect the buffer",
                "Keep risk low",
            ]
            warnings = ["Avoid risky investing until the goal is stable"]
            next_step = (
                f"Save {format_currency(monthly_contribution)} monthly for {goal_title}."
                if monthly_contribution > 0
                else f"Direct surplus to {goal_title} before risky investing."
            )
        else:
            readiness = {
                "label": "Goal Ready",
                "reason": "The profile can support goal progress and growth.",
            }
            risk = {
                "level": "Low",
                "reason": "You can split money between the goal and growth.",
            }
            split = _build_split_payload(requested_amount, 0.20, 0.05 if debt_pressure > 0 else 0.0, 0.35)
            why = [
                "Goal is on track",
                "Surplus is healthy",
                "Room for growth",
            ]
            warnings = []
            next_step = goal_context.get("next_step") or (
                f"Keep saving {format_currency(monthly_contribution or max(int(monthly_surplus * 0.5), 0))} monthly for {goal_title}."
            )
    elif debt_pressure <= 0:
        if savings_rate < 15:
            readiness = {
                "label": "Needs Stabilization",
                "reason": "No EMI burden, but your savings rate is still below target.",
            }
            risk = {
                "level": "Moderate",
                "reason": "No EMI burden, so the focus should be on buffer first.",
            }
            split = _build_split_payload(requested_amount, 0.30, 0.00, 0.20)
            why = [
                "No EMI burden",
                "Savings rate is below target",
                "Emergency buffer needs top-up",
            ]
            warnings = ["Build emergency fund first"]
            next_step = "Increase the emergency buffer before scaling investments."
        else:
            readiness = {
                "label": "Ready to Invest",
                "reason": "No EMI burden and your surplus is healthy.",
            }
            risk = {
                "level": "Low",
                "reason": "You can invest with a balanced split.",
            }
            split = _build_split_payload(requested_amount, 0.20, 0.00, 0.25)
            why = [
                "No EMI burden",
                "Healthy surplus",
                "Room to invest",
            ]
            warnings = []
            next_step = "Start the SIP and keep the emergency buffer untouched."
    elif debt_pressure > income * 0.35 or savings_rate < 15:
        readiness = {
            "label": "Needs Stabilization",
            "reason": "Debt pressure is high, so keep the plan conservative.",
        }
        risk = {
            "level": "Moderate",
            "reason": "Keep the plan conservative until the buffer improves.",
        }
        split = _build_split_payload(requested_amount, 0.40, 0.30, 0.20)
        why = [
            "EMI burden is high",
            "Emergency fund is low",
            "Income is not fully stable",
        ]
        warnings = ["Build emergency fund first"]
        next_step = "Reduce debt pressure before increasing investment."
    else:
        readiness = {
            "label": "Ready to Invest",
            "reason": "Surplus is stable and debt pressure is manageable.",
        }
        risk = {
            "level": "Low",
            "reason": "You can invest now with a balanced split.",
        }
        split = _build_split_payload(requested_amount, 0.20, 0.10, 0.25)
        why = [
            "Stable income",
            "Manageable EMI burden",
            "Enough surplus for investing",
        ]
        warnings = []
        next_step = "Start with a small SIP and keep the emergency buffer in place."

    if requested_amount > 0:
        split["investment"] = max(
            requested_amount
            - split["emergency_fund"]
            - split["debt_emi"]
            - split["savings"],
            0,
        )

    summary = f'{readiness["label"]}. {next_step}'
    chart_labels = query_context.get("chart_blueprint") or [
        "Emergency Fund",
        "Debt / EMI",
        "Savings",
        "Investment",
    ]
    effective_asset_intent = "goal" if (intent == "goal" or goal_context.get("has_active_goal")) else intent
    recommended_assets = _default_recommended_assets(
        effective_asset_intent,
        risk["level"],
        query_context.get("asset_mentions", []),
    )

    return {
        "summary": summary,
        "readiness": readiness,
        "risk": risk,
        "recommended_assets": recommended_assets,
        "split": split,
        "chart": {
            "labels": chart_labels,
            "values": [
                split["emergency_fund"],
                split["debt_emi"],
                split["savings"],
                split["investment"],
            ],
            "colors": ["#10b981", "#ef4444", "#3b82f6", "#8b5cf6"],
        },
        "why": why,
        "warnings": warnings,
        "next_step": next_step,
        "inputs": {
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "debt": debt,
            "emi": emi,
            "requested_amount": requested_amount,
        },
    }


def _load_prompt_template(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def build_ai_prompt(context: dict) -> str:
    template = _load_prompt_template(QUERY_PROMPT_TEMPLATE_PATH)
    if not template:
        template = (
            "You are FinArmor's financial decision assistant.\n"
            "Return only compact JSON that matches the schema exactly.\n"
            "Solve the user's actual question using the backend context.\n"
            "Support purchase, investment, debt, savings, goal, and mixed intents.\n"
            "Use the active goal if present.\n\n"
            "User question:\n{{USER_QUESTION}}\n\n"
            "Response schema:\n{{RESPONSE_SCHEMA_JSON}}\n\n"
            "Backend context:\n{{QUERY_CONTEXT_JSON}}\n"
        )

    return (
        template.replace("{{USER_QUESTION}}", str(context.get("question", "")).strip())
        .replace("{{RESPONSE_SCHEMA_JSON}}", json.dumps(QUERY_AI_PACKET_SCHEMA, indent=2))
        .replace("{{QUERY_CONTEXT_JSON}}", json.dumps(context, indent=2, default=str))
    )


def _extract_json_payload(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    return cleaned.strip()


def call_llm(
    prompt: str,
    schema: dict = QUERY_AI_PACKET_SCHEMA,
    temperature: float = 0.1,
    max_output_tokens: int = 900,
) -> dict | None:
    if gemini_client is None:
        print("GEMINI ERROR: client unavailable")
        return None

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                maxOutputTokens=max_output_tokens,
                responseMimeType="application/json",
                responseSchema=schema,
            ),
        )

        raw_text = ""
        if hasattr(response, "text") and response.text:
            raw_text = response.text.strip()
        elif getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
            if parts:
                raw_text = getattr(parts[0], "text", "") or ""

        if not raw_text:
            print("GEMINI EMPTY RESPONSE")
            return None

        parsed = json.loads(_extract_json_payload(raw_text))
        return parsed if isinstance(parsed, dict) else None

    except Exception as e:
        print("GEMINI ERROR:", type(e).__name__, e)
        error_text = str(e).lower()
        if "resource_exhausted" in error_text or "quota exceeded" in error_text or "429" in error_text:
            raise HTTPException(
                status_code=429,
                detail="Gemini quota exceeded. Check the backend console and your API limits/billing.",
            )
        return None


def call_llm_text(
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 80,
) -> str | None:
    global GEMINI_TEXT_DISABLED

    if GEMINI_TEXT_DISABLED:
        return None

    if gemini_client is None:
        print("GEMINI TEXT ERROR: client unavailable")
        return None

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                maxOutputTokens=max_output_tokens,
            ),
        )

        text = ""
        if hasattr(response, "text") and response.text:
            text = response.text.strip()
        elif getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
            if parts:
                text = getattr(parts[0], "text", "") or ""

        return text.strip() if text else None

    except Exception as e:
        print("GEMINI TEXT ERROR:", type(e).__name__, e)
        error_text = str(e).lower()
        if "resource_exhausted" in error_text or "quota exceeded" in error_text or "429" in error_text:
            GEMINI_TEXT_DISABLED = True
            return None
        return None


def _validate_query_response_payload(response: dict) -> bool:
    if not isinstance(response, dict):
        return False

    required = [
        "summary",
        "intent",
        "decision",
        "recommended_assets",
        "readiness_label",
        "readiness_reason",
        "risk_level",
        "risk_reason",
        "why",
        "warnings",
        "next_step",
    ]

    for key in required:
        if key not in response:
            return False

    if not isinstance(response.get("recommended_assets"), list) or len(response.get("recommended_assets")) == 0:
        return False
    if not isinstance(response.get("why"), list):
        return False
    if not isinstance(response.get("warnings"), list):
        return False

    return True


def _normalize_text_list(values, fallback: list[str] | None = None, limit: int = 4) -> list[str]:
    items = []
    source = values if isinstance(values, list) else (fallback or [])

    for value in source:
        text = str(value or "").strip()
        if text and text not in items:
            items.append(text)
        if len(items) >= limit:
            break

    return items


def _default_recommended_assets(intent: str, risk_level: str, asset_mentions: list[str]) -> list[str]:
    assets = []
    for item in asset_mentions:
        if item and item not in assets:
            assets.append(item)

    risk_key = (risk_level or "").lower()
    if intent == "purchase":
        base = ["Emergency Fund", "Debt Repayment", "Savings Buffer"]
    elif intent == "goal":
        if risk_key == "high":
            base = ["Goal Fund", "FD", "RD", "Emergency Fund"]
        elif risk_key == "medium":
            base = ["Goal Fund", "FD", "SIP", "Emergency Fund"]
        else:
            base = ["Goal Fund", "SIP", "FD", "RD"]
    elif intent == "debt":
        base = ["Debt Repayment", "EMI Clearance", "Emergency Fund"]
    elif intent == "savings":
        base = ["Emergency Fund", "Goal Fund", "Cash Buffer"]
    elif risk_key == "high":
        base = ["FD", "RD", "Gold", "Mutual Fund"]
    elif risk_key == "medium":
        base = ["SIP", "Mutual Fund", "Gold", "FD"]
    else:
        base = ["SIP", "FD", "RD", "Gold"]

    for item in base:
        if item not in assets:
            assets.append(item)

    return assets[:4]


def _default_query_summary(intent: str, readiness_label: str, next_step: str) -> str:
    readiness = (readiness_label or "").strip()
    step = (next_step or "").strip()
    if readiness and step:
        return f"{readiness}. {step}"
    if readiness:
        return readiness
    if step:
        return step
    if intent == "purchase":
        return "Wait. Protect the emergency buffer first."
    if intent == "debt":
        return "Debt first. Clear EMI pressure before new plans."
    if intent == "goal":
        return "Goal first. Keep the surplus focused on the target."
    if intent == "savings":
        return "Save first. Build the emergency buffer."
    return "Invest carefully. Keep the buffer in place."


def _default_readiness(intent: str, risk_level: str) -> tuple[str, str]:
    risk_key = (risk_level or "").lower()
    if intent == "purchase":
        if risk_key == "high":
            return "Wait", "The purchase is too tight for the current buffer."
        if risk_key == "medium":
            return "Check Buffer", "The purchase needs a smaller buffer gap."
        return "Buy Now", "The purchase fits the current finances."
    if intent == "goal":
        if risk_key == "high":
            return "Goal First", "Protect the buffer before speeding up the goal."
        if risk_key == "medium":
            return "Goal Track", "The goal can move forward with discipline."
        return "Goal Ready", "The profile can support goal progress."
    if intent == "debt":
        return "Debt First", "EMI or debt pressure needs attention first."
    if intent == "savings":
        return "Save First", "Build the emergency buffer before anything else."
    if risk_key == "high":
        return "Low Risk Only", "Keep the plan conservative for now."
    if risk_key == "medium":
        return "Balanced", "A mixed approach is reasonable."
    return "Invest Now", "The current profile can support small investing."


def _default_risk(intent: str, financial: dict) -> tuple[str, str]:
    risk_bucket = (financial.get("risk_bucket") or "").lower()
    debt_pressure = float(financial.get("debt_to_income_pct", 0) or 0)
    savings_rate = float(financial.get("savings_rate_pct", 0) or 0)
    buffer_months = float(financial.get("emergency_buffer_months", 0) or 0)

    if intent == "purchase":
        if debt_pressure >= 35 or buffer_months < 3:
            return "High", "The purchase would strain the emergency buffer."
        if debt_pressure >= 20 or savings_rate < 15:
            return "Medium", "The purchase is possible but needs caution."
        return "Low", "The purchase looks affordable."

    if intent == "debt":
        return ("High" if debt_pressure > 20 else "Medium"), "Debt pressure should be handled first."

    if intent == "goal":
        if debt_pressure >= 35 or buffer_months < 3:
            return "High", "Goal savings should stay conservative until the buffer improves."
        if savings_rate < 15:
            return "Medium", "The goal is possible, but the pace is tight."
        return "Low", "The profile can support steady goal progress."

    if risk_bucket == "high" or debt_pressure >= 35 or buffer_months < 3:
        return "High", "Debt pressure and buffer coverage are too tight."
    if risk_bucket == "medium" or savings_rate < 20:
        return "Medium", "The profile can support only moderate risk."
    return "Low", "The profile can support low-risk investing."


def _build_query_split_and_chart(query_context: dict, readiness_label: str, risk_level: str) -> tuple[dict, dict]:
    financial = query_context["financial"]
    intent = query_context["intent"]
    goal_context = query_context.get("goal_context") or {}
    requested_amount = _to_int_amount(financial.get("requested_amount", 0))
    if requested_amount <= 0:
        requested_amount = _to_int_amount(max(financial.get("available_capacity", 0), financial.get("monthly_surplus", 0), financial.get("savings", 0)))

    debt_pressure = float(financial.get("debt_to_income_pct", 0) or 0)
    buffer_months = float(financial.get("emergency_buffer_months", 0) or 0)
    savings_rate = float(financial.get("savings_rate_pct", 0) or 0)
    risk_key = (risk_level or "").lower()
    readiness_key = (readiness_label or "").lower()

    if intent == "purchase":
        if "wait" in readiness_key or "debt" in readiness_key or risk_key == "high" or buffer_months < 3:
            emergency_pct, debt_pct, savings_pct = 0.35, 0.25 if debt_pressure > 0 else 0.10, 0.30
        elif "buy" in readiness_key:
            emergency_pct, debt_pct, savings_pct = 0.20, 0.0 if debt_pressure == 0 else 0.10, 0.20
        else:
            emergency_pct, debt_pct, savings_pct = 0.25, 0.15 if debt_pressure > 0 else 0.05, 0.20
        split = _build_split_payload(requested_amount, emergency_pct, debt_pct, savings_pct)
        chart = {
            "labels": ["Emergency Fund", "Debt / EMI", "Savings Buffer", "Purchase Budget"],
            "values": [split["emergency_fund"], split["debt_emi"], split["savings"], split["investment"]],
            "colors": ["#10b981", "#ef4444", "#3b82f6", "#8b5cf6"],
        }
        return split, chart

    if intent == "goal":
        if risk_key == "high" or debt_pressure >= 35 or buffer_months < 3:
            emergency_pct, debt_pct, savings_pct = 0.35, 0.20 if debt_pressure > 0 else 0.10, 0.30
        elif (goal_context.get("status") or "").lower() in {"on_track", "almost_there"}:
            emergency_pct, debt_pct, savings_pct = 0.20, 0.05 if debt_pressure > 0 else 0.0, 0.35
        else:
            emergency_pct, debt_pct, savings_pct = 0.25, 0.10 if debt_pressure > 0 else 0.0, 0.35

        split = _build_split_payload(requested_amount, emergency_pct, debt_pct, savings_pct)
        chart = {
            "labels": ["Emergency Fund", "Debt / EMI", "Goal Fund", "Growth Bucket"],
            "values": [split["emergency_fund"], split["debt_emi"], split["savings"], split["investment"]],
            "colors": ["#10b981", "#ef4444", "#3b82f6", "#8b5cf6"],
        }
        return split, chart

    if intent == "debt":
        emergency_pct, debt_pct, savings_pct = 0.20, 0.50 if debt_pressure > 0 else 0.35, 0.10
        split = _build_split_payload(requested_amount, emergency_pct, debt_pct, savings_pct)
        chart = {
            "labels": ["Emergency Fund", "Debt / EMI", "Savings", "Debt Paydown"],
            "values": [split["emergency_fund"], split["debt_emi"], split["savings"], split["investment"]],
            "colors": ["#10b981", "#ef4444", "#3b82f6", "#f59e0b"],
        }
        return split, chart

    if intent == "savings":
        emergency_pct, debt_pct, savings_pct = 0.35, 0.10 if debt_pressure > 0 else 0.0, 0.30 if savings_rate < 20 else 0.20
        split = _build_split_payload(requested_amount, emergency_pct, debt_pct, savings_pct)
        chart = {
            "labels": ["Emergency Fund", "Debt / EMI", "Savings", "Goal Buffer"],
            "values": [split["emergency_fund"], split["debt_emi"], split["savings"], split["investment"]],
            "colors": ["#10b981", "#ef4444", "#3b82f6", "#14b8a6"],
        }
        return split, chart

    if risk_key == "high":
        emergency_pct, debt_pct, savings_pct = 0.35, 0.30 if debt_pressure > 0 else 0.20, 0.15
    elif risk_key == "medium":
        emergency_pct, debt_pct, savings_pct = 0.25, 0.15 if debt_pressure > 0 else 0.10, 0.20
    else:
        emergency_pct, debt_pct, savings_pct = 0.20, 0.05 if debt_pressure > 0 else 0.0, 0.20

    split = _build_split_payload(requested_amount, emergency_pct, debt_pct, savings_pct)
    chart = {
        "labels": ["Emergency Fund", "Debt / EMI", "Savings", "Investment"],
        "values": [split["emergency_fund"], split["debt_emi"], split["savings"], split["investment"]],
        "colors": ["#10b981", "#ef4444", "#3b82f6", "#8b5cf6"],
    }
    return split, chart


def _format_query_response(query_context: dict, packet: dict) -> dict:
    financial = query_context["financial"]
    intent = (packet.get("intent") or query_context["intent"] or "mixed").strip().lower()
    risk_level, risk_reason = _default_risk(intent, financial)
    readiness_label, readiness_reason = _default_readiness(intent, risk_level)
    goal_context = query_context.get("goal_context") or {}
    packet_readiness = packet.get("readiness") if isinstance(packet.get("readiness"), dict) else {}
    packet_risk = packet.get("risk") if isinstance(packet.get("risk"), dict) else {}

    readiness_label_value = str(
        packet.get("readiness_label")
        or packet_readiness.get("label")
        or readiness_label
    ).strip()
    readiness_reason_value = str(
        packet.get("readiness_reason")
        or packet_readiness.get("reason")
        or readiness_reason
    ).strip()
    risk_level_value = str(
        packet.get("risk_level")
        or packet_risk.get("level")
        or risk_level
    ).strip()
    risk_reason_value = str(
        packet.get("risk_reason")
        or packet_risk.get("reason")
        or risk_reason
    ).strip()

    summary = str(packet.get("summary") or "").strip() or _default_query_summary(
        intent,
        readiness_label_value,
        packet.get("next_step") or "",
    )
    decision = str(packet.get("decision") or readiness_label_value).strip()
    recommended_assets = _normalize_text_list(
        packet.get("recommended_assets"),
        fallback=_default_recommended_assets(intent, risk_level, query_context.get("asset_mentions", [])),
        limit=4,
    )
    why = _normalize_text_list(
        packet.get("why"),
        fallback=[
            query_context["decision_hint"],
            f"Risk level: {risk_level}",
            f"Intent: {intent}",
        ],
        limit=3,
    )
    warnings = _normalize_text_list(
        packet.get("warnings"),
        fallback=["Protect the emergency buffer."] if intent == "purchase" else ["Stay conservative until the profile improves."],
        limit=3,
    )
    next_step = str(packet.get("next_step") or "").strip() or (
        "Build the emergency buffer first."
        if intent in {"purchase", "debt", "savings"} and risk_level == "High"
        else "Proceed with a conservative plan."
    )

    goal_focus = packet.get("goal_focus") if isinstance(packet.get("goal_focus"), dict) else None
    if goal_context.get("has_active_goal") or intent == "goal":
        default_goal_focus = {
            "title": goal_context.get("title") or "No active goal",
            "target_amount": int(goal_context.get("target_amount", 0) or 0),
            "saved_amount": int(goal_context.get("saved_amount", 0) or 0),
            "remaining_amount": int(goal_context.get("remaining_amount", 0) or 0),
            "monthly_target": int(goal_context.get("monthly_target", 0) or 0),
            "progress": float(goal_context.get("progress", 0) or 0),
            "reason": str(goal_context.get("reason") or query_context["decision_hint"]).strip(),
            "next_step": str(goal_context.get("next_step") or next_step).strip(),
        }

        if goal_focus:
            merged_goal_focus = default_goal_focus.copy()
            merged_goal_focus.update(goal_focus)
            goal_focus = merged_goal_focus
        else:
            goal_focus = default_goal_focus

    split = packet.get("split")
    chart = packet.get("chart")
    if not isinstance(split, dict) or not isinstance(chart, dict):
        split, chart = _build_query_split_and_chart(
            query_context,
            readiness_label_value,
            risk_level_value,
        )

    response = {
        "summary": summary,
        "intent": intent,
        "decision": decision,
        "recommended_assets": recommended_assets,
        "readiness": {
            "label": readiness_label_value,
            "reason": readiness_reason_value,
        },
        "risk": {
            "level": risk_level_value,
            "reason": risk_reason_value,
        },
        "split": split,
        "chart": chart,
        "why": why,
        "warnings": warnings,
        "next_step": next_step,
        "inputs": {
            "income": financial["income"],
            "expenses": financial["expenses"],
            "savings": financial["savings"],
            "debt": financial["debt"],
            "emi": financial["emi"],
            "requested_amount": financial["requested_amount"],
        },
    }

    if goal_focus:
        response["goal_focus"] = goal_focus

    return response


def _validate_dashboard_response_payload(response: dict) -> bool:
    required = [
        "sentiment",
        "behavior",
        "risk",
        "highlights",
        "recommendations",
        "goal_focus",
        "next_action",
        "notification",
    ]

    if not isinstance(response, dict):
        return False

    for key in required:
        if key not in response:
            return False

    sentiment = response.get("sentiment") or {}
    behavior = response.get("behavior") or {}
    risk = response.get("risk") or {}
    goal_focus = response.get("goal_focus") or {}
    notification = response.get("notification") or {}

    if not isinstance(sentiment, dict) or not sentiment.get("label") or sentiment.get("score") is None:
        return False
    if not isinstance(behavior, dict) or not behavior.get("label") or behavior.get("score") is None:
        return False
    if not isinstance(risk, dict) or not risk.get("level") or not risk.get("reason"):
        return False
    if not isinstance(goal_focus, dict) or not goal_focus.get("title") or goal_focus.get("target_amount") is None:
        return False
    if not isinstance(notification, dict) or not notification.get("title") or not notification.get("message"):
        return False

    return True


def _call_llm_strict(
    label: str,
    prompt: str,
    schema: dict,
    debug_context: dict,
    temperature: float,
    max_output_tokens: int,
    validator,
) -> dict:
    response = call_llm(prompt, schema=schema, temperature=temperature, max_output_tokens=max_output_tokens)

    if isinstance(response, dict) and validator(response):
        return response

    print(f"{label} GEMINI ERROR: invalid or empty structured response")
    print(f"{label} PROMPT:")
    print(prompt)
    print(f"{label} CONTEXT:")
    print(json.dumps(debug_context, indent=2, default=str))
    if isinstance(response, dict):
        print(f"{label} RAW RESPONSE:")
        print(json.dumps(response, indent=2, default=str))
    raise HTTPException(status_code=502, detail=f"{label} failed. Check the backend console logs.")


def _build_query_ai_response(user_email: str, user_query: str) -> tuple[dict, str]:
    snapshot = _load_finance_snapshot(user_email)
    goal_docs = _load_goals(user_email)
    query_context = _build_query_context(snapshot, user_query, goal_docs)
    fallback = _format_query_response(query_context, build_fallback_response(query_context))

    prompt = build_ai_prompt(query_context)
    gemini_packet = None
    try:
        gemini_packet = call_llm(
            prompt,
            schema=QUERY_AI_PACKET_SCHEMA,
            temperature=0.2,
            max_output_tokens=900,
        )
    except HTTPException as exc:
        if exc.status_code != 429:
            print("QUERY AI GEMINI ERROR:", exc.detail)

    if isinstance(gemini_packet, dict):
        response = _format_query_response(query_context, gemini_packet)
        if _validate_query_response_payload(response):
            return response, "gemini"

    return fallback, "fallback"


def _recent_queries(email: str, limit: int = 6) -> list[dict]:
    return list(
        queries.find({"email": email}, {"_id": 0})
        .sort([("created_at", -1), ("timestamp", -1)])
        .limit(limit)
    )


def build_dashboard_prompt(snapshot: dict, goal_docs: list[dict], recent_activity: dict, analysis: dict) -> str:
    context = {
        "finance": {
            "income": snapshot["income"],
            "expenses": snapshot["expenses"],
            "savings": snapshot["savings"],
            "debt": snapshot["debt"],
            "emi": snapshot["emi"],
            "profile_completion": analysis.get("profile_completion", "0%"),
            "health_score": analysis.get("total_score", 0),
            "grade": analysis.get("grade", "F"),
        },
        "goals": [
            {
                "title": goal.get("title"),
                "target_amount": float(goal.get("target_amount", 0) or 0),
                "saved_amount": float(goal.get("saved_amount", 0) or 0),
                "progress": goal.get("progress", 0),
            }
            for goal in goal_docs[:4]
        ],
        "recent_activity": recent_activity,
    }

    return (
        "You are FinArmor's behavioral finance analyst.\n"
        "Return only compact JSON that matches the response schema exactly.\n"
        "Do not add markdown, code fences, disclaimers, or extra keys.\n"
        "Analyze the user's financial sentiment and behavior using only numeric financial data and recent activity counts.\n"
        "Sentiment should describe how the user likely feels about money right now.\n"
        "Behavior should describe how consistent or reactive their money habits look.\n"
        "Use short, practical reasons and keep recommendations concrete. Keep every string field short.\n"
        "Stay conservative when the data is thin.\n\n"
        f"Context:\n{json.dumps(context, indent=2)}"
    )


def build_dashboard_fallback(snapshot: dict, goal_docs: list[dict], recent_queries: list[dict], analysis: dict) -> dict:
    income = float(snapshot["income"] or 0)
    savings = float(snapshot["savings"] or 0)
    debt = float(snapshot["debt"] or 0)
    emi = float(snapshot["emi"] or 0)
    goal_count = len(goal_docs)
    query_count = len(recent_queries)
    savings_rate = analysis.get("savings_rate", (savings / income * 100) if income > 0 else 0)
    debt_pressure = analysis.get("debt_pressure", ((debt + emi) / income * 100) if income > 0 else 100)

    if savings_rate >= 20 and debt_pressure <= 10:
        sentiment = {
            "label": "Confident",
            "score": 82,
            "reason": "Savings are healthy and debt pressure is low.",
        }
    elif debt_pressure > 25:
        sentiment = {
            "label": "Stressed",
            "score": 48,
            "reason": "Debt pressure is high, so the plan should stay conservative.",
        }
    elif savings_rate < 10:
        sentiment = {
            "label": "Cautious",
            "score": 58,
            "reason": "There is room to improve savings before expanding risk.",
        }
    else:
        sentiment = {
            "label": "Balanced",
            "score": 70,
            "reason": "Your money flow looks steady and manageable.",
        }

    if goal_count > 0 and savings_rate >= 15:
        behavior = {
            "label": "Goal-oriented",
            "score": 80,
            "reason": "You already have a savings goal and a workable surplus.",
        }
    elif query_count > 4:
        behavior = {
            "label": "Active Planner",
            "score": 72,
            "reason": "You are asking regular questions and checking the plan often.",
        }
    elif debt_pressure > 20:
        behavior = {
            "label": "Reactive",
            "score": 52,
            "reason": "Debt pressure is pushing the plan toward short-term fixes.",
        }
    else:
        behavior = {
            "label": "Early Stage",
            "score": 60,
            "reason": "The profile is still building, so focus on simple habits.",
        }

    risk_level = "Low" if savings_rate >= 20 and debt_pressure <= 10 else "Moderate" if debt_pressure <= 25 else "High"

    highlights = [
        f"{query_count} recent questions logged",
        f"{goal_count} active goals",
        f"Savings rate around {round(savings_rate, 1)}%",
    ]

    recommendations = []
    if goal_count == 0:
        recommendations.append("Set one upcoming savings goal and track it weekly.")
    if savings_rate < 12 and income > 0:
        recommendations.append("Raise monthly savings to at least 12% of income.")
    if debt_pressure > 20 and income > 0:
        recommendations.append("Trim debt pressure before adding new spending.")
    if not recommendations:
        recommendations.append("Keep the current plan and review it at month-end.")

    active_goal = goal_docs[0] if goal_docs else None
    goal_focus = {
        "title": active_goal.get("title") if active_goal else "Emergency fund",
        "target_amount": int(active_goal.get("target_amount", 0) or 50000) if active_goal else 50000,
        "reason": "A near-term savings target keeps the dashboard focused.",
    }
    if active_goal:
        goal_focus["reason"] = "The most recent goal should stay on top of your plan."

    return {
        "sentiment": sentiment,
        "behavior": behavior,
        "risk": {"level": risk_level, "reason": "Based on savings rate, debt pressure, and recent questions."},
        "highlights": highlights,
        "recommendations": recommendations,
        "goal_focus": goal_focus,
        "next_action": (
            "Keep saving into the active goal and review debt pressure each month."
            if goal_count
            else "Create one upcoming savings goal before taking new risks."
        ),
        "notification": {
            "title": "FinArmor check-in",
            "message": "Your dashboard is ready with a fresh behavior and goal review.",
        },
    }

@app.get("/query/history")
def get_history(user=Depends(verify_token)):
    data = list(
        queries.find({"email": user["email"]}, {"_id": 0})
        .sort([("created_at", -1), ("timestamp", -1)])
    )
    return data

@app.get("/goals")
def list_goals(user=Depends(verify_token)):
    return [_serialize_goal(goal) for goal in _load_goals(user["email"])]


@app.post("/goals")
def create_goal(goal: GoalInput, user=Depends(verify_token)):
    title = goal.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Goal title is required")
    if goal.target_amount <= 0:
        raise HTTPException(status_code=400, detail="target_amount must be greater than 0")

    target_amount = float(goal.target_amount)
    saved_amount = max(float(goal.saved_amount or 0), 0.0)
    if saved_amount > target_amount:
        saved_amount = target_amount

    goal_doc = {
        "goal_id": uuid.uuid4().hex,
        "email": user["email"],
        "title": title,
        "target_amount": target_amount,
        "saved_amount": saved_amount,
        "target_date": goal.target_date,
        "monthly_target": float(goal.monthly_target or 0) if goal.monthly_target is not None else 0,
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    goals.insert_one(goal_doc)
    return _serialize_goal(goal_doc)


@app.get("/ai/dashboard")
def ai_dashboard(user=Depends(verify_token)):
    snapshot = _load_finance_snapshot(user["email"])
    goal_docs = _load_goals(user["email"])
    recent_queries = _recent_queries(user["email"], limit=6)
    recent_activity = _summarize_recent_queries(recent_queries)

    if snapshot["has_data"]:
        analysis_summary = _build_analysis_scores(snapshot, goal_docs)
        profile_completion = "90%" if snapshot["totals"] else "80%"
    else:
        analysis_summary = {
            "total_score": 0,
            "grade": "F",
            "score_breakdown": {
                "profile_score": 0,
                "context_score": 0,
                "behavior_score": 0,
                "goal_score": 0,
            },
            "recommendation": "Complete your profile",
            "recommendations": ["Complete your profile to unlock the full score."],
            "financial_goals": "No active goal",
            "goal_count": 0,
            "active_goal": None,
            "savings_rate": 0,
            "debt_pressure": 0,
        }
        profile_completion = "20%"

    analysis_summary["profile_completion"] = profile_completion
    return {
        "insight": build_dashboard_fallback(snapshot, goal_docs, recent_queries, analysis_summary),
        "source": "fallback",
    }


@app.post("/query/ask")
def ask_query(q: QueryInput, user=Depends(verify_token)):
    user_query = q.question.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="question is required")

    response, source = _build_query_ai_response(user["email"], user_query)
    answer = response.get("summary", "")

    queries.insert_one({
        "email": user["email"],
        "question": user_query,
        "answer": answer,
        "response": response,
        "source": source,
        "created_at": datetime.utcnow(),
        "timestamp": datetime.utcnow(),
    })

    return {"answer": answer, "response": response, "source": source}


@app.post("/ai/query")
def ai_query(data: dict, user=Depends(verify_token)):
    try:
        user_query = extract_user_question(data)
        if not user_query:
            raise HTTPException(status_code=400, detail="Prompt is required")
        response, source = _build_query_ai_response(user["email"], user_query)
        answer = response.get("summary") if isinstance(response, dict) else ""

        # --- store history (safe) ---
        try:
            queries.insert_one({
                "email": user["email"],
                "question": user_query,
                "answer": answer,
                "response": response,
                "source": source,
                "created_at": datetime.utcnow(),
                "timestamp": datetime.utcnow(),
            })
        except Exception as db_err:
            print("DB STORE ERROR:", db_err)

        return {"response": response, "answer": answer, "source": source}

    except HTTPException as e:
        raise e
    except Exception as e:
        print("AI QUERY ERROR:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

