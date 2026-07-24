from fastapi import APIRouter, Depends, HTTPException, Query
from models import TransferCreate
from app_state import backend
from auth import require_auth

router = APIRouter()


@router.get("/transfers")
def list_transfers(currency: str | None = Query(None)):
    return backend.get_transfers(currency=currency)


@router.post("/transfers", status_code=201)
def create_transfer(data: TransferCreate, _auth: None = Depends(require_auth)):
    try:
        return backend.create_transfer(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/transfers/{transfer_id}", status_code=204)
def delete_transfer(transfer_id: str, _auth: None = Depends(require_auth)):
    try:
        backend.delete_transfer(transfer_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Transfer not found")
