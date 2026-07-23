# Design Spec: Budget Tab, Accounts → Goals, Dashboard Improvements

Date: 2026-07-24
Status: Approved — Ready for implementation

---

## Feature 1: Budget Tab

### Overview

Redesign the Budgets page to support per-category budgets with progress tracking. Users set a total monthly budget and individual category budgets. Each category shows a color-coded progress bar indicating spending status.

### Backend Changes

**No model changes needed.** The `Category` model already has `budget_amount: float` and `budget_currency: str` fields. These are currently unused in the UI.

**New endpoint: `PUT /api/categories/{id}/budget`**

Request body:
```json
{
  "budget_amount": 945.00,
  "budget_currency": "PHP"
}
```

Updates a single category's budget. Validates that `budget_amount >= 0`.

**New endpoint: `GET /api/budgets/{month}/summary`**

Returns a computed summary for the given month (YYYY-MM format):

```json
{
  "month": "2026-07",
  "total_budget": 1995.00,
  "total_spent": 1150.00,
  "categories": [
    {
      "name": "Rent",
      "group": "Fixed",
      "budget": 945.00,
      "currency": "PHP",
      "spent": 970.00
    },
    {
      "name": "Groceries",
      "group": "Essential",
      "budget": 200.00,
      "currency": "PHP",
      "spent": 180.00
    }
  ]
}
```

Logic:
- `total_budget` = sum of all expense categories' `budget_amount` values
- `total_spent` = sum of expense transactions in the month
- `spent` per category = sum of expense transactions in that category for the month
- Categories with `budget_amount == 0` are excluded from the categories array
- Categories are grouped by their `group` field

### Frontend: Budgets.vue

**Layout structure:**

1. **Header row** — Month selector (left arrow / month name / right arrow) + total budget card
2. **Total budget card** — Large card showing:
   - "Total Budget" label
   - Total spent / Total budget (e.g., "₱1,150 / ₱1,995")
   - Large progress bar (full width)
   - Percentage text (e.g., "57.6% spent")
3. **Category groups** — Each group (Fixed, Essential, Lifestyle, School, Misc, Sinking) as a section:
   - Group header: group name + group spent / group budget summary
   - Collapsible: click header to expand/collapse category cards
   - Default: all groups expanded
4. **Category cards** — Within each group, each category as a card:
   - Category name (left) + budget amount (right, inline editable)
   - Progress bar (color-coded)
   - Spent / Budget text below bar (e.g., "₱970 / ₱945")

**Progress bar color thresholds:**
- Green (`kangkong-500`): spent < 70% of budget
- Orange (`carrot-500`): spent 70-90% of budget
- Red (`tomato-500`): spent > 90% of budget

**Inline editing:**
- Click the budget amount text → input field appears with current value
- Enter → save via `PUT /api/categories/{id}/budget`
- Escape → cancel, restore original text
- Click outside → save

**Month navigation:**
- Previous/next arrows
- Current month displayed as "July 2026"
- Persisted in localStorage (`budgets-month`)

### Data Flow

1. Component mounts → fetch `GET /api/budgets/{month}/summary`
2. Summary provides per-category budget + spent data
3. User edits a category budget → `PUT /api/categories/{id}/budget` → re-fetch summary
4. Month change → re-fetch summary for new month

### Default Category Budgets

