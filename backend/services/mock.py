import uuid
import json
import os
from datetime import date, datetime, timedelta
import random

from services.base import BackendService
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate, Budget, BudgetSet,
    Balance, AccountBalance, CategorySummary, MonthlyTotal,
    AnnualSummary, RatesResponse, SubAccount, MonthlyCategoryRow,
    RecurringRule, RecurringRuleCreate, RecurringRunResult,
    Transfer, TransferCreate,
)

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
        self.budgets: dict[str, Budget] = {}
        self.recurring_rules: dict[str, RecurringRule] = {}
        self.transfers: dict[str, Transfer] = {}
        self.monthly_budgets: dict[str, dict[str, dict]] = {}
        if not self._load() or not self.accounts:
            self._seed()

    def _uid(self) -> str:
        return uuid.uuid4().hex[:12]

    def _save(self):
        data = {
            "accounts": {k: v.model_dump() for k, v in self.accounts.items()},
            "transactions": {k: v.model_dump() for k, v in self.transactions.items()},
            "categories": {k: v.model_dump() for k, v in self.categories.items()},
            "budgets": {k: v.model_dump() for k, v in self.budgets.items()},
            "recurring_rules": {k: v.model_dump() for k, v in self.recurring_rules.items()},
            "transfers": {k: v.model_dump() for k, v in self.transfers.items()},
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
            for k, v in data.get("transactions", {}).items():
                if "created_at" in v and isinstance(v["created_at"], str):
                    v["created_at"] = datetime.fromisoformat(v["created_at"])
                if "date" in v and isinstance(v["date"], str):
                    v["date"] = date.fromisoformat(v["date"])
                self.transactions[k] = Transaction(**v)
            for k, v in data.get("categories", {}).items():
                self.categories[k] = Category(**v)
            for k, v in data.get("budgets", {}).items():
                self.budgets[k] = Budget(**v)
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
            if os.path.exists(MONTHLY_BUDGETS_FILE):
                with open(MONTHLY_BUDGETS_FILE) as f:
                    self.monthly_budgets = json.load(f)
            return True
        except Exception:
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
            c = Category(
                id=self._uid(),
                name=name,
                type=ctype,
                group=group,
                budget_amount=budget,
                budget_currency="PHP",
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

        for i in range(3):
            m = today.replace(day=1) - timedelta(days=30 * i)
            month_str = f"{m.year}-{m.month:02d}"
            b = Budget(id=self._uid(), month=month_str, total_budget=random.uniform(60000, 120000), currency="PHP")
            self.budgets[b.id] = b

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
        result.sort(key=lambda t: t.date, reverse=True)
        return result

    def create_transaction(self, data: TransactionCreate) -> Transaction:
        t = Transaction(id=self._uid(), **data.model_dump())
        self.transactions[t.id] = t
        self._save()
        return t

    def update_transaction(self, transaction_id: str, data: TransactionCreate) -> Transaction:
        if transaction_id not in self.transactions:
            raise KeyError("Transaction not found")
        t = Transaction(id=transaction_id, **data.model_dump(), created_at=self.transactions[transaction_id].created_at)
        self.transactions[transaction_id] = t
        self._save()
        return t

    def delete_transaction(self, transaction_id: str) -> None:
        if transaction_id not in self.transactions:
            raise KeyError("Transaction not found")
        del self.transactions[transaction_id]
        self._save()

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

    def get_budget(self, month: str) -> Budget | None:
        for b in self.budgets.values():
            if b.month == month:
                return b
        return None

    def set_budget(self, month: str, data: BudgetSet) -> Budget:
        for b in self.budgets.values():
            if b.month == month:
                b.total_budget = data.total_budget
                b.currency = data.currency
                self._save()
                return b
        b = Budget(id=self._uid(), month=month, **data.model_dump())
        self.budgets[b.id] = b
        self._save()
        return b

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
            if t.type == "expense" and start <= t.date < end:
                if currency_account_ids is not None and t.account_id not in currency_account_ids:
                    continue
                cat_spent[t.category] = cat_spent.get(t.category, 0) + t.amount

        overrides = self.monthly_budgets.get(month, {})

        categories = []
        for c in exp_cats:
            if c.name in overrides:
                ov = overrides[c.name]
                budget_val = ov["budget"]
            else:
                budget_val = c.budget_amount

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

    def get_monthly_budgets(self, month: str, currency: str | None = None) -> dict:
        overrides = self.monthly_budgets.get(month, {})
        if currency:
            return {k: v for k, v in overrides.items() if v.get("currency", "PHP") == currency}
        return overrides

    def set_monthly_budget(self, month: str, category: str, budget: float, currency: str = "PHP"):
        if month not in self.monthly_budgets:
            self.monthly_budgets[month] = {}
        self.monthly_budgets[month][category] = {"budget": budget, "currency": currency}
        self._save()

    def bulk_set_monthly_budget(self, month: str, overrides: list[dict], currency: str = "PHP"):
        if month not in self.monthly_budgets:
            self.monthly_budgets[month] = {}
        for ov in overrides:
            self.monthly_budgets[month][ov["category"]] = {"budget": ov["budget"], "currency": currency}
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
        balances = {}
        for acc in self.accounts.values():
            balances[acc.id] = acc.initial_balance
        for t in self.transactions.values():
            if t.account_id in balances:
                if t.type == "income":
                    balances[t.account_id] += t.amount
                elif t.type == "expense":
                    balances[t.account_id] -= t.amount

        result = []
        for acc in self.accounts.values():
            if currency and acc.currency != currency:
                continue
            bal = balances.get(acc.id, acc.initial_balance)
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

    _rates_cache = None
    _rates_cache_time = None

    def get_rates(self) -> RatesResponse:
        import httpx
        from datetime import timedelta

        # Use cache if less than 12 hours old
        if MockBackend._rates_cache and MockBackend._rates_cache_time:
            if datetime.now() - MockBackend._rates_cache_time < timedelta(hours=12):
                return MockBackend._rates_cache

        # Try multiple sources for accuracy
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
                                "USD": 1.0,
                                "PHP": php_rate,
                                "EUR": rates.get("EUR", 0.92),
                                "GBP": rates.get("GBP", 0.79),
                                "JPY": rates.get("JPY", 149.5),
                            }
                        )
                        MockBackend._rates_cache = result
                        MockBackend._rates_cache_time = datetime.now()
                        return result
                except Exception:
                    continue

        # Return cache even if stale, or defaults
        if MockBackend._rates_cache:
            return MockBackend._rates_cache
        return RatesResponse(base="USD", rates={"USD": 1.0, "PHP": 56.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5})

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
        y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
        if frequency == "monthly":
            m += 1
            if m > 12:
                m = 1
                y += 1
            # clamp day to last day of month
            import calendar
            last_day = calendar.monthrange(y, m)[1]
            d = min(d, last_day)
        else:
            y += 1
        return f"{y}-{m:02d}-{d:02d}"

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
        bal = from_acc.initial_balance
        for t in self.transactions.values():
            if t.account_id == data.from_account_id:
                if t.type == "income":
                    bal += t.amount
                elif t.type == "expense":
                    bal -= t.amount
        if bal < data.amount + data.fee:
            raise ValueError(f"Insufficient balance. Available: {bal:.2f}")
        t = Transfer(id=self._uid(), **{k: v for k, v in data.model_dump().items() if k != "date"}, date=date.fromisoformat(data.date) if isinstance(data.date, str) else data.date)
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
        return t

    def delete_transfer(self, transfer_id: str) -> None:
        if transfer_id not in self.transfers:
            raise KeyError("Transfer not found")
        del self.transfers[transfer_id]
        # Remove paired transactions
        to_remove = [tid for tid, t in self.transactions.items()
                     if getattr(t, 'transfer_pair_id', None) and
                     (tid == t.transfer_pair_id or t.transfer_pair_id in [tt.id for tt in self.transactions.values()])]
        # Simpler: remove any transaction whose pair is also in the set
        txns_to_remove = set()
        for tid, t in self.transactions.items():
            if t.transfer_pair_id and t.transfer_pair_id != tid:
                # This is part of a transfer pair — both should be removed
                txns_to_remove.add(tid)
                txns_to_remove.add(t.transfer_pair_id)
        for tid in list(txns_to_remove):
            if tid in self.transactions:
                del self.transactions[tid]
        self._save()
