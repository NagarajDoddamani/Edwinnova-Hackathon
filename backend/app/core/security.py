"""
core/security.py
────────────────
JWT creation/verification and bcrypt password hashing.
All auth logic lives here so routes stay thin.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password Hashing ──────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* text password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ── JWT Tokens ────────────────────────────────────────────────────────────────
def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Encode a JWT with `sub` = *subject* (typically user_id as str).

    Args:
        subject: The value to embed in the token's `sub` claim.
        expires_delta: Custom TTL; defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT, returning the `sub` claim.

    Raises:
        JWTError: If the token is expired, malformed, or has an invalid signature.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    subject: str | None = payload.get("sub")
    if subject is None:
        raise JWTError("Token payload missing 'sub' claim.")
    return subject
