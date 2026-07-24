from fastapi import APIRouter, Depends, Query
from models import MonthlyBudgetOverride, MonthlyBudgetBulkSet
from app_state import backend
from auth import require_auth

router = APIRouter()


@router.get("/monthly-budgets/{month}")
def get_monthly_budgets(month: str, currency: str | None = Query(None)):
    return backend.get_monthly_budgets(month, currency=currency)


@router.put("/monthly-budgets/{month}")
def set_monthly_budget(month: str, data: MonthlyBudgetOverride, _auth: None = Depends(require_auth)):
    backend.set_monthly_budget(month, data.category, data.budget, data.currency)
    return {"ok": True}


@router.post("/monthly-budgets/{month}/bulk")
def bulk_set_monthly_budget(month: str, data: MonthlyBudgetBulkSet, _auth: None = Depends(require_auth)):
    currency = data.overrides[0].currency if data.overrides else "PHP"
    overrides = [{"category": o.category, "budget": o.budget} for o in data.overrides]
    backend.bulk_set_monthly_budget(month, overrides, currency)
    return {"ok": True}


@router.delete("/monthly-budgets/{month}")
def clear_monthly_budgets(month: str, currency: str | None = Query(None), _auth: None = Depends(require_auth)):
    backend.clear_monthly_budgets(month, currency)
    return {"ok": True}
