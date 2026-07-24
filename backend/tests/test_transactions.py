def test_list_transactions(client):
    resp = client.get("/api/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0


def test_filter_by_currency(client):
    resp = client.get("/api/transactions", params={"currency": "USD"})
    assert resp.status_code == 200
    data = resp.json()
    accounts = {a["id"]: a for a in client.get("/api/accounts").json()}
    for t in data:
        assert accounts[t["account_id"]]["currency"] == "USD"


def test_filter_by_type(client):
    resp = client.get("/api/transactions", params={"type": "income"})
    assert resp.status_code == 200
    for t in resp.json():
        assert t["type"] == "income"


def test_filter_by_category(client):
    resp = client.get("/api/transactions", params={"category": "Rent"})
    assert resp.status_code == 200
    for t in resp.json():
        assert t["category"] == "Rent"


def test_filter_by_date_range(client):
    resp = client.get("/api/transactions", params={
        "start_date": "2026-06-01", "end_date": "2026-06-30"
    })
    assert resp.status_code == 200
    for t in resp.json():
        assert "2026-06" in t["date"]


def test_filter_by_account(client):
    accounts = client.get("/api/accounts").json()
    acc_id = accounts[0]["id"]
    resp = client.get("/api/transactions", params={"account_id": acc_id})
    assert resp.status_code == 200
    for t in resp.json():
        assert t["account_id"] == acc_id


def test_create_transaction(client):
    accounts = client.get("/api/accounts").json()
    acc = next(a for a in accounts if a["currency"] == "PHP")
    resp = client.post("/api/transactions", json={
        "date": "2026-07-15",
        "account_id": acc["id"],
        "type": "expense",
        "amount": 500.0,
        "currency": "PHP",
        "category": "Groceries",
        "description": "Test transaction",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 500.0
    assert data["category"] == "Groceries"


def test_update_transaction(client):
    txns = client.get("/api/transactions").json()
    txn_id = txns[0]["id"]
    original = txns[0]
    resp = client.put(f"/api/transactions/{txn_id}", json={
        "date": original["date"],
        "account_id": original["account_id"],
        "type": original["type"],
        "amount": 9999.99,
        "currency": original["currency"],
        "category": original["category"],
        "description": "Updated",
    })
    assert resp.status_code == 200
    assert resp.json()["amount"] == 9999.99


def test_delete_transaction(client):
    txns = client.get("/api/transactions").json()
    txn_id = txns[0]["id"]
    resp = client.delete(f"/api/transactions/{txn_id}")
    assert resp.status_code == 204
    remaining = client.get("/api/transactions").json()
    assert all(t["id"] != txn_id for t in remaining)


def test_update_transaction_404(client):
    resp = client.put("/api/transactions/nonexistent", json={
        "date": "2026-01-01", "account_id": "x", "type": "expense",
        "amount": 1, "currency": "PHP", "category": "X",
    })
    assert resp.status_code == 404


def test_delete_transaction_404(client):
    resp = client.delete("/api/transactions/nonexistent")
    assert resp.status_code == 404


def test_transactions_sorted_by_date_desc(client):
    resp = client.get("/api/transactions")
    dates = [t["date"] for t in resp.json()]
    assert dates == sorted(dates, reverse=True)


def test_create_transaction_requires_positive_amount(client):
    accounts = client.get("/api/accounts").json()
    acc = accounts[0]
    resp = client.post("/api/transactions", json={
        "date": "2026-01-01", "account_id": acc["id"],
        "type": "expense", "amount": -100, "currency": "PHP",
        "category": "Test",
    })
    assert resp.status_code == 422
