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
)

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data.json")


class MockBackend(BackendService):
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.transactions: dict[str, Transaction] = {}
        self.categories: dict[str, Category] = {}
        self.budgets: dict[str, Budget] = {}
        if not self._load():
            self._seed()

    def _uid(self) -> str:
        return uuid.uuid4().hex[:12]

    def _save(self):
        data = {
            "accounts": {k: v.model_dump() for k, v in self.accounts.items()},
            "transactions": {k: v.model_dump() for k, v in self.transactions.items()},
            "categories": {k: v.model_dump() for k, v in self.categories.items()},
            "budgets": {k: v.model_dump() for k, v in self.budgets.items()},
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, default=str)

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
            return True
        except Exception:
            return False

    def _seed(self):
        random.seed(42)

        accounts_data = [
            ("BPI Savings", "savings", "PHP", 125000.0),
            ("Maya Savings", "savings", "PHP", 85000.0),
            ("BDO Savings", "savings", "PHP", 200000.0),
            ("Bank of America Savings", "savings", "USD", 15000.0),
            ("BPI Settlement", "savings", "PHP", 75000.0),
            ("Bank of America Checking", "checking", "USD", 8500.0),
            ("Maya Time Deposit", "time_deposit", "PHP", 100000.0),
            ("BPI Time Deposit", "time_deposit", "PHP", 250000.0),
            ("BPI Investments", "investment", "PHP", 500000.0, [
                SubAccount(id=self._uid(), name="Preferred Shares", balance=200000.0),
                SubAccount(id=self._uid(), name="REIT", balance=150000.0),
                SubAccount(id=self._uid(), name="Bonds", balance=100000.0),
                SubAccount(id=self._uid(), name="Index Funds", balance=50000.0),
            ]),
        ]

        for data in accounts_data:
            name, atype, currency, balance = data[0], data[1], data[2], data[3]
            subs = data[4] if len(data) > 4 else []
            acc = Account(id=self._uid(), name=name, type=atype, currency=currency, initial_balance=balance, sub_accounts=subs)
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
        acc = Account(id=account_id, **data.model_dump(), created_at=self.accounts[account_id].created_at)
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

    def get_transactions(self, account_id=None, type=None, group=None, category=None, start_date=None, end_date=None) -> list[Transaction]:
        result = list(self.transactions.values())
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

    def update_category_budget(self, category_id: str, budget_amount: float, budget_currency: str) -> Category:
        if category_id not in self.categories:
            raise KeyError("Category not found")
        c = self.categories[category_id]
        c.budget_amount = budget_amount
        c.budget_currency = budget_currency
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

    def get_budget_summary(self, month: str) -> BudgetSummary:
        from models import CategoryBudgetSummary, BudgetSummary
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start = date(year, mon, 1)
        if mon == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, mon + 1, 1)

        rates = self.get_rates().rates
        php_to_usd = 1 / rates.get("PHP", 56)

        def to_usd(amount, currency):
            if currency == "USD":
                return amount
            if currency == "PHP":
                return amount * php_to_usd
            return amount

        exp_cats = [c for c in self.categories.values() if c.type == "expense"]
        cat_spent = {c.name: 0.0 for c in exp_cats}
        for t in self.transactions.values():
            if t.type == "expense" and start <= t.date < end:
                cat_spent[t.category] = cat_spent.get(t.category, 0) + to_usd(t.amount, t.currency)

        categories = []
        for c in exp_cats:
            if c.budget_amount > 0:
                budget_usd = to_usd(c.budget_amount, c.budget_currency)
                categories.append(CategoryBudgetSummary(
                    name=c.name, group=c.group, budget=round(budget_usd, 2),
                    currency="USD", spent=round(cat_spent.get(c.name, 0), 2),
                ))

        total_budget = sum(c.budget for c in categories)
        total_spent = sum(c.spent for c in categories)

        return BudgetSummary(
            month=month, total_budget=round(total_budget, 2),
            total_spent=round(total_spent, 2), categories=categories,
        )

    def get_balances(self) -> list[Balance]:
        balances = {}
        for acc in self.accounts.values():
            balances[acc.id] = acc.initial_balance
        for t in self.transactions.values():
            if t.account_id in balances:
                if t.type == "income":
                    balances[t.account_id] += t.amount
                elif t.type == "expense":
                    balances[t.account_id] -= t.amount

        rates = self.get_rates().rates
        php_to_usd = 1 / rates.get("PHP", 56)

        result = []
        for acc in self.accounts.values():
            bal = balances.get(acc.id, acc.initial_balance)
            if acc.currency == "PHP":
                bal_display = round(bal * php_to_usd, 2)
            else:
                bal_display = round(bal, 2)
            result.append(Balance(
                account_id=acc.id,
                account_name=acc.name,
                currency=acc.currency,
                balance=round(bal, 2),
                balance_display=bal_display,
            ))
        return result

    def get_annual_summary(self, year: int) -> AnnualSummary:
        all_txns = [t for t in self.transactions.values() if t.date.year == year]
        rates = self.get_rates().rates
        php_to_usd = 1 / rates.get("PHP", 56)

        def to_usd(amount, currency):
            if currency == "USD":
                return amount
            if currency == "PHP":
                return amount * php_to_usd
            return amount

        total_income = sum(to_usd(t.amount, t.currency) for t in all_txns if t.type == "income")
        total_expense = sum(to_usd(t.amount, t.currency) for t in all_txns if t.type == "expense")

        by_account = {}
        for t in all_txns:
            if t.account_id not in by_account:
                acc = self.accounts.get(t.account_id)
                by_account[t.account_id] = AccountBalance(
                    account_id=t.account_id,
                    account_name=acc.name if acc else "Unknown",
                    currency="USD",
                    balance=0,
                )
            if t.type == "income":
                by_account[t.account_id].balance += to_usd(t.amount, t.currency)
            else:
                by_account[t.account_id].balance -= to_usd(t.amount, t.currency)

        by_category = {}
        for t in all_txns:
            if t.type == "expense":
                if t.category not in by_category:
                    by_category[t.category] = CategorySummary(category=t.category, total=0, currency="USD")
                by_category[t.category].total += to_usd(t.amount, t.currency)

        monthly = {}
        for t in all_txns:
            m = f"{t.date.year}-{t.date.month:02d}"
            if m not in monthly:
                monthly[m] = MonthlyTotal(month=m, income=0, expense=0, currency="USD")
            if t.type == "income":
                monthly[m].income += to_usd(t.amount, t.currency)
            else:
                monthly[m].expense += to_usd(t.amount, t.currency)

        return AnnualSummary(
            year=year,
            total_income=round(total_income, 2),
            total_expense=round(total_expense, 2),
            currency="USD",
            by_account=list(by_account.values()),
            by_category=sorted(by_category.values(), key=lambda x: x.total, reverse=True),
            monthly=sorted(monthly.values(), key=lambda x: x.month),
        )

    _rates_cache = None
    _rates_cache_time = None

    def get_rates(self) -> RatesResponse:
        import urllib.request
        import json
        from datetime import datetime, timedelta

        # Use cache if less than 12 hours old
        if MockBackend._rates_cache and MockBackend._rates_cache_time:
            if datetime.now() - MockBackend._rates_cache_time < timedelta(hours=12):
                return MockBackend._rates_cache

        # Try multiple sources for accuracy
        apis = [
            'https://open.er-api.com/v6/latest/USD',
            'https://api.exchangerate-api.com/v4/latest/USD',
        ]

        for api_url in apis:
            try:
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as res:
                    data = json.loads(res.read())
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

    def get_monthly_category_breakdown(self, year: int) -> list[MonthlyCategoryRow]:
        all_txns = [t for t in self.transactions.values() if t.date.year == year and t.type == "expense"]
        rates = self.get_rates().rates
        php_to_usd = 1 / rates.get("PHP", 56)

        def to_usd(amount, currency):
            if currency == "USD":
                return amount
            if currency == "PHP":
                return amount * php_to_usd
            return amount

        cats = {}
        for t in all_txns:
            if t.category not in cats:
                cats[t.category] = {}
            m = f"{t.date.month:02d}"
            cats[t.category][m] = cats[t.category].get(m, 0) + to_usd(t.amount, t.currency)
        return [MonthlyCategoryRow(category=c, monthly=m) for c, m in sorted(cats.items())]
