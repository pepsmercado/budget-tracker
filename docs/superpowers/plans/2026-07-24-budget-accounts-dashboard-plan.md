# Budget Tab, Accounts → Goals, Dashboard Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-category budgets with progress bars, redesign accounts as savings goals dashboard, and improve the dashboard with tooltips, interactive chart legend, and AI insights.

**Architecture:** Backend gets two new endpoints (category budget update, budget summary) and one model change (Account.goal_amount). Frontend gets three redesigned views (Budgets, Accounts, Dashboard) and one new composable (useInsights).

**Tech Stack:** Python FastAPI, Pydantic, Vue 3 Composition API, Tailwind CSS 4, Chart.js (vue-chartjs)

## Global Constraints

- Python 3.14+, FastAPI, Pydantic v2
- Vue 3.5+ with `<script setup>`, Vite 8, Tailwind CSS 4 (`@tailwindcss/vite`)
- Chart.js via vue-chartjs
- No Pinia/Vuex — use composables with `ref()` state
- Toge Design System: Geist font, mushroom/kangkong/tomato palette, `.card-elevated`, `.btn-primary`, `.input-field`, `.select-field`
- Backend persists to `backend/data.json` via `_save()`/`_load()` on MockBackend
- Currency: PHP and USD

---

## File Structure

### Modified Files
- `backend/models.py` — Add `goal_amount` to Account
- `backend/services/base.py` — Add abstract methods for budget summary + account goal
- `backend/services/mock.py` — Implement budget summary + account goal methods
- `backend/routers/categories.py` — Add `PUT /categories/{id}/budget`
- `backend/routers/budgets.py` — Add `GET /budgets/{month}/summary`
- `backend/routers/accounts.py` — Add `PUT /accounts/{id}/goal`
- `src/components/BudgetProgressBar.vue` — Add configurable thresholds prop
- `src/composables/useBudgets.js` — Add `fetchBudgetSummary`
- `src/composables/useAccounts.js` — Add `updateAccountGoal`
- `src/views/Budgets.vue` — Full redesign
- `src/views/Accounts.vue` — Full redesign
- `src/views/Dashboard.vue` — Add chart legend toggle + AI insights
- `src/components/TopBar.vue` — Add tooltips

### Created Files
- `src/composables/useInsights.js` — AI insights computation

---

## Feature 1: Budget Tab

### Task 1: Backend — Category budget update endpoint

**Files:**
- Modify: `backend/services/base.py:44-57`
- Modify: `backend/services/mock.py:237-258`
- Modify: `backend/routers/categories.py`

**Interfaces:**
- Consumes: `Category.budget_amount`, `Category.budget_currency` (existing fields)
- Produces: `update_category_budget(category_id, budget_amount, budget_currency) -> Category`

- [ ] **Step 1: Add abstract method to base service**

Add after `delete_category` in `backend/services/base.py`:

```python
@abstractmethod
def update_category_budget(self, category_id: str, budget_amount: float, budget_currency: str) -> Category:
    pass
```

- [ ] **Step 2: Add Pydantic model for budget update**

Add to `backend/models.py` after `CategoryCreate`:

```python
class CategoryBudgetUpdate(BaseModel):
    budget_amount: float = Field(ge=0)
    budget_currency: str = "PHP"
```

- [ ] **Step 3: Implement in MockBackend**

Add to `backend/services/mock.py` after `delete_category`:

```python
def update_category_budget(self, category_id: str, budget_amount: float, budget_currency: str) -> Category:
    if category_id not in self.categories:
        raise KeyError("Category not found")
    c = self.categories[category_id]
    c.budget_amount = budget_amount
    c.budget_currency = budget_currency
    self._save()
    return c
```

- [ ] **Step 4: Add router endpoint**

Add to `backend/routers/categories.py`:

```python
from models import CategoryCreate, CategoryBudgetUpdate

@router.put("/categories/{category_id}/budget")
def update_category_budget(category_id: str, data: CategoryBudgetUpdate):
    try:
        return backend.update_category_budget(category_id, data.budget_amount, data.budget_currency)
    except KeyError:
        raise HTTPException(status_code=404, detail="Category not found")
```

- [ ] **Step 5: Test endpoint**

Run: `curl -s http://localhost:8000/api/categories | python3 -c "import json,sys; cats=json.load(sys.stdin); print(cats[0]['id'], cats[0]['budget_amount'])"`

Expected: Shows category ID and current budget amount.

Run: `curl -s -X PUT http://localhost:8000/api/categories/CATEGORY_ID/budget -H 'Content-Type: application/json' -d '{"budget_amount": 999, "budget_currency": "PHP"}' | python3 -m json.tool`

Expected: Returns updated category with `budget_amount: 999`.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/services/base.py backend/services/mock.py backend/routers/categories.py
git commit -m "feat: add category budget update endpoint"
```

---

### Task 2: Backend — Budget summary endpoint

**Files:**
- Modify: `backend/services/base.py:60-66`
- Modify: `backend/services/mock.py:260-276`
- Modify: `backend/routers/budgets.py`

**Interfaces:**
- Consumes: `Category.budget_amount`, transactions filtered by date/category
- Produces: `get_budget_summary(month: str) -> dict` with `total_budget`, `total_spent`, `categories[]`

- [ ] **Step 1: Add Pydantic model for budget summary**

Add to `backend/models.py`:

```python
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
```

- [ ] **Step 2: Add abstract method to base service**

Add to `backend/services/base.py` after `set_budget`:

```python
@abstractmethod
def get_budget_summary(self, month: str) -> BudgetSummary:
    pass
