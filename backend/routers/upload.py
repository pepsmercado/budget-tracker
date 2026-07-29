import csv
import io
import re
import pdfplumber
from datetime import datetime, date
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from models import BankStatementRow, BankStatementPreview, TransactionCreate
from app_state import backend
from auth import require_auth


MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def normalize_date(raw: str, default_year: int | None = None) -> str:
    """Convert various date strings to ISO YYYY-MM-DD."""
    raw = raw.strip()
    if not raw:
        return ""
    if default_year is None:
        default_year = date.today().year
    # Already ISO
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        pass
    # "05/01/2026" MM/DD/YYYY
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    # "1 May, 12:47 AM" — Maya style (strip time)
    m = re.match(r'(\d{1,2})\s+([A-Z][a-z]{2})(?:,|\s)', raw)
    if m:
        day = int(m.group(1))
        mon = MONTH_MAP.get(m.group(2).lower())
        if mon:
            return date(default_year, mon, day).isoformat()
    # "May 1, 2026" or "1 May 2026"
    for fmt in ("%B %d, %Y", "%d %B %Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return raw

router = APIRouter()

CATEGORY_KEYWORDS = {
    "Rent": ["rent", "lease", "condo", "apartment"],
    "Electricity": ["electric", "electricity", "meralco", "power bill"],
    "Gas": ["gas", "lpg", "gasul"],
    "Subscriptions": ["netflix", "spotify", "subscription", "hulu", "disney", "youtube premium", "icloud"],
    "Phone & Wifi": ["globe", "smart", "dito", "pldt", "converge", "internet", "wifi", "phone", "telecom"],
    "Groceries": ["grocery", "supermarket", "sm market", "puregold", "ralphs", "trader joe", "whole foods", "walmart", "costco", "safeway"],
    "Household": ["household", "shopee", "lazada", "home depot"],
    "Transportation": ["grab", "angkas", "gasoline", "fuel", "parking", "toll", "uber", "lyft", "train", "bus"],
    "Medical": ["pharmacy", "drugstore", "hospital", "clinic", "doctor", "medical", "mercury", "watsons"],
    "Eating Out": ["restaurant", "food", "mcdonald", "jollibee", "starbucks", "coffee", "dining", "cafe", "doordash", "ubereats", "grubhub"],
    "Social Events": ["bar", "club", "party", "event", "concert"],
    "Shopping": ["shopping", "mall", "store", "amazon", "clothing", "shoes"],
    "Beauty": ["salon", "beauty", "spa", "skincare"],
    "Travel": ["airline", "hotel", "booking", "agoda", "airbnb", "travel", "flight"],
    "Transfer Fees": ["transfer fee", "bank charge", "service fee"],
    "Salary": ["salary", "payroll", "wage", "sweldo"],
    "Cashback": ["cashback", "cash back", "reward"],
    "Interest": ["interest", "dividend"],
    "Others": ["others", "misc"],
}


def guess_category(description, tx_type):
    desc_lower = description.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                return cat
    return "Others"


def detect_bank(content: str) -> str:
    lower = content.lower()
    if "bpi" in lower:
        return "bpi"
    if "bdo" in lower:
        return "bdo"
    if "maya" in lower or "paymaya" in lower:
        return "maya"
    if "bank of america" in lower or "boa" in lower:
        return "bank_of_america"
    return "unknown"


def _parse_credit_debit(rows: list[dict]) -> list[BankStatementRow]:
    result = []
    for row in rows:
        date_str = normalize_date(row.get("Date", row.get("Transaction Date", "")).strip())
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


def parse_bpi(rows: list[dict]) -> list[BankStatementRow]:
    return _parse_credit_debit(rows)


def parse_bdo(rows: list[dict]) -> list[BankStatementRow]:
    return _parse_credit_debit(rows)


MAYA_TX_RE = re.compile(
    r'(\d{1,2}\s+[A-Z][a-z]{2},\s+\d{1,2}:\d{2}\s+[AP]M)\s+'  # date+time
    r'(.+?)\s+'                                                   # description
    r'(-?\s*\d[\d,]*\.\d{2})\s+'                                 # amount (may have sign)
    r'(\d[\d,]*\.\d{2})'                                          # balance
)


def _parse_maya_amount(raw: str) -> tuple[float, str]:
    clean = raw.replace(" ", "").replace(",", "")
    if clean.startswith("-"):
        return abs(float(clean)), "expense"
    return float(clean), "income"


def parse_maya_text(text: str) -> list[BankStatementRow]:
    """Parse Maya PDF statements by extracting text lines with regex."""
    # Extract year from statement header (e.g. "1 June 2026" or "May 2026")
    year_match = re.search(r'(\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}|[A-Z][a-z]+\s+20\d{2})', text)
    default_year = date.today().year
    if year_match:
        for fmt in ("%d %B %Y", "%B %Y"):
            try:
                default_year = datetime.strptime(year_match.group(1), fmt).year
                break
            except ValueError:
                pass
    result = []
    for line in text.split("\n"):
        m = MAYA_TX_RE.search(line)
        if m:
            date_str = normalize_date(m.group(1).strip(), default_year)
            desc = m.group(2).strip()
            amt, tx_type = _parse_maya_amount(m.group(3))
            result.append(BankStatementRow(
                date=date_str, description=desc, amount=round(amt, 2),
                type=tx_type, raw={"raw_line": line.strip()},
            ))
    return result


def parse_maya(rows: list[dict]) -> list[BankStatementRow]:
    result = []
    for row in rows:
        date_str = normalize_date(row.get("DateTime", row.get("Date", "")).strip())
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
        date_str = normalize_date(row.get("Date", row.get("Transaction Date", "")).strip())
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
async def preview_statement(file: UploadFile = File(...), bank: str = Form(""), _auth: None = Depends(require_auth)):
    content = await file.read()
    filename = file.filename.lower()

    if filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    if not text:
                        text = ",".join([str(c) if c else "" for c in table[0]]) + "\n"
                    for row in table[1:]:
                        text += ",".join([str(c) if c else "" for c in row]) + "\n"
                else:
                    text += (page.extract_text() or "") + "\n"
        # Maya PDFs have no tables — use text-based parser
        if not bank or bank == "auto":
            bank = detect_bank(text)
        if bank == "maya":
            parsed = parse_maya_text(text)
            for row in parsed:
                row.category = guess_category(row.description, row.type)
            total_income = sum(r.amount for r in parsed if r.type == "income")
            total_expense = sum(r.amount for r in parsed if r.type == "expense")
            return BankStatementPreview(
                bank=bank, account_hint="", rows=parsed,
                total_rows=len(parsed), total_income=round(total_income, 2),
                total_expense=round(total_expense, 2),
            )
    elif filename.endswith(".csv"):
        text = content.decode("utf-8-sig")
    else:
        raise HTTPException(status_code=400, detail="Only CSV and PDF files are supported")

    if not bank or bank == "auto":
        bank = detect_bank(text)

    if bank not in PARSERS:
        raise HTTPException(status_code=400, detail=f"Unsupported bank: {bank}. Supported: {', '.join(PARSERS.keys())}")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="File is empty or has no parseable data rows")

    parsed = PARSERS[bank](rows)

    for row in parsed:
        row.category = guess_category(row.description, row.type)

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


