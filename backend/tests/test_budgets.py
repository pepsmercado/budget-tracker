def test_budget_summary(client):
    resp = client.get("/api/budgets/2026-07/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_budget" in data
    assert "total_spent" in data
    assert "categories" in data
    assert isinstance(data["categories"], list)


def test_budget_summary_with_currency(client):
    resp = client.get("/api/budgets/2026-07/summary", params={"currency": "PHP"})
    assert resp.status_code == 200
    assert len(resp.json()["categories"]) >= 0


def test_budget_summary_excludes_transfers(client):
    before = client.get("/api/budgets/2026-07/summary", params={"currency": "PHP"}).json()
    accounts = client.get("/api/accounts").json()
    php_accs = [a for a in accounts if a["currency"] == "PHP"]
    resp = client.post("/api/transfers", json={
        "from_account_id": php_accs[0]["id"],
        "to_account_id": php_accs[1]["id"],
        "amount": 5000.0,
        "currency": "PHP",
        "fee": 0,
        "date": "2026-07-15",
    })
    assert resp.status_code == 201
    after = client.get("/api/budgets/2026-07/summary", params={"currency": "PHP"}).json()
    assert after["total_spent"] == before["total_spent"]
    assert all(c["name"] != "Transfer" for c in after["categories"])