```

- [ ] **Step 3: Implement in MockBackend**

Add to `backend/services/mock.py` after `set_budget`:

```python
def get_budget_summary(self, month: str) -> BudgetSummary:
    from models import CategoryBudgetSummary, BudgetSummary
    year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    start = date(year, mon, 1)
    if mon == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, mon + 1, 1)

    exp_cats = [c for c in self.categories.values() if c.type == "expense"]
    cat_spent = {c.name: 0.0 for c in exp_cats}
    for t in self.transactions.values():
        if t.type == "expense" and start <= t.date < end:
            cat_spent[t.category] = cat_spent.get(t.category, 0) + t.amount

    categories = []
    for c in exp_cats:
        if c.budget_amount > 0:
            categories.append(CategoryBudgetSummary(
                name=c.name, group=c.group, budget=c.budget_amount,
                currency=c.budget_currency, spent=round(cat_spent.get(c.name, 0), 2),
            ))

    total_budget = sum(c.budget for c in categories)
    total_spent = sum(c.spent for c in categories)

    return BudgetSummary(
        month=month, total_budget=round(total_budget, 2),
        total_spent=round(total_spent, 2), categories=categories,
    )
```

- [ ] **Step 4: Add router endpoint**

Add to `backend/routers/budgets.py`:

```python
@router.get("/budgets/{month}/summary")
def get_budget_summary(month: str):
    return backend.get_budget_summary(month)
```

- [ ] **Step 5: Test endpoint**

Run: `curl -s http://localhost:8000/api/budgets/2026-07/summary | python3 -m json.tool | head -20`

Expected: Returns JSON with `month`, `total_budget`, `total_spent`, `categories` array.

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/services/base.py backend/services/mock.py backend/routers/budgets.py
git commit -m "feat: add budget summary endpoint with per-category spending"
```

---

### Task 3: Frontend — Update BudgetProgressBar with thresholds

**Files:**
- Modify: `src/components/BudgetProgressBar.vue`

**Interfaces:**
- Consumes: `spent`, `budget`, `thresholds` (optional)
- Produces: Color-coded progress bar

- [ ] **Step 1: Update BudgetProgressBar.vue**

Replace `src/components/BudgetProgressBar.vue` with:

```vue
<script setup>
import { computed } from 'vue'

const props = defineProps({
  spent: { type: Number, default: 0 },
  budget: { type: Number, default: 0 },
  greenThreshold: { type: Number, default: 0.7 },
  orangeThreshold: { type: Number, default: 0.9 },
})

const percentage = computed(() => props.budget > 0 ? Math.min((props.spent / props.budget) * 100, 100) : 0)
const ratio = computed(() => props.budget > 0 ? props.spent / props.budget : 0)
const colorClass = computed(() => {
  if (ratio.value < props.greenThreshold) return 'bg-kangkong-500'
  if (ratio.value < props.orangeThreshold) return 'bg-carrot-500'
  return 'bg-tomato-500'
})
</script>

<template>
  <div class="w-full bg-mushroom-100 rounded-full h-2">
    <div
      class="h-2 rounded-full transition-all duration-500 ease-out"
      :class="colorClass"
      :style="{ width: percentage + '%' }"
    ></div>
  </div>
</template>
```

- [ ] **Step 2: Verify no regressions**

Check that existing Budgets.vue progress bar still works (same default thresholds as before are slightly different but acceptable).

- [ ] **Step 3: Commit**

```bash
git add src/components/BudgetProgressBar.vue
git commit -m "feat: add configurable thresholds to BudgetProgressBar"
```

---

### Task 4: Frontend — Update useBudgets composable

**Files:**
- Modify: `src/composables/useBudgets.js`

**Interfaces:**
- Consumes: `GET /api/budgets/{month}/summary`
- Produces: `fetchBudgetSummary(month)` → `budgetSummary` ref

- [ ] **Step 1: Add fetchBudgetSummary to useBudgets.js**

Replace `src/composables/useBudgets.js` with:

```javascript
import { ref } from 'vue'
import api from '../api'

export function useBudgets() {
  const budget = ref(null)
  const loading = ref(false)
  const budgetSummary = ref(null)

  async function fetchBudget(month) {
    loading.value = true
    try {
      const { data } = await api.get(`/budgets/${month}`)
      budget.value = data
    } finally {
      loading.value = false
    }
  }

  async function setBudget(month, payload) {
    const { data } = await api.put(`/budgets/${month}`, payload)
    budget.value = data
    return data
  }

  async function fetchBudgetSummary(month) {
    loading.value = true
    try {
      const { data } = await api.get(`/budgets/${month}/summary`)
      budgetSummary.value = data
    } finally {
      loading.value = false
    }
  }

  return { budget, loading, budgetSummary, fetchBudget, setBudget, fetchBudgetSummary }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/composables/useBudgets.js
git commit -m "feat: add fetchBudgetSummary to useBudgets composable"
```

---

### Task 5: Frontend — Redesign Budgets.vue

**Files:**
- Modify: `src/views/Budgets.vue`

**Interfaces:**
- Consumes: `useBudgets().fetchBudgetSummary`, `useBudgets().budgetSummary`, `BudgetProgressBar`
- Produces: Full Budgets page with month nav, total card, grouped category cards

- [ ] **Step 1: Replace Budgets.vue**

Replace entire `src/views/Budgets.vue` with:

```vue
<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useBudgets } from '../composables/useBudgets'
import { useAccounts } from '../composables/useAccounts'
import api from '../api'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'

