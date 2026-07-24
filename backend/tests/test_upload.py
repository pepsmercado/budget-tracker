import io
import csv


def _make_csv_content(headers, rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def test_preview_bpi_csv(client):
    csv_content = _make_csv_content(
        ["Date", "Description", "Credit", "Debit"],
        [
            {"Date": "07/01/2026", "Description": "BPI Salary", "Credit": "50000", "Debit": ""},
            {"Date": "07/02/2026", "Description": "BPI Grocery", "Credit": "", "Debit": "3500"},
        ],
    )
    resp = client.post("/api/upload/preview", files={"file": ("test.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["bank"] == "bpi"
    assert data["total_rows"] == 2
    assert data["total_income"] == 50000.0
    assert data["total_expense"] == 3500.0


def test_preview_bdo_csv(client):
    csv_content = _make_csv_content(
        ["Date", "Description", "Amount"],
        [
            {"Date": "07/01/2026", "Description": "Deposit", "Amount": "10000"},
            {"Date": "07/02/2026", "Description": "Purchase", "Amount": "-2500"},
        ],
    )
    resp = client.post("/api/upload/preview",
                       files={"file": ("bdo.csv", csv_content, "text/csv")},
                       data={"bank": "bdo"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["bank"] == "bdo"
    assert data["total_rows"] == 2


def test_bulk_preview(client):
    accounts = client.get("/api/accounts").json()
    acc = accounts[0]
    csv_content = _make_csv_content(
        ["date", "account_id", "type", "amount", "currency", "category", "description", "sub_account_id"],
        [
            {"date": "2026-07-15", "account_id": acc["id"], "type": "expense", "amount": "500", "currency": "PHP", "category": "Groceries", "description": "Test", "sub_account_id": ""},
        ],
    )
    resp = client.post("/api/upload/bulk-preview", files={"file": ("test.csv", csv_content, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 1
    assert data["total_expense"] == 500.0


def test_bulk_import(client):
    accounts = client.get("/api/accounts").json()
    acc = accounts[0]
    csv_content = _make_csv_content(
        ["date", "account_id", "type", "amount", "currency", "category", "description", "sub_account_id"],
        [
            {"date": "2026-07-15", "account_id": acc["id"], "type": "expense", "amount": "250", "currency": "PHP", "category": "Groceries", "description": "Bulk test", "sub_account_id": ""},
        ],
    )
    resp = client.post("/api/upload/bulk-import", json={
        "rows": [{
            "date": "2026-07-15", "account_id": acc["id"], "type": "expense",
            "amount": 250.0, "currency": "PHP", "category": "Groceries",
            "description": "Bulk test", "sub_account_id": "",
        }],
    })
    assert resp.status_code == 200
    assert resp.json()["created"] == 1
    assert len(resp.json()["errors"]) == 0


def test_bank_import(client):
    accounts = client.get("/api/accounts").json()
    acc = accounts[0]
    resp = client.post("/api/upload/bank-import", json={
        "rows": [
            {"date": "2026-07-15", "description": "Test", "amount": 1000, "type": "expense", "category": "Groceries", "warnings": [], "raw": {}},
        ],
        "account_id": acc["id"],
    })
    assert resp.status_code == 200
    assert resp.json()["created"] == 1


def test_bank_import_invalid_account(client):
    resp = client.post("/api/upload/bank-import", json={
        "rows": [
            {"date": "2026-07-15", "description": "Test", "amount": 1000, "type": "expense", "category": "Groceries", "warnings": [], "raw": {}},
        ],
        "account_id": "nonexistent",
    })
    assert resp.status_code == 400


def test_unsupported_file_type(client):
    resp = client.post("/api/upload/preview", files={"file": ("test.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_legend(client):
    resp = client.get("/api/upload/legend")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "VALID ACCOUNTS" in content
    assert "VALID CATEGORIES" in content


def test_template(client):
    resp = client.get("/api/upload/template")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "date" in content
    assert "account_id" in content
