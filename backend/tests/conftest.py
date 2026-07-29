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
    b._balance_cache = {}
    b._seed()
    with patch.object(b, "_save"):
        yield b


@pytest.fixture
def client(backend):
    from fastapi.testclient import TestClient
    import app_state
    import main

    with patch.object(app_state, "backend", backend):
        with TestClient(main.app) as c:
            yield c
