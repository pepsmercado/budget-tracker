import uuid
from datetime import date, datetime, timedelta
import random

from services.base import BackendService
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate, Budget, BudgetSet,
    Balance, AccountBalance, CategorySummary, MonthlyTotal,
    AnnualSummary, RatesResponse, SubAccount,
)


class MockBackend(BackendService):
    def __init__(self):
        self.accounts: dict[str, Account] = {}
        self.transactions: dict[str, Transaction] = {}
        self.categories: dict[str, Category] = {}
        self.budgets: dict[str, Budget] = {}
        self._seed()

    def _uid(self) -> str:
        return uuid.uuid4().hex[:12]

    def _seed(self):
        random.seed(42)

        accounts_data = [
            ("BPI Savings", "savings", "PHP", 125000.0),
            ("Maya Savings", "savings", "PHP", 85000.0),
            ("BDO Savings", "savings", "PHP", 200000.0),
            ("Bank of America Savings", "savings", "USD", 15000.0),
            ("BPI Beneficiary", "checking", "PHP", 75000.0),
            ("Bank of America Checking", "checking", "USD", 8500.0),
            ("Maya Time Deposit", "time_deposit", "PHP", 100000.0),
            ("BPI Time Deposit", "time_deposit", "PHP", 250000.0),
            ("BPI Investments", "investment", "PHP", 500000.0, [
                SubAccount(id=self._uid(), name="UITF", balance=200000.0),
                SubAccount(id=self._uid(), name="FMETF", balance=150000.0),
                SubAccount(id=self._uid(), name="Bonds", balance=100000.0),
                SubAccount(id=self._uid(), name="Other", balance=50000.0),
            ]),
            ("BPI Credit Card", "credit_card", "PHP", 0.0),
            ("Bank of America Credit Card", "credit_card", "USD", 0.0),
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
            ("Phone + Wifi", "expense", "Fixed", 1500),
            ("Renter's Insurance", "expense", "Fixed", 800),
            ("Health Insurance", "expense", "Fixed", 2500),
            ("Groceries", "expense", "Essential", 12000),
            ("Household and Toiletries", "expense", "Essential", 3000),
            ("Transportation", "expense", "Essential", 4000),
            ("Medical and Health", "expense", "Essential", 2000),
            ("Eating Out", "expense", "Lifestyle", 5000),
            ("Social Events", "expense", "Lifestyle", 3000),
            ("Hobbies", "expense", "Lifestyle", 2000),
            ("Shopping", "expense", "Sinking", 5000),
            ("Beauty and Grooming", "expense", "Sinking", 2000),
            ("Travel", "expense", "Sinking", 8000),
            ("Others", "expense", "Sinking", 2000),
            ("Tuition", "expense", "School", 25000),
            ("School Supplies", "expense", "School", 2000),
            ("Salary", "income", "Income", 0),
            ("Cashback", "income", "Income", 0),
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
        return acc

    def update_account(self, account_id: str, data: AccountCreate) -> Account:
        if account_id not in self.accounts:
            raise KeyError("Account not found")
        acc = Account(id=account_id, **data.model_dump(), created_at=self.accounts[account_id].created_at)
        self.accounts[account_id] = acc
        return acc

    def delete_account(self, account_id: str) -> None:
        if account_id not in self.accounts:
            raise KeyError("Account not found")
        del self.accounts[account_id]

    def get_transactions(self, account_id=None, category=None, start_date=None, end_date=None) -> list[Transaction]:
        result = list(self.transactions.values())
        if account_id:
            result = [t for t in result if t.account_id == account_id]
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
        return t

    def update_transaction(self, transaction_id: str, data: TransactionCreate) -> Transaction:
        if transaction_id not in self.transactions:
            raise KeyError("Transaction not found")
        t = Transaction(id=transaction_id, **data.model_dump(), created_at=self.transactions[transaction_id].created_at)
        self.transactions[transaction_id] = t
        return t

    def delete_transaction(self, transaction_id: str) -> None:
        if transaction_id not in self.transactions:
            raise KeyError("Transaction not found")
        del self.transactions[transaction_id]

    def get_categories(self) -> list[Category]:
        return list(self.categories.values())

    def create_category(self, data: CategoryCreate) -> Category:
        c = Category(id=self._uid(), **data.model_dump())
        self.categories[c.id] = c
        return c

    def update_category(self, category_id: str, data: CategoryCreate) -> Category:
        if category_id not in self.categories:
            raise KeyError("Category not found")
        c = Category(id=category_id, **data.model_dump())
        self.categories[category_id] = c
        return c

    def delete_category(self, category_id: str) -> None:
        if category_id not in self.categories:
            raise KeyError("Category not found")
        del self.categories[category_id]

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
                return b
        b = Budget(id=self._uid(), month=month, **data.model_dump())
        self.budgets[b.id] = b
        return b

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
        result = []
        for acc in self.accounts.values():
            bal = balances.get(acc.id, acc.initial_balance)
            result.append(Balance(
                account_id=acc.id,
                account_name=acc.name,
                currency=acc.currency,
                balance=round(bal, 2),
                balance_display=round(bal, 2),
            ))
        return result

    def get_annual_summary(self, year: int) -> AnnualSummary:
        all_txns = [t for t in self.transactions.values() if t.date.year == year]
        total_income = sum(t.amount for t in all_txns if t.type == "income")
        total_expense = sum(t.amount for t in all_txns if t.type == "expense")

        by_account = {}
        for t in all_txns:
            if t.account_id not in by_account:
                acc = self.accounts.get(t.account_id)
                by_account[t.account_id] = AccountBalance(
                    account_id=t.account_id,
                    account_name=acc.name if acc else "Unknown",
                    currency=t.currency,
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
                    by_category[t.category] = CategorySummary(category=t.category, total=0, currency=t.currency)
                by_category[t.category].total += t.amount

        monthly = {}
        for t in all_txns:
            m = f"{t.date.year}-{t.date.month:02d}"
            if m not in monthly:
                monthly[m] = MonthlyTotal(month=m, income=0, expense=0, currency="PHP")
            if t.type == "income":
                monthly[m].income += t.amount
            else:
                monthly[m].expense += t.amount

        return AnnualSummary(
            year=year,
            total_income=round(total_income, 2),
            total_expense=round(total_expense, 2),
            currency="PHP",
            by_account=list(by_account.values()),
            by_category=sorted(by_category.values(), key=lambda x: x.total, reverse=True),
            monthly=sorted(monthly.values(), key=lambda x: x.month),
        )

    def get_rates(self) -> RatesResponse:
        return RatesResponse(base="USD", rates={"USD": 1.0, "PHP": 56.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5})
