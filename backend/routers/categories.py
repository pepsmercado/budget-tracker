from fastapi import APIRouter, Depends, HTTPException
from models import CategoryCreate, CategoryBudgetUpdate
from app_state import backend
from auth import require_auth

router = APIRouter()


@router.get("/categories")
def list_categories():
    return backend.get_categories()


@router.post("/categories", status_code=201)
def create_category(data: CategoryCreate, _auth: None = Depends(require_auth)):
    return backend.create_category(data)


@router.put("/categories/{category_id}")
def update_category(category_id: str, data: CategoryCreate, _auth: None = Depends(require_auth)):
    try:
        return backend.update_category(category_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")


@router.put("/categories/{category_id}/budget")
def update_category_budget(category_id: str, data: CategoryBudgetUpdate, _auth: None = Depends(require_auth)):
    try:
        return backend.update_category_budget(category_id, data.budget_amount)
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: str, _auth: None = Depends(require_auth)):
    try:
        backend.delete_category(category_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")