class BankImportRequest(BaseModel):
    rows: list[BankStatementRow]
    account_id: str


@router.post("/upload/bank-import")
async def bank_import(req: BankImportRequest, _auth: None = Depends(require_auth)):
    accounts = {a.id: a for a in backend.get_accounts()}
    if req.account_id not in accounts:
        suggestions = [a.name for a in backend.get_accounts()][:5]
        raise HTTPException(
            status_code=400,
            detail=f"Account '{req.account_id}' not found. Did you mean: {', '.join(suggestions)}?"
        )
    acc = accounts[req.account_id]
    created = []
    errors = []
    for i, row in enumerate(req.rows, start=1):
        try:
            txn = TransactionCreate(
                date=row.date,
                account_id=req.account_id,
                type=row.type,
                amount=row.amount,
                currency=acc.currency,
                category=row.category or "Others",
                description=row.description,
            )
            result = backend.create_transaction(txn)
            created.append(result.id)
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return {"created": len(created), "errors": errors}


BULK_CSV_HEADERS = ["date", "account_id", "type", "amount", "currency", "category", "description", "sub_account_id"]


@router.get("/upload/legend")
async def download_legend():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== VALID ACCOUNTS ==="])
    writer.writerow(["account_name", "account_id", "type", "currency"])
    for a in backend.get_accounts():
        writer.writerow([a.name, a.id, a.type, a.currency])

    writer.writerow([])
    writer.writerow(["=== VALID SUB-ACCOUNTS (for investment type) ==="])
    writer.writerow(["account_name", "sub_account_name", "sub_account_id"])
    for a in backend.get_accounts():
        for sub in a.sub_accounts:
            writer.writerow([a.name, sub.name, sub.id])

    writer.writerow([])
    writer.writerow(["=== VALID CATEGORIES ==="])
    writer.writerow(["category_name", "type", "group"])
    for c in backend.get_categories():
        writer.writerow([c.name, c.type, c.group])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bulk-upload-legend.csv"},
    )


