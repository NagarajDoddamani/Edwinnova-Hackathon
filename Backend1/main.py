import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import Base, engine
from app.models import User, Loan, Investment
from app.models.snapshot import FinancialSnapshot
from app.routes.health_report import router as health_router
from app.routes.investments import router as investments_router
from app.routes.loans import router as loans_router
from app.routes.pdf_upload import router as pdf_router
from app.routes.ai_suggestions import router as ai_router

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Password & JWT helpers ─────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer = HTTPBearer()

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)

def create_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Missing sub")
    return sub

# ── MongoDB ────────────────────────────────────────────────────────────────────
_mongo_client: AsyncIOMotorClient | None = None

def get_mongo_db():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
    return _mongo_client[settings.MONGO_DB_NAME]

# ── MongoDB Collections ────────────────────────────────────────────────────────
def users_col():
    return get_mongo_db()["users"]

def query_col():
    return get_mongo_db()["query_history"]

# ── Current User Dependency ────────────────────────────────────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        user_id = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.", headers={"WWW-Authenticate": "Bearer"})
    user = await users_col().find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user

# ── Pydantic Schemas ───────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    name: str
    email: EmailStr

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserUpdateRequest(BaseModel):
    name: str | None = None
    age: int | None = None
    employment_type: str | None = None
    location: str | None = None

class AskRequest(BaseModel):
    question: str

# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s ...", settings.APP_NAME, settings.APP_VERSION)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables and upload dir ready.")
    yield
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
    await engine.dispose()
    logger.info("%s shut down cleanly.", settings.APP_NAME)

