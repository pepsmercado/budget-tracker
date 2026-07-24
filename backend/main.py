from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from routers import accounts, transactions, categories, budgets, summary, upload, recurring, transfers, reports
from auth import router as auth_router

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
