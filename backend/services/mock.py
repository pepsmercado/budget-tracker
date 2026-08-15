import uuid
import json
import os
from datetime import date, datetime, timedelta
import random

from services.base import BackendService
from services.seed_data import CATEGORIES_DATA
from services.helpers import advance_date, fetch_rates
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate,
    Balance, AccountBalance, CategorySummary, MonthlyTotal,
    AnnualSummary, RatesResponse, SubAccount, MonthlyCategoryRow,
    RecurringRule, RecurringRuleCreate, RecurringRunResult,
    Transfer, TransferCreate,
    SavingsPlanner, SavingsReserve, SavingsGoal, SavingsActivity,
    SavingsReserveCreate, SavingsReserveUpdate, SavingsGoalCreate,
    SavingsGoalUpdate, SavingsMove, SavingsAllocate,
)
from services.savings_planner import reconcile, replenish_floor, move_money, unallocated, completed_goals

# Use /tmp on Vercel (serverless), local file otherwise
if os.environ.get("VERCEL"):
    DATA_DIR = "/tmp"
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..")

DATA_FILE = os.path.join(DATA_DIR, "data.json")
MONTHLY_BUDGETS_FILE = os.path.join(DATA_DIR, "monthly_budgets.json")


class MockBackend(BackendService):
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.transactions: dict[str, Transaction] = {}
        self.categories: dict[str, Category] = {}
        self.recurring_rules: dict[str, RecurringRule] = {}
        self.transfers: dict[str, Transfer] = {}
        self.monthly_budgets: dict[str, dict[str, dict]] = {}
        self.planners: dict[str, SavingsPlanner] = {}
        self.savings_reserves: dict[str, SavingsReserve] = {}
        self.savings_goals: dict[str, SavingsGoal] = {}
        self.savings_activity: dict[str, SavingsActivity] = {}
        self._balance_cache: dict[str, float] = {}
        if not self._load() or not self.accounts:
            self._seed()
        self._rebuild_balance_cache()

    def _uid(self) -> str:
        return uuid.uuid4().hex[:12]

    def _save(self):
        data = {
            "accounts": {k: v.model_dump() for k, v in self.accounts.items()},
            "transactions": {k: v.model_dump() for k, v in self.transactions.items()},
            "categories": {k: v.model_dump() for k, v in self.categories.items()},
            "recurring_rules": {k: v.model_dump() for k, v in self.recurring_rules.items()},
            "transfers": {k: v.model_dump() for k, v in self.transfers.items()},
            "planners": {k: v.model_dump() for k, v in self.planners.items()},
            "savings_reserves": {k: v.model_dump() for k, v in self.savings_reserves.items()},
            "savings_goals": {k: v.model_dump() for k, v in self.savings_goals.items()},
            "savings_activity": {k: v.model_dump() for k, v in self.savings_activity.items()},
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, default=str)
        with open(MONTHLY_BUDGETS_FILE, "w") as f:
            json.dump(self.monthly_budgets, f, default=str)

    def _load(self) -> bool:
        if not os.path.exists(DATA_FILE):
            return False
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
            for k, v in data.get("accounts", {}).items():
                self.accounts[k] = Account(**v)
            tx_time = None
            for k, v in data.get("transactions", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                if "date" in v and isinstance(v["date"], str):
                    v["date"] = date.fromisoformat(v["date"])
                if tx_time is None:
                    tx_time = v.get("created_at") or datetime.now()
                else:
                    tx_time += timedelta(microseconds=1)
                v["created_at"] = tx_time
                self.transactions[k] = Transaction(**v)
            for k, v in data.get("categories", {}).items():
                self.categories[k] = Category(**v)
            for k, v in data.get("recurring_rules", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                self.recurring_rules[k] = RecurringRule(**v)
            for k, v in data.get("transfers", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                if "date" in v and isinstance(v["date"], str):
                    v["date"] = date.fromisoformat(v["date"])
                self.transfers[k] = Transfer(**v)
            for k, v in data.get("planners", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                self.planners[k] = SavingsPlanner(**v)
            for k, v in data.get("savings_reserves", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                self.savings_reserves[k] = SavingsReserve(**v)
            for k, v in data.get("savings_goals", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                self.savings_goals[k] = SavingsGoal(**v)
            act_time = None
            for k, v in data.get("savings_activity", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                if act_time is None:
                    act_time = v.get("created_at") or datetime.now()
                else:
                    act_time += timedelta(microseconds=1)
                v["created_at"] = act_time
                self.savings_activity[k] = SavingsActivity(**v)
            if os.path.exists(MONTHLY_BUDGETS_FILE):
                with open(MONTHLY_BUDGETS_FILE) as f:
                    self.monthly_budgets = json.load(f)
            self._rebuild_balance_cache()
            return True
        except Exception as e:
            print(f"MockBackend: Error loading data: {e}")
            return False

    def _seed(self):
        random.seed(42)

        accounts_data = [
            # (name, type, currency, initial_balance, bank, account_number, sub_accounts, dividend_type, maturity_date)
            # PHP - Savings
            ("Savings", "savings", "PHP", 125000.0, "BPI", "****4521"),
            ("Savings", "savings", "PHP", 85000.0, "Maya", "****7893"),
            ("Savings", "savings", "PHP", 200000.0, "BDO", "****1167"),
            ("Settlement", "savings", "PHP", 75000.0, "BPI", "****3308"),
            # PHP - Time Deposits
            ("Time Deposit", "time_deposit", "PHP", 250000.0, "BPI", "****6612", [], "Monthly Dividends", ""),
            ("Time Deposit", "time_deposit", "PHP", 100000.0, "Maya", "****9945", [], "Maturity Dividends", ""),
            # PHP - Equity
            ("Preferred Shares | Ayala Corporation", "equity", "PHP", 200000.0, "BPI", "****2280"),
            ("Preferred Shares | GCash Mynt", "equity", "PHP", 150000.0, "BPI", "****5574"),
            # USD - Checking
            ("Checking", "checking", "USD", 8500.0, "Bank of America", "****4419"),
            # USD - Savings
            ("Savings", "savings", "USD", 15000.0, "Bank of America", "****8837"),
        ]

        for data in accounts_data:
            name, atype, currency, balance, bank, acct_num = data[0], data[1], data[2], data[3], data[4], data[5]
            subs = data[6] if len(data) > 6 else []
            dividend_type = data[7] if len(data) > 7 else ""
            maturity_date = data[8] if len(data) > 8 else ""
            acc = Account(id=self._uid(), name=name, type=atype, currency=currency, bank=bank, account_number=acct_num, initial_balance=balance, sub_accounts=subs, dividend_type=dividend_type, maturity_date=maturity_date)
            self.accounts[acc.id] = acc

        categories_data = CATEGORIES_DATA

        for name, ctype, group, budget in categories_data:
            c = Category(
                id=self._uid(),
                name=name,
                type=ctype,
                group=group,
                budget_amount=budget,
            )
            self.categories[c.id] = c

        today = date.today()
        exp_cat_ids = [c.id for c in self.categories.values() if c.type == "expense"]
        inc_cat_ids = [c.id for c in self.categories.values() if c.type == "income"]
        acc_list = list(self.accounts.values())

        for i in range(12):
            month_date = today.replace(day=1) - timedelta(days=30 * i)
            year, month = month_date.year, month_date.month

            for _ in range(random.randint(2, 3)):
                day = random.randint(1, 28)
                cat_id = random.choice(inc_cat_ids)
                cat = self.categories[cat_id]
                acc = random.choice(acc_list)
                t = Transaction(
                    id=self._uid(),
                    date=date(year, month, day),
                    account_id=acc.id,
                    type="income",
                    amount=round(random.uniform(30000, 80000), 2) if acc.currency == "PHP" else round(random.uniform(500, 3000), 2),
                    currency=acc.currency,
                    category=cat.name,
                    description=f"{cat.name} payment",
                )
                self.transactions[t.id] = t

            for _ in range(random.randint(10, 15)):
                day = random.randint(1, 28)
                cat_id = random.choice(exp_cat_ids)
                cat = self.categories[cat_id]
                acc = random.choice(acc_list)
                t = Transaction(
                    id=self._uid(),
                    date=date(year, month, day),
                    account_id=acc.id,
                    type="expense",
                    amount=round(random.uniform(100, 8000), 2) if acc.currency == "PHP" else round(random.uniform(5, 200), 2),
                    currency=acc.currency,
                    category=cat.name,
                    description=f"{cat.name} expense",
                )
                self.transactions[t.id] = t

        usd_checking = [a for a in self.accounts.values() if a.currency == "USD" and a.type == "checking"][0]
        usd_savings = [a for a in self.accounts.values() if a.currency == "USD" and a.type == "savings"][0]

        r1 = RecurringRule(
            id=self._uid(), name="Rent", account_id=usd_checking.id, category="Rent",
            amount=1200.0, currency="USD", frequency="monthly", day_of_month=1,
            start_date="2026-01-01", end_date="2027-06-30", active=True,
            next_date=f"{today.year}-{today.month:02d}-01" if today.day <= 1 else f"{today.year}-{today.month + 1:02d}-01" if today.month < 12 else f"{today.year + 1}-01-01",
        )
        self.recurring_rules[r1.id] = r1

        r2 = RecurringRule(
            id=self._uid(), name="Tuition", account_id=usd_savings.id, category="Tuition",
            amount=3000.0, currency="USD", frequency="yearly", day_of_month=15,
            start_date="2026-01-01", end_date="2030-12-31", active=True,
            next_date=f"{today.year}-08-15",
        )
        self.recurring_rules[r2.id] = r2

        self._save()
        self._rebuild_balance_cache()

    def _rebuild_balance_cache(self):
        self._balance_cache.clear()
        for acc in self.accounts.values():
            self._balance_cache[acc.id] = acc.initial_balance
        for t in self.transactions.values():
            if t.transfer_pair_id:
                continue
            if t.account_id in self._balance_cache:
                if t.type == "income":
                    self._balance_cache[t.account_id] += t.amount
                elif t.type == "expense":
                    self._balance_cache[t.account_id] -= t.amount

    def get_accounts(self) -> list[Account]:
        return list(self.accounts.values())

    def create_account(self, data: AccountCreate) -> Account:
        acc = Account(id=self._uid(), **data.model_dump())
        self.accounts[acc.id] = acc
        self._save()
        return acc

    def update_account(self, account_id: str, data: AccountCreate) -> Account:
        if account_id not in self.accounts:
            raise KeyError("Account not found")
        old = self.accounts[account_id]
        acc = Account(id=account_id, **data.model_dump(), goal_amount=old.goal_amount, created_at=old.created_at)
        self.accounts[account_id] = acc
        self._save()
        return acc

    def delete_account(self, account_id: str) -> None:
        if account_id not in self.accounts:
            raise KeyError("Account not found")
        del self.accounts[account_id]
        self._save()

    def update_account_goal(self, account_id: str, goal_amount: float) -> Account:
        if account_id not in self.accounts:
            raise KeyError("Account not found")
        self.accounts[account_id].goal_amount = goal_amount
        self._save()
        return self.accounts[account_id]

    def get_transactions(self, account_id=None, type=None, group=None, category=None, start_date=None, end_date=None, currency=None) -> list[Transaction]:
        result = list(self.transactions.values())
        if currency:
            currency_account_ids = {a.id for a in self.accounts.values() if a.currency == currency}
            result = [t for t in result if t.account_id in currency_account_ids]
        if account_id:
            result = [t for t in result if t.account_id == account_id]
        if type:
            result = [t for t in result if t.type == type]
        if group:
            group_cats = {c.name for c in self.categories.values() if c.group == group}
            result = [t for t in result if t.category in group_cats]
        if category:
            result = [t for t in result if t.category == category]
        if start_date:
            result = [t for t in result if str(t.date) >= start_date]
        if end_date:
            result = [t for t in result if str(t.date) <= end_date]
        result.sort(key=lambda t: (str(t.date), str(t.created_at or '')), reverse=True)
        return result

    def create_transaction(self, data: TransactionCreate) -> Transaction:
        t = Transaction(id=self._uid(), **data.model_dump())
        self.transactions[t.id] = t
        if not t.transfer_pair_id and t.account_id in self._balance_cache:
            if t.type == "income":
                self._balance_cache[t.account_id] += t.amount
            elif t.type == "expense":
                self._balance_cache[t.account_id] -= t.amount
        self._save()
        self._reconcile_planner_for_account(t.account_id)
        return t

    def update_transaction(self, transaction_id: str, data: TransactionCreate) -> Transaction:
        if transaction_id not in self.transactions:
            raise KeyError("Transaction not found")
        old = self.transactions[transaction_id]
        if not old.transfer_pair_id:
            if old.type == "income":
                self._balance_cache[old.account_id] = self._balance_cache.get(old.account_id, 0) - old.amount
            elif old.type == "expense":
                self._balance_cache[old.account_id] = self._balance_cache.get(old.account_id, 0) + old.amount
        t = Transaction(id=transaction_id, **data.model_dump(), created_at=old.created_at)
        self.transactions[transaction_id] = t
        if not t.transfer_pair_id:
            if t.type == "income":
                self._balance_cache[t.account_id] = self._balance_cache.get(t.account_id, 0) + t.amount
            elif t.type == "expense":
                self._balance_cache[t.account_id] = self._balance_cache.get(t.account_id, 0) - t.amount
        self._save()
        for account_id in {old.account_id, t.account_id}:
            self._reconcile_planner_for_account(account_id)
        return t

    def delete_transaction(self, transaction_id: str) -> None:
        if transaction_id not in self.transactions:
            raise KeyError("Transaction not found")
        old = self.transactions[transaction_id]
        if not old.transfer_pair_id and old.account_id in self._balance_cache:
            if old.type == "income":
                self._balance_cache[old.account_id] -= old.amount
            elif old.type == "expense":
                self._balance_cache[old.account_id] += old.amount
        del self.transactions[transaction_id]
        self._save()
        self._reconcile_planner_for_account(old.account_id)

    def get_categories(self) -> list[Category]:
        return list(self.categories.values())

    def create_category(self, data: CategoryCreate) -> Category:
        c = Category(id=self._uid(), **data.model_dump())
        self.categories[c.id] = c
        self._save()
        return c

    def update_category(self, category_id: str, data: CategoryCreate) -> Category:
        if category_id not in self.categories:
            raise KeyError("Category not found")
        c = Category(id=category_id, **data.model_dump())
        self.categories[category_id] = c
        self._save()
        return c

    def delete_category(self, category_id: str) -> None:
        if category_id not in self.categories:
            raise KeyError("Category not found")
        del self.categories[category_id]
        self._save()

    def update_category_budget(self, category_id: str, budget_amount: float) -> Category:
        if category_id not in self.categories:
            raise KeyError("Category not found")
        c = self.categories[category_id]
        c.budget_amount = budget_amount
        self._save()
        return c

    def bulk_update_category_budgets(self, updates: dict[str, float]) -> list[Category]:
        for c in self.categories.values():
            if c.name in updates:
                c.budget_amount = updates[c.name]
        self._save()
        return list(self.categories.values())

    def get_budget_summary(self, month: str, currency: str | None = None) -> BudgetSummary:
        from models import CategoryBudgetSummary, BudgetSummary
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start = date(year, mon, 1)
        if mon == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, mon + 1, 1)

        if currency:
            currency_account_ids = {a.id for a in self.accounts.values() if a.currency == currency}
        else:
            currency_account_ids = None

        exp_cats = [c for c in self.categories.values() if c.type == "expense"]
        cat_spent = {c.name: 0.0 for c in exp_cats}
        for t in self.transactions.values():
            if t.type == "expense" and start <= t.date < end and not t.transfer_pair_id:
                if currency_account_ids is not None and t.account_id not in currency_account_ids:
                    continue
                cat_spent[t.category] = cat_spent.get(t.category, 0) + t.amount

        all_overrides = self.monthly_budgets.get(month, {})
        overrides = {}
        for k, v in all_overrides.items():
            if v.get("currency", "PHP") == (currency or "PHP"):
                cat_name = v.get("category", k.split("||")[0] if "||" in k else k)
                overrides[cat_name] = v

        template_key = f"template-{currency or 'PHP'}"
        template_all = self.monthly_budgets.get(template_key, {})
        template_filtered = {}
        for k, v in template_all.items():
            if v.get("currency", "PHP") == (currency or "PHP"):
                cat_name = v.get("category", k.split("||")[0] if "||" in k else k)
                template_filtered[cat_name] = v
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

    def get_monthly_budgets(self, month: str, currency: str | None = None) -> dict:
        overrides = self.monthly_budgets.get(month, {})
        result = {}
        for k, v in overrides.items():
            if currency and v.get("currency", "PHP") != currency:
                continue
            cat_name = v.get("category", k.split("||")[0] if "||" in k else k)
            result[cat_name] = v
        return result

    def set_monthly_budget(self, month: str, category: str, budget: float, currency: str = "PHP"):
        if month not in self.monthly_budgets:
            self.monthly_budgets[month] = {}
        key = f"{category}||{currency}"
        self.monthly_budgets[month][key] = {"budget": budget, "currency": currency, "category": category}
        self._save()

    def bulk_set_monthly_budget(self, month: str, overrides: list[dict], currency: str = "PHP"):
        if month not in self.monthly_budgets:
            self.monthly_budgets[month] = {}
        for ov in overrides:
            key = f"{ov['category']}||{currency}"
            self.monthly_budgets[month][key] = {"budget": ov["budget"], "currency": currency, "category": ov["category"]}
        self._save()

    def clear_monthly_budgets(self, month: str, currency: str | None = None):
        if month not in self.monthly_budgets:
            return
        if currency:
            self.monthly_budgets[month] = {k: v for k, v in self.monthly_budgets[month].items() if v.get("currency") != currency}
        else:
            del self.monthly_budgets[month]
        self._save()

    def get_balances(self, currency: str | None = None) -> list[Balance]:
        result = []
        for acc in self.accounts.values():
            if currency and acc.currency != currency:
                continue
            bal = self._balance_cache.get(acc.id, acc.initial_balance)
            result.append(Balance(
                account_id=acc.id,
                account_name=acc.name,
                currency=acc.currency,
                balance=round(bal, 2),
                balance_display=round(bal, 2),
            ))
        return result

    def get_annual_summary(self, year: int, currency: str | None = None) -> AnnualSummary:
        all_txns = [t for t in self.transactions.values() if t.date.year == year]
        if currency:
            currency_account_ids = {a.id for a in self.accounts.values() if a.currency == currency}
            all_txns = [t for t in all_txns if t.account_id in currency_account_ids]

        cur = currency or "USD"

        total_income = sum(t.amount for t in all_txns if t.type == "income")
        total_expense = sum(t.amount for t in all_txns if t.type == "expense")

        by_account = {}
        for t in all_txns:
            if t.account_id not in by_account:
                acc = self.accounts.get(t.account_id)
                by_account[t.account_id] = AccountBalance(
                    account_id=t.account_id,
                    account_name=acc.name if acc else "Unknown",
                    currency=cur,
                    balance=0,
                )
            if t.type == "income":
                by_account[t.account_id].balance += t.amount
            else:
                by_account[t.account_id].balance -= t.amount

        by_category = {}
        for t in all_txns:
            if t.type == "expense":
                if t.category not in by_category:
                    by_category[t.category] = CategorySummary(category=t.category, total=0, currency=cur)
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
            year=year,
            total_income=round(total_income, 2),
            total_expense=round(total_expense, 2),
            currency=cur,
            by_account=list(by_account.values()),
            by_category=sorted(by_category.values(), key=lambda x: x.total, reverse=True),
            monthly=sorted(monthly.values(), key=lambda x: x.month),
        )

    def get_rates(self) -> RatesResponse:
        return fetch_rates()

    def get_monthly_category_breakdown(self, year: int, currency: str | None = None) -> list[MonthlyCategoryRow]:
        all_txns = [t for t in self.transactions.values() if t.date.year == year and t.type == "expense"]
        if currency:
            currency_account_ids = {a.id for a in self.accounts.values() if a.currency == currency}
            all_txns = [t for t in all_txns if t.account_id in currency_account_ids]

        cats = {}
        for t in all_txns:
            if t.category not in cats:
                cat_obj = next((c for c in self.categories.values() if c.name == t.category), None)
                group = cat_obj.group if cat_obj else "Misc"
                cats[t.category] = {"group": group, "data": {}}
            m = f"{t.date.month:02d}"
            cats[t.category]["data"][m] = cats[t.category]["data"].get(m, 0) + t.amount
        return [MonthlyCategoryRow(category=c, group=v["group"], monthly=v["data"]) for c, v in sorted(cats.items())]

    def _advance_date(self, date_str: str, frequency: str) -> str:
        return advance_date(date_str, frequency)

    def get_recurring_rules(self, currency: str | None = None) -> list[RecurringRule]:
        rules = list(self.recurring_rules.values())
        if currency:
            rules = [r for r in rules if r.currency == currency]
        return rules

    def create_recurring_rule(self, data: RecurringRuleCreate) -> RecurringRule:
        r = RecurringRule(id=self._uid(), **data.model_dump(), next_date=data.start_date)
        self.recurring_rules[r.id] = r
        self._save()
        return r

    def update_recurring_rule(self, rule_id: str, data: RecurringRuleCreate) -> RecurringRule:
        if rule_id not in self.recurring_rules:
            raise KeyError("Rule not found")
        old = self.recurring_rules[rule_id]
        r = RecurringRule(id=rule_id, **data.model_dump(), active=old.active,
                          last_generated=old.last_generated, next_date=old.next_date,
                          created_at=old.created_at)
        self.recurring_rules[rule_id] = r
        self._save()
        return r

    def delete_recurring_rule(self, rule_id: str) -> None:
        if rule_id not in self.recurring_rules:
            raise KeyError("Rule not found")
        del self.recurring_rules[rule_id]
        self._save()

    def toggle_recurring_rule(self, rule_id: str, active: bool) -> RecurringRule:
        if rule_id not in self.recurring_rules:
            raise KeyError("Rule not found")
        self.recurring_rules[rule_id].active = active
        self._save()
        return self.recurring_rules[rule_id]

    def run_recurring(self, currency: str | None = None) -> RecurringRunResult:
        today = date.today()
        generated = 0
        for r in list(self.recurring_rules.values()):
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
            t = Transaction(
                id=self._uid(),
                date=next_d,
                account_id=r.account_id,
                type="expense",
                amount=r.amount,
                currency=r.currency,
                category=r.category,
                description=f"[Recurring] {r.name}",
            )
            self.transactions[t.id] = t
            r.last_generated = r.next_date
            r.next_date = self._advance_date(r.next_date, r.frequency)
            self._reconcile_planner_for_account(r.account_id)
            generated += 1
        self._save()
        rules = list(self.recurring_rules.values())
        if currency:
            rules = [r for r in rules if r.currency == currency]
        return RecurringRunResult(generated=generated, rules=rules)

    def get_transfers(self, currency: str | None = None) -> list[Transfer]:
        transfers = list(self.transfers.values())
        if currency:
            transfers = [t for t in transfers if t.currency == currency]
        return transfers

    def create_transfer(self, data: TransferCreate) -> Transfer:
        from_acc = self.accounts.get(data.from_account_id)
        to_acc = self.accounts.get(data.to_account_id)
        if not from_acc or not to_acc:
            raise ValueError("Account not found")
        if from_acc.currency != to_acc.currency:
            raise ValueError("Cannot transfer between different currencies")
        bal = self._balance_cache.get(data.from_account_id, from_acc.initial_balance)
        if bal < data.amount + data.fee:
            raise ValueError(f"Insufficient balance. Available: {bal:.2f}")
        t = Transfer(id=self._uid(), **{k: v for k, v in data.model_dump().items() if k != "date"}, date=date.fromisoformat(data.date))
        self.transfers[t.id] = t
        # Create paired transactions
        exp_id = self._uid()
        inc_id = self._uid()
        exp = Transaction(
            id=exp_id, date=t.date, account_id=data.from_account_id,
            type="expense", amount=data.amount + data.fee, currency=from_acc.currency,
            category="Transfer", description=f"Transfer → {to_acc.name}" + (f" (fee: {data.fee})" if data.fee else ""),
            transfer_pair_id=inc_id,
        )
        inc = Transaction(
            id=inc_id, date=t.date, account_id=data.to_account_id,
            type="income", amount=data.amount, currency=to_acc.currency,
            category="Transfer", description=f"Transfer ← {from_acc.name}",
            transfer_pair_id=exp_id,
        )
        self.transactions[exp.id] = exp
        self.transactions[inc.id] = inc
        self._save()
        self._reconcile_planner_for_account(data.from_account_id)
        self._reconcile_planner_for_account(data.to_account_id)
        return t

    def delete_transfer(self, transfer_id: str) -> None:
        if transfer_id not in self.transfers:
            raise KeyError("Transfer not found")
        transfer = self.transfers[transfer_id]
        del self.transfers[transfer_id]
        # Remove only the 2 transactions belonging to this transfer
        txns_to_remove = set()
        for tid, t in self.transactions.items():
            if t.transfer_pair_id and t.category == "Transfer":
                if (t.account_id == transfer.from_account_id and t.type == "expense") or \
                   (t.account_id == transfer.to_account_id and t.type == "income"):
                    txns_to_remove.add(tid)
                    txns_to_remove.add(t.transfer_pair_id)
        for tid in list(txns_to_remove):
            if tid in self.transactions:
                del self.transactions[tid]
        self._save()
        self._reconcile_planner_for_account(transfer.from_account_id)
        self._reconcile_planner_for_account(transfer.to_account_id)

    # ===================== SAVINGS PLANNER =====================

    def _account_balance(self, account_id: str) -> float:
        acc = self.accounts.get(account_id)
        if acc is None:
            return 0.0
        bal = acc.initial_balance
        for t in self.transactions.values():
            if t.account_id == account_id:
                if t.type == "income":
                    bal += t.amount
                elif t.type == "expense":
                    bal -= t.amount
        return round(bal, 2)

    def _planner_for_currency(self, currency: str) -> SavingsPlanner | None:
        return next((p for p in self.planners.values() if p.currency == currency), None)

    def _planner_for_account(self, account_id: str) -> SavingsPlanner | None:
        return next((p for p in self.planners.values() if p.linked_account_id == account_id), None)

    def _reserves_for(self, planner_id: str) -> list[SavingsReserve]:
        return sorted((r for r in self.savings_reserves.values() if r.planner_id == planner_id),
                      key=lambda r: r.position)

    def _goals_for(self, planner_id: str) -> list[SavingsGoal]:
        return sorted((g for g in self.savings_goals.values() if g.planner_id == planner_id),
                      key=lambda g: g.position)

    def _log_activity(self, planner_id: str, events: list[dict]):
        for ev in events:
            a = SavingsActivity(
                id=self._uid(), planner_id=planner_id,
                type=ev.get("type", "Planner Recalculated"),
                amount=round(float(ev.get("amount", 0)), 2),
                description=ev.get("description", ""),
            )
            self.savings_activity[a.id] = a

    def _reconcile_planner(self, planner: SavingsPlanner):
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        reserves, goals, events, _ = reconcile(balance, reserves, goals)
        conv_events = self._convert_completed_goals(planner, reserves, goals)
        self._log_activity(planner.id, events + conv_events)
        if events or conv_events:
            self._save()

    def _convert_completed_goals(self, planner: SavingsPlanner, reserves: list, goals: list) -> list:
        """Auto-convert fully-funded goals into floor-less reserves."""
        events = []
        for g in completed_goals(goals):
            position = max((r.position for r in reserves), default=-1) + 1
            r = SavingsReserve(
                id=self._uid(), planner_id=planner.id, name=g.name, icon=g.icon,
                allocated=g.allocated, floor=None, position=position,
            )
            self.savings_reserves[r.id] = r
            del self.savings_goals[g.id]
            events.append({
                "type": "Goal Converted",
                "amount": r.allocated,
                "description": f"Goal '{r.name}' completed and moved to Reserves",
            })
        return events

    def _reconcile_planner_for_account(self, account_id: str):
        planner = self._planner_for_account(account_id)
        if planner is None:
            return
        self._reconcile_planner(planner)

    def _planner_state(self, planner: SavingsPlanner | None, limit: int = 50) -> dict:
        if planner is None:
            return {
                "planner": None, "linked_account": None, "balance": 0.0,
                "unallocated": 0.0, "reserves": [], "goals": [],
                "activity": [], "underfunded": False,
                "savings_accounts": [
                    a for a in self.accounts.values()
                    if a.type == "savings"
                ],
            }
        balance = self._account_balance(planner.linked_account_id)
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
        activity = sorted(self.savings_activity.values(),
                          key=lambda a: a.created_at, reverse=True)[:limit]
        linked_account = self.accounts.get(planner.linked_account_id)
        return {
            "planner": planner,
            "linked_account": linked_account,
            "balance": balance,
            "unallocated": unallocated(balance, reserves, goals),
            "reserves": reserves,
            "goals": goals,
            "activity": activity,
            "underfunded": unallocated(balance, reserves, goals) < 0,
            "savings_accounts": [
                a for a in self.accounts.values()
                if a.type == "savings"
            ],
        }

    def get_savings_planner(self, currency: str, limit: int = 50) -> dict:
        return self._planner_state(self._planner_for_currency(currency), limit)

    def link_savings_planner(self, currency: str, account_id: str) -> dict:
        acc = self.accounts.get(account_id)
        if acc is None:
            raise KeyError("Account not found")
        if acc.type != "savings":
            raise ValueError("Only savings accounts can be linked to the planner")
        if acc.currency != currency:
            raise ValueError("Account currency does not match planner currency")
        planner = self._planner_for_currency(currency)
        if planner is None:
            planner = SavingsPlanner(id=self._uid(), currency=currency)
            self.planners[planner.id] = planner
        changed = planner.linked_account_id != account_id
        planner.linked_account_id = account_id
        if changed:
            self._log_activity(planner.id, [{
                "type": "Planner Recalculated",
                "amount": 0,
                "description": f"Linked to savings account '{acc.name}'",
            }])
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def create_savings_reserve(self, currency: str, data: SavingsReserveCreate) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        avail = unallocated(balance, reserves, goals)
        if data.allocated > avail + 0.005:
            raise ValueError(f"Insufficient Unallocated balance. Available: {avail:,.2f}")
        position = max((r.position for r in reserves), default=-1) + 1
        r = SavingsReserve(
            id=self._uid(), planner_id=planner.id, name=data.name, icon=data.icon,
            allocated=max(0.0, data.allocated), floor=data.floor, position=position,
        )
        self.savings_reserves[r.id] = r
        self._log_activity(planner.id, [{
            "type": "Moved Funds" if r.allocated > 0 else "Planner Recalculated",
            "amount": r.allocated,
            "description": f"Reserve '{r.name}' created" + (f" with {r.allocated:,.2f} allocated" if r.allocated > 0 else ""),
        }])
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def update_savings_reserve(self, currency: str, reserve_id: str, data: SavingsReserveUpdate) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        r = self.savings_reserves.get(reserve_id)
        if r is None or r.planner_id != planner.id:
            raise KeyError("Reserve not found")
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
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
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def delete_savings_reserve(self, currency: str, reserve_id: str) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        r = self.savings_reserves.get(reserve_id)
        if r is None or r.planner_id != planner.id:
            raise KeyError("Reserve not found")
        released = r.allocated
        del self.savings_reserves[reserve_id]
        self._log_activity(planner.id, [{
            "type": "Reserve Deleted",
            "amount": released,
            "description": f"Reserve '{r.name}' deleted; {released:,.2f} released to Unallocated",
        }])
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def create_savings_goal(self, currency: str, data: SavingsGoalCreate) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        goals = self._goals_for(planner.id)
        reserves = self._reserves_for(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        avail = unallocated(balance, reserves, goals)
        if data.allocated > avail + 0.005:
            raise ValueError(f"Insufficient Unallocated balance. Available: {avail:,.2f}")
        position = max((g.position for g in goals), default=-1) + 1
        g = SavingsGoal(
            id=self._uid(), planner_id=planner.id, name=data.name, icon=data.icon,
            target=data.target, allocated=max(0.0, data.allocated), position=position,
        )
        self.savings_goals[g.id] = g
        self._log_activity(planner.id, [{
            "type": "Moved Funds" if g.allocated > 0 else "Planner Recalculated",
            "amount": g.allocated,
            "description": f"Goal '{g.name}' created" + (f" with {g.allocated:,.2f} allocated" if g.allocated > 0 else ""),
        }])
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def update_savings_goal(self, currency: str, goal_id: str, data: SavingsGoalUpdate) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        g = self.savings_goals.get(goal_id)
        if g is None or g.planner_id != planner.id:
            raise KeyError("Goal not found")
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
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
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def delete_savings_goal(self, currency: str, goal_id: str) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        g = self.savings_goals.get(goal_id)
        if g is None or g.planner_id != planner.id:
            raise KeyError("Goal not found")
        released = g.allocated
        del self.savings_goals[goal_id]
        self._log_activity(planner.id, [{
            "type": "Goal Deleted",
            "amount": released,
            "description": f"Goal '{g.name}' deleted; {released:,.2f} released to Unallocated",
        }])
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def move_savings_money(self, currency: str, data: SavingsMove) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
        balance = self._account_balance(planner.linked_account_id)
        reserves, goals, events, error = move_money(
            balance, reserves, goals, data.from_bucket, data.to_bucket, data.amount)
        if error:
            raise ValueError(error)
        self._log_activity(planner.id, events)
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)

    def allocate_savings_money(self, currency: str, data: SavingsAllocate) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        reserves = self._reserves_for(planner.id)
        goals = self._goals_for(planner.id)
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
        self._save()
        return self._planner_state(planner)

    def convert_savings_goal(self, currency: str, goal_id: str) -> dict:
        planner = self._planner_for_currency(currency)
        if planner is None:
            raise ValueError("Planner not linked")
        g = self.savings_goals.get(goal_id)
        if g is None or g.planner_id != planner.id:
            raise KeyError("Goal not found")
        reserves = self._reserves_for(planner.id)
        position = max((r.position for r in reserves), default=-1) + 1
        r = SavingsReserve(
            id=self._uid(), planner_id=planner.id, name=g.name, icon=g.icon,
            allocated=g.allocated, floor=None, position=position,
        )
        self.savings_reserves[r.id] = r
        del self.savings_goals[goal_id]
        self._log_activity(planner.id, [{
            "type": "Goal Converted",
            "amount": r.allocated,
            "description": f"Goal '{r.name}' converted to a Reserve",
        }])
        self._reconcile_planner(planner)
        self._save()
        return self._planner_state(planner)
