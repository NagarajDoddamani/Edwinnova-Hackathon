from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.finance_routes import router as finance_router
from app.routes.recommendation_routes import router as recommendation_router
from app.routes.user_routes import router as user_router


app = FastAPI(title="FinArmor Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(finance_router, prefix="/finance", tags=["finance"])
app.include_router(recommendation_router, prefix="/recommendations", tags=["recommendations"])


@app.get("/")
def root():
    return {"message": "FinArmor backend is running"}