@router.get("/upload/template")
async def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(BULK_CSV_HEADERS)

    accounts = backend.get_accounts()
    categories = backend.get_categories()
    exp_cats = [c.name for c in categories if c.type == "expense"]
    inc_cats = [c.name for c in categories if c.type == "income"]

    for acc in accounts:
        cat_list = exp_cats if acc.type != "income" else inc_cats
        for cat in cat_list[:2]:
            writer.writerow(["2025-01-15", acc.name, "expense" if cat in exp_cats else "income", "1500.00", acc.currency, cat, f"Sample {cat.lower()} transaction", ""])
        for sub in (acc.sub_accounts or []):
            writer.writerow(["2025-01-15", acc.name, "expense", "10000.00", acc.currency, "Shopping", f"Investment in {sub.name}", sub.name])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions-template.csv"},
    )


class BulkRow(BaseModel):
    date: str
    account_id: str
    type: str
    amount: float
    currency: str
    category: str
    description: str = ""
    sub_account_id: str = ""
    warnings: list[str] = []
    resolved: dict = {}


class BulkPreview(BaseModel):
    rows: list[BulkRow]
    total_rows: int
    total_income: float
    total_expense: float
    errors: list[str]


def normalize(s):
    return s.lower().strip().replace("_", " ").replace("-", " ").replace("  ", " ")

def fuzzy_match(query, candidates):
    q = normalize(query)
    for c in candidates:
        if q == normalize(c):
            return c
    for c in candidates:
        if q in normalize(c) or normalize(c) in q:
            return c
    return None


