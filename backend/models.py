from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


class SubAccount(BaseModel):
    id: str
    name: str
    balance: float = 0.0


class Account(BaseModel):
    id: str
    name: str
    type: str  # "savings", "checking", "time_deposit", "investment", "credit_card"
    currency: str
    bank: str = ""
    account_number: str = ""
    initial_balance: float = 0.0
    goal_amount: float = 0.0
    sub_accounts: list[SubAccount] = []
    dividend_type: str = ""  # e.g. "Monthly Dividends", "Maturity Dividends"
    maturity_date: str = ""  # e.g. "2027-06-15"
    created_at: datetime = Field(default_factory=datetime.now)


class AccountCreate(BaseModel):
    name: str
    type: str
    currency: str
    bank: str = ""
    account_number: str = ""
    initial_balance: float = 0.0
    sub_accounts: list[SubAccount] = []
    dividend_type: str = ""
    maturity_date: str = ""


class AccountGoalUpdate(BaseModel):
    goal_amount: float = Field(ge=0)


class Transaction(BaseModel):
    id: str
    date: date
    account_id: str
    type: str  # "income", "expense", "transfer"
    amount: float = Field(gt=0)
    currency: str
    category: str
    description: str = ""
    transfer_pair_id: Optional[str] = None
    sub_account_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class TransactionCreate(BaseModel):
    date: date
    account_id: str
    type: str
    amount: float = Field(gt=0)
    currency: str
    category: str
    description: str = ""
    transfer_pair_id: Optional[str] = None
    sub_account_id: Optional[str] = None


class Category(BaseModel):
    id: str
    name: str
    type: str  # "income" or "expense"
    group: str  # "Fixed", "Essential", "Lifestyle", "Sinking", "School", "Income", "Misc"
    budget_amount: float = 0.0


class CategoryCreate(BaseModel):
    name: str
    type: str
    group: str
    budget_amount: float = 0.0


class CategoryBudgetUpdate(BaseModel):
    budget_amount: float = Field(ge=0)


class CategoryBudgetBulkItem(BaseModel):
    name: str
    budget_amount: float = Field(ge=0)


class CategoryBudgetBulkUpdate(BaseModel):
    updates: list[CategoryBudgetBulkItem]


class MonthlyBudgetOverride(BaseModel):
    category: str
    budget: float
    currency: str = "PHP"


class MonthlyBudgetBulkSet(BaseModel):
    overrides: list[MonthlyBudgetOverride]


class Balance(BaseModel):
    account_id: str
    account_name: str
    currency: str
    balance: float
    balance_display: float  # converted to display currency


class AccountBalance(BaseModel):
    account_id: str
    account_name: str
    currency: str
    balance: float


class CategorySummary(BaseModel):
    category: str
    total: float
    currency: str


class MonthlyTotal(BaseModel):
    month: str
    income: float
    expense: float
    currency: str


class AnnualSummary(BaseModel):
    year: int
    total_income: float
    total_expense: float
    currency: str
    by_account: list[AccountBalance]
    by_category: list[CategorySummary]
    monthly: list[MonthlyTotal]


class RatesResponse(BaseModel):
    base: str
    rates: dict[str, float]


class BankStatementRow(BaseModel):
    date: str
    description: str
    amount: float
    type: str  # "income" or "expense"
    category: str = ""
    warnings: list[str] = []
    raw: dict = {}


class BankStatementPreview(BaseModel):
    bank: str
    account_hint: str
    rows: list[BankStatementRow]
    total_rows: int
    total_income: float
    total_expense: float


class MonthlyCategoryRow(BaseModel):
    category: str
    group: str = ""
    monthly: dict[str, float]  # "01": amount, "02": amount, ...


class CategoryBudgetSummary(BaseModel):
    name: str
    group: str
    budget: float
    currency: str
    spent: float

class BudgetSummary(BaseModel):
    month: str
    total_budget: float
    total_spent: float
    categories: list[CategoryBudgetSummary]


class RecurringRule(BaseModel):
    id: str
    name: str
    account_id: str
    category: str
    amount: float
    currency: str
    frequency: str  # "monthly" or "yearly"
    day_of_month: int  # 1-31
    start_date: str  # "YYYY-MM-DD"
    end_date: str = ""  # "YYYY-MM-DD" or empty for open-ended
    active: bool = True
    last_generated: str = ""  # "YYYY-MM-DD" or empty
    next_date: str = ""  # "YYYY-MM-DD" computed
    created_at: datetime = Field(default_factory=datetime.now)


class RecurringRuleCreate(BaseModel):
    name: str
    account_id: str
    category: str
    amount: float
    currency: str
    frequency: str
    day_of_month: int = 1
    start_date: str
    end_date: str = ""


class RecurringRunResult(BaseModel):
    generated: int
    rules: list[RecurringRule]


class Transfer(BaseModel):
    id: str
    from_account_id: str
    to_account_id: str
    amount: float
    currency: str
    fee: float = 0.0
    date: date
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class TransferCreate(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float
    currency: str
    fee: float = 0.0
    date: str
    note: str = ""


class SavingsPlanner(BaseModel):
    id: str
    currency: str
    linked_account_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class SavingsPlannerLink(BaseModel):
    account_id: str


class SavingsReserve(BaseModel):
    id: str
    planner_id: str
    name: str
    icon: str = "🏦"
    allocated: float = 0.0
    floor: Optional[float] = None  # None = no floor (sinking fund)
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class SavingsReserveCreate(BaseModel):
    name: str
    icon: str = "🏦"
    allocated: float = 0.0
    floor: Optional[float] = None


class SavingsReserveUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    allocated: Optional[float] = None
    floor: Optional[float] = None


class SavingsGoal(BaseModel):
    id: str
    planner_id: str
    name: str
    icon: str = "🎯"
    target: float
    allocated: float = 0.0
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


class SavingsGoalCreate(BaseModel):
    name: str
    icon: str = "🎯"
    target: float = Field(gt=0)
    allocated: float = 0.0


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    target: Optional[float] = None
    allocated: Optional[float] = None
    position: Optional[int] = None


class SavingsMove(BaseModel):
    from_bucket: str  # "unallocated" or bucket id
    to_bucket: str  # "unallocated" or bucket id
    amount: float = Field(gt=0)


class SavingsAllocateItem(BaseModel):
    to_bucket: str
    amount: float = Field(gt=0)


class SavingsAllocate(BaseModel):
    allocations: list[SavingsAllocateItem]


class SavingsActivity(BaseModel):
    id: str
    planner_id: str
    type: str
    amount: float = 0.0
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
