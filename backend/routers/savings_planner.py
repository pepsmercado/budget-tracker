from fastapi import APIRouter, Depends, HTTPException, Query

from models import (
    SavingsPlannerLink,
    SavingsReserveCreate, SavingsReserveUpdate,
    SavingsGoalCreate, SavingsGoalUpdate,
    SavingsMove, SavingsAllocate,
)
from app_state import backend
from auth import require_auth

router = APIRouter()

VALID_CURRENCIES = {"PHP", "USD"}


def _ensure_currency(currency: str):
    if currency.upper() not in VALID_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Invalid currency '{currency}'")


@router.get("/savings-planner/{currency}")
def get_savings_planner(currency: str, limit: int = Query(50, ge=1, le=500)):
    _ensure_currency(currency)
    return backend.get_savings_planner(currency.upper(), limit)


@router.post("/savings-planner/{currency}/link")
def link_savings_planner(currency: str, data: SavingsPlannerLink, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.link_savings_planner(currency.upper(), data.account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/savings-planner/{currency}/reserves")
def create_reserve(currency: str, data: SavingsReserveCreate, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.create_savings_reserve(currency.upper(), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/savings-planner/{currency}/reserves/{reserve_id}")
def update_reserve(currency: str, reserve_id: str, data: SavingsReserveUpdate, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.update_savings_reserve(currency.upper(), reserve_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Reserve not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/savings-planner/{currency}/reserves/{reserve_id}")
def delete_reserve(currency: str, reserve_id: str, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.delete_savings_reserve(currency.upper(), reserve_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Reserve not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/savings-planner/{currency}/goals")
def create_goal(currency: str, data: SavingsGoalCreate, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.create_savings_goal(currency.upper(), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/savings-planner/{currency}/goals/{goal_id}")
def update_goal(currency: str, goal_id: str, data: SavingsGoalUpdate, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.update_savings_goal(currency.upper(), goal_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Goal not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/savings-planner/{currency}/goals/{goal_id}")
def delete_goal(currency: str, goal_id: str, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.delete_savings_goal(currency.upper(), goal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Goal not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/savings-planner/{currency}/goals/{goal_id}/convert")
def convert_goal(currency: str, goal_id: str, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.convert_savings_goal(currency.upper(), goal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Goal not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/savings-planner/{currency}/move")
def move_money(currency: str, data: SavingsMove, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.move_savings_money(currency.upper(), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/savings-planner/{currency}/allocate")
def allocate_money(currency: str, data: SavingsAllocate, _auth: None = Depends(require_auth)):
    _ensure_currency(currency)
    try:
        return backend.allocate_savings_money(currency.upper(), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