Initial budget amounts (from user's reference data):

| Category | Group | Budget | Currency |
|----------|-------|-------:|----------|
| Rent | Fixed | 945 | PHP |
| Electricity | Fixed | 100 | PHP |
| Gas | Fixed | 30 | PHP |
| Subscriptions | Fixed | 30 | PHP |
| Groceries | Essential | 200 | PHP |
| Household | Essential | 60 | PHP |
| Transportation | Essential | 100 | PHP |
| Medical | Essential | 50 | PHP |
| Eating Out | Lifestyle | 150 | PHP |
| Social Events | Lifestyle | 50 | PHP |
| Hobbies | Lifestyle | 50 | PHP |
| School Supplies | Sinking | 50 | PHP |
| Shopping | Sinking | 50 | PHP |
| Beauty | Sinking | 50 | PHP |
| Travel | Sinking | 50 | PHP |
| Others | Sinking | 30 | PHP |

These will be set via the PUT endpoint during initial seeding or first user interaction.

---

## Feature 2: Accounts → Savings Goals

### Overview

Redesign the Accounts page from a simple account list into a Savings Goals dashboard. Savings and Time Deposit accounts get goal cards with progress bars. Other account types show simple balance cards.

### Backend Changes

**Model change: `Account`** — add `goal_amount: float = 0.0` field.

Updated Account model:
```python
class Account(BaseModel):
    id: str
    name: str
    type: str
    currency: str
    initial_balance: float = 0.0
    goal_amount: float = 0.0  # NEW
    sub_accounts: list[SubAccount] = []
    created_at: datetime = Field(default_factory=datetime.now)
```

**New endpoint: `PUT /api/accounts/{id}/goal`**

Request body:
```json
{
  "goal_amount": 50000.00
}
```

Updates only the `goal_amount` field. Validates `goal_amount >= 0`.

**Migration:** Existing accounts in `data.json` will get `goal_amount: 0.0` by default (Pydantic default). No data migration needed.

### Frontend: Accounts.vue

**Layout (redesigned):**

1. **Section: US Accounts**
   - Section header: "🇺🇸 US Accounts" + total balance summary
   - **Goal Cards** (Savings + Time Deposits) — each as:
     - Left-border color stripe (savings=`kangkong`, time_deposit=`mango`)
     - Account name (bold) + type badge
     - Current balance (large font, e.g., "$12,345.00")
     - Goal progress bar + " $X / $Y · Z%" text
     - If goal is 0: show "Set goal" link instead of progress bar
   - **Other Accounts** (Checking, Investment) — simple cards:
     - Account name + type badge
     - Current balance
     - Sub-accounts listed if investment type

2. **Section: Philippine Accounts**
   - Same structure as US Accounts
   - PHP currency amounts

**Card design:**
- `card-elevated` with left-border color by account type
- Balance in `text-2xl font-semibold`
- Progress bar: full width, 8px height, rounded
- Goal text: `text-xs text-mushroom-500`

**Goal editing UX:**
- Click the goal amount text → inline input appears (pre-filled with current value)
- Enter → `PUT /api/accounts/{id}/goal` → re-fetch accounts → re-render
- Escape → cancel, restore original text
- Accounts with `goal_amount == 0` show a subtle "Set goal" link

**Progress bar colors (goal-based):**
- Green (`kangkong-500`): balance ≥ 70% of goal
- Orange (`carrot-500`: balance 40-70% of goal
- Red (`tomato-500`): balance < 40% of goal

**Data source:** Use existing `GET /api/balance` endpoint which computes current balances from `initial_balance + transactions`.

---

## Feature 3: Dashboard Improvements

### 3a. Exchange Rate Card (TopBar)

**Current:** Shows "1 USD = ₱XX.XX" in TopBar.

**Changes:**
- **Hover** → tooltip appears: "Source: open.er-api.com"
- **Click** → opens `https://open.er-api.com` in new browser tab
- No other changes to the exchange rate display

**Implementation:**
- Add `title` attribute for hover tooltip
- Add `@click` handler with `window.open()`
- Style cursor as `cursor-pointer`

### 3b. Net Worth Tooltip (TopBar)

**Current:** Shows total net worth in TopBar.

**Changes:** Hover over Net Worth card → floating tooltip showing account breakdown.

**Tooltip content:**
```
Net Worth Breakdown

🇺🇸 US Accounts
  Bank of America Savings    $12,345.00
  Bank of America Checking    $5,678.00

🇵🇭 Philippine Accounts
  BPI Savings                ₱45,000.00
  Maya Savings               ₱12,000.00

Total (USD)                 $XX,XXX.XX
```

**Implementation:**
- Tooltip appears on hover (CSS `group-hover` or Vue `@mouseenter`/`@mouseleave`)
- Positions below the TopBar
- Uses existing `useSummary().balances` data
- Non-blocking: pointer-events on tooltip, disappears on mouse leave
- Styled with `card-elevated` + `shadow-lg` + `z-50`

### 3c. Monthly Trends Chart Legend

**Current:** Chart.js default legend (two colored squares + labels).

**Changes:** Custom interactive legend below the chart.

**Behavior:**
- Two legend items: "● Income" (green) and "● Expenses" (red)
- **Click Income** → hide Expenses line, show only Income line
- **Click Income again** → restore both lines
- Same for Expenses
- Active state: full opacity + bold text
- Inactive state: 40% opacity + normal text

**Implementation:**
- Disable Chart.js default legend
- Render custom legend div below the chart
- Toggle visibility by updating dataset `hidden` property
- Use `chart.update()` to re-render

### 3d. AI Insights Widget

**Location:** New card on Dashboard, below the monthly trends chart.

**Data sources (all local, no API calls):**
- Spending trends: month-over-month changes by category
- Unusual spending: transactions > 2x rolling 3-month average for that category
- Budget warnings: categories where spent > 90% of budget
- Savings milestones: net worth crossed a round number threshold
- Top spending categories this month (top 3)
- Category breakdown: which categories consumed the most budget

**Card design:**
- Title: "💡 Insights" with lightbulb icon
- 3-5 insight items, each as a row with:
  - Icon (trend arrow, warning triangle, etc.)
  - Short text (e.g., "Groceries spending up 23% vs last month")
  - Subtle color coding (green for positive, orange for warning, red for alert)
- Empty state: "No insights available yet — add more transactions to see patterns"

**Composable:** `useInsights(transactions, budgets, balances)` — pure function that computes insights from existing data. No API calls.

**Insight types:**

1. **Spending trend** — "Groceries up 23% vs last month" (compare current vs previous month)
2. **Unusual spending** — "Uber charge of ₱2,500 is 3x your average" (amount > 2x rolling average)
3. **Budget warning** — "Eating Out at 92% of budget" (spent/budget > 0.9)
4. **Savings milestone** — "Net worth crossed $20,000" (round number threshold)
5. **Top spender** — "Rent consumed 47% of your budget this month" (highest budget percentage)
6. **Month comparison** — "You spent 15% less this month vs last month" (overall comparison)

---

## Shared Patterns

### Inline Editing

Both Budgets and Accounts use the same inline editing pattern:

```vue
<template v-if="editing">
  <input
    v-model="editValue"
    @keyup.enter="save"
    @keyup.escape="cancel"
    @blur="save"
    class="input-field text-sm py-0.5 px-1 w-24"
    type="number"
    step="0.01"
    min="0"
    autofocus
  />
</template>
<template v-else>
  <span @click="startEdit" class="cursor-pointer hover:text-kangkong-600">
    {{ formatAmount(value) }}
  </span>
</template>
```

### Progress Bar Component

Reuse `BudgetProgressBar.vue` with props:
- `spent: number`
- `budget: number`
- `thresholds?: { green: 0.7, orange: 0.9 }` (configurable)

Returns color based on `spent / budget` ratio.

### Card Styling

All new cards use existing `card-elevated` class:
```css
.card-elevated {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04);
}
```

---

## Implementation Order

1. **Budget Tab** — Backend endpoints + Budgets.vue redesign
2. **Accounts → Goals** — Backend goal field + Accounts.vue redesign
3. **Dashboard improvements** — TopBar tooltip + chart legend + AI insights widget

Each feature is independently deployable. No cross-feature dependencies.
