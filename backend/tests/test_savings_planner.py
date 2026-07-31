def _php_savings_account(client):
    accounts = client.get("/api/accounts").json()
    return next(a for a in accounts if a["currency"] == "PHP" and a["type"] == "savings")


def _link(client, account_id=None, currency="PHP"):
    acc = account_id or _php_savings_account(client)["id"]
    return client.post(f"/api/savings-planner/{currency.lower()}/link",
                       json={"account_id": acc}).json()


def _create_goal(client, name, target, allocated=0):
    return client.post("/api/savings-planner/php/goals", json={
        "name": name, "target": target, "allocated": allocated,
    }).json()


def _create_reserve(client, name, allocated=0, floor=None):
    return client.post("/api/savings-planner/php/reserves", json={
        "name": name, "allocated": allocated, "floor": floor,
    }).json()["reserves"][0]


def _goal_id(client, name):
    return next(g["id"] for g in client.get("/api/savings-planner/php").json()["goals"]
                if g["name"] == name)


def _expense(client, account_id, amount, category="Others"):
    return client.post("/api/transactions", json={
        "date": "2026-08-01", "account_id": account_id, "type": "expense",
        "amount": amount, "currency": "PHP", "category": category,
    })


def test_planner_unlinked(client):
    resp = client.get("/api/savings-planner/php")
    assert resp.status_code == 200
    data = resp.json()
    assert data["planner"] is None
    assert len(data["savings_accounts"]) >= 1


def test_link_planner(client):
    acc = _php_savings_account(client)
    data = _link(client, acc["id"])
    assert data["planner"] is not None
    assert data["planner"]["linked_account_id"] == acc["id"]
    assert data["balance"] > 0
    assert abs(data["unallocated"] - data["balance"]) < 0.01
    assert data["reserves"] == []
    assert data["goals"] == []


def test_link_rejects_non_savings(client):
    acc = next(a for a in client.get("/api/accounts").json()
               if a["type"] == "checking")
    resp = client.post("/api/savings-planner/php/link", json={"account_id": acc["id"]})
    assert resp.status_code == 400


def test_link_rejects_wrong_currency(client):
    acc = next(a for a in client.get("/api/accounts").json()
               if a["currency"] == "USD")
    resp = client.post("/api/savings-planner/php/link", json={"account_id": acc["id"]})
    assert resp.status_code == 400


def test_create_goal_and_allocate(client):
    state = _link(client)
    acc_id = state["planner"]["linked_account_id"]
    balance = state["balance"]

    goal = client.post("/api/savings-planner/php/goals", json={
        "name": "Japan", "target": 5000, "allocated": 0,
    }).json()
    goal_id = goal["goals"][0]["id"]

    moved = client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": goal_id, "amount": 3000,
    }).json()
    assert moved["goals"][0]["allocated"] == 3000
    assert abs(moved["unallocated"] - (balance - 3000)) < 0.01


def test_goal_overfund_spills_to_unallocated(client):
    state = _link(client)
    balance = state["balance"]
    client.post("/api/savings-planner/php/goals", json={
        "name": "Waterpark", "target": 1000, "allocated": 0,
    })

    moved = client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": _goal_id(client, "Waterpark"), "amount": 2500,
    }).json()
    assert moved["goals"] == []
    assert len(moved["reserves"]) == 1
    assert moved["reserves"][0]["allocated"] == 1000
    assert abs(moved["unallocated"] - (balance - 1000)) < 0.01
    assert any(a["type"] == "Goal Converted" for a in moved["activity"])


def test_goal_auto_converts_to_reserve_on_completion(client):
    state = _link(client)
    balance = state["balance"]
    _create_goal(client, "Japan", 5000)

    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": _goal_id(client, "Japan"), "amount": 5000,
    })
    state = client.get("/api/savings-planner/php").json()
    assert state["goals"] == []
    assert len(state["reserves"]) == 1
    assert state["reserves"][0]["name"] == "Japan"
    assert state["reserves"][0]["allocated"] == 5000
    assert state["reserves"][0]["floor"] is None
    assert abs(state["unallocated"] - (balance - 5000)) < 0.01
    assert any(a["type"] == "Goal Converted" for a in state["activity"])