@router.post("/upload/bulk-preview")
async def bulk_preview(file: UploadFile = File(...), _auth: None = Depends(require_auth)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file has no headers")

    missing = [h for h in BULK_CSV_HEADERS if h not in reader.fieldnames]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")

    accounts = backend.get_accounts()
    categories = backend.get_categories()
    account_names = [a.name for a in accounts]
    account_ids = {a.id for a in accounts}
    category_names = [c.name for c in categories]
    sub_account_map = {}
    for a in accounts:
        for sub in a.sub_accounts:
            sub_account_map[sub.name.lower()] = (sub.id, a.name)
            sub_account_map[f"{a.name.lower()}:{sub.name.lower()}"] = (sub.id, a.name)

    rows = []
    errors = []
    for i, row in enumerate(reader, start=2):
        try:
            amount = float(row["amount"].replace(",", "").strip())
            if amount <= 0:
                errors.append(f"Row {i}: amount must be positive")
                continue
            raw_type = row["type"].strip().lower()
            if raw_type not in ("income", "expense"):
                errors.append(f"Row {i}: type must be 'income' or 'expense'")
                continue

            warnings = []
            resolved = {}

            raw_account = row["account_id"].strip()
            account_match = None
            if raw_account in account_ids:
                account_match = raw_account
            else:
                found = fuzzy_match(raw_account, account_names)
                if found:
                    acc_obj = next(a for a in accounts if a.name == found)
                    account_match = acc_obj.id
                    warnings.append(f"Account '{raw_account}' → '{found}'")
                    resolved["account_id"] = account_match
                else:
                    suggestions = ", ".join(account_names[:5])
                    warnings.append(f"Account '{raw_account}' not found — did you mean: {suggestions}?")

            raw_category = row["category"].strip()
            cat_match = fuzzy_match(raw_category, category_names)
            if cat_match and cat_match != raw_category:
                warnings.append(f"Category '{raw_category}' → '{cat_match}'")
                resolved["category"] = cat_match
            elif not cat_match:
                warnings.append(f"Category '{raw_category}' not found — will be saved as-is")

            raw_sub = row.get("sub_account_id", "").strip() if row.get("sub_account_id") else ""
            sub_match = None
            if raw_sub:
                if raw_sub in sub_account_map:
                    sub_match = sub_account_map[raw_sub][0]
                    if raw_sub != sub_match:
                        warnings.append(f"Sub-account '{raw_sub}' resolved")
                        resolved["sub_account_id"] = sub_match
                else:
                    found_sub = fuzzy_match(raw_sub, list(sub_account_map.keys()))
                    if found_sub:
                        sub_match = sub_account_map[found_sub][0]
                        warnings.append(f"Sub-account '{raw_sub}' → '{found_sub.split(':')[-1] if ':' in found_sub else found_sub}'")
                        resolved["sub_account_id"] = sub_match
                    else:
                        warnings.append(f"Sub-account '{raw_sub}' not found")

            rows.append(BulkRow(
                date=row["date"].strip(),
                account_id=account_match or raw_account,
                type=raw_type,
                amount=amount,
                currency=row["currency"].strip().upper(),
                category=cat_match or raw_category,
                description=row.get("description", "").strip(),
                sub_account_id=sub_match or raw_sub,
                warnings=warnings,
                resolved=resolved,
            ))
        except (ValueError, KeyError) as e:
            errors.append(f"Row {i}: {str(e)}")

    total_income = sum(r.amount for r in rows if r.type == "income")
    total_expense = sum(r.amount for r in rows if r.type == "expense")

    return BulkPreview(
        rows=rows,
        total_rows=len(rows),
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        errors=errors,
    )


class BulkImportRequest(BaseModel):
    rows: list[BulkRow]


@router.post("/upload/bulk-import")
async def bulk_import(req: BulkImportRequest, _auth: None = Depends(require_auth)):
    categories_map = {c.name.lower(): c.name for c in backend.get_categories()}
    accounts = backend.get_accounts()
    account_by_id = {a.id: a for a in accounts}
    account_by_name = {a.name.lower(): a for a in accounts}
    sub_account_by_name = {}
    for a in accounts:
        for sub in a.sub_accounts:
            sub_account_by_name[sub.name.lower()] = sub.id
            sub_account_by_name[f"{a.name.lower()}:{sub.name.lower()}"] = sub.id

    created = []
    errors = []
    for i, row in enumerate(req.rows, start=1):
        try:
            matched_category = categories_map.get(row.category.lower().strip(), row.category)

            account_id = row.account_id.strip()
            acc = account_by_id.get(account_id) or account_by_name.get(account_id.lower())
            if not acc:
                errors.append(f"Row {i}: account '{row.account_id}' not found")
                continue
            account_id = acc.id

            sub_account_id = row.sub_account_id.strip() if row.sub_account_id else ""
            resolved_sub = None
            if sub_account_id:
                resolved_sub = sub_account_by_name.get(sub_account_id.lower())
                if not resolved_sub:
                    for sub in acc.sub_accounts:
                        if sub.name.lower() == sub_account_id.lower():
                            resolved_sub = sub.id
                            break
                if not resolved_sub:
                    errors.append(f"Row {i}: sub-account '{sub_account_id}' not found in '{acc.name}'")
                    continue

            txn = TransactionCreate(
                date=row.date,
                account_id=account_id,
                type=row.type,
                amount=row.amount,
                currency=row.currency,
                category=matched_category,
                description=row.description,
                sub_account_id=resolved_sub,
            )
            result = backend.create_transaction(txn)
            created.append(result.id)
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
    return {"created": len(created), "errors": errors}
