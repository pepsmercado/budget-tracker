from fastapi import APIRouter, Query
from app_state import backend

router = APIRouter()


def _prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    m -= 1
    if m < 1:
        m = 12
        y -= 1
    return f"{y}-{m:02d}"


@router.get("/reports/monthly")
def get_monthly_report(month: str = Query(...), currency: str | None = Query(None)):
    budget = backend.get_budget_summary(month, currency=currency)
    prev_budget = backend.get_budget_summary(_prev_month(month), currency=currency)
    balances = backend.get_balances(currency=currency)
    return {"budget": budget, "prev_budget": prev_budget, "balances": balances}


@router.get("/reports/yearly")
def get_yearly_report(year: int = Query(...), currency: str | None = Query(None)):
    annual = backend.get_annual_summary(year, currency=currency)
    monthly_cats = backend.get_monthly_category_breakdown(year, currency=currency)
    # Per-month income/expense totals
    monthly_summary = []
    for m in range(1, 13):
        ms = f"{year}-{m:02d}"
        b = backend.get_budget_summary(ms, currency=currency)
        monthly_summary.append({
            "month": ms,
            "total_budget": b.total_budget,
            "total_spent": b.total_spent,
        })
    # Account balances per quarter
    balances = backend.get_balances(currency=currency)
    return {
        "annual": annual,
        "monthly_categories": monthly_cats,
        "monthly_summary": monthly_summary,
        "balances": balances,
    }
