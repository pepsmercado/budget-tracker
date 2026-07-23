from fastapi import APIRouter, HTTPException, Query
from models import TransactionCreate
from app_state import backend

router = APIRouter()


@router.get("/transactions")
def list_transactions(
    account_id: str | None = Query(None),
    category: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
):
    return backend.get_transactions(
        account_id=account_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )


@router.post("/transactions", status_code=201)
def create_transaction(data: TransactionCreate):
    return backend.create_transaction(data)


@router.put("/transactions/{transaction_id}")
def update_transaction(transaction_id: str, data: TransactionCreate):
    try:
        return backend.update_transaction(transaction_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Transaction not found")


@router.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: str):
    try:
        backend.delete_transaction(transaction_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Transaction not found")
