def test_get_budget(client):
    resp = client.get("/api/budgets/2026-07")
    assert resp.status_code == 200
    data = resp.json()
    assert "month" in data
    assert "total_budget" in data


def test_set_budget(client):
    resp = client.put("/api/budgets/2026-12", json={
        "total_budget": 75000.0,
        "currency": "PHP",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_budget"] == 75000.0
    assert data["month"] == "2026-12"


def test_set_budget_upsert(client):
    client.put("/api/budgets/2026-12", json={"total_budget": 50000, "currency": "PHP"})
    client.put("/api/budgets/2026-12", json={"total_budget": 60000, "currency": "PHP"})
    resp = client.get("/api/budgets/2026-12")
    assert resp.json()["total_budget"] == 60000


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


def test_budget_not_found_returns_default(client):
    resp = client.get("/api/budgets/2099-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_budget"] == 0
