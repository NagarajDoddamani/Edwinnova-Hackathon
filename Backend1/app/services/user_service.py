"""
services/user_service.py
─────────────────────────
Data-access layer for the User resource.
All DB queries live here — routes stay free of SQLAlchemy.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Return a User by primary key, or None if not found."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return a User by email address (case-sensitive), or None."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, email: str, full_name: str, password: str
) -> User:
    """
    Hash *password* and persist a new User row.

    The caller's `get_db` dependency handles commit/rollback.
    """
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    await db.flush()   # obtain auto-generated id without committing
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """
    Verify email + password.

    Returns the User on success, None on any mismatch.
    Constant-time comparison via passlib prevents timing attacks.
    """
    user = await get_user_by_email(db, email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None
