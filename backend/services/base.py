from abc import ABC, abstractmethod
from models import (
    Account, AccountCreate, Transaction, TransactionCreate,
    Category, CategoryCreate, Budget, BudgetSet,
    Balance, AnnualSummary, RatesResponse, MonthlyCategoryRow,
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
    def get_transactions(self, account_id: str | None = None, type: str | None = None, group: str | None = None, category: str | None = None, start_date: str | None = None, end_date: str | None = None) -> list[Transaction]:
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
    def update_category_budget(self, category_id: str, budget_amount: float, budget_currency: str) -> Category:
        pass

    @abstractmethod
    def get_budget(self, month: str) -> Budget | None:
        pass

    @abstractmethod
    def set_budget(self, month: str, data: BudgetSet) -> Budget:
        pass

    @abstractmethod
    def get_balances(self) -> list[Balance]:
        pass

    @abstractmethod
    def get_annual_summary(self, year: int) -> AnnualSummary:
        pass

    @abstractmethod
    def get_rates(self) -> RatesResponse:
        pass

    @abstractmethod
    def get_monthly_category_breakdown(self, year: int) -> list[MonthlyCategoryRow]:
        pass
