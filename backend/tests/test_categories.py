def test_list_categories(client):
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 25


def test_create_category(client):
    resp = client.post("/api/categories", json={
        "name": "Test Category",
        "type": "expense",
        "group": "Lifestyle",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Category"
    assert data["group"] == "Lifestyle"


def test_update_category(client):
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]
    resp = client.put(f"/api/categories/{cat_id}", json={
        "name": "Updated Category",
        "type": "expense",
        "group": "Fixed",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Category"


def test_update_category_budget(client):
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]
    resp = client.put(f"/api/categories/{cat_id}/budget", json={
        "budget_amount": 25000,
        "budget_currency": "PHP",
    })
    assert resp.status_code == 200
    assert resp.json()["budget_amount"] == 25000


def test_delete_category(client):
    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"]
    resp = client.delete(f"/api/categories/{cat_id}")
    assert resp.status_code == 204
    remaining = client.get("/api/categories").json()
    assert all(c["id"] != cat_id for c in remaining)


def test_update_category_404(client):
    resp = client.put("/api/categories/nonexistent", json={
        "name": "X", "type": "expense", "group": "Misc",
    })
    assert resp.status_code == 404


def test_update_category_budget_404(client):
    resp = client.put("/api/categories/nonexistent/budget", json={
        "budget_amount": 0, "budget_currency": "PHP",
    })
    assert resp.status_code == 404


def test_delete_category_404(client):
    resp = client.delete("/api/categories/nonexistent")
    assert resp.status_code == 404


def test_categories_have_groups(client):
    cats = client.get("/api/categories").json()
    groups = {c["group"] for c in cats}
    assert "Fixed" in groups
    assert "Essential" in groups
    assert "Lifestyle" in groups
    assert "Income" in groups
