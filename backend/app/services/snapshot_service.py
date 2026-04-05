"""
services/snapshot_service.py
──────────────────────────────
Persist and retrieve a user's parsed FinancialData JSON snapshot.

The `financial_snapshots` table stores one JSON blob per user per document_type.
Rows are upserted so re-uploading a document replaces the previous parse.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import FinancialSnapshot
from app.schemas.financial_data import FinancialData


async def upsert_snapshot(
    db: AsyncSession,
    user_id: int,
    document_type: str,
    financial_data: FinancialData,
) -> FinancialSnapshot:
    """
    Insert or replace the snapshot for (user_id, document_type).

    Args:
        db            : Active async session.
        user_id       : Owner of the snapshot.
        document_type : 'bank_statement' | 'it_return' | 'cibil'.
        financial_data: Pydantic model returned by pdf_service.

    Returns:
        The persisted FinancialSnapshot ORM row.
    """
    result = await db.execute(
        select(FinancialSnapshot).where(
            FinancialSnapshot.user_id == user_id,
            FinancialSnapshot.document_type == document_type,
        )
    )
    snapshot = result.scalar_one_or_none()

    payload_json = financial_data.model_dump_json()

    if snapshot:
        snapshot.data = payload_json
        snapshot.updated_at = datetime.now(timezone.utc)
    else:
        snapshot = FinancialSnapshot(
            user_id=user_id,
            document_type=document_type,
            data=payload_json,
        )
        db.add(snapshot)

    await db.flush()
    return snapshot


async def get_merged_financial_data(
    db: AsyncSession, user_id: int
) -> FinancialData | None:
    """
    Merge all available snapshots for *user_id* into a single FinancialData envelope.

    Returns None if no snapshots exist yet.
    """
    result = await db.execute(
        select(FinancialSnapshot).where(FinancialSnapshot.user_id == user_id)
    )
    snapshots = result.scalars().all()

    if not snapshots:
        return None

    merged = FinancialData(user_id=user_id)

    for snap in snapshots:
        partial = FinancialData.model_validate(json.loads(snap.data))
        if snap.document_type == "bank_statement" and partial.bank_statement:
            merged.bank_statement = partial.bank_statement
        elif snap.document_type == "it_return" and partial.it_return:
            merged.it_return = partial.it_return
        elif snap.document_type == "cibil" and partial.cibil:
            merged.cibil = partial.cibil

    return merged
