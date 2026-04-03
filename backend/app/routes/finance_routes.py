from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_finance_records():
    return {"records": []}

