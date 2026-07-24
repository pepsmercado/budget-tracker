import hashlib
import os
from fastapi import APIRouter, Depends, HTTPException, Header

router = APIRouter()

SALT = "budget-tracker-salt"


def get_access_pin():
    return os.environ.get("ACCESS_PIN")


def get_token(pin: str) -> str:
    return hashlib.sha256(f"{pin}{SALT}".encode()).hexdigest()


def require_auth(authorization: str | None = Header(None)):
    access_pin = get_access_pin()
    if not access_pin:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    expected = get_token(access_pin)
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid code")


@router.get("/auth/status")
def auth_status():
    return {"enabled": get_access_pin() is not None}


@router.post("/auth/verify")
def verify_pin(body: dict):
    pin = body.get("pin", "")
    access_pin = get_access_pin()
    if not access_pin:
        return {"token": ""}
    if pin != access_pin:
        raise HTTPException(status_code=401, detail="Invalid code")
    return {"token": get_token(pin)}
