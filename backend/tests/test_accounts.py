def test_list_accounts(client):
    resp = client.get("/api/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10


def test_create_account(client):
    resp = client.post("/api/accounts", json={
        "name": "Test Account",
        "type": "savings",
        "currency": "PHP",
        "bank": "TestBank",
        "account_number": "****1234",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Account"
    assert data["currency"] == "PHP"
    assert data["bank"] == "TestBank"
    assert "id" in data


def test_update_account(client):
    accounts = client.get("/api/accounts").json()
    acc_id = accounts[0]["id"]
    resp = client.put(f"/api/accounts/{acc_id}", json={
        "name": "Updated Name",
        "type": "savings",
        "currency": "PHP",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_update_account_preserves_goal(client):
    accounts = client.get("/api/accounts").json()
    acc_id = accounts[0]["id"]
    client.put(f"/api/accounts/{acc_id}/goal", json={"goal_amount": 50000})
    client.put(f"/api/accounts/{acc_id}", json={
        "name": "Still Has Goal",
        "type": "savings",
        "currency": "PHP",
    })
    updated = client.get("/api/accounts").json()
    acc = next(a for a in updated if a["id"] == acc_id)
    assert acc["goal_amount"] == 50000
    assert acc["name"] == "Still Has Goal"


def test_delete_account(client):
    accounts = client.get("/api/accounts").json()
    acc_id = accounts[0]["id"]
    resp = client.delete(f"/api/accounts/{acc_id}")
    assert resp.status_code == 204
    remaining = client.get("/api/accounts").json()
    assert all(a["id"] != acc_id for a in remaining)


def test_update_account_goal(client):
    accounts = client.get("/api/accounts").json()
    acc_id = accounts[0]["id"]
    resp = client.put(f"/api/accounts/{acc_id}/goal", json={"goal_amount": 100000})
    assert resp.status_code == 200
    assert resp.json()["goal_amount"] == 100000


def test_update_account_404(client):
    resp = client.put("/api/accounts/nonexistent", json={
        "name": "X", "type": "savings", "currency": "PHP",
    })
    assert resp.status_code == 404


def test_delete_account_404(client):
    resp = client.delete("/api/accounts/nonexistent")
    assert resp.status_code == 404


def test_update_goal_404(client):
    resp = client.put("/api/accounts/nonexistent/goal", json={"goal_amount": 0})
    assert resp.status_code == 404


def test_accounts_have_bank_and_account_number(client):
    accounts = client.get("/api/accounts").json()
    bpi_accounts = [a for a in accounts if a["bank"] == "BPI"]
    assert len(bpi_accounts) > 0
    for a in bpi_accounts:
        assert a["account_number"].startswith("****")


def test_account_types(client):
    accounts = client.get("/api/accounts").json()
    types = {a["type"] for a in accounts}
    assert "savings" in types
    assert "checking" in types
    assert "time_deposit" in types
    assert "equity" in types


def test_account_currencies(client):
    accounts = client.get("/api/accounts").json()
    currencies = {a["currency"] for a in accounts}
    assert "PHP" in currencies
    assert "USD" in currencies
