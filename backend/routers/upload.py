import csv
import io
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from models import BankStatementRow, BankStatementPreview

router = APIRouter()


def detect_bank(content: str) -> str:
    lower = content.lower()
    if "bpi" in lower or "bpi" in lower:
        return "bpi"
    if "bdo" in lower:
        return "bdo"
    if "maya" in lower or "paymaya" in lower:
        return "maya"
    if "bank of america" in lower or "boa" in lower:
        return "bank_of_america"
    return "unknown"


def parse_bpi(rows: list[dict]) -> list[BankStatementRow]:
    result = []
    for row in rows:
        date_str = row.get("Date", row.get("Transaction Date", "")).strip()
        desc = row.get("Description", row.get("Particulars", "")).strip()
        amount_str = row.get("Amount", "0").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()
        credit = row.get("Credit", "").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()
        debit = row.get("Debit", "").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()

        if credit and credit != "0" and credit != "":
            try:
                amt = float(credit)
                result.append(BankStatementRow(date=date_str, description=desc, amount=amt, type="income", raw=dict(row)))
            except ValueError:
                pass
        elif debit and debit != "0" and debit != "":
            try:
                amt = float(debit)
                result.append(BankStatementRow(date=date_str, description=desc, amount=amt, type="expense", raw=dict(row)))
            except ValueError:
                pass
        elif amount_str and amount_str != "0":
            try:
                amt = float(amount_str)
                tx_type = "income" if amt > 0 else "expense"
                result.append(BankStatementRow(date=date_str, description=desc, amount=abs(amt), type=tx_type, raw=dict(row)))
            except ValueError:
                pass
    return result


def parse_bdo(rows: list[dict]) -> list[BankStatementRow]:
    result = []
    for row in rows:
        date_str = row.get("Date", row.get("Transaction Date", "")).strip()
        desc = row.get("Description", row.get("Particulars", "")).strip()
        amount_str = row.get("Amount", "0").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()
        credit = row.get("Credit", "").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()
        debit = row.get("Debit", "").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()

        if credit and credit != "0" and credit != "":
            try:
                amt = float(credit)
                result.append(BankStatementRow(date=date_str, description=desc, amount=amt, type="income", raw=dict(row)))
            except ValueError:
                pass
        elif debit and debit != "0" and debit != "":
            try:
                amt = float(debit)
                result.append(BankStatementRow(date=date_str, description=desc, amount=amt, type="expense", raw=dict(row)))
            except ValueError:
                pass
        elif amount_str and amount_str != "0":
            try:
                amt = float(amount_str)
                tx_type = "income" if amt > 0 else "expense"
                result.append(BankStatementRow(date=date_str, description=desc, amount=abs(amt), type=tx_type, raw=dict(row)))
            except ValueError:
                pass
    return result


def parse_maya(rows: list[dict]) -> list[BankStatementRow]:
    result = []
    for row in rows:
        date_str = row.get("DateTime", row.get("Date", "")).strip()
        desc = row.get("Description", row.get("Particulars", "")).strip()
        amount_str = row.get("Amount", "0").strip().replace(",", "").replace("PHP", "").replace("USD", "").strip()
        tx_type_raw = row.get("Type", row.get("Transaction Type", "")).strip().lower()

        try:
            amt = float(amount_str)
            if tx_type_raw in ("cr", "credit", "income", "deposit"):
                tx_type = "income"
            elif tx_type_raw in ("dr", "debit", "expense", "withdrawal"):
                tx_type = "expense"
            else:
                tx_type = "income" if amt > 0 else "expense"
            result.append(BankStatementRow(date=date_str, description=desc, amount=abs(amt), type=tx_type, raw=dict(row)))
        except ValueError:
            pass
    return result


def parse_bank_of_america(rows: list[dict]) -> list[BankStatementRow]:
    result = []
    for row in rows:
        date_str = row.get("Date", row.get("Transaction Date", "")).strip()
        desc = row.get("Description", row.get("Payee", "")).strip()
        withdrawal = row.get("Withdrawals", "").strip().replace(",", "").replace("$", "").strip()
        deposit = row.get("Deposits", "").strip().replace(",", "").replace("$", "").strip()
        amount_str = row.get("Amount", "0").strip().replace(",", "").replace("$", "").strip()

        if deposit and deposit != "0" and deposit != "":
            try:
                amt = float(deposit)
                result.append(BankStatementRow(date=date_str, description=desc, amount=amt, type="income", raw=dict(row)))
            except ValueError:
                pass
        elif withdrawal and withdrawal != "0" and withdrawal != "":
            try:
                amt = float(withdrawal)
                result.append(BankStatementRow(date=date_str, description=desc, amount=amt, type="expense", raw=dict(row)))
            except ValueError:
                pass
        elif amount_str and amount_str != "0":
            try:
                amt = float(amount_str)
                tx_type = "income" if amt > 0 else "expense"
                result.append(BankStatementRow(date=date_str, description=desc, amount=abs(amt), type=tx_type, raw=dict(row)))
            except ValueError:
                pass
    return result


PARSERS = {
    "bpi": parse_bpi,
    "bdo": parse_bdo,
    "maya": parse_maya,
    "bank_of_america": parse_bank_of_america,
}


@router.post("/upload/preview")
async def preview_statement(file: UploadFile = File(...), bank: str = ""):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    text = content.decode("utf-8-sig")

    if not bank or bank == "auto":
        bank = detect_bank(text)

    if bank not in PARSERS:
        raise HTTPException(status_code=400, detail=f"Unsupported bank: {bank}. Supported: {', '.join(PARSERS.keys())}")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no data rows")

    parsed = PARSERS[bank](rows)

    total_income = sum(r.amount for r in parsed if r.type == "income")
    total_expense = sum(r.amount for r in parsed if r.type == "expense")

    return BankStatementPreview(
        bank=bank,
        account_hint="",
        rows=parsed,
        total_rows=len(parsed),
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
    )
