from fastapi import APIRouter, Query
from app_state import backend

router = APIRouter()


@router.get("/balance")
def get_balances(currency: str | None = Query(None)):
    return backend.get_balances(currency=currency)


@router.get("/summary/{year}")
def get_annual_summary(year: int, currency: str | None = Query(None)):
    return backend.get_annual_summary(year, currency=currency)


@router.get("/summary/{year}/monthly-categories")
def get_monthly_categories(year: int, currency: str | None = Query(None)):
    return backend.get_monthly_category_breakdown(year, currency=currency)


@router.get("/rates")
def get_rates():
    return backend.get_rates()
