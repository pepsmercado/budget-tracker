def test_list_transfers(client):
    resp = client.get("/api/transfers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_transfer(client):
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    from_acc = php_accs[0]
    to_acc = php_accs[1]
    resp = client.post("/api/transfers", json={
        "from_account_id": from_acc["id"],
        "to_account_id": to_acc["id"],
        "amount": 5000.0,
        "currency": "PHP",
        "fee": 0,
        "date": "2026-07-15",
        "note": "Test transfer",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == 5000.0
    assert data["from_account_id"] == from_acc["id"]
    assert data["to_account_id"] == to_acc["id"]


def test_create_transfer_creates_paired_transactions(client):
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    from_acc = php_accs[0]
    to_acc = php_accs[1]
    before_count = len(client.get("/api/transactions").json())
    client.post("/api/transfers", json={
        "from_account_id": from_acc["id"],
        "to_account_id": to_acc["id"],
        "amount": 5000.0,
        "currency": "PHP",
        "fee": 0,
        "date": "2026-07-15",
    })
    after_count = len(client.get("/api/transactions").json())
    assert after_count == before_count + 2


def test_create_transfer_with_fee(client):
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    from_acc = php_accs[0]
    to_acc = php_accs[1]
    resp = client.post("/api/transfers", json={
        "from_account_id": from_acc["id"],
        "to_account_id": to_acc["id"],
        "amount": 10000.0,
        "currency": "PHP",
        "fee": 50.0,
        "date": "2026-07-15",
    })
    assert resp.status_code == 201
    assert resp.json()["fee"] == 50.0


def test_delete_transfer(client):
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    client.post("/api/transfers", json={
        "from_account_id": php_accs[0]["id"],
        "to_account_id": php_accs[1]["id"],
        "amount": 1000.0,
        "currency": "PHP",
        "date": "2026-07-15",
    })
    transfers = client.get("/api/transfers").json()
    t_id = transfers[0]["id"]
    resp = client.delete(f"/api/transfers/{t_id}")
    assert resp.status_code == 204
    remaining = client.get("/api/transfers").json()
    assert all(t["id"] != t_id for t in remaining)


def test_transfer_different_currencies_fails(client):
    accounts = client.get("/api/accounts").json()
    php_acc = next(a for a in accounts if a["currency"] == "PHP")
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    resp = client.post("/api/transfers", json={
        "from_account_id": php_acc["id"],
        "to_account_id": usd_acc["id"],
        "amount": 1000.0,
        "currency": "PHP",
        "date": "2026-07-15",
    })
    assert resp.status_code == 400


def test_transfer_insufficient_balance_fails(client):
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    resp = client.post("/api/transfers", json={
        "from_account_id": php_accs[0]["id"],
        "to_account_id": php_accs[1]["id"],
        "amount": 999999999.0,
        "currency": "PHP",
        "date": "2026-07-15",
    })
    assert resp.status_code == 400


def test_transfer_nonexistent_account_fails(client):
    accounts = client.get("/api/accounts").json()
    php_acc = next(a for a in accounts if a["currency"] == "PHP")
    resp = client.post("/api/transfers", json={
        "from_account_id": "nonexistent",
        "to_account_id": php_acc["id"],
        "amount": 1000.0,
        "currency": "PHP",
        "date": "2026-07-15",
    })
    assert resp.status_code == 400


def test_delete_transfer_404(client):
    resp = client.delete("/api/transfers/nonexistent")
    assert resp.status_code == 404


def test_list_transfers_by_currency(client):
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    client.post("/api/transfers", json={
        "from_account_id": php_accs[0]["id"],
        "to_account_id": php_accs[1]["id"],
        "amount": 1000.0,
        "currency": "PHP",
        "date": "2026-07-15",
    })
    resp = client.get("/api/transfers", params={"currency": "PHP"})
    assert resp.status_code == 200
    assert all(t["currency"] == "PHP" for t in resp.json())
