"""
routes/pdf_upload.py
─────────────────────
PDF upload endpoint.

Flow:
  1. Validate file type and size.
  2. Save to disk under uploads/{user_id}/{uuid}.pdf.
  3. Enqueue background processing via FastAPI BackgroundTasks.
  4. Return 202 Accepted immediately so the frontend isn't blocked.

Background task:
  • Calls pdf_service.process_pdf()
  • Upserts the result into financial_snapshots via snapshot_service
  • Deletes the temporary file regardless of outcome
"""

import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.pdf_service import process_pdf
from app.services.snapshot_service import upsert_snapshot

router = APIRouter(prefix="/documents", tags=["PDF Upload"])

ALLOWED_DOCUMENT_TYPES = {"bank_statement", "it_return", "cibil"}
ALLOWED_CONTENT_TYPES = {"application/pdf"}


# ── Background task ───────────────────────────────────────────────────────────

async def _process_and_store(file_path: Path, document_type: str, user_id: int) -> None:
    """
    Run inside BackgroundTasks.

    Opens its own DB session (the request session is already closed).
    Always removes the temp file, even on failure — we log errors but do not crash.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        financial_data = await process_pdf(file_path, document_type, user_id)

        async with AsyncSessionLocal() as db:
            await upsert_snapshot(db, user_id, document_type, financial_data)
            await db.commit()

        logger.info(
            "Snapshot saved: user_id=%d document_type=%s", user_id, document_type
        )
    except Exception:
        logger.exception(
            "Background PDF processing failed: user_id=%d file=%s",
            user_id,
            file_path.name,
        )
    finally:
        file_path.unlink(missing_ok=True)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a financial PDF for background processing",
    responses={
        202: {"description": "File accepted; processing started in background."},
        400: {"description": "Invalid document type, file type, or file too large."},
        401: {"description": "Not authenticated."},
    },
)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    document_type: str = Form(
        ...,
        description="One of: bank_statement, it_return, cibil",
        examples=["bank_statement"],
    ),
    file: UploadFile = File(..., description="PDF file (max 20 MB)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Accept a PDF and enqueue it for parsing.

    - **document_type**: tells the parser which extractor to use.
    - **file**: must be a valid PDF (checked by Content-Type and extension).
    - Returns `202 Accepted` immediately; the client should poll `/health-report`
      or a status endpoint to know when data is ready.
    """
    # ── Validation ────────────────────────────────────────────────────────────
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"document_type must be one of: {', '.join(sorted(ALLOWED_DOCUMENT_TYPES))}",
        )

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted. Please upload a .pdf file.",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type '{file.content_type}'. Expected 'application/pdf'.",
        )

    # ── Size check (read first chunk to verify before saving) ─────────────────
    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum allowed size is {settings.MAX_FILE_SIZE_MB} MB.",
        )

    # ── Save to disk ──────────────────────────────────────────────────────────
    upload_dir = Path(settings.UPLOAD_DIR) / str(current_user.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / f"{uuid.uuid4()}.pdf"

    with dest.open("wb") as f:
        f.write(content)

    # ── Enqueue ───────────────────────────────────────────────────────────────
    background_tasks.add_task(
        _process_and_store, dest, document_type, current_user.id
    )

    return {
        "message": "PDF accepted for processing.",
        "document_type": document_type,
        "filename": filename,
        "status": "queued",
    }


@router.get(
    "/status",
    summary="Check which document types have been processed for the current user",
)
async def get_upload_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Returns which document types have a stored snapshot (i.e., have been processed).
    """
    from sqlalchemy import select
    from app.models.snapshot import FinancialSnapshot

    result = await db.execute(
        select(FinancialSnapshot.document_type, FinancialSnapshot.updated_at).where(
            FinancialSnapshot.user_id == current_user.id
        )
    )
    rows = result.all()
    processed = {row.document_type: row.updated_at.isoformat() for row in rows}

    return {
        "user_id": current_user.id,
        "processed_documents": processed,
        "pending": [dt for dt in ALLOWED_DOCUMENT_TYPES if dt not in processed],
    }
