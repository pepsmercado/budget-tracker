from fastapi import APIRouter
from app_state import backend

router = APIRouter()


@router.get("/balance")
def get_balances():
    return backend.get_balances()


@router.get("/summary/{year}")
def get_annual_summary(year: int):
    return backend.get_annual_summary(year)


@router.get("/rates")
def get_rates():
    return backend.get_rates()