def test_expense_deducts_reserves_by_priority(client):
    state = _link(client)
    acc_id = state["planner"]["linked_account_id"]
    balance = state["balance"]

    # Tuition: no floor, position 0 (highest priority -> protected)
    _create_reserve(client, "Tuition", allocated=5000, floor=None)
    # Emergency: has a floor, position 1 (lower priority -> pulled first)
    _create_reserve(client, "Emergency", allocated=5000, floor=1000)

    # Spend all Unallocated plus 4000 -> only Emergency has spendable room
    resp = _expense(client, acc_id, round(balance - 6000, 2))
    assert resp.status_code == 201
    state = client.get("/api/savings-planner/php").json()
    reserves = {r["name"]: r["allocated"] for r in state["reserves"]}
    assert reserves["Emergency"] == 1000
    assert reserves["Tuition"] == 5000
    assert state["underfunded"] is False


def test_expense_auto_deducts_lowest_priority_goal(client):
    state = _link(client)
    acc_id = state["planner"]["linked_account_id"]
    balance = state["balance"]

    _create_goal(client, "High", 20000)
    _create_goal(client, "Low", 20000)
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": _goal_id(client, "High"), "amount": 5000})
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": _goal_id(client, "Low"), "amount": 5000})

    # Spend all Unallocated plus 3000 -> pulls 3000 from lowest-priority goal
    resp = _expense(client, acc_id, round(balance - 7000, 2))
    assert resp.status_code == 201
    state = client.get("/api/savings-planner/php").json()
    goals = {g["name"]: g["allocated"] for g in state["goals"]}
    assert goals["Low"] == 2000
    assert goals["High"] == 5000


def test_income_goes_to_unallocated(client):
    state = _link(client)
    acc_id = state["planner"]["linked_account_id"]
    balance = state["balance"]
    _create_goal(client, "Japan", 5000)
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": _goal_id(client, "Japan"), "amount": 2000})

    resp = client.post("/api/transactions", json={
        "date": "2026-08-01", "account_id": acc_id, "type": "income",
        "amount": 1000, "currency": "PHP", "category": "Salary",
    })
    assert resp.status_code == 201
    state = client.get("/api/savings-planner/php").json()
    assert abs(state["unallocated"] - (balance - 2000 + 1000)) < 0.01
    assert state["goals"][0]["allocated"] == 2000


def test_delete_goal_releases_to_unallocated(client):
    state = _link(client)
    balance = state["balance"]
    goal = client.post("/api/savings-planner/php/goals", json={
        "name": "Japan", "target": 5000, "allocated": 0}).json()["goals"][0]
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": goal["id"], "amount": 2000})

    state = client.delete(f"/api/savings-planner/php/goals/{goal['id']}").json()
    assert state["goals"] == []
    assert abs(state["unallocated"] - balance) < 0.01


def test_convert_goal_to_reserve(client):
    state = _link(client)
    goal = client.post("/api/savings-planner/php/goals", json={
        "name": "Japan", "target": 5000, "allocated": 0}).json()["goals"][0]
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": goal["id"], "amount": 2000})

    state = client.post(f"/api/savings-planner/php/goals/{goal['id']}/convert").json()
    assert state["goals"] == []
    assert len(state["reserves"]) == 1
    assert state["reserves"][0]["allocated"] == 2000
    assert state["reserves"][0]["floor"] is None


def test_floor_replenished_from_unallocated(client):
    state = _link(client)
    balance = state["balance"]
    reserve = client.post("/api/savings-planner/php/reserves", json={
        "name": "Emergency Fund", "allocated": 0, "floor": 1000,
    }).json()["reserves"][0]

    # Increase floor -> replenished from Unallocated
    state = client.put(f"/api/savings-planner/php/reserves/{reserve['id']}", json={
        "floor": 5000,
    }).json()
    assert state["reserves"][0]["allocated"] == 5000
    assert abs(state["unallocated"] - (balance - 5000)) < 0.01


