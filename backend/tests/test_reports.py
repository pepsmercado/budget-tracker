def test_monthly_report(client):
    resp = client.get("/api/reports/monthly", params={"month": "2026-07"})
    assert resp.status_code == 200
    data = resp.json()
    assert "budget" in data
    assert "prev_budget" in data
    assert "balances" in data


def test_monthly_report_with_currency(client):
    resp = client.get("/api/reports/monthly", params={"month": "2026-07", "currency": "PHP"})
    assert resp.status_code == 200
    data = resp.json()
    assert "budget" in data
    assert "balances" in data


def test_yearly_report(client):
    resp = client.get("/api/reports/yearly", params={"year": 2026})
    assert resp.status_code == 200
    data = resp.json()
    assert "annual" in data
    assert "monthly_categories" in data
    assert "monthly_summary" in data
    assert "balances" in data
    assert len(data["monthly_summary"]) == 12


def test_yearly_report_with_currency(client):
    resp = client.get("/api/reports/yearly", params={"year": 2026, "currency": "USD"})
    assert resp.status_code == 200
    data = resp.json()
    assert "annual" in data
    assert data["annual"]["currency"] == "USD"


def test_monthly_report_budget_has_categories(client):
    resp = client.get("/api/reports/monthly", params={"month": "2026-07"})
    budget = resp.json()["budget"]
    assert "categories" in budget
    assert isinstance(budget["categories"], list)


def test_prev_month_calculation(client):
    from routers.reports import _prev_month
    assert _prev_month("2026-07-01") == "2026-06"
    assert _prev_month("2026-01-01") == "2025-12"
    assert _prev_month("2026-12-15") == "2026-11"
