def test_get_balances(client):
    resp = client.get("/api/balance")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    for b in data:
        assert "account_id" in b
        assert "balance" in b
        assert "currency" in b


def test_get_balances_by_currency(client):
    resp = client.get("/api/balance", params={"currency": "USD"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    for b in data:
        assert b["currency"] == "USD"


def test_get_annual_summary(client):
    resp = client.get("/api/summary/2026")
    assert resp.status_code == 200
    data = resp.json()
    assert data["year"] == 2026
    assert "total_income" in data
    assert "total_expense" in data
    assert "by_account" in data
    assert "by_category" in data
    assert "monthly" in data
    assert isinstance(data["monthly"], list)


def test_annual_summary_by_currency(client):
    resp = client.get("/api/summary/2026", params={"currency": "PHP"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["currency"] == "PHP"


def test_monthly_categories(client):
    resp = client.get("/api/summary/2026/monthly-categories")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        row = data[0]
        assert "category" in row
        assert "monthly" in row
        assert "group" in row


def test_monthly_categories_by_currency(client):
    resp = client.get("/api/summary/2026/monthly-categories", params={"currency": "USD"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_rates(client):
    resp = client.get("/api/rates")
    assert resp.status_code == 200
    data = resp.json()
    assert "base" in data
    assert "rates" in data
    assert "USD" in data["rates"]
    assert "PHP" in data["rates"]


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
