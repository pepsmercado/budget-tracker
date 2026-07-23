from fastapi import APIRouter, HTTPException
from models import AccountCreate
from app_state import backend

router = APIRouter()


@router.get("/accounts")
def list_accounts():
    return backend.get_accounts()


@router.post("/accounts", status_code=201)
def create_account(data: AccountCreate):
    return backend.create_account(data)


@router.put("/accounts/{account_id}")
def update_account(account_id: str, data: AccountCreate):
    try:
        return backend.update_account(account_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: str):
    try:
        backend.delete_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
