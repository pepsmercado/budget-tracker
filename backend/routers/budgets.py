from fastapi import APIRouter, Depends, Query
from models import BudgetSet
from app_state import backend
from auth import require_auth

router = APIRouter()


@router.get("/budgets/{month}")
def get_budget(month: str, currency: str | None = Query(None)):
    budget = backend.get_budget(month, currency=currency)
    if not budget:
        budget = backend.get_budget(month)
    return budget if budget else {"month": month, "total_budget": 0, "currency": currency or "USD"}


@router.put("/budgets/{month}")
def set_budget(month: str, data: BudgetSet, _auth: None = Depends(require_auth)):
    return backend.set_budget(month, data)


@router.get("/budgets/{month}/summary")
def get_budget_summary(month: str, currency: str | None = Query(None)):
    return backend.get_budget_summary(month, currency=currency)
