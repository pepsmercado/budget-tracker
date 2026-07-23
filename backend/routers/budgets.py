from fastapi import APIRouter
from models import BudgetSet
from app_state import backend

router = APIRouter()


@router.get("/budgets/{month}")
def get_budget(month: str):
    budget = backend.get_budget(month)
    return budget if budget else {"month": month, "total_budget": 0, "currency": "USD"}


@router.put("/budgets/{month}")
def set_budget(month: str, data: BudgetSet):
    return backend.set_budget(month, data)


@router.get("/budgets/{month}/summary")
def get_budget_summary(month: str):
    return backend.get_budget_summary(month)
