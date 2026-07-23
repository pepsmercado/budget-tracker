from fastapi import APIRouter, HTTPException
from models import CategoryCreate
from app_state import backend

router = APIRouter()


@router.get("/categories")
def list_categories():
    return backend.get_categories()


@router.post("/categories", status_code=201)
def create_category(data: CategoryCreate):
    return backend.create_category(data)


@router.put("/categories/{category_id}")
def update_category(category_id: str, data: CategoryCreate):
    try:
        return backend.update_category(category_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: str):
    try:
        backend.delete_category(category_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")
