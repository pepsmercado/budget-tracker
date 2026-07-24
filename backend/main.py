from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json

from routers import accounts, transactions, categories, budgets, summary, upload, recurring, transfers, reports
from routers import monthly_budgets
from auth import router as auth_router
from app_state import backend

app = FastAPI(title="Expense Tracker API", redirect_slashes=False)

cors_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
]
vercel_url = os.environ.get("VERCEL_URL")
if vercel_url:
    cors_origins.append(f"https://{vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(budgets.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(recurring.router, prefix="/api")
app.include_router(transfers.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(monthly_budgets.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug/env")
def debug_env():
    """Debug endpoint to check environment"""
    return {
        "VERCEL": os.environ.get("VERCEL"),
        "DATA_DIR": os.environ.get("DATA_DIR"),
        "PWD": os.environ.get("PWD"),
    }


@app.get("/api/debug/data")
def debug_data():
    """Debug endpoint to check data file contents"""
    # Use same DATA_DIR logic as MockBackend
    if os.environ.get("VERCEL"):
        DATA_DIR = "/tmp"
    else:
        DATA_DIR = os.path.join(os.path.dirname(__file__), "services", "..")
    DATA_FILE = os.path.join(DATA_DIR, "data.json")
    
    result = {"file_exists": os.path.exists(DATA_FILE), "data_file_path": DATA_FILE}
    if result["file_exists"]:
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
            result["accounts_count"] = len(data.get("accounts", {}))
            result["transactions_count"] = len(data.get("transactions", {}))
            result["categories_count"] = len(data.get("categories", {}))
            result["budgets_count"] = len(data.get("budgets", {}))
            result["recurring_rules_count"] = len(data.get("recurring_rules", {}))
            result["transfers_count"] = len(data.get("transfers", {}))
            # Show first few transactions
            transactions = data.get("transactions", {})
            result["sample_transactions"] = list(transactions.items())[:3] if transactions else []
        except Exception as e:
            result["error"] = str(e)
    return result
