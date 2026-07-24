from fastapi import APIRouter, Depends, HTTPException
from models import AccountCreate, AccountGoalUpdate
from app_state import backend
from auth import require_auth

router = APIRouter()


@router.get("/accounts")
def list_accounts():
    return backend.get_accounts()


@router.post("/accounts", status_code=201)
def create_account(data: AccountCreate, _auth: None = Depends(require_auth)):
    return backend.create_account(data)


@router.put("/accounts/{account_id}")
def update_account(account_id: str, data: AccountCreate, _auth: None = Depends(require_auth)):
    try:
        return backend.update_account(account_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: str, _auth: None = Depends(require_auth)):
    try:
        backend.delete_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")


@router.put("/accounts/{account_id}/goal")
def update_account_goal(account_id: str, data: AccountGoalUpdate, _auth: None = Depends(require_auth)):
    try:
        return backend.update_account_goal(account_id, data.goal_amount)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