const { budgetSummary, fetchBudgetSummary, fetchBudget, setBudget } = useBudgets()
const { accounts, fetchAccounts } = useAccounts()

const now = new Date()
const selectedMonth = ref(localStorage.getItem('budgets-month') || `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`)
const categories = ref([])
const editingCategory = ref(null)
const editValue = ref(0)
const collapsedGroups = ref({})
const loadingCatBudget = ref(null)

const monthLabel = computed(() => {
  const [y, m] = selectedMonth.value.split('-')
  return new Date(parseInt(y), parseInt(m) - 1).toLocaleString('en-US', { month: 'long', year: 'numeric' })
})

const groupedCategories = computed(() => {
  if (!budgetSummary.value?.categories) return {}
  const groups = {}
  for (const cat of budgetSummary.value.categories) {
    if (!groups[cat.group]) groups[cat.group] = []
    groups[cat.group].push(cat)
  }
  return groups
})

const groupOrder = ['Fixed', 'Essential', 'Lifestyle', 'School', 'Misc', 'Sinking']
const sortedGroups = computed(() => {
  return groupOrder.filter(g => groupedCategories.value[g])
})

function groupSpent(group) {
  return (groupedCategories.value[group] || []).reduce((s, c) => s + c.spent, 0)
}

function groupBudget(group) {
  return (groupedCategories.value[group] || []).reduce((s, c) => s + c.budget, 0)
}

