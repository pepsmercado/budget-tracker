import uuid
import json
import os
import time
import gspread
from datetime import date, datetime
from google.oauth2.service_account import Credentials

from services.base import BackendService
from services.seed_data import CATEGORIES_DATA
from services.helpers import advance_date, fetch_rates
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate,
    Balance, AccountBalance, CategorySummary, MonthlyTotal,
    AnnualSummary, RatesResponse, SubAccount, MonthlyCategoryRow,
    BudgetSummary, CategoryBudgetSummary,
    RecurringRule, RecurringRuleCreate, RecurringRunResult,
    Transfer, TransferCreate,
    SavingsPlanner, SavingsReserve, SavingsGoal, SavingsActivity,
    SavingsReserveCreate, SavingsReserveUpdate, SavingsGoalCreate,
    SavingsGoalUpdate, SavingsMove, SavingsAllocate,
)
from services.savings_planner import reconcile, replenish_floor, move_money, unallocated, completed_goals


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
    "recurring_rules": ["id", "name", "account_id", "category", "amount",
                        "currency", "frequency", "day_of_month", "start_date",
                        "end_date", "active", "last_generated", "next_date",
                        "created_at"],
    "transfers": ["id", "from_account_id", "to_account_id", "amount",
                  "currency", "fee", "date", "note", "created_at"],
    "monthly_budgets": ["month", "category", "budget", "currency"],
    "savings_planner": ["id", "currency", "linked_account_id", "created_at"],
    "savings_reserves": ["id", "planner_id", "name", "icon", "allocated",
                         "floor", "position", "created_at"],
    "savings_goals": ["id", "planner_id", "name", "icon", "target", "allocated",
                      "position", "created_at"],
    "savings_activity": ["id", "planner_id", "type", "amount", "description",
                         "created_at"],
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
        print(f"WARNING: failed to parse date '{val}', using today()")
        return date.today()


def _parse_datetime(val):
    if not val:
        return datetime.now()
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).strip())
    except ValueError:
        print(f"WARNING: failed to parse datetime '{val}', using now()")
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
        existing = {str(r.get("name", "")).strip() for r in rows}
        categories_data = CATEGORIES_DATA
        missing = [(name, ctype, group, budget) for name, ctype, group, budget in categories_data
                   if name not in existing]
        for name, ctype, group, budget in missing:
            c = Category(id=_uid(), name=name, type=ctype, group=group,
                         budget_amount=budget)
            row = {"id": c.id, "name": c.name, "type": c.type, "group": c.group,
                   "budget_amount": c.budget_amount}
            self._append_row("categories", row)
            existing.add(name)

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
        except Exception as e:
            print(f"WARNING: failed to warm cache for {to_fetch}: {e}")

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
        rows = self._read_all("transactions")
        result = [(i, self._row_to_transaction(r)) for i, r in enumerate(rows)]
        if currency:
            acc_ids = {a.id for a in self.get_accounts() if a.currency == currency}
            result = [(i, t) for i, t in result if t.account_id in acc_ids]
        if account_id:
            result = [(i, t) for i, t in result if t.account_id == account_id]
        if type:
            result = [(i, t) for i, t in result if t.type == type]
        if group:
            cats = {c.name for c in self.get_categories() if c.group == group}
            result = [(i, t) for i, t in result if t.category in cats]
        if category:
            result = [(i, t) for i, t in result if t.category == category]
        if start_date:
            result = [(i, t) for i, t in result if str(t.date) >= start_date]
        if end_date:
            result = [(i, t) for i, t in result if str(t.date) <= end_date]
        result.sort(key=lambda x: (str(x[1].date), x[0]), reverse=True)
        return [t for _, t in result]

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
        self._reconcile_planner_for_account(t.account_id)
        return t

    def update_transaction(self, transaction_id: str, data: TransactionCreate) -> Transaction:
        idx = self._find_row_index("transactions", transaction_id)
        if idx is None:
            raise KeyError("Transaction not found")
        rows = self._read_all("transactions")
        old = rows[idx]
        old_account = str(old.get("account_id", ""))
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
        for account_id in {old_account, t.account_id}:
            self._reconcile_planner_for_account(account_id)
        return t

    def delete_transaction(self, transaction_id: str) -> None:
        idx = self._find_row_index("transactions", transaction_id)
        if idx is None:
            raise KeyError("Transaction not found")
        rows = self._read_all("transactions")
        account_id = str(rows[idx].get("account_id", ""))
        self._delete_row("transactions", idx)
        self._reconcile_planner_for_account(account_id)

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

    # ===================== BUDGET SUMMARY =====================

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
            if t.type == "expense" and start <= t.date < end and not t.transfer_pair_id:
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
        seen = set()
        for c in exp_cats:
            if c.name in merged:
                budget_val = merged[c.name]["budget"]
            else:
                budget_val = c.budget_amount
            spent = cat_spent.get(c.name, 0)
            if budget_val > 0 or spent > 0:
                seen.add(c.name)
                categories.append(CategoryBudgetSummary(
                    name=c.name, group=c.group, budget=round(budget_val, 2),
                    currency=currency or "PHP", spent=round(spent, 2),
                ))
        for cat_name, spent in cat_spent.items():
            if spent > 0 and cat_name not in seen:
                categories.append(CategoryBudgetSummary(
                    name=cat_name, group="Misc", budget=0.0,
                    currency=currency or "PHP", spent=round(spent, 2),
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

    def get_rates(self) -> RatesResponse:
        return fetch_rates()

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
        return advance_date(date_str, frequency)

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

        tx_date = date.fromisoformat(data.date)
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
        self._reconcile_planner_for_account(from_account)
        self._reconcile_planner_for_account(to_account)

    # ===================== SAVINGS PLANNER =====================

    def _row_to_savings_planner(self, row: dict) -> SavingsPlanner:
        return SavingsPlanner(
            id=str(row.get("id", "")),
            currency=str(row.get("currency", "")),
            linked_account_id=str(row.get("linked_account_id", "")),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def _planner_to_row(self, p: SavingsPlanner) -> dict:
        return {"id": p.id, "currency": p.currency,
                "linked_account_id": p.linked_account_id,
                "created_at": str(p.created_at)}

    def _row_to_savings_reserve(self, row: dict) -> SavingsReserve:
        floor_raw = row.get("floor")
        return SavingsReserve(
            id=str(row.get("id", "")),
            planner_id=str(row.get("planner_id", "")),
            name=str(row.get("name", "")),
            icon=str(row.get("icon", "")),
            allocated=_parse_float(row.get("allocated")),
            floor=None if floor_raw in (None, "") else _parse_float(floor_raw),
            position=_parse_int(row.get("position"), 0),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def _reserve_to_row(self, r: SavingsReserve) -> dict:
        return {
            "id": r.id, "planner_id": r.planner_id, "name": r.name,
            "icon": r.icon, "allocated": r.allocated,
            "floor": "" if r.floor is None else r.floor,
            "position": r.position, "created_at": str(r.created_at),
        }

    def _row_to_savings_goal(self, row: dict) -> SavingsGoal:
        return SavingsGoal(
            id=str(row.get("id", "")),
            planner_id=str(row.get("planner_id", "")),
            name=str(row.get("name", "")),
            icon=str(row.get("icon", "")),
            target=_parse_float(row.get("target")),
            allocated=_parse_float(row.get("allocated")),
            position=_parse_int(row.get("position"), 0),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def _goal_to_row(self, g: SavingsGoal) -> dict:
        return {
            "id": g.id, "planner_id": g.planner_id, "name": g.name,
            "icon": g.icon, "target": g.target, "allocated": g.allocated,
            "position": g.position, "created_at": str(g.created_at),
        }

    def _row_to_savings_activity(self, row: dict) -> SavingsActivity:
        return SavingsActivity(
            id=str(row.get("id", "")),
            planner_id=str(row.get("planner_id", "")),
            type=str(row.get("type", "")),
            amount=_parse_float(row.get("amount")),
            description=str(row.get("description", "")),
            created_at=_parse_datetime(row.get("created_at")),
        )

    def _activity_to_row(self, a: SavingsActivity) -> dict:
        return {
            "id": a.id, "planner_id": a.planner_id, "type": a.type,
            "amount": a.amount, "description": a.description,
            "created_at": str(a.created_at),
        }

    def _get_planner(self, currency: str) -> SavingsPlanner | None:
        for row in self._read_all("savings_planner"):
            p = self._row_to_savings_planner(row)
            if p.currency == currency:
                return p
        return None

    def _get_reserves(self, planner_id: str) -> list[SavingsReserve]:
        result = [self._row_to_savings_reserve(r) for r in self._read_all("savings_reserves")
                  if str(r.get("planner_id", "")) == planner_id]
        return sorted(result, key=lambda r: r.position)

    def _get_goals(self, planner_id: str) -> list[SavingsGoal]:
        result = [self._row_to_savings_goal(g) for g in self._read_all("savings_goals")
                  if str(g.get("planner_id", "")) == planner_id]
        return sorted(result, key=lambda g: g.position)

    def _get_activity(self, planner_id: str, limit: int = 50) -> list[SavingsActivity]:
        result = [self._row_to_savings_activity(a) for a in self._read_all("savings_activity")
                  if str(a.get("planner_id", "")) == planner_id]
        result.sort(key=lambda a: a.created_at, reverse=True)
        return result[:limit]

    def _log_activity(self, planner_id: str, events: list[dict]):
        for ev in events:
            a = SavingsActivity(
                id=_uid(), planner_id=planner_id,
                type=ev.get("type", "Planner Recalculated"),
                amount=round(float(ev.get("amount", 0)), 2),
                description=ev.get("description", ""),
            )
            self._append_row("savings_activity", self._activity_to_row(a))

    def _account_balance(self, account_id: str) -> float:
        acc = next((a for a in self.get_accounts() if a.id == account_id), None)
        if acc is None:
            return 0.0
        bal = acc.initial_balance
        for t in self.get_transactions():
            if t.account_id == account_id:
                if t.type == "income":
                    bal += t.amount
                elif t.type == "expense":
                    bal -= t.amount
        return round(bal, 2)

    def _persist_buckets(self, reserves: list[SavingsReserve], goals: list[SavingsGoal]):
        for r in reserves:
            idx = self._find_row_index("savings_reserves", r.id)
            if idx is not None:
                self._write_row("savings_reserves", idx + 2, self._reserve_to_row(r))
        for g in goals:
            idx = self._find_row_index("savings_goals", g.id)
            if idx is not None:
                self._write_row("savings_goals", idx + 2, self._goal_to_row(g))

    def _reconcile_planner(self, planner: SavingsPlanner):
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        reserves, goals, events, _ = reconcile(balance, reserves, goals)
        conv_events = self._convert_completed_goals(planner, reserves, goals)
        events = events + conv_events
        if events:
            self._log_activity(planner.id, events)
            self._persist_buckets(reserves, goals)

    def _convert_completed_goals(self, planner: SavingsPlanner, reserves: list, goals: list) -> list:
        """Auto-convert fully-funded goals into floor-less reserves."""
        events = []
        for g in completed_goals(goals):
            position = max((r.position for r in reserves), default=-1) + 1
            r = SavingsReserve(
                id=_uid(), planner_id=planner.id, name=g.name, icon=g.icon,
                allocated=g.allocated, floor=None, position=position,
            )
            self._append_row("savings_reserves", self._reserve_to_row(r))
            idx = self._find_row_index("savings_goals", g.id)
            if idx is not None:
                self._delete_row("savings_goals", idx)
            events.append({
                "type": "Goal Converted",
                "amount": r.allocated,
                "description": f"Goal '{r.name}' completed and moved to Reserves",
            })
        return events

    def _reconcile_planner_for_account(self, account_id: str):
        for row in self._read_all("savings_planner"):
            p = self._row_to_savings_planner(row)
            if p.linked_account_id == account_id:
                self._reconcile_planner(p)

    def _savings_planner_state(self, currency: str, limit: int = 50) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            return {
                "planner": None, "linked_account": None, "balance": 0.0,
                "unallocated": 0.0, "reserves": [], "goals": [],
                "activity": [], "underfunded": False,
                "savings_accounts": [a for a in self.get_accounts() if a.type == "savings"],
            }
        balance = self._account_balance(planner.linked_account_id)
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        linked_account = next((a for a in self.get_accounts()
                               if a.id == planner.linked_account_id), None)
        return {
            "planner": planner,
            "linked_account": linked_account,
            "balance": balance,
            "unallocated": unallocated(balance, reserves, goals),
            "reserves": reserves,
            "goals": goals,
            "activity": self._get_activity(planner.id, limit),
            "underfunded": unallocated(balance, reserves, goals) < 0,
            "savings_accounts": [a for a in self.get_accounts() if a.type == "savings"],
        }

    def get_savings_planner(self, currency: str, limit: int = 50) -> dict:
        return self._savings_planner_state(currency, limit)

    def link_savings_planner(self, currency: str, account_id: str) -> dict:
        acc = next((a for a in self.get_accounts() if a.id == account_id), None)
        if acc is None:
            raise KeyError("Account not found")
        if acc.type != "savings":
            raise ValueError("Only savings accounts can be linked to the planner")
        if acc.currency != currency:
            raise ValueError("Account currency does not match planner currency")
        planner = self._get_planner(currency)
        if planner is None:
            planner = SavingsPlanner(id=_uid(), currency=currency)
            self._append_row("savings_planner", self._planner_to_row(planner))
        changed = planner.linked_account_id != account_id
        planner.linked_account_id = account_id
        idx = self._find_row_index("savings_planner", planner.id)
        if idx is not None:
            self._write_row("savings_planner", idx + 2, self._planner_to_row(planner))
        if changed:
            self._log_activity(planner.id, [{
                "type": "Planner Recalculated",
                "amount": 0,
                "description": f"Linked to savings account '{acc.name}'",
            }])
        self._reconcile_planner(planner)
        return self._savings_planner_state(currency)

    def create_savings_reserve(self, currency: str, data: SavingsReserveCreate) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        avail = unallocated(balance, reserves, goals)
        if data.allocated > avail + 0.005:
            raise ValueError(f"Insufficient Unallocated balance. Available: {avail:,.2f}")
        position = max((r.position for r in reserves), default=-1) + 1
        r = SavingsReserve(
            id=_uid(), planner_id=planner.id, name=data.name, icon=data.icon,
            allocated=max(0.0, data.allocated), floor=data.floor, position=position,
        )
        self._append_row("savings_reserves", self._reserve_to_row(r))
        self._log_activity(planner.id, [{
            "type": "Moved Funds" if r.allocated > 0 else "Planner Recalculated",
            "amount": r.allocated,
            "description": f"Reserve '{r.name}' created" + (f" with {r.allocated:,.2f} allocated" if r.allocated > 0 else ""),
        }])
        return self._savings_planner_state(currency)

    def update_savings_reserve(self, currency: str, reserve_id: str, data: SavingsReserveUpdate) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        rows = self._read_all("savings_reserves")
        idx = self._find_row_index("savings_reserves", reserve_id)
        if idx is None or str(rows[idx].get("planner_id", "")) != planner.id:
            raise KeyError("Reserve not found")
        r = self._row_to_savings_reserve(rows[idx])
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        fields = data.model_fields_set
        if "name" in fields:
            r.name = data.name
        if "icon" in fields:
            r.icon = data.icon
        if "allocated" in fields and data.allocated is not None:
            avail = unallocated(balance, reserves, goals) + r.allocated
            if data.allocated > avail + 0.005:
                raise ValueError(f"Insufficient Unallocated balance. Available: {avail:,.2f}")
            r.allocated = max(0.0, data.allocated)
        old_floor = r.floor
        if "floor" in fields:
            r.floor = data.floor
            if data.floor is not None and (old_floor is None or data.floor > old_floor):
                reserves, goals, events = replenish_floor(r, reserves, goals, balance)
                self._log_activity(planner.id, events)
                self._persist_buckets(reserves, goals)
        self._write_row("savings_reserves", idx + 2, self._reserve_to_row(r))
        return self._savings_planner_state(currency)

    def delete_savings_reserve(self, currency: str, reserve_id: str) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        rows = self._read_all("savings_reserves")
        idx = self._find_row_index("savings_reserves", reserve_id)
        if idx is None or str(rows[idx].get("planner_id", "")) != planner.id:
            raise KeyError("Reserve not found")
        r = self._row_to_savings_reserve(rows[idx])
        released = r.allocated
        self._delete_row("savings_reserves", idx)
        self._log_activity(planner.id, [{
            "type": "Reserve Deleted",
            "amount": released,
            "description": f"Reserve '{r.name}' deleted; {released:,.2f} released to Unallocated",
        }])
        return self._savings_planner_state(currency)

    def create_savings_goal(self, currency: str, data: SavingsGoalCreate) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        avail = unallocated(balance, reserves, goals)
        if data.allocated > avail + 0.005:
            raise ValueError(f"Insufficient Unallocated balance. Available: {avail:,.2f}")
        position = max((g.position for g in goals), default=-1) + 1
        g = SavingsGoal(
            id=_uid(), planner_id=planner.id, name=data.name, icon=data.icon,
            target=data.target, allocated=max(0.0, data.allocated), position=position,
        )
        self._append_row("savings_goals", self._goal_to_row(g))
        self._log_activity(planner.id, [{
            "type": "Moved Funds" if g.allocated > 0 else "Planner Recalculated",
            "amount": g.allocated,
            "description": f"Goal '{g.name}' created" + (f" with {g.allocated:,.2f} allocated" if g.allocated > 0 else ""),
        }])
        return self._savings_planner_state(currency)

    def update_savings_goal(self, currency: str, goal_id: str, data: SavingsGoalUpdate) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        rows = self._read_all("savings_goals")
        idx = self._find_row_index("savings_goals", goal_id)
        if idx is None or str(rows[idx].get("planner_id", "")) != planner.id:
            raise KeyError("Goal not found")
        g = self._row_to_savings_goal(rows[idx])
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        fields = data.model_fields_set
        if "name" in fields:
            g.name = data.name
        if "icon" in fields:
            g.icon = data.icon
        if "position" in fields:
            g.position = data.position
        if "target" in fields and data.target is not None:
            g.target = data.target
            if g.allocated > g.target:
                excess = round(g.allocated - g.target, 2)
                g.allocated = g.target
                self._log_activity(planner.id, [{
                    "type": "Planner Recalculated",
                    "amount": excess,
                    "description": f"Goal '{g.name}' target reduced; {excess:,.2f} released to Unallocated",
                }])
        if "allocated" in fields and data.allocated is not None:
            avail = unallocated(balance, reserves, goals) + g.allocated
            if data.allocated > avail + 0.005:
                raise ValueError(f"Insufficient Unallocated balance. Available: {avail:,.2f}")
            g.allocated = max(0.0, data.allocated)
            if g.allocated > g.target:
                excess = round(g.allocated - g.target, 2)
                g.allocated = g.target
                self._log_activity(planner.id, [{
                    "type": "Planner Recalculated",
                    "amount": excess,
                    "description": f"Goal '{g.name}' overfunded; {excess:,.2f} spilled to Unallocated",
                }])
        self._write_row("savings_goals", idx + 2, self._goal_to_row(g))
        return self._savings_planner_state(currency)

    def delete_savings_goal(self, currency: str, goal_id: str) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        rows = self._read_all("savings_goals")
        idx = self._find_row_index("savings_goals", goal_id)
        if idx is None or str(rows[idx].get("planner_id", "")) != planner.id:
            raise KeyError("Goal not found")
        g = self._row_to_savings_goal(rows[idx])
        released = g.allocated
        self._delete_row("savings_goals", idx)
        self._log_activity(planner.id, [{
            "type": "Goal Deleted",
            "amount": released,
            "description": f"Goal '{g.name}' deleted; {released:,.2f} released to Unallocated",
        }])
        return self._savings_planner_state(currency)

    def move_savings_money(self, currency: str, data: SavingsMove) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        reserves, goals, events, error = move_money(
            balance, reserves, goals, data.from_bucket, data.to_bucket, data.amount)
        if error:
            raise ValueError(error)
        self._log_activity(planner.id, events)
        self._reconcile_planner(planner)
        return self._savings_planner_state(currency)

    def allocate_savings_money(self, currency: str, data: SavingsAllocate) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._get_reserves(planner.id)
        goals = self._get_goals(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        total = round(sum(item.amount for item in data.allocations), 2)
        if round(unallocated(balance, reserves, goals), 2) < total:
            raise ValueError("Total allocation exceeds Unallocated balance")
        events = []
        for item in data.allocations:
            reserves, goals, ev, error = move_money(
                balance, reserves, goals, "unallocated", item.to_bucket, item.amount)
            if error:
                raise ValueError(error)
            events.extend(ev)
        self._log_activity(planner.id, events)
        self._reconcile_planner(planner)
        return self._savings_planner_state(currency)

    def convert_savings_goal(self, currency: str, goal_id: str) -> dict:
        planner = self._get_planner(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        rows = self._read_all("savings_goals")
        idx = self._find_row_index("savings_goals", goal_id)
        if idx is None or str(rows[idx].get("planner_id", "")) != planner.id:
            raise KeyError("Goal not found")
        g = self._row_to_savings_goal(rows[idx])
        reserves = self._get_reserves(planner.id)
        position = max((r.position for r in reserves), default=-1) + 1
        r = SavingsReserve(
            id=_uid(), planner_id=planner.id, name=g.name, icon=g.icon,
            allocated=g.allocated, floor=None, position=position,
        )
        self._append_row("savings_reserves", self._reserve_to_row(r))
        self._delete_row("savings_goals", idx)
        self._log_activity(planner.id, [{
            "type": "Goal Converted",
            "amount": r.allocated,
            "description": f"Goal '{r.name}' converted to a Reserve",
        }])
        return self._savings_planner_state(currency)
