def test_list_recurring(client):
    resp = client.get("/api/recurring")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_list_recurring_by_currency(client):
    resp = client.get("/api/recurring", params={"currency": "USD"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(r["currency"] == "USD" for r in data)


def test_create_recurring_rule(client):
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    resp = client.post("/api/recurring", json={
        "name": "Internet",
        "account_id": usd_acc["id"],
        "category": "Phone & Wifi",
        "amount": 80.0,
        "currency": "USD",
        "frequency": "monthly",
        "day_of_month": 15,
        "start_date": "2026-01-01",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Internet"
    assert data["amount"] == 80.0


def test_update_recurring_rule(client):
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]
    resp = client.put(f"/api/recurring/{rule_id}", json={
        "name": "Updated Rule",
        "account_id": rules[0]["account_id"],
        "category": rules[0]["category"],
        "amount": 999.0,
        "currency": rules[0]["currency"],
        "frequency": "monthly",
        "day_of_month": 1,
        "start_date": "2026-01-01",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Rule"
    assert resp.json()["amount"] == 999.0


def test_delete_recurring_rule(client):
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]
    resp = client.delete(f"/api/recurring/{rule_id}")
    assert resp.status_code == 204
    remaining = client.get("/api/recurring").json()
    assert all(r["id"] != rule_id for r in remaining)


def test_toggle_recurring_rule(client):
    rules = client.get("/api/recurring").json()
    rule_id = rules[0]["id"]
    resp = client.put(f"/api/recurring/{rule_id}/toggle", json={"active": False})
    assert resp.status_code == 200
    assert resp.json()["active"] is False
    resp = client.put(f"/api/recurring/{rule_id}/toggle", json={"active": True})
    assert resp.json()["active"] is True


def test_update_recurring_404(client):
    resp = client.put("/api/recurring/nonexistent", json={
        "name": "X", "account_id": "x", "category": "X",
        "amount": 1, "currency": "USD", "frequency": "monthly",
        "day_of_month": 1, "start_date": "2026-01-01",
    })
    assert resp.status_code == 404


def test_delete_recurring_404(client):
    resp = client.delete("/api/recurring/nonexistent")
    assert resp.status_code == 404


def test_toggle_recurring_404(client):
    resp = client.put("/api/recurring/nonexistent/toggle", json={"active": True})
    assert resp.status_code == 404


def test_recurring_has_end_date(client):
    rules = client.get("/api/recurring").json()
    for r in rules:
        assert "end_date" in r
        assert "next_date" in r


def test_run_recurring(client):
    resp = client.post("/api/recurring/run")
    assert resp.status_code == 200
    data = resp.json()
    assert "generated" in data
    assert "rules" in data
    assert isinstance(data["generated"], int)