# ── App Factory ────────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="FinArmor Backend API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Existing routers ───────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(pdf_router, prefix=prefix)
    app.include_router(loans_router, prefix=prefix)
    app.include_router(investments_router, prefix=prefix)
    app.include_router(health_router, prefix=prefix)
    app.include_router(ai_router, prefix=prefix)

    # ── System endpoints ───────────────────────────────────────────────────────
    @app.get("/", tags=["System"])
    async def root() -> dict:
        return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}

    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    # ══════════════════════════════════════════════════════════════════════════
    # 1. POST /auth/register
    # ══════════════════════════════════════════════════════════════════════════
    @app.post("/api/v1/auth/register", response_model=TokenResponse, status_code=201, tags=["Auth"])
    async def register(payload: RegisterRequest):
        existing = await users_col().find_one({"email": payload.email})
        if existing:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        user = {
            "email": payload.email,
            "full_name": payload.name,
            "hashed_password": hash_password(payload.password),
            "is_active": True,
            "age": None,
            "employment_type": None,
            "location": None,
            "created_at": datetime.now(timezone.utc),
        }
        result = await users_col().insert_one(user)
        return TokenResponse(access_token=create_token(str(result.inserted_id)))

    # ══════════════════════════════════════════════════════════════════════════
    # 2. POST /auth/login
    # ══════════════════════════════════════════════════════════════════════════
    @app.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Auth"])
    async def login(payload: LoginRequest):
        user = await users_col().find_one({"email": payload.email})
        if not user or not verify_password(payload.password, user.get("hashed_password", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password.", headers={"WWW-Authenticate": "Bearer"})
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account is disabled.")
        return TokenResponse(access_token=create_token(str(user["_id"])))

    # ══════════════════════════════════════════════════════════════════════════
    # 3. POST /auth/google
    # ══════════════════════════════════════════════════════════════════════════
    @app.post("/api/v1/auth/google", response_model=TokenResponse, tags=["Auth"])
    async def google_login(payload: GoogleLoginRequest):
        user = await users_col().find_one({"email": payload.email})
        if not user:
            doc = {
                "email": payload.email,
                "full_name": payload.name,
                "hashed_password": "",
                "is_active": True,
                "age": None,
                "employment_type": None,
                "location": None,
                "created_at": datetime.now(timezone.utc),
            }
            result = await users_col().insert_one(doc)
            user_id = str(result.inserted_id)
        else:
            user_id = str(user["_id"])
        return TokenResponse(access_token=create_token(user_id))

    # ══════════════════════════════════════════════════════════════════════════
    # 4. GET /user/me
    # ══════════════════════════════════════════════════════════════════════════
    @app.get("/api/v1/user/me", tags=["User"])
    async def get_me(current_user: dict = Depends(get_current_user)):
        return {
            "name": current_user.get("full_name", ""),
            "email": current_user.get("email", ""),
            "age": current_user.get("age"),
            "employment_type": current_user.get("employment_type"),
            "location": current_user.get("location"),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 5. PUT /user/update
    # ══════════════════════════════════════════════════════════════════════════
    @app.put("/api/v1/user/update", tags=["User"])
    async def update_profile(payload: UserUpdateRequest, current_user: dict = Depends(get_current_user)):
        updates = {}
        if payload.name is not None: updates["full_name"] = payload.name
        if payload.age is not None: updates["age"] = payload.age
        if payload.employment_type is not None: updates["employment_type"] = payload.employment_type
        if payload.location is not None: updates["location"] = payload.location
        if updates:
            await users_col().update_one({"_id": current_user["_id"]}, {"$set": updates})
        return {"message": "updated"}

    # ══════════════════════════════════════════════════════════════════════════
    # 6. GET /finance/analysis
    # ══════════════════════════════════════════════════════════════════════════
    @app.get("/api/v1/finance/analysis", tags=["Finance"])
    async def get_financial_analysis(current_user: dict = Depends(get_current_user)):
        user_id = str(current_user["_id"])
        db = get_mongo_db()
        snapshot = await db["financial_snapshots"].find_one(
            {"user_id": user_id}, sort=[("updated_at", -1)]
        )
        if not snapshot:
            return {
                "income": 0, "expenses": 0, "savings": 0, "goals": 0,
                "profile_completion": "0%",
                "recommendation": "Upload your bank statement or ITR to get a full analysis.",
            }
        data = snapshot.get("data", {})
        incomes = data.get("monthly_income", [0])
        expenses = data.get("monthly_expenses", [0])
        income = sum(incomes) / max(len(incomes), 1)
        expense = sum(expenses) / max(len(expenses), 1)
        savings = income - expense
        profile_fields = ["full_name", "age", "employment_type", "location"]
        filled = sum(1 for f in profile_fields if current_user.get(f))
        profile_pct = f"{int((filled / len(profile_fields)) * 100)}%"
        recommendation = "Your finances look stable." if savings > 0 else "Your expenses exceed income. Consider reducing discretionary spending."
        return {
            "income": round(income, 2),
            "expenses": round(expense, 2),
            "savings": round(savings, 2),
            "goals": 0,
            "profile_completion": profile_pct,
            "recommendation": recommendation,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # 7. GET /query/history
    # ══════════════════════════════════════════════════════════════════════════
    @app.get("/api/v1/query/history", tags=["Query"])
    async def query_history(current_user: dict = Depends(get_current_user)):
        user_id = str(current_user["_id"])
        cursor = query_col().find({"user_id": user_id}).sort("timestamp", -1).limit(50)
        docs = await cursor.to_list(length=50)
        return [
            {
                "id": str(d["_id"]),
                "question": d["question"],
                "answer": d["answer"],
                "timestamp": d["timestamp"],
            }
            for d in docs
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # 8. POST /query/ask
    # ══════════════════════════════════════════════════════════════════════════
    @app.post("/api/v1/query/ask", tags=["Query"])
    async def ask_query(payload: AskRequest, current_user: dict = Depends(get_current_user)):
        from app.services.gemini_service import get_investment_suggestions
        user_id = str(current_user["_id"])
        financial_context = {
            "monthly_income": [], "monthly_expenses": [], "tax_paid": [],
            "account_balance": [], "total_assets": [], "credit_score": None,
        }
        try:
            result = await get_investment_suggestions(financial_context, payload.question)
            answer = result.get("financial_summary", "") + "\n" + "\n".join(
                s.get("title", "") + ": " + s.get("rationale", "")
                for s in result.get("suggestions", [])
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

        await query_col().insert_one({
            "user_id": user_id,
            "question": payload.question,
            "answer": answer,
            "analysis": result,
            "timestamp": datetime.now(timezone.utc),
        })
        return {"answer": answer, "analysis": result}

    return app


app = create_app()