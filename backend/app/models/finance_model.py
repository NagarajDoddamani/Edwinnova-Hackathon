from pydantic import BaseModel


class FinanceRecord(BaseModel):
    id: int | None = None
    user_id: int
    income: float
    expenses: float

