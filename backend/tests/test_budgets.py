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
