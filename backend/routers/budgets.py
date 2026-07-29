from fastapi import APIRouter, Query
from app_state import backend

router = APIRouter()


@router.get("/budgets/{month}/summary")
def get_budget_summary(month: str, currency: str | None = Query(None)):
    return backend.get_budget_summary(month, currency=currency)
