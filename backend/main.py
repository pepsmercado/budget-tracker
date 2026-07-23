from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import accounts, transactions, categories, budgets, summary, upload

app = FastAPI(title="Expense Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(budgets.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