def test_floored_reserve_stops_at_floor(client):
    state = _link(client)
    acc_id = state["planner"]["linked_account_id"]
    balance = state["balance"]
    reserve = client.post("/api/savings-planner/php/reserves", json={
        "name": "Emergency", "allocated": 0, "floor": 1000,
    }).json()["reserves"][0]
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": reserve["id"], "amount": 10000})

    # Spend everything: Unallocated is drained, then the floored reserve is
    # pulled but stops at its floor.
    _expense(client, acc_id, round(balance, 2))
    state = client.get("/api/savings-planner/php").json()
    assert state["reserves"][0]["allocated"] == 1000
    assert state["underfunded"] is True


def test_reserve_floor_blocks_moving_below_floor(client):
    state = _link(client)
    reserve = client.post("/api/savings-planner/php/reserves", json={
        "name": "Emergency", "allocated": 0, "floor": 1000,
    }).json()["reserves"][0]
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": reserve["id"], "amount": 3000})

    resp = client.post("/api/savings-planner/php/move", json={
        "from_bucket": reserve["id"], "to_bucket": "unallocated", "amount": 2500,
    })
    assert resp.status_code == 400


def test_allocate_endpoint(client):
    state = _link(client)
    balance = state["balance"]
    _create_goal(client, "Japan", 5000)
    _create_goal(client, "Waterpark", 5000)

    resp = client.post("/api/savings-planner/php/allocate", json={
        "allocations": [{"to_bucket": _goal_id(client, "Japan"), "amount": 1500},
                        {"to_bucket": _goal_id(client, "Waterpark"), "amount": 2500}],
    })
    assert resp.status_code == 200
    state = resp.json()
    goals = {g["name"]: g["allocated"] for g in state["goals"]}
    assert goals["Japan"] == 1500
    assert goals["Waterpark"] == 2500
    assert abs(state["unallocated"] - (balance - 4000)) < 0.01


def test_transfer_from_savings_deducts_planner(client):
    state = _link(client)
    acc_id = state["planner"]["linked_account_id"]
    balance = state["balance"]

    _create_goal(client, "Japan", 20000)
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": _goal_id(client, "Japan"), "amount": 5000})

    checking = client.post("/api/accounts", json={
        "name": "Checking", "type": "checking", "currency": "PHP",
        "bank": "BPI", "account_number": "****1111", "initial_balance": 0,
    }).json()
    # Transfer all Unallocated plus 3000 out of the linked savings account
    resp = client.post("/api/transfers", json={
        "from_account_id": acc_id, "to_account_id": checking["id"],
        "amount": round(balance - 2000, 2), "currency": "PHP", "fee": 0,
        "date": "2026-08-01", "note": "",
    })
    assert resp.status_code == 201
    state = client.get("/api/savings-planner/php").json()
    goals = {g["name"]: g["allocated"] for g in state["goals"]}
    assert goals["Japan"] == 2000


def test_activity_logged(client):
    state = _link(client)
    goal = client.post("/api/savings-planner/php/goals", json={
        "name": "Japan", "target": 5000, "allocated": 0}).json()["goals"][0]
    client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": goal["id"], "amount": 2000})
    state = client.get("/api/savings-planner/php").json()
    types = {a["type"] for a in state["activity"]}
    assert "Moved Funds" in types


def test_move_insufficient_funds(client):
    state = _link(client)
    goal = client.post("/api/savings-planner/php/goals", json={
        "name": "Japan", "target": 5000, "allocated": 0}).json()["goals"][0]
    balance = state["balance"]
    resp = client.post("/api/savings-planner/php/move", json={
        "from_bucket": "unallocated", "to_bucket": goal["id"],
        "amount": balance + 99999,
    })
    assert resp.status_code == 400


def test_create_reserve_too_much_allocated(client):
    state = _link(client)
    balance = state["balance"]
    resp = client.post("/api/savings-planner/php/reserves", json={
        "name": "Too Much", "allocated": balance + 99999, "floor": None,
    })
    assert resp.status_code == 400
