content = '''import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

from app.models import User, Loan, Investment
from app.models.snapshot import FinancialSnapshot

from app.routes.auth import router as auth_router
from app.routes.health_report import router as health_router
from app.routes.investments import router as investments_router
from app.routes.loans import router as loans_router
from app.routes.pdf_upload import router as pdf_router
from app.routes.ai_suggestions import router as ai_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s ...", settings.APP_NAME, settings.APP_VERSION)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", settings.UPLOAD_DIR)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified / created.")
    yield
    await engine.dispose()
    logger.info("%s shut down cleanly.", settings.APP_NAME)


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

    prefix = "/api/v1"
    app.include_router(auth_router, prefix=prefix)
    app.include_router(pdf_router, prefix=prefix)
    app.include_router(loans_router, prefix=prefix)
    app.include_router(investments_router, prefix=prefix)
    app.include_router(health_router, prefix=prefix)
    app.include_router(ai_router, prefix=prefix)

    @app.get("/", tags=["System"], summary="Root")
    async def root() -> dict:
        return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}

    @app.get("/health", tags=["System"], summary="Health check")
    async def health_check() -> dict:
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
'''

with open('main.py', 'w') as f:
    f.write(content)

print("main.py fixed successfully!")