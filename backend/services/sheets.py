import uuid
import json
import os
import time
import gspread
from datetime import date, datetime
from google.oauth2.service_account import Credentials

from services.base import BackendService
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate, Budget, BudgetSet,
    Balance, AccountBalance, CategorySummary, MonthlyTotal,
    AnnualSummary, RatesResponse, SubAccount, MonthlyCategoryRow,
    BudgetSummary, CategoryBudgetSummary,
    RecurringRule, RecurringRuleCreate, RecurringRunResult,
    Transfer, TransferCreate,
)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_TABS = {
    "accounts": ["id", "name", "type", "currency", "bank", "account_number",
                 "initial_balance", "goal_amount", "sub_accounts",
                 "dividend_type", "maturity_date", "created_at"],
    "transactions": ["id", "date", "account_id", "type", "amount", "currency",
                     "category", "description", "transfer_pair_id",
                     "sub_account_id", "created_at"],
"categories": ["id", "name", "type", "group", "budget_amount"],
    "budgets": ["id", "month", "total_budget", "currency"],
    "recurring_rules": ["id", "name", "account_id", "category", "amount",
                        "currency", "frequency", "day_of_month", "start_date",
                        "end_date", "active", "last_generated", "next_date",
                        "created_at"],
    "transfers": ["id", "from_account_id", "to_account_id", "amount",
                  "currency", "fee", "date", "note", "created_at"],
    "monthly_budgets": ["month", "category", "budget", "currency"],
}


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _parse_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def _parse_float(val, default=0.0):
    if val is None or val == "":
        return default
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return default


def _parse_int(val, default=0):
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _parse_date(val):
    if not val:
        return date.today()
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val).strip())
    except ValueError:
        return date.today()


def _parse_datetime(val):
    if not val:
        return datetime.now()
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).strip())
    except ValueError:
        return datetime.now()


class SheetsBackend(BackendService):
    CACHE_TTL = 10  # seconds — fast enough to feel fresh, short enough to limit staleness

    def __init__(self):
        self._client = None
        self._spreadsheet = None
        self._sheets_cache: dict[str, list[dict]] = {}
        self._cache_times: dict[str, float] = {}

    def _seed_categories_if_empty(self):
        rows = self._read_all("categories")
        if len(rows) > 0:
            return
        categories_data = [
            ("Rent", "expense", "Fixed", 15000),
            ("Electricity", "expense", "Fixed", 3000),
            ("Gas", "expense", "Fixed", 1500),
            ("Subscriptions", "expense", "Fixed", 2000),
            ("Phone & Wifi", "expense", "Fixed", 1500),
            ("Rent Insurance", "expense", "Fixed", 800),
            ("Health Insurance", "expense", "Fixed", 2500),
            ("Groceries", "expense", "Essential", 12000),
            ("Household", "expense", "Essential", 3000),
            ("Transportation", "expense", "Essential", 4000),
            ("Medical", "expense", "Essential", 2000),
            ("Eating Out", "expense", "Lifestyle", 5000),
            ("Social Events", "expense", "Lifestyle", 3000),
            ("Hobbies", "expense", "Lifestyle", 2000),
            ("Shopping", "expense", "Sinking", 5000),
            ("Beauty", "expense", "Sinking", 2000),
            ("Travel", "expense", "Sinking", 8000),
            ("Others", "expense", "Sinking", 2000),
            ("Tuition", "expense", "School", 25000),
            ("School Supplies", "expense", "School", 2000),
            ("Salary", "income", "Income", 0),
            ("Cashback", "income", "Income", 0),
            ("Interest", "income", "Income", 0),
            ("Others", "income", "Income", 0),
            ("Transfer Fees", "expense", "Misc", 0),
        ]
        for name, ctype, group, budget in categories_data:
            c = Category(id=_uid(), name=name, type=ctype, group=group,
                         budget_amount=budget)
            row = {"id": c.id, "name": c.name, "type": c.type, "group": c.group,
                   "budget_amount": c.budget_amount}
            self._append_row("categories", row)

    def _get_client(self):
        if self._client is None:
            creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
            if not creds_json:
                raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON environment variable not set")
            creds_info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            self._client = gspread.authorize(creds)
        return self._client

    def _get_spreadsheet(self):
        if self._spreadsheet is None:
            sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
            if not sheet_id:
                raise RuntimeError("GOOGLE_SHEET_ID environment variable not set")
            client = self._get_client()
            self._spreadsheet = client.open_by_key(sheet_id)
        return self._spreadsheet

    def _get_sheet(self, tab_name: str):
        spreadsheet = self._get_spreadsheet()
        try:
            return spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=20)
            headers = SHEET_TABS.get(tab_name, [])
            if headers:
                sheet.update("A1", [headers])
            return sheet

    def _warm_cache(self, tab_names: list[str]):
        now = time.time()
        to_fetch = [t for t in tab_names if t not in self._sheets_cache or (now - self._cache_times.get(t, 0)) >= self.CACHE_TTL]
        if not to_fetch:
            return
        try:
            spreadsheet = self._get_spreadsheet()
            ranges = [f"'{t}'" for t in to_fetch]
            resp = spreadsheet.values_batch_get(ranges)
            for tab_name, item in zip(to_fetch, resp.get("valueRanges", [])):
                values = item.get("values", [])
                if not values:
                    continue
                headers = [str(h).strip() for h in values[0]]
                rows = []
                for row in values[1:]:
                    if all(v == "" for v in row):
                        continue
                    rows.append({h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)})
                if rows:
                    self._sheets_cache[tab_name] = rows
                    self._cache_times[tab_name] = now
        except Exception:
            pass

    def _read_all(self, tab_name: str) -> list[dict]:
        now = time.time()
        if tab_name in self._sheets_cache:
            if (now - self._cache_times.get(tab_name, 0)) < self.CACHE_TTL:
                return self._sheets_cache[tab_name]
            del self._sheets_cache[tab_name]
            self._cache_times.pop(tab_name, None)
        sheet = self._get_sheet(tab_name)
        rows = sheet.get_all_records()
        self._sheets_cache[tab_name] = rows
        self._cache_times[tab_name] = now
        return rows

    def _find_row_index(self, tab_name: str, record_id: str) -> int | None:
        rows = self._read_all(tab_name)
        for i, row in enumerate(rows):
            if str(row.get("id", "")).strip() == record_id:
                return i
        return None

    def _invalidate(self, tab_name: str):
        self._sheets_cache.pop(tab_name, None)
        self._cache_times.pop(tab_name, None)

    def _write_row(self, tab_name: str, row_num: int, data: dict):
        sheet = self._get_sheet(tab_name)
        headers = SHEET_TABS.get(tab_name, [])
        values = [str(data.get(h, "")) for h in headers]
        sheet.update(f"A{row_num}", [values])
        self._invalidate(tab_name)

    def _append_row(self, tab_name: str, data: dict):
        sheet = self._get_sheet(tab_name)
        headers = SHEET_TABS.get(tab_name, [])
        values = [str(data.get(h, "")) for h in headers]
        sheet.append_row(values, value_input_option="USER_ENTERED")
        self._invalidate(tab_name)

    def _delete_row(self, tab_name: str, row_num: int):
        sheet = self._get_sheet(tab_name)
        sheet.delete_rows(row_num + 2)  # gspread is 1-indexed, +1 for header
        self._invalidate(tab_name)

    def _row_to_dict(self, tab_name: str, row: dict) -> dict:
        headers = SHEET_TABS.get(tab_name, [])
        return {h: row.get(h, "") for h in headers}

    # ===================== ACCOUNTS =====================

    def _row_to_account(self, row: dict) -> Account:
        sub_accounts = []
        raw_subs = row.get("sub_accounts", "")
        if raw_subs and isinstance(raw_subs, str):
            try:
                sub_accounts = [SubAccount(**s) for s in json.loads(raw_subs)]
            except (json.JSONDecodeError, TypeError):
                sub_accounts = []
        elif isinstance(raw_subs, list):
            sub_accounts = [SubAccount(**s) for s in raw_subs]

        return Account(
            id=str(row.get("id", "")),
            name=str(row.get("name", "")),
            type=str(row.get("type", "")),
            currency=str(row.get("currency", "")),
            bank=str(row.get("bank", "")),
            account_number=str(row.get("account_number", "")),
            initial_balance=_parse_float(row.get("initial_balance")),
            goal_amount=_parse_float(row.get("goal_amount")),
            sub_accounts=sub_accounts,
            dividend_type=str(row.get("dividend_type", "")),
            maturity_date=str(row.get("maturity_date", "")),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def get_accounts(self) -> list[Account]:
        rows = self._read_all("accounts")
        return [self._row_to_account(r) for r in rows]

    def create_account(self, data: AccountCreate) -> Account:
        acc = Account(id=_uid(), **data.model_dump())
        row = {
            "id": acc.id, "name": acc.name, "type": acc.type,
            "currency": acc.currency, "bank": acc.bank,
            "account_number": acc.account_number,
            "initial_balance": acc.initial_balance,
            "goal_amount": acc.goal_amount,
            "sub_accounts": json.dumps([s.model_dump() for s in acc.sub_accounts]),
            "dividend_type": acc.dividend_type,
            "maturity_date": acc.maturity_date,
            "created_at": str(acc.created_at),
        }
        self._append_row("accounts", row)
        return acc

    def update_account(self, account_id: str, data: AccountCreate) -> Account:
        rows = self._read_all("accounts")
        idx = self._find_row_index("accounts", account_id)
        if idx is None:
            raise KeyError("Account not found")
        old = rows[idx]
        acc = Account(
            id=account_id, **data.model_dump(),
            goal_amount=_parse_float(old.get("goal_amount")),
            created_at=_parse_datetime(old.get("created_at")),
        )
        row = {
            "id": acc.id, "name": acc.name, "type": acc.type,
            "currency": acc.currency, "bank": acc.bank,
            "account_number": acc.account_number,
            "initial_balance": acc.initial_balance,
            "goal_amount": acc.goal_amount,
            "sub_accounts": json.dumps([s.model_dump() for s in acc.sub_accounts]),
            "dividend_type": acc.dividend_type,
            "maturity_date": acc.maturity_date,
            "created_at": str(acc.created_at),
        }
        self._write_row("accounts", idx + 2, row)
        return acc

    def delete_account(self, account_id: str) -> None:
        idx = self._find_row_index("accounts", account_id)
        if idx is None:
            raise KeyError("Account not found")
        self._delete_row("accounts", idx)

    def update_account_goal(self, account_id: str, goal_amount: float) -> Account:
        rows = self._read_all("accounts")
        idx = self._find_row_index("accounts", account_id)
        if idx is None:
            raise KeyError("Account not found")
        row = rows[idx]
        row["goal_amount"] = str(goal_amount)
        self._write_row("accounts", idx + 2, self._row_to_dict("accounts", row))
        return self._row_to_account(row)

    # ===================== TRANSACTIONS =====================

    def _row_to_transaction(self, row: dict) -> Transaction:
        return Transaction(
            id=str(row.get("id", "")),
            date=_parse_date(row.get("date")),
            account_id=str(row.get("account_id", "")),
            type=str(row.get("type", "")),
            amount=_parse_float(row.get("amount"), 0),
            currency=str(row.get("currency", "")),
            category=str(row.get("category", "")),
            description=str(row.get("description", "")),
            transfer_pair_id=row.get("transfer_pair_id") or None,
            sub_account_id=row.get("sub_account_id") or None,
            created_at=_parse_datetime(row.get("created_at")),
        )

    def get_transactions(self, account_id=None, type=None, group=None,
                         category=None, start_date=None, end_date=None,
                         currency=None) -> list[Transaction]:
        tabs = ["transactions"]
        if currency:
            tabs.append("accounts")
        if group:
            tabs.append("categories")
        self._warm_cache(tabs)
        result = [self._row_to_transaction(r) for r in self._read_all("transactions")]
        if currency:
            acc_ids = {a.id for a in self.get_accounts() if a.currency == currency}
            result = [t for t in result if t.account_id in acc_ids]
        if account_id:
            result = [t for t in result if t.account_id == account_id]
        if type:
            result = [t for t in result if t.type == type]
        if group:
            cats = {c.name for c in self.get_categories() if c.group == group}
            result = [t for t in result if t.category in cats]
        if category:
            result = [t for t in result if t.category == category]
        if start_date:
            result = [t for t in result if str(t.date) >= start_date]
        if end_date:
            result = [t for t in result if str(t.date) <= end_date]
        result.sort(key=lambda t: t.date, reverse=True)
        return result

    def create_transaction(self, data: TransactionCreate) -> Transaction:
        t = Transaction(id=_uid(), **data.model_dump())
        row = {
            "id": t.id, "date": str(t.date), "account_id": t.account_id,
            "type": t.type, "amount": t.amount, "currency": t.currency,
            "category": t.category, "description": t.description,
            "transfer_pair_id": t.transfer_pair_id or "",
            "sub_account_id": t.sub_account_id or "",
            "created_at": str(t.created_at),
        }
        self._append_row("transactions", row)
        return t

    def update_transaction(self, transaction_id: str, data: TransactionCreate) -> Transaction:
        idx = self._find_row_index("transactions", transaction_id)
        if idx is None:
            raise KeyError("Transaction not found")
        rows = self._read_all("transactions")
        old = rows[idx]
        t = Transaction(id=transaction_id, **data.model_dump(),
                        created_at=_parse_datetime(old.get("created_at")))
        row = {
            "id": t.id, "date": str(t.date), "account_id": t.account_id,
            "type": t.type, "amount": t.amount, "currency": t.currency,
            "category": t.category, "description": t.description,
            "transfer_pair_id": t.transfer_pair_id or "",
            "sub_account_id": t.sub_account_id or "",
            "created_at": str(t.created_at),
        }
        self._write_row("transactions", idx + 2, row)
        return t

    def delete_transaction(self, transaction_id: str) -> None:
        idx = self._find_row_index("transactions", transaction_id)
        if idx is None:
            raise KeyError("Transaction not found")
        self._delete_row("transactions", idx)

    # ===================== CATEGORIES =====================

    def _row_to_category(self, row: dict) -> Category:
        return Category(
            id=str(row.get("id", "")),
            name=str(row.get("name", "")),
            type=str(row.get("type", "")),
            group=str(row.get("group", "")),
            budget_amount=_parse_float(row.get("budget_amount")),
        )

    def get_categories(self) -> list[Category]:
        self._seed_categories_if_empty()
        return [self._row_to_category(r) for r in self._read_all("categories")]

    def create_category(self, data: CategoryCreate) -> Category:
        c = Category(id=_uid(), **data.model_dump())
        row = {"id": c.id, "name": c.name, "type": c.type, "group": c.group,
               "budget_amount": c.budget_amount}
        self._append_row("categories", row)
        return c

    def update_category(self, category_id: str, data: CategoryCreate) -> Category:
        idx = self._find_row_index("categories", category_id)
        if idx is None:
            raise KeyError("Category not found")
        c = Category(id=category_id, **data.model_dump())
        row = {"id": c.id, "name": c.name, "type": c.type, "group": c.group,
               "budget_amount": c.budget_amount}
        self._write_row("categories", idx + 2, row)
        return c

    def delete_category(self, category_id: str) -> None:
        idx = self._find_row_index("categories", category_id)
        if idx is None:
            raise KeyError("Category not found")
        self._delete_row("categories", idx)

    def update_category_budget(self, category_id: str, budget_amount: float) -> Category:
        idx = self._find_row_index("categories", category_id)
        if idx is None:
            raise KeyError("Category not found")
        rows = self._read_all("categories")
        row = rows[idx]
        row["budget_amount"] = str(budget_amount)
        self._write_row("categories", idx + 2, self._row_to_dict("categories", row))
        return self._row_to_category(row)

    def bulk_update_category_budgets(self, updates: dict[str, float]) -> list[Category]:
        rows = self._read_all("categories")
        sheet = self._get_sheet("categories")
        headers = SHEET_TABS["categories"]
        batch_data = []
        for i, row in enumerate(rows):
            name = str(row.get("name", ""))
            if name in updates:
                row["budget_amount"] = str(updates[name])
                values = [str(row.get(h, "")) for h in headers]
                batch_data.append({"range": f"A{i + 2}", "values": [values]})
        if batch_data:
            sheet.batch_update(batch_data, value_input_option="USER_ENTERED")
            self._invalidate("categories")
        return [self._row_to_category(r) for r in rows]

    # ===================== BUDGETS =====================

    def _row_to_budget(self, row: dict) -> Budget:
        return Budget(
            id=str(row.get("id", "")),
            month=str(row.get("month", "")),
            total_budget=_parse_float(row.get("total_budget")),
            currency=str(row.get("currency", "PHP")),
        )

    def get_budget(self, month: str, currency: str | None = None) -> Budget | None:
        for row in self._read_all("budgets"):
            if str(row.get("month", "")).strip() == month:
                if currency and str(row.get("currency", "")).strip() != currency:
                    continue
                return self._row_to_budget(row)
        return None

    def set_budget(self, month: str, data: BudgetSet) -> Budget:
        idx = None
        rows = self._read_all("budgets")
        for i, row in enumerate(rows):
            if str(row.get("month", "")).strip() == month and str(row.get("currency", "")).strip() == data.currency:
                idx = i
                break

        if idx is not None:
            b = Budget(id=str(rows[idx].get("id", "")), month=month,
                       total_budget=data.total_budget, currency=data.currency)
        else:
            b = Budget(id=_uid(), month=month, total_budget=data.total_budget,
                       currency=data.currency)

        row = {"id": b.id, "month": b.month, "total_budget": b.total_budget,
               "currency": b.currency}
        if idx is not None:
            self._write_row("budgets", idx + 2, row)
        else:
            self._append_row("budgets", row)
        return b

    def get_budget_summary(self, month: str, currency: str | None = None) -> BudgetSummary:
        self._warm_cache(["accounts", "categories", "transactions"])
        year, mon = int(month.split("-")[0]), int(month.split("-")[1])
        start = date(year, mon, 1)
        if mon == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, mon + 1, 1)

        if currency:
            currency_account_ids = {a.id for a in self.get_accounts() if a.currency == currency}
        else:
            currency_account_ids = None

        exp_cats = [c for c in self.get_categories() if c.type == "expense"]
        cat_spent = {c.name: 0.0 for c in exp_cats}

        for t in self.get_transactions():
            if t.type == "expense" and start <= t.date < end:
                if currency_account_ids is not None and t.account_id not in currency_account_ids:
                    continue
                cat_spent[t.category] = cat_spent.get(t.category, 0) + t.amount

        all_overrides = self._load_monthly_budgets().get(month, {})
        overrides = {k: v for k, v in all_overrides.items() if v.get("currency", "PHP") == (currency or "PHP")}

        template_key = f"template-{currency or 'PHP'}"
        template_all = self._load_monthly_budgets().get(template_key, {})
        template_filtered = {k: v for k, v in template_all.items() if v.get("currency", "PHP") == (currency or "PHP")}
        merged = {**template_filtered, **overrides}

        categories = []
        for c in exp_cats:
            if c.name in merged:
                budget_val = merged[c.name]["budget"]
            else:
                budget_val = c.budget_amount

            # Show category if it has a budget > 0, use view currency for display
            if budget_val > 0:
                categories.append(CategoryBudgetSummary(
                    name=c.name, group=c.group, budget=round(budget_val, 2),
                    currency=currency or "PHP", spent=round(cat_spent.get(c.name, 0), 2),
                ))

        total_budget = sum(c.budget for c in categories)
        total_spent = sum(c.spent for c in categories)

        return BudgetSummary(
            month=month, total_budget=round(total_budget, 2),
            total_spent=round(total_spent, 2), categories=categories,
        )

    def _load_monthly_budgets(self) -> dict:
        rows = self._read_all("monthly_budgets")
        result: dict[str, dict] = {}
        for row in rows:
            month = str(row.get("month", "")).strip()
            category = str(row.get("category", "")).strip()
            if not month or not category:
                continue
            if month not in result:
                result[month] = {}
            result[month][category] = {
                "budget": _parse_float(row.get("budget")),
                "currency": str(row.get("currency", "PHP")),
            }
        return result

    def _save_monthly_budget(self, month: str, category: str, budget: float, currency: str = "PHP"):
        rows = self._read_all("monthly_budgets")
        for i, row in enumerate(rows):
            if str(row.get("month", "")).strip() == month and str(row.get("category", "")).strip() == category and str(row.get("currency", "")).strip() == currency:
                self._write_row("monthly_budgets", i + 2, {"month": month, "category": category, "budget": str(budget), "currency": currency})
                return
        self._append_row("monthly_budgets", {"month": month, "category": category, "budget": str(budget), "currency": currency})

    def _delete_monthly_budgets_for_month(self, month: str, currency: str | None = None):
        rows = self._read_all("monthly_budgets")
        indices_to_delete = []
        for i, row in enumerate(rows):
            if str(row.get("month", "")).strip() == month:
                if currency and str(row.get("currency", "PHP")) != currency:
                    continue
                indices_to_delete.append(i)
        for idx in sorted(indices_to_delete, reverse=True):
            self._delete_row("monthly_budgets", idx)

    def get_monthly_budgets(self, month: str, currency: str | None = None) -> dict:
        all_mb = self._load_monthly_budgets()
        overrides = all_mb.get(month, {})
        if currency:
            return {k: v for k, v in overrides.items() if v.get("currency", "PHP") == currency}
        return overrides

    def set_monthly_budget(self, month: str, category: str, budget: float, currency: str = "PHP"):
        self._save_monthly_budget(month, category, budget, currency)

    def bulk_set_monthly_budget(self, month: str, overrides: list[dict], currency: str = "PHP"):
        rows = self._read_all("monthly_budgets")
        headers = SHEET_TABS["monthly_budgets"]
        update_map = {ov["category"]: ov["budget"] for ov in overrides}

        existing_indices = {}
        for i, row in enumerate(rows):
            if (str(row.get("month", "")).strip() == month
                    and str(row.get("currency", "")).strip() == currency):
                cat = str(row.get("category", "")).strip()
                if cat in update_map:
                    existing_indices[cat] = i

        batch_data = []
        new_rows = []
        for cat, budget in update_map.items():
            if cat in existing_indices:
                idx = existing_indices[cat]
                row_data = {"month": month, "category": cat, "budget": str(budget), "currency": currency}
                values = [str(row_data.get(h, "")) for h in headers]
                batch_data.append({"range": f"A{idx + 2}", "values": [values]})
            else:
                new_rows.append({"month": month, "category": cat, "budget": str(budget), "currency": currency})

        sheet = self._get_sheet("monthly_budgets")
        if batch_data:
            sheet.batch_update(batch_data, value_input_option="USER_ENTERED")
        for nr in new_rows:
            values = [str(nr.get(h, "")) for h in headers]
            sheet.append_row(values, value_input_option="USER_ENTERED")
        self._invalidate("monthly_budgets")

    def clear_monthly_budgets(self, month: str, currency: str | None = None):
        self._delete_monthly_budgets_for_month(month, currency)

    # ===================== BALANCES / SUMMARY =====================

    def get_balances(self, currency: str | None = None) -> list[Balance]:
        self._warm_cache(["accounts", "transactions"])
        accounts = self.get_accounts()
        transactions = self.get_transactions()

        balances = {}
        for acc in accounts:
            balances[acc.id] = acc.initial_balance
        for t in transactions:
            if t.account_id in balances:
                if t.type == "income":
                    balances[t.account_id] += t.amount
                elif t.type == "expense":
                    balances[t.account_id] -= t.amount

        result = []
        for acc in accounts:
            if currency and acc.currency != currency:
                continue
            bal = balances.get(acc.id, acc.initial_balance)
            result.append(Balance(
                account_id=acc.id, account_name=acc.name,
                currency=acc.currency, balance=round(bal, 2),
                balance_display=round(bal, 2),
            ))
        return result

    def get_annual_summary(self, year: int, currency: str | None = None) -> AnnualSummary:
        self._warm_cache(["accounts", "transactions"])
        all_txns = [t for t in self.get_transactions() if t.date.year == year]
        if currency:
            currency_account_ids = {a.id for a in self.get_accounts() if a.currency == currency}
            all_txns = [t for t in all_txns if t.account_id in currency_account_ids]

        cur = currency or "USD"
        total_income = sum(t.amount for t in all_txns if t.type == "income")
        total_expense = sum(t.amount for t in all_txns if t.type == "expense")

        accounts_map = {a.id: a for a in self.get_accounts()}
        by_account = {}
        for t in all_txns:
            if t.account_id not in by_account:
                acc = accounts_map.get(t.account_id)
                by_account[t.account_id] = AccountBalance(
                    account_id=t.account_id,
                    account_name=acc.name if acc else "Unknown",
                    currency=cur, balance=0,
                )
            if t.type == "income":
                by_account[t.account_id].balance += t.amount
            else:
                by_account[t.account_id].balance -= t.amount

        by_category = {}
        for t in all_txns:
            if t.type == "expense":
                if t.category not in by_category:
                    by_category[t.category] = CategorySummary(
                        category=t.category, total=0, currency=cur)
                by_category[t.category].total += t.amount

        monthly = {}
        for t in all_txns:
            m = f"{t.date.year}-{t.date.month:02d}"
            if m not in monthly:
                monthly[m] = MonthlyTotal(month=m, income=0, expense=0, currency=cur)
            if t.type == "income":
                monthly[m].income += t.amount
            else:
                monthly[m].expense += t.amount

        return AnnualSummary(
            year=year, total_income=round(total_income, 2),
            total_expense=round(total_expense, 2), currency=cur,
            by_account=list(by_account.values()),
            by_category=sorted(by_category.values(), key=lambda x: x.total, reverse=True),
            monthly=sorted(monthly.values(), key=lambda x: x.month),
        )

    _rates_cache = None
    _rates_cache_time = None

    def get_rates(self) -> RatesResponse:
        import httpx
        from datetime import timedelta

        if SheetsBackend._rates_cache and SheetsBackend._rates_cache_time:
            if datetime.now() - SheetsBackend._rates_cache_time < timedelta(hours=12):
                return SheetsBackend._rates_cache

        apis = [
            'https://open.er-api.com/v6/latest/USD',
            'https://api.exchangerate-api.com/v4/latest/USD',
        ]

        with httpx.Client(timeout=10) as client:
            for api_url in apis:
                try:
                    res = client.get(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                    data = res.json()
                    rates = data.get('rates', {})
                    php_rate = rates.get("PHP")
                    if php_rate:
                        result = RatesResponse(
                            base="USD",
                            rates={
                                "USD": 1.0, "PHP": php_rate,
                                "EUR": rates.get("EUR", 0.92),
                                "GBP": rates.get("GBP", 0.79),
                                "JPY": rates.get("JPY", 149.5),
                            }
                        )
                        SheetsBackend._rates_cache = result
                        SheetsBackend._rates_cache_time = datetime.now()
                        return result
                except Exception:
                    continue

        if SheetsBackend._rates_cache:
            return SheetsBackend._rates_cache
        return RatesResponse(base="USD", rates={"USD": 1.0, "PHP": 56.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5})

    def get_monthly_category_breakdown(self, year: int, currency: str | None = None) -> list[MonthlyCategoryRow]:
        self._warm_cache(["accounts", "transactions", "categories"])
        all_txns = [t for t in self.get_transactions() if t.date.year == year and t.type == "expense"]
        if currency:
            currency_account_ids = {a.id for a in self.get_accounts() if a.currency == currency}
            all_txns = [t for t in all_txns if t.account_id in currency_account_ids]

        categories_map = {c.name: c for c in self.get_categories()}
        cats = {}
        for t in all_txns:
            if t.category not in cats:
                cat_obj = categories_map.get(t.category)
                group = cat_obj.group if cat_obj else "Misc"
                cats[t.category] = {"group": group, "data": {}}
            m = f"{t.date.month:02d}"
            cats[t.category]["data"][m] = cats[t.category]["data"].get(m, 0) + t.amount

        return [MonthlyCategoryRow(category=c, group=v["group"], monthly=v["data"])
                for c, v in sorted(cats.items())]

    # ===================== RECURRING =====================

    def _row_to_recurring(self, row: dict) -> RecurringRule:
        return RecurringRule(
            id=str(row.get("id", "")),
            name=str(row.get("name", "")),
            account_id=str(row.get("account_id", "")),
            category=str(row.get("category", "")),
            amount=_parse_float(row.get("amount")),
            currency=str(row.get("currency", "")),
            frequency=str(row.get("frequency", "")),
            day_of_month=_parse_int(row.get("day_of_month"), 1),
            start_date=str(row.get("start_date", "")),
            end_date=str(row.get("end_date", "")),
            active=_parse_bool(row.get("active", True)),
            last_generated=str(row.get("last_generated", "")),
            next_date=str(row.get("next_date", "")),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def _recurring_to_row(self, r: RecurringRule) -> dict:
        return {
            "id": r.id, "name": r.name, "account_id": r.account_id,
            "category": r.category, "amount": r.amount, "currency": r.currency,
            "frequency": r.frequency, "day_of_month": r.day_of_month,
            "start_date": r.start_date, "end_date": r.end_date,
            "active": str(r.active), "last_generated": r.last_generated,
            "next_date": r.next_date, "created_at": str(r.created_at),
        }

    def get_recurring_rules(self, currency: str | None = None) -> list[RecurringRule]:
        rules = [self._row_to_recurring(r) for r in self._read_all("recurring_rules")]
        if currency:
            rules = [r for r in rules if r.currency == currency]
        return rules

    def create_recurring_rule(self, data: RecurringRuleCreate) -> RecurringRule:
        r = RecurringRule(id=_uid(), **data.model_dump(), next_date=data.start_date)
        self._append_row("recurring_rules", self._recurring_to_row(r))
        return r

    def update_recurring_rule(self, rule_id: str, data: RecurringRuleCreate) -> RecurringRule:
        idx = self._find_row_index("recurring_rules", rule_id)
        if idx is None:
            raise KeyError("Rule not found")
        rows = self._read_all("recurring_rules")
        old = rows[idx]
        r = RecurringRule(id=rule_id, **data.model_dump(),
                          active=_parse_bool(old.get("active", True)),
                          last_generated=str(old.get("last_generated", "")),
                          next_date=str(old.get("next_date", "")),
                          created_at=_parse_datetime(old.get("created_at")))
        self._write_row("recurring_rules", idx + 2, self._recurring_to_row(r))
        return r

    def delete_recurring_rule(self, rule_id: str) -> None:
        idx = self._find_row_index("recurring_rules", rule_id)
        if idx is None:
            raise KeyError("Rule not found")
        self._delete_row("recurring_rules", idx)

    def toggle_recurring_rule(self, rule_id: str, active: bool) -> RecurringRule:
        idx = self._find_row_index("recurring_rules", rule_id)
        if idx is None:
            raise KeyError("Rule not found")
        rows = self._read_all("recurring_rules")
        rows[idx]["active"] = str(active)
        self._write_row("recurring_rules", idx + 2,
                        self._row_to_dict("recurring_rules", rows[idx]))
        return self._row_to_recurring(rows[idx])

    def _advance_date(self, date_str: str, frequency: str) -> str:
        import calendar
        y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
        if frequency == "monthly":
            m += 1
            if m > 12:
                m = 1
                y += 1
            last_day = calendar.monthrange(y, m)[1]
            d = min(d, last_day)
        else:
            y += 1
        return f"{y}-{m:02d}-{d:02d}"

    def run_recurring(self, currency: str | None = None) -> RecurringRunResult:
        today = date.today()
        generated = 0

        rules = self.get_recurring_rules(currency)
        rules_to_update: list[tuple[int, dict]] = []

        for r in rules:
            if not r.active:
                continue
            if currency and r.currency != currency:
                continue
            if not r.next_date:
                continue
            next_d = date.fromisoformat(r.next_date)
            if next_d > today:
                continue
            if r.end_date and date.fromisoformat(r.end_date) < today:
                continue

            self.create_transaction(TransactionCreate(
                date=next_d, account_id=r.account_id, type="expense",
                amount=r.amount, currency=r.currency, category=r.category,
                description=f"[Recurring] {r.name}",
            ))

            idx = self._find_row_index("recurring_rules", r.id)
            if idx is not None:
                rows = self._read_all("recurring_rules")
                row_data = self._row_to_dict("recurring_rules", rows[idx])
                row_data["last_generated"] = r.next_date
                row_data["next_date"] = self._advance_date(r.next_date, r.frequency)
                rules_to_update.append((idx, row_data))
            generated += 1

        # Batch-write all rule updates in reverse order to avoid index shifts
        for idx, row_data in sorted(rules_to_update, key=lambda x: x[0], reverse=True):
            self._write_row("recurring_rules", idx + 2, row_data)

        rules = self.get_recurring_rules(currency)
        return RecurringRunResult(generated=generated, rules=rules)

    # ===================== TRANSFERS =====================

    def _row_to_transfer(self, row: dict) -> Transfer:
        return Transfer(
            id=str(row.get("id", "")),
            from_account_id=str(row.get("from_account_id", "")),
            to_account_id=str(row.get("to_account_id", "")),
            amount=_parse_float(row.get("amount")),
            currency=str(row.get("currency", "")),
            fee=_parse_float(row.get("fee")),
            date=_parse_date(row.get("date")),
            note=str(row.get("note", "")),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def get_transfers(self, currency: str | None = None) -> list[Transfer]:
        transfers = [self._row_to_transfer(r) for r in self._read_all("transfers")]
        if currency:
            transfers = [t for t in transfers if t.currency == currency]
        return transfers

    def create_transfer(self, data: TransferCreate) -> Transfer:
        accounts_map = {a.id: a for a in self.get_accounts()}
        from_acc = accounts_map.get(data.from_account_id)
        to_acc = accounts_map.get(data.to_account_id)
        if not from_acc or not to_acc:
            raise ValueError("Account not found")
        if from_acc.currency != to_acc.currency:
            raise ValueError("Cannot transfer between different currencies")

        bal = from_acc.initial_balance
        for t in self.get_transactions():
            if t.account_id == data.from_account_id:
                if t.type == "income":
                    bal += t.amount
                elif t.type == "expense":
                    bal -= t.amount
        if bal < data.amount + data.fee:
            raise ValueError(f"Insufficient balance. Available: {bal:.2f}")

        tx_date = date.fromisoformat(data.date) if isinstance(data.date, str) else data.date
        t = Transfer(
            id=_uid(), from_account_id=data.from_account_id,
            to_account_id=data.to_account_id, amount=data.amount,
            currency=data.currency, fee=data.fee, date=tx_date, note=data.note,
        )
        row = {
            "id": t.id, "from_account_id": t.from_account_id,
            "to_account_id": t.to_account_id, "amount": t.amount,
            "currency": t.currency, "fee": t.fee, "date": str(t.date),
            "note": t.note, "created_at": str(t.created_at),
        }
        self._append_row("transfers", row)

        exp_id = _uid()
        inc_id = _uid()
        self.create_transaction(TransactionCreate(
            date=tx_date, account_id=data.from_account_id, type="expense",
            amount=data.amount + data.fee, currency=from_acc.currency,
            category="Transfer",
            description=f"Transfer → {to_acc.name}" + (f" (fee: {data.fee})" if data.fee else ""),
            transfer_pair_id=inc_id,
        ))
        self.create_transaction(TransactionCreate(
            date=tx_date, account_id=data.to_account_id, type="income",
            amount=data.amount, currency=to_acc.currency,
            category="Transfer",
            description=f"Transfer ← {from_acc.name}",
            transfer_pair_id=exp_id,
        ))

        return t

    def delete_transfer(self, transfer_id: str) -> None:
        idx = self._find_row_index("transfers", transfer_id)
        if idx is None:
            raise KeyError("Transfer not found")

        rows = self._read_all("transfers")
        transfer_row = rows[idx]
        from_account = transfer_row.get("from_account_id", "")
        to_account = transfer_row.get("to_account_id", "")

        # Find transaction indices in one pass, delete in reverse order
        txn_rows = self._read_all("transactions")
        txn_indices: list[int] = []
        for i, txn_row in enumerate(txn_rows):
            pair_id = str(txn_row.get("transfer_pair_id", ""))
            txn_account = txn_row.get("account_id", "")
            txn_type = txn_row.get("type", "")
            cat = txn_row.get("category", "")
            if pair_id and cat == "Transfer":
                if (txn_account == from_account and txn_type == "expense") or \
                   (txn_account == to_account and txn_type == "income"):
                    txn_indices.append(i)

        self._delete_row("transfers", idx)
        for txn_idx in sorted(txn_indices, reverse=True):
            self._delete_row("transactions", txn_idx)