function prevMonth() {
  const [y, m] = selectedMonth.value.split('-').map(Number)
  const d = new Date(y, m - 2, 1)
  selectedMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function nextMonth() {
  const [y, m] = selectedMonth.value.split('-').map(Number)
  const d = new Date(y, m, 1)
  selectedMonth.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function toggleGroup(group) {
  collapsedGroups.value[group] = !collapsedGroups.value[group]
}

function startEdit(cat) {
  editingCategory.value = cat.name
  editValue.value = cat.budget
}

async function saveEdit(cat) {
  loadingCatBudget.value = cat.name
  const catObj = categories.value.find(c => c.name === cat.name)
  if (catObj) {
    await api.put(`/categories/${catObj.id}/budget`, {
      budget_amount: editValue.value,
      budget_currency: cat.currency || 'PHP'
    })
  }
  editingCategory.value = null
  await fetchBudgetSummary(selectedMonth.value)
  loadingCatBudget.value = null
}

function cancelEdit() {
  editingCategory.value = null
}

function formatAmount(val, currency) {
  if (currency === 'USD') return `$${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
  return `₱${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

onMounted(async () => {
  const { data } = await api.get('/categories')
  categories.value = data
  await fetchBudgetSummary(selectedMonth.value)
})

watch(selectedMonth, (val) => {
  localStorage.setItem('budgets-month', val)
  fetchBudgetSummary(val)
})
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950">Budget</h2>
      <div class="flex items-center gap-2">
        <button @click="prevMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 text-mushroom-500 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <span class="text-sm font-medium text-mushroom-700 min-w-[120px] text-center">{{ monthLabel }}</span>
        <button @click="nextMonth" class="p-1.5 rounded-lg hover:bg-mushroom-100 text-mushroom-500 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
        </button>
      </div>
    </div>

    <div v-if="budgetSummary" class="card-elevated p-5">
      <div class="flex items-center justify-between mb-3">
        <div>
          <div class="text-xs text-mushroom-400">Total Budget</div>
          <div class="text-2xl font-semibold text-mushroom-950">
            {{ formatAmount(budgetSummary.total_spent, 'PHP') }}
            <span class="text-sm font-normal text-mushroom-400">/ {{ formatAmount(budgetSummary.total_budget, 'PHP') }}</span>
          </div>
        </div>
        <div class="text-right">
          <div class="text-xs text-mushroom-400">Remaining</div>
          <div class="text-sm font-semibold" :class="budgetSummary.total_spent > budgetSummary.total_budget ? 'text-tomato-600' : 'text-kangkong-700'">
            {{ formatAmount(Math.max(0, budgetSummary.total_budget - budgetSummary.total_spent), 'PHP') }}
          </div>
        </div>
      </div>
      <BudgetProgressBar :spent="budgetSummary.total_spent" :budget="budgetSummary.total_budget" />
      <div class="mt-2 text-right text-xs text-mushroom-400">
        {{ budgetSummary.total_budget > 0 ? ((budgetSummary.total_spent / budgetSummary.total_budget) * 100).toFixed(1) : 0 }}% spent
      </div>
    </div>

    <div v-if="budgetSummary" class="space-y-3">
      <div v-for="group in sortedGroups" :key="group" class="card-elevated overflow-hidden">
        <button
          @click="toggleGroup(group)"
          class="w-full flex items-center justify-between px-5 py-3 hover:bg-mushroom-50 transition-colors"
        >
          <div class="flex items-center gap-2">
            <svg
              width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
              class="text-mushroom-400 transition-transform duration-200"
              :class="collapsedGroups[group] ? '' : 'rotate-90'"
            ><path d="M9 18l6-6-6-6"/></svg>
            <span class="text-sm font-medium text-mushroom-800">{{ group }}</span>
          </div>
          <div class="flex items-center gap-3 text-xs">
            <span class="text-mushroom-500">{{ formatAmount(groupSpent(group), 'PHP') }} / {{ formatAmount(groupBudget(group), 'PHP') }}</span>
            <BudgetProgressBar :spent="groupSpent(group)" :budget="groupBudget(group)" class="w-20" />
          </div>
        </button>

        <div v-if="!collapsedGroups[group]" class="border-t border-mushroom-100">
          <div v-for="cat in groupedCategories[group]" :key="cat.name" class="px-5 py-3 border-b border-mushroom-50 last:border-b-0">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm text-mushroom-700">{{ cat.name }}</span>
              <div class="flex items-center gap-2">
                <template v-if="editingCategory === cat.name">
                  <input
                    v-model.number="editValue"
                    @keyup.enter="saveEdit(cat)"
                    @keyup.escape="cancelEdit"
                    @blur="saveEdit(cat)"
                    type="number"
                    step="1"
                    min="0"
                    class="input-field text-sm py-0.5 px-2 w-24"
                    autofocus
                  />
                </template>
                <template v-else>
                  <span
                    @click="startEdit(cat)"
                    class="cursor-pointer hover:text-kangkong-600 text-sm font-medium text-mushroom-700"
                  >
                    {{ formatAmount(cat.budget, cat.currency) }}
                  </span>
                </template>
              </div>
            </div>
            <BudgetProgressBar :spent="cat.spent" :budget="cat.budget" />
            <div class="mt-1 text-xs text-mushroom-400 text-right">
              {{ formatAmount(cat.spent, cat.currency) }} / {{ formatAmount(cat.budget, cat.currency) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-12 text-mushroom-400 text-sm">Loading budget data...</div>
  </div>
</template>
```

- [ ] **Step 2: Test in browser**

Navigate to `http://localhost:5173/budgets`. Verify:
- Month navigation works (prev/next arrows)
- Total budget card shows correct totals
- Category groups appear with headers
- Inline editing works (click amount → type new value → Enter)
- Progress bars are color-coded correctly

- [ ] **Step 3: Commit**

```bash
git add src/views/Budgets.vue
git commit -m "feat: redesign Budgets page with grouped category cards and progress bars"
```

---

## Feature 2: Accounts → Savings Goals

### Task 6: Backend — Add goal_amount to Account

**Files:**
- Modify: `backend/models.py:12-19`
- Modify: `backend/services/mock.py:82-86`

**Interfaces:**
- Consumes: `Account.goal_amount` (new field, default 0.0)
- Produces: `update_account_goal(account_id, goal_amount) -> Account`

- [ ] **Step 1: Add goal_amount to Account model**

In `backend/models.py`, add after `initial_balance` in `Account`:

```python
class Account(BaseModel):
    id: str
    name: str
    type: str
    currency: str
    initial_balance: float = 0.0
    goal_amount: float = 0.0
    sub_accounts: list[SubAccount] = []
    created_at: datetime = Field(default_factory=datetime.now)
```

- [ ] **Step 2: Add GoalUpdate model**

Add to `backend/models.py` after `AccountCreate`:

```python
class AccountGoalUpdate(BaseModel):
    goal_amount: float = Field(ge=0)
```

- [ ] **Step 3: Add abstract method to base service**

Add to `backend/services/base.py` after `delete_account`:

```python
@abstractmethod
def update_account_goal(self, account_id: str, goal_amount: float) -> Account:
    pass
```

- [ ] **Step 4: Implement in MockBackend**

Add to `backend/services/mock.py` after `delete_account`:

```python
def update_account_goal(self, account_id: str, goal_amount: float) -> Account:
    if account_id not in self.accounts:
        raise KeyError("Account not found")
    self.accounts[account_id].goal_amount = goal_amount
    self._save()
    return self.accounts[account_id]
```

- [ ] **Step 5: Add router endpoint**

Add to `backend/routers/accounts.py`:

```python
from models import AccountCreate, AccountGoalUpdate

@router.put("/accounts/{account_id}/goal")
def update_account_goal(account_id: str, data: AccountGoalUpdate):
    try:
        return backend.update_account_goal(account_id, data.goal_amount)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")
```

- [ ] **Step 6: Test endpoint**

Run: `curl -s http://localhost:8000/api/accounts | python3 -c "import json,sys; a=json.load(sys.stdin); print(a[0]['id'], a[0].get('goal_amount', 'MISSING'))"`

Expected: Shows account ID and `goal_amount: 0.0` (or missing if not yet loaded — old data.json).

Run: `curl -s -X PUT http://localhost:8000/api/accounts/ACCOUNT_ID/goal -H 'Content-Type: application/json' -d '{"goal_amount": 50000}' | python3 -m json.tool`

Expected: Returns account with `goal_amount: 50000`.

- [ ] **Step 7: Commit**

```bash
git add backend/models.py backend/services/base.py backend/services/mock.py backend/routers/accounts.py
git commit -m "feat: add goal_amount to Account model and PUT goal endpoint"
```

---

### Task 7: Frontend — Update useAccounts composable

**Files:**
- Modify: `src/composables/useAccounts.js`

**Interfaces:**
- Consumes: `PUT /api/accounts/{id}/goal`
- Produces: `updateAccountGoal(id, goalAmount)` → updates account in local state

- [ ] **Step 1: Add updateAccountGoal to useAccounts.js**

Add after `deleteAccount` in `src/composables/useAccounts.js`:

```javascript
async function updateAccountGoal(id, goalAmount) {
  const { data } = await api.put(`/accounts/${id}/goal`, { goal_amount: goalAmount })
  const idx = accounts.value.findIndex(a => a.id === id)
  if (idx !== -1) accounts.value[idx] = data
  return data
}
```

Update the return statement:

```javascript
return { accounts, loading, fetchAccounts, createAccount, updateAccount, deleteAccount, updateAccountGoal }
```

- [ ] **Step 2: Commit**

```bash
git add src/composables/useAccounts.js
git commit -m "feat: add updateAccountGoal to useAccounts composable"
```

---

### Task 8: Frontend — Redesign Accounts.vue as Savings Goals

**Files:**
- Modify: `src/views/Accounts.vue`

**Interfaces:**
- Consumes: `useAccounts().updateAccountGoal`, `useSummary().balances`
- Produces: Savings Goals dashboard with goal cards + progress bars

- [ ] **Step 1: Replace Accounts.vue**

Replace entire `src/views/Accounts.vue` with:

```vue
<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAccounts } from '../composables/useAccounts'
import { useSummary } from '../composables/useSummary'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'

const { accounts, loading, fetchAccounts, createAccount, deleteAccount, updateAccount, updateAccountGoal } = useAccounts()
const { balances, fetchBalances } = useSummary()

const showForm = ref(false)
const form = ref({ name: '', type: 'savings', currency: 'PHP', initial_balance: 0 })
const eyeHidden = ref(false)
const editingGoal = ref(null)
const goalValue = ref(0)

const goalTypes = ['savings', 'time_deposit']

const accountTypeLabels = {
  savings: 'Savings',
  checking: 'Checking',
  time_deposit: 'Time Deposit',
  investment: 'Investment',
  credit_card: 'Credit Card',
}

const accountTypeColors = {
  savings: 'border-l-kangkong-500',
  checking: 'border-l-blueberry-500',
  time_deposit: 'border-l-mango-500',
  investment: 'border-l-ubas-500',
}

const currencyLabels = { USD: '🇺🇸 US Accounts', PHP: '🇵🇭 Philippine Accounts' }
const currencyOrder = ['USD', 'PHP']

const groupedAccounts = computed(() => {
  const groups = {}
  for (const acc of accounts.value) {
    const currency = acc.currency || 'PHP'
    if (!groups[currency]) groups[currency] = []
    groups[currency].push(acc)
  }
  const sorted = {}
  for (const curr of currencyOrder) {
    if (groups[curr]) sorted[curr] = groups[curr]
  }
  for (const curr of Object.keys(groups).sort()) {
    if (!sorted[curr]) sorted[curr] = groups[curr]
  }
  return sorted
})

function getBalance(accountId) {
  const b = balances.value.find(x => x.account_id === accountId)
  return b ? b.balance : 0
}

function formatCurrency(val, currency) {
  if (eyeHidden.value) return '***'
  if (currency === 'USD') return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
  return `₱${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
}

function goalProgress(balance, goal) {
  if (!goal || goal <= 0) return 0
  return Math.min((balance / goal) * 100, 100)
}

function startEditGoal(acc) {
  editingGoal.value = acc.id
  goalValue.value = acc.goal_amount || 0
}

async function saveGoal(acc) {
  await updateAccountGoal(acc.id, goalValue.value)
  editingGoal.value = null
}

function cancelGoal() {
  editingGoal.value = null
}

onMounted(async () => {
  await Promise.all([fetchAccounts(), fetchBalances()])
})

async function handleCreate() {
  await createAccount(form.value)
  showForm.value = false
  form.value = { name: '', type: 'savings', currency: 'PHP', initial_balance: 0 }
  await fetchBalances()
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950">Savings Goals</h2>
      <div class="flex items-center gap-3">
        <button @click="eyeHidden = !eyeHidden" class="text-mushroom-400 hover:text-mushroom-600">
          <svg v-if="!eyeHidden" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
        </button>
        <button @click="showForm = !showForm" class="btn-primary text-xs">
          {{ showForm ? 'Cancel' : '+ Add Account' }}
        </button>
      </div>
    </div>

    <form v-if="showForm" @submit.prevent="handleCreate" class="card-elevated p-5 space-y-3">
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label-text">Account Name</label>
          <input v-model="form.name" placeholder="e.g. BPI Savings" required class="input-field" />
        </div>
        <div>
          <label class="label-text">Type</label>
          <select v-model="form.type" class="select-field">
            <option value="savings">Savings</option>
            <option value="checking">Checking</option>
            <option value="time_deposit">Time Deposit</option>
            <option value="investment">Investment</option>
          </select>
        </div>
        <div>
          <label class="label-text">Currency</label>
          <select v-model="form.currency" required class="select-field">
            <option value="PHP">PHP</option>
            <option value="USD">USD</option>
          </select>
        </div>
        <div>
          <label class="label-text">Initial Balance</label>
          <input v-model.number="form.initial_balance" type="number" step="0.01" class="input-field" />
        </div>
      </div>
      <button type="submit" class="btn-secondary text-xs">Create Account</button>
    </form>

    <div v-if="loading" class="text-center text-mushroom-400 py-8 text-sm">Loading...</div>

    <div v-else class="space-y-6">
      <div v-for="currency in currencyOrder" :key="currency" v-show="groupedAccounts[currency]">
        <div class="text-sm font-medium text-mushroom-700 mb-3">{{ currencyLabels[currency] || currency }}</div>

        <div class="space-y-3">
          <template v-for="acc in groupedAccounts[currency]" :key="acc.id">
            <div v-if="goalTypes.includes(acc.type)" class="card-elevated p-4 border-l-4" :class="accountTypeColors[acc.type] || 'border-l-mushroom-400'">
              <div class="flex items-center justify-between mb-3">
                <div>
                  <div class="text-sm font-medium text-mushroom-950">{{ acc.name }}</div>
                  <div class="text-xs text-mushroom-400">{{ accountTypeLabels[acc.type] }}</div>
                </div>
                <div class="text-right">
                  <div class="text-xl font-semibold text-mushroom-950">{{ formatCurrency(getBalance(acc.id), acc.currency) }}</div>
                </div>
              </div>

              <div v-if="acc.goal_amount > 0">
                <BudgetProgressBar
                  :spent="getBalance(acc.id)"
                  :budget="acc.goal_amount"
                  :greenThreshold="0.7"
                  :orangeThreshold="0.4"
                  class="mb-2"
                />
                <div class="flex items-center justify-between text-xs text-mushroom-500">
                  <span>
                    <template v-if="editingGoal === acc.id">
                      <input
                        v-model.number="goalValue"
                        @keyup.enter="saveGoal(acc)"
                        @keyup.escape="cancelGoal"
                        @blur="saveGoal(acc)"
                        type="number"
                        step="1"
                        min="0"
                        class="input-field text-xs py-0.5 px-1.5 w-24 inline"
                        autofocus
                      />
                    </template>
                    <template v-else>
                      <span @click="startEditGoal(acc)" class="cursor-pointer hover:text-kangkong-600">
                        {{ formatCurrency(acc.goal_amount, acc.currency) }}
                      </span>
                    </template>
                  </span>
                  <span>{{ goalProgress(getBalance(acc.id), acc.goal_amount).toFixed(1) }}%</span>
                </div>
              </div>

              <div v-else>
                <button @click="startEditGoal(acc)" class="text-xs text-kangkong-600 hover:text-kangkong-800">Set goal</button>
              </div>
            </div>

            <div v-else class="card p-3 border-l-4 flex items-center justify-between" :class="accountTypeColors[acc.type] || 'border-l-mushroom-400'">
              <div>
                <div class="text-sm font-medium text-mushroom-950">{{ acc.name }}</div>
                <div class="text-xs text-mushroom-400">{{ accountTypeLabels[acc.type] }}</div>
              </div>
              <div class="text-sm font-semibold text-mushroom-950">
                {{ formatCurrency(getBalance(acc.id), acc.currency) }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Test in browser**

Navigate to `http://localhost:5173/accounts`. Verify:
- Accounts grouped by currency (USD first, then PHP)
- Savings/Time Deposit accounts show goal cards with progress bars
- Other accounts show simple balance cards
- "Set goal" link appears for accounts without goals
- Inline editing works (click goal amount → edit → Enter)
- Eye toggle hides/shows balances

- [ ] **Step 3: Commit**

```bash
git add src/views/Accounts.vue
git commit -m "feat: redesign Accounts page as Savings Goals dashboard"
```

---

## Feature 3: Dashboard Improvements

### Task 9: Frontend — Exchange rate tooltip + click + Net worth tooltip

**Files:**
- Modify: `src/components/TopBar.vue`

**Interfaces:**
- Consumes: `useExchangeRate()`, `useSummary().balances`
- Produces: Tooltips on hover, click handler on exchange rate

- [ ] **Step 1: Replace TopBar.vue**

Replace entire `src/components/TopBar.vue` with:

```vue
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useSummary } from '../composables/useSummary'
import { useExchangeRate } from '../composables/useExchangeRate'

const { balances, fetchBalances } = useSummary()
const { exchangeRate, lastUpdated, fetchExchangeRate } = useExchangeRate()

const showNetWorthTooltip = ref(false)

onMounted(() => {
  fetchBalances()
  fetchExchangeRate()
})

const totalNetWorth = computed(() => {
  return balances.value.reduce((sum, b) => sum + b.balance_display, 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const rateDisplay = computed(() => {
  if (!exchangeRate.value) return '—'
  return `1 USD = ₱${exchangeRate.value.toFixed(2)}`
})

const usAccounts = computed(() => balances.value.filter(b => b.currency === 'USD'))
const phpAccounts = computed(() => balances.value.filter(b => b.currency === 'PHP'))

function openExchangeRateSource() {
  window.open('https://open.er-api.com', '_blank')
}

function formatBal(val, currency) {
  if (currency === 'USD') return `$${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
  return `₱${val.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
}
</script>

<template>
  <header class="h-12 bg-white border-b border-mushroom-200 flex items-center justify-between px-5 relative">
    <div></div>
    <div class="flex items-center gap-5">
      <span
        class="text-xs text-mushroom-500 cursor-pointer hover:text-kangkong-600 transition-colors"
        title="Source: open.er-api.com"
        @click="openExchangeRateSource"
      >{{ rateDisplay }}</span>
      <div class="w-px h-4 bg-mushroom-200"></div>
      <div
        class="relative group"
        @mouseenter="showNetWorthTooltip = true"
        @mouseleave="showNetWorthTooltip = false"
      >
        <div class="flex items-center gap-1.5 cursor-default">
          <span class="text-xs text-mushroom-400">Net Worth</span>
          <span class="text-sm font-semibold text-kangkong-700">{{ totalNetWorth }}</span>
        </div>

        <div
          v-if="showNetWorthTooltip"
          class="absolute right-0 top-full mt-2 w-72 card-elevated shadow-lg p-4 z-50"
        >
          <div class="text-xs font-medium text-mushroom-700 mb-3">Net Worth Breakdown</div>

          <div v-if="usAccounts.length" class="mb-3">
            <div class="text-[10px] uppercase tracking-wide text-mushroom-400 mb-1">🇺🇸 US Accounts</div>
            <div v-for="b in usAccounts" :key="b.account_id" class="flex items-center justify-between py-0.5 text-xs">
              <span class="text-mushroom-600">{{ b.account_name }}</span>
              <span class="font-medium text-mushroom-800">{{ formatBal(b.balance, b.currency) }}</span>
            </div>
          </div>

          <div v-if="phpAccounts.length" class="mb-3">
            <div class="text-[10px] uppercase tracking-wide text-mushroom-400 mb-1">🇵🇭 Philippine Accounts</div>
            <div v-for="b in phpAccounts" :key="b.account_id" class="flex items-center justify-between py-0.5 text-xs">
              <span class="text-mushroom-600">{{ b.account_name }}</span>
              <span class="font-medium text-mushroom-800">{{ formatBal(b.balance, b.currency) }}</span>
            </div>
          </div>

          <div class="border-t border-mushroom-100 pt-2 mt-2">
            <div class="flex items-center justify-between text-xs">
              <span class="text-mushroom-500">Total (USD)</span>
              <span class="font-semibold text-kangkong-700">{{ totalNetWorth }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>
```

- [ ] **Step 2: Test in browser**

Verify:
- Hovering exchange rate shows "Source: open.er-api.com" tooltip
- Clicking exchange rate opens https://open.er-api.com in new tab
- Hovering Net Worth shows dropdown with account breakdown
- Tooltip disappears on mouse leave

- [ ] **Step 3: Commit**

```bash
git add src/components/TopBar.vue
git commit -m "feat: add exchange rate source tooltip and Net Worth breakdown tooltip"
```

---

### Task 10: Frontend — Custom interactive chart legend in Dashboard

**Files:**
- Modify: `src/views/Dashboard.vue` (lines ~550-620 where the monthly trends chart is rendered)

**Interfaces:**
- Consumes: Chart.js chart instance ref
- Produces: Custom legend with toggle behavior

- [ ] **Step 1: Find the monthly trends chart section**

In `src/views/Dashboard.vue`, locate the section with the monthly trends Line chart. It should have a `<Line :data="..." :options="...">` component.

- [ ] **Step 2: Add chart ref and legend toggle logic**

Add to the `<script setup>` section (near the other refs):

```javascript
const trendChartRef = ref(null)
const incomeVisible = ref(true)
const expensesVisible = ref(true)

function toggleIncome() {
  if (incomeVisible.value && expensesVisible.value) {
    expensesVisible.value = false
  } else if (!incomeVisible.value) {
    incomeVisible.value = true
    expensesVisible.value = true
  } else {
    incomeVisible.value = true
  }
  updateChartVisibility()
}

function toggleExpenses() {
  if (incomeVisible.value && expensesVisible.value) {
    incomeVisible.value = false
  } else if (!expensesVisible.value) {
    incomeVisible.value = true
    expensesVisible.value = true
  } else {
    expensesVisible.value = true
  }
  updateChartVisibility()
}

function updateChartVisibility() {
  const chart = trendChartRef.value?.chart
  if (!chart) return
  chart.data.datasets[0].hidden = !incomeVisible.value
  chart.data.datasets[1].hidden = !expensesVisible.value
  chart.update()
}
```

- [ ] **Step 3: Add `ref` to the Line chart component**

Find the `<Line` component in the template and add `ref="trendChartRef"`:

```html
<Line ref="trendChartRef" :data="trendData" :options="trendOptions" />
```

- [ ] **Step 4: Add custom legend below the chart**

After the `<Line>` component, add:

```html
<div class="flex items-center justify-center gap-4 mt-2">
  <button
    @click="toggleIncome"
    class="flex items-center gap-1.5 text-xs transition-opacity"
    :class="incomeVisible ? 'opacity-100 font-medium text-mushroom-700' : 'opacity-40 text-mushroom-500'"
  >
    <span class="w-2.5 h-2.5 rounded-full bg-kangkong-500"></span>
    Income
  </button>
  <button
    @click="toggleExpenses"
    class="flex items-center gap-1.5 text-xs transition-opacity"
    :class="expensesVisible ? 'opacity-100 font-medium text-mushroom-700' : 'opacity-40 text-mushroom-500'"
  >
    <span class="w-2.5 h-2.5 rounded-full bg-tomato-500"></span>
    Expenses
  </button>
</div>
```

- [ ] **Step 5: Disable Chart.js default legend**

In the chart options, set:

```javascript
plugins: {
  legend: { display: false }
}
```

- [ ] **Step 6: Test in browser**

Verify:
- Chart shows both Income and Expenses lines by default
- Clicking "Income" hides Expenses, shows only Income
- Clicking "Income" again restores both
- Same behavior for "Expenses"
- Active legend items are full opacity + bold
- Inactive items are 40% opacity

- [ ] **Step 7: Commit**

```bash
git add src/views/Dashboard.vue
git commit -m "feat: add interactive chart legend toggle for Income/Expenses"
```

---

### Task 11: Frontend — Create useInsights composable

**Files:**
- Create: `src/composables/useInsights.js`

**Interfaces:**
- Consumes: transactions, categories, budgetSummary, balances
- Produces: `computeInsights(transactions, categories, budgetSummary, balances)` → array of insight objects

- [ ] **Step 1: Create useInsights.js**

Create `src/composables/useInsights.js`:

```javascript
export function useInsights() {

  function computeInsights(transactions, categories, budgetSummary, balances) {
    const insights = []
    const now = new Date()
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    const prevDate = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    const prevMonth = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`

    const currentTxns = transactions.filter(t => t.date.startsWith(currentMonth))
    const prevTxns = transactions.filter(t => t.date.startsWith(prevMonth))

    const currentExpense = currentTxns.filter(t => t.type === 'expense')
    const prevExpense = prevTxns.filter(t => t.type === 'expense')

    const currentTotal = currentExpense.reduce((s, t) => s + t.amount, 0)
    const prevTotal = prevExpense.reduce((s, t) => s + t.amount, 0)

    if (prevTotal > 0) {
      const pctChange = ((currentTotal - prevTotal) / prevTotal) * 100
      if (Math.abs(pctChange) > 10) {
        insights.push({
          icon: pctChange > 0 ? '📈' : '📉',
          text: `You spent ${Math.abs(pctChange).toFixed(0)}% ${pctChange > 0 ? 'more' : 'less'} this month vs last month`,
          color: pctChange > 0 ? 'text-carrot-600' : 'text-kangkong-600',
        })
      }
    }

    const catSpend = {}
    for (const t of currentExpense) {
      catSpend[t.category] = (catSpend[t.category] || 0) + t.amount
    }

    const prevCatSpend = {}
    for (const t of prevExpense) {
      prevCatSpend[t.category] = (prevCatSpend[t.category] || 0) + t.amount
    }

    for (const [cat, spent] of Object.entries(catSpend)) {
      const prev = prevCatSpend[cat] || 0
      if (prev > 0 && spent > prev * 1.5) {
        const pct = ((spent - prev) / prev * 100).toFixed(0)
        insights.push({
          icon: '⚠️',
          text: `${cat} spending up ${pct}% vs last month`,
          color: 'text-carrot-600',
        })
      }
    }

    if (budgetSummary?.categories) {
      for (const cat of budgetSummary.categories) {
        if (cat.budget > 0 && cat.spent / cat.budget > 0.9) {
          insights.push({
            icon: '🔴',
            text: `${cat.name} at ${((cat.spent / cat.budget) * 100).toFixed(0)}% of budget`,
            color: 'text-tomato-600',
          })
        }
      }
    }

    const totalNetWorth = balances.reduce((s, b) => s + b.balance_display, 0)
    const milestones = [5000, 10000, 15000, 20000, 25000, 30000, 50000, 100000]
    for (const m of milestones) {
      if (totalNetWorth >= m && totalNetWorth < m * 1.05) {
        insights.push({
          icon: '🎉',
          text: `Net worth crossed $${m.toLocaleString()}!`,
          color: 'text-kangkong-600',
        })
        break
      }
    }

    const topCats = Object.entries(catSpend)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)

    if (topCats.length > 0 && currentTotal > 0) {
      const [topCat, topAmt] = topCats[0]
      const pct = ((topAmt / currentTotal) * 100).toFixed(0)
      insights.push({
        icon: '💡',
        text: `${topCat} is your biggest expense at ${pct}% of total spending`,
        color: 'text-mushroom-600',
      })
    }

    return insights.slice(0, 5)
  }

  return { computeInsights }
}
```

- [ ] **Step 2: Commit**

```bash
git add src/composables/useInsights.js
git commit -m "feat: create useInsights composable for AI spending insights"
```

---

### Task 12: Frontend — Add AI Insights widget to Dashboard

**Files:**
- Modify: `src/views/Dashboard.vue`

**Interfaces:**
- Consumes: `useInsights().computeInsights`, transactions, categories, budgetSummary, balances
- Produces: Insights card on Dashboard

- [ ] **Step 1: Import useInsights**

Add to the imports at the top of `src/views/Dashboard.vue`:

```javascript
import { useInsights } from '../composables/useInsights'
```

Add to the script setup:

```javascript
const { computeInsights } = useInsights()
const insights = ref([])
```

- [ ] **Step 2: Compute insights after data loads**

After the existing `onMounted` data fetching, add:

```javascript
const budgetSummary = ref(null)

onMounted(async () => {
  // ... existing fetch calls ...
  const { data: summary } = await api.get(`/budgets/${currentMonth.value}/summary`)
  budgetSummary.value = summary
  insights.value = computeInsights(transactions.value, categories.value, budgetSummary.value, balances.value)
})
```

Note: `currentMonth` needs to be defined as:

```javascript
const currentMonth = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
})
```

- [ ] **Step 3: Add insights card to template**

Add after the monthly trends chart section (before the closing `</div>` of the main content area):

```html
<div v-if="insights.length > 0" class="card-elevated p-5">
  <div class="flex items-center gap-2 mb-3">
    <span class="text-lg">💡</span>
    <h3 class="text-sm font-medium text-mushroom-700">Insights</h3>
  </div>
  <div class="space-y-2">
    <div v-for="(insight, i) in insights" :key="i" class="flex items-start gap-2 py-1.5">
      <span class="text-sm mt-0.5">{{ insight.icon }}</span>
      <span class="text-xs" :class="insight.color">{{ insight.text }}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 4: Test in browser**

Verify:
- Insights card appears below the monthly trends chart
- Shows 3-5 relevant insights based on spending data
- Insights are color-coded (green for positive, orange for warnings, red for alerts)
- Empty state shows when no insights available

- [ ] **Step 5: Commit**

```bash
git add src/views/Dashboard.vue
git commit -m "feat: add AI Insights widget to Dashboard"
```

---

## Final Verification

After all tasks are complete, verify the full application:

1. Start backend: `cd backend && venv2/bin/uvicorn main:app --reload --port 8000`
2. Start frontend: `npm run dev`
3. Test Budget Tab: Navigate to `/budgets`, set category budgets, verify progress bars
4. Test Accounts: Navigate to `/accounts`, set goals on savings accounts, verify progress bars
5. Test Dashboard: Verify tooltips on TopBar, chart legend toggle, insights widget
6. Test Bank Upload: Upload Maya PDF, verify dates are ISO format, import works
