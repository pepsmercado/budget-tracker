import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.mock import MockBackend


@pytest.fixture
def backend():
    b = MockBackend.__new__(MockBackend)
    b.accounts = {}
    b.transactions = {}
    b.categories = {}
    b.recurring_rules = {}
    b.transfers = {}
    b.monthly_budgets = {}
    b.planners = {}
    b.savings_reserves = {}
    b.savings_goals = {}
    b.savings_activity = {}
    b._balance_cache = {}
    b._seed()
    with patch.object(b, "_save"):
        yield b


@pytest.fixture
def client(backend):
    from fastapi.testclient import TestClient
    import app_state
    import main
    from routers import (
        accounts, transactions, categories, budgets, summary, upload,
        recurring, transfers, reports, monthly_budgets, savings_planner,
    )

    # Routers bind `backend` at import time (`from app_state import backend`),
    # so patching app_state alone is not enough. Patch every module attribute.
    modules = [app_state, accounts, transactions, categories, budgets,
               summary, upload, recurring, transfers, reports,
               monthly_budgets, savings_planner]
    patches = [patch.object(m, "backend", backend) for m in modules]
    for p in patches:
        p.start()
    try:
        with TestClient(main.app) as c:
            yield c
    finally:
        for p in reversed(patches):
            p.stop()
