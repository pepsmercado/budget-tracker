from fastapi import APIRouter, HTTPException, Query
from models import RecurringRuleCreate
from app_state import backend

router = APIRouter()


@router.get("/recurring")
def list_recurring(currency: str | None = Query(None)):
    return backend.get_recurring_rules(currency=currency)


@router.post("/recurring", status_code=201)
def create_recurring(data: RecurringRuleCreate):
    return backend.create_recurring_rule(data)


@router.put("/recurring/{rule_id}")
def update_recurring(rule_id: str, data: RecurringRuleCreate):
    try:
        return backend.update_recurring_rule(rule_id, data)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recurring rule not found")


@router.delete("/recurring/{rule_id}", status_code=204)
def delete_recurring(rule_id: str):
    try:
        backend.delete_recurring_rule(rule_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recurring rule not found")


@router.put("/recurring/{rule_id}/toggle")
def toggle_recurring(rule_id: str, data: dict):
    try:
        return backend.toggle_recurring_rule(rule_id, data.get("active", True))
    except KeyError:
        raise HTTPException(status_code=404, detail="Recurring rule not found")


@router.post("/recurring/run")
def run_recurring(currency: str | None = Query(None)):
    return backend.run_recurring(currency=currency)
