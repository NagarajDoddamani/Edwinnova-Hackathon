"""
routes/auth.py
──────────────
Authentication endpoints: register and login.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """
    Create a new FinArmor account.

    - Rejects duplicate emails with **400**.
    - Passwords are bcrypt-hashed; plain text is never stored.
    """
    existing = await user_service.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )
    user = await user_service.create_user(db, payload.email, payload.full_name, payload.password)
    return user  # type: ignore[return-value]


@router.post("/login", response_model=TokenResponse, summary="Login and receive JWT")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    Authenticate with email + password.

    Returns a signed JWT access token valid for the configured TTL.
    Intentionally vague error message to prevent user enumeration.
    """
    user = await user_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact support.",
        )
    token = create_access_token(str(user.id))
    return TokenResponse(access_token=token)
