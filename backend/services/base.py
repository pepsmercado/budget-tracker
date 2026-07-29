from abc import ABC, abstractmethod
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate,
    Balance, AnnualSummary, RatesResponse, MonthlyCategoryRow,
    BudgetSummary, RecurringRule, RecurringRuleCreate, RecurringRunResult,
    Transfer, TransferCreate,
)


class BackendService(ABC):

    @abstractmethod
    def get_accounts(self) -> list[Account]:
        pass

    @abstractmethod
    def create_account(self, data: AccountCreate) -> Account:
        pass

    @abstractmethod
    def update_account(self, account_id: str, data: AccountCreate) -> Account:
        pass

    @abstractmethod
    def delete_account(self, account_id: str) -> None:
        pass

    @abstractmethod
    def update_account_goal(self, account_id: str, goal_amount: float) -> Account:
        pass

    @abstractmethod
    def get_transactions(self, account_id: str | None = None, type: str | None = None, group: str | None = None, category: str | None = None, start_date: str | None = None, end_date: str | None = None, currency: str | None = None) -> list[Transaction]:
        pass

    @abstractmethod
    def create_transaction(self, data: TransactionCreate) -> Transaction:
        pass

    @abstractmethod
    def update_transaction(self, transaction_id: str, data: TransactionCreate) -> Transaction:
        pass

    @abstractmethod
    def delete_transaction(self, transaction_id: str) -> None:
        pass

    @abstractmethod
    def get_categories(self) -> list[Category]:
        pass

    @abstractmethod
    def create_category(self, data: CategoryCreate) -> Category:
        pass

    @abstractmethod
    def update_category(self, category_id: str, data: CategoryCreate) -> Category:
        pass

    @abstractmethod
    def delete_category(self, category_id: str) -> None:
        pass

    @abstractmethod
    def update_category_budget(self, category_id: str, budget_amount: float) -> Category:
        pass

    @abstractmethod
    def get_budget_summary(self, month: str, currency: str | None = None) -> BudgetSummary:
        pass

    @abstractmethod
    def get_monthly_budgets(self, month: str, currency: str | None = None) -> dict:
        pass

    @abstractmethod
    def set_monthly_budget(self, month: str, category: str, budget: float, currency: str = "PHP"):
        pass

    @abstractmethod
    def bulk_set_monthly_budget(self, month: str, overrides: list[dict], currency: str = "PHP"):
        pass

    @abstractmethod
    def clear_monthly_budgets(self, month: str, currency: str | None = None):
        pass

    @abstractmethod
    def get_balances(self, currency: str | None = None) -> list[Balance]:
        pass

    @abstractmethod
    def get_annual_summary(self, year: int, currency: str | None = None) -> AnnualSummary:
        pass

    @abstractmethod
    def get_rates(self) -> RatesResponse:
        pass

    @abstractmethod
    def get_monthly_category_breakdown(self, year: int, currency: str | None = None) -> list[MonthlyCategoryRow]:
        pass

    @abstractmethod
    def get_recurring_rules(self, currency: str | None = None) -> list[RecurringRule]:
        pass

    @abstractmethod
    def create_recurring_rule(self, data: RecurringRuleCreate) -> RecurringRule:
        pass

    @abstractmethod
    def update_recurring_rule(self, rule_id: str, data: RecurringRuleCreate) -> RecurringRule:
        pass

    @abstractmethod
    def delete_recurring_rule(self, rule_id: str) -> None:
        pass

    @abstractmethod
    def toggle_recurring_rule(self, rule_id: str, active: bool) -> RecurringRule:
        pass

    @abstractmethod
    def run_recurring(self, currency: str | None = None) -> RecurringRunResult:
        pass

    @abstractmethod
    def get_transfers(self, currency: str | None = None) -> list[Transfer]:
        pass

    @abstractmethod
    def create_transfer(self, data: TransferCreate) -> Transfer:
        pass

    @abstractmethod
    def delete_transfer(self, transfer_id: str) -> None:
        pass

    @abstractmethod
    def bulk_update_category_budgets(self, updates: dict[str, float]) -> list[Category]:
        pass
