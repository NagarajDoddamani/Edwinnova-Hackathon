import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.gemini_service import (
    extract_text, anonymize, extract_financial_data, get_investment_suggestions
)
from app.services.gatekeeper import run_gatekeeper
from app.services.sentiment_service import score_sentiment
from app.services.market_data import get_market_data
from app.services.local_processor import process_locally

router = APIRouter(prefix="/ai", tags=["AI Suggestions"])


@router.post("/analyze", summary="Upload PDFs and get AI investment suggestions")
async def analyze_documents(
    files: List[UploadFile] = File(...),
    query: str = Form(default="What are the best investment options for my profile?"),
    current_user: User = Depends(get_current_user),
):
    merged = {
        "monthly_income": [],
        "monthly_expenses": [],
        "tax_paid": [],
        "account_balance": [],
        "total_assets": [],
        "credit_score": None,
    }
    temp_paths = []
    local_reports = []

    try:
        for upload in files:
            if not upload.filename.endswith(".pdf"):
                raise HTTPException(status_code=400, detail=f"{upload.filename} is not a PDF.")

            temp_path = os.path.join(settings.UPLOAD_DIR, f"tmp_{upload.filename}")
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(upload.file, f)
            temp_paths.append(temp_path)

            # ── Local Processing Layer (Privacy-Preserving) ───────────────────
            raw_text = extract_text(temp_path)
            local_result = process_locally(raw_text)
            clean_text = local_result.anonymized_text
            file_data = extract_financial_data(clean_text)

            # Track local processing metadata
            local_reports.append({
                "filename": upload.filename,
                "document_type": local_result.document_type,
                "pii_removed": local_result.pii_items_removed,
                "privacy_score": local_result.privacy_score,
                "local_summary": local_result.local_summary,
            })

            for key in ["monthly_income", "monthly_expenses", "tax_paid", "account_balance", "total_assets"]:
                merged[key].extend(file_data.get(key, []))

            if not merged["credit_score"] and file_data.get("credit_score"):
                merged["credit_score"] = file_data["credit_score"]

        # ── Step 1: Run Gatekeeper ────────────────────────────────────────────
        gate = run_gatekeeper(merged)

        # ── Step 2: Score Sentiment ───────────────────────────────────────────
        sentiment = score_sentiment(merged, gate.risk_level)

        # ── Step 3: Fetch real-time market data ───────────────────────────────
        market = await get_market_data()

        # ── Step 4: Block if gatekeeper says no ──────────────────────────────
        if not gate.allowed:
            return {
                "status": "blocked",
                "reason": gate.reason,
                "risk_level": gate.risk_level,
                "monthly_surplus": gate.monthly_surplus,
                "local_processing": local_reports,
                "sentiment": {
                    "score": sentiment.score,
                    "mode": sentiment.mode,
                    "label": sentiment.label,
                    "color": sentiment.color,
                    "message": sentiment.message,
                },
                "market_data": market,
                "suggestions": None,
            }

        # ── Step 5: Get Gemini suggestions (Cloud Layer) ──────────────────────
        result = await get_investment_suggestions(merged, query)

        return {
            "status": "success",
            "risk_level": gate.risk_level,
            "monthly_surplus": gate.monthly_surplus,
            "safe_invest_amount": gate.safe_invest_amount,
            "local_processing": local_reports,
            "sentiment": {
                "score": sentiment.score,
                "mode": sentiment.mode,
                "label": sentiment.label,
                "color": sentiment.color,
                "message": sentiment.message,
            },
            "market_data": market,
            "financial_summary": result["financial_summary"],
            "suggestions": result["suggestions"],
        }

    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)


@router.get("/market", summary="Get real-time Indian market data")
async def get_market(current_user: User = Depends(get_current_user)):
    return await get_market_data()