<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useSavingsPlanner } from '../composables/useSavingsPlanner'
import { useToast } from '../composables/useToast'
import BudgetProgressBar from '../components/BudgetProgressBar.vue'
import Skeleton from '../components/Skeleton.vue'
import { formatCurrency } from '../utils/format.js'
import { currencySymbol } from '../utils/currency.js'

const props = defineProps({ currency: { type: String, default: 'php' } })

const {
  loading, linked, linkedAccount, savingsAccounts, balance, unallocated,
  underfunded, reserves, goals, activity,
  fetchPlanner, linkPlanner, createReserve, updateReserve, deleteReserve,
  createGoal, updateGoal, deleteGoal, convertGoal, moveMoney, allocateMoney,
} = useSavingsPlanner()
const toast = useToast()

const currencyParam = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')
const curSym = computed(() => currencySymbol(currencyParam.value))
const viewLabel = computed(() => props.currency === 'usd' ? 'USD' : 'PHP')

function fmt(v) {
  return formatCurrency(v ?? 0, curSym.value)
}

function fmtDateTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('en-US', { month: 'short', day: '2-digit', hour: 'numeric', minute: '2-digit' })
}

// --- Linking ---
const selectedAccount = ref('')
const linking = ref(false)

async function handleLink() {
  if (!selectedAccount.value) return
  linking.value = true
  try {
    await linkPlanner(currencyParam.value, selectedAccount.value)
    toast.success('Savings account linked')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to link account')
  } finally {
    linking.value = false
  }
}

// --- Add forms ---
const showAddReserve = ref(false)
const reserveForm = ref({ name: '', icon: '', allocated: '', floor: '' })
const creatingReserve = ref(false)

const showAddGoal = ref(false)
const goalForm = ref({ name: '', icon: '', target: '', allocated: '' })
const creatingGoal = ref(false)

async function handleCreateReserve() {
  if (!reserveForm.value.name.trim()) return
  creatingReserve.value = true
  try {
    const payload = {
      name: reserveForm.value.name.trim(),
      icon: reserveForm.value.icon.trim() || undefined,
      allocated: reserveForm.value.allocated === '' ? 0 : parseFloat(reserveForm.value.allocated),
    }
    if (reserveForm.value.floor !== '') {
      payload.floor = parseFloat(reserveForm.value.floor)
    }
    await createReserve(currencyParam.value, payload)
    showAddReserve.value = false
    reserveForm.value = { name: '', icon: '', allocated: '', floor: '' }
    toast.success('Reserve added')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to create reserve')
  } finally {
    creatingReserve.value = false
  }
}

async function handleCreateGoal() {
  if (!goalForm.value.name.trim() || goalForm.value.target === '') return
  creatingGoal.value = true
  try {
    const payload = {
      name: goalForm.value.name.trim(),
      icon: goalForm.value.icon.trim() || undefined,
      target: parseFloat(goalForm.value.target),
      allocated: goalForm.value.allocated === '' ? 0 : parseFloat(goalForm.value.allocated),
    }
    await createGoal(currencyParam.value, payload)
    showAddGoal.value = false
    goalForm.value = { name: '', icon: '', target: '', allocated: '' }
    toast.success('Goal added')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to create goal')
  } finally {
    creatingGoal.value = false
  }
}

// --- Inline edits ---
const editingFloor = ref(null)
const floorValue = ref(0)

function startEditFloor(reserve) {
  editingFloor.value = reserve.id
  floorValue.value = reserve.floor ?? 0
}

async function saveFloor(reserve) {
  editingFloor.value = null
  try {
    await updateReserve(currencyParam.value, reserve.id, {
      floor: floorValue.value > 0 ? floorValue.value : null,
    })
    toast.success('Floor updated')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update floor')
  }
}

function cancelFloor() {
  editingFloor.value = null
}

const editingAllocated = ref(null)
const allocatedValue = ref(0)

function startEditAllocated(reserve) {
  editingAllocated.value = reserve.id
  allocatedValue.value = reserve.allocated
}

async function saveAllocated(reserve) {
  editingAllocated.value = null
  try {
    await updateReserve(currencyParam.value, reserve.id, { allocated: allocatedValue.value })
    toast.success('Reserve updated')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update reserve')
  }
}

function cancelAllocated() {
  editingAllocated.value = null
}

const editingTarget = ref(null)
const targetValue = ref(0)

function startEditTarget(goal) {
  editingTarget.value = goal.id
  targetValue.value = goal.target
}

async function saveTarget(goal) {
  editingTarget.value = null
  try {
    await updateGoal(currencyParam.value, goal.id, { target: targetValue.value })
    toast.success('Target updated')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to update target')
  }
}

function cancelTarget() {
  editingTarget.value = null
}

// --- Priority reordering ---
async function movePriority(goal, dir) {
  const list = [...goals.value]
  const idx = list.findIndex(g => g.id === goal.id)
  const swapIdx = idx + dir
  if (swapIdx < 0 || swapIdx >= list.length) return
  const other = list[swapIdx]
  try {
    await updateGoal(currencyParam.value, goal.id, { position: other.position })
    await updateGoal(currencyParam.value, other.id, { position: goal.position })
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to reorder goal')
  }
}

// --- Deletes & conversions ---
const confirmingDelete = ref(null)

async function handleDelete() {
  try {
    if (confirmingDelete.value?.type === 'reserve') {
      await deleteReserve(currencyParam.value, confirmingDelete.value.id)
      toast.success('Reserve deleted')
    } else {
      await deleteGoal(currencyParam.value, confirmingDelete.value.id)
      toast.success('Goal deleted')
    }
    confirmingDelete.value = null
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to delete')
  }
}

const confirmingConvert = ref(null)

async function handleConvert() {
  try {
    await convertGoal(currencyParam.value, confirmingConvert.value)
    toast.success('Goal converted to reserve')
    confirmingConvert.value = null
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to convert goal')
  }
}

// --- Move money ---
const showMove = ref(false)
const moveForm = ref({ from_bucket: 'unallocated', to_bucket: '', amount: 0 })
const moving = ref(false)

const bucketOptions = computed(() => {
  const opts = [{ value: 'unallocated', label: 'Unallocated' }]
  for (const r of reserves.value) {
    opts.push({ value: r.id, label: `${r.name} (Reserve)` })
  }
  for (const g of goals.value) {
    opts.push({ value: g.id, label: `${g.name} (Goal)` })
  }
  return opts
})

const moveSource = computed(() => moveForm.value.from_bucket)
const moveDest = computed(() => moveForm.value.to_bucket)

function openMove(bucketValue) {
  moveForm.value = {
    from_bucket: bucketValue || 'unallocated',
    to_bucket: bucketOptions.value.find(o => o.value !== (bucketValue || 'unallocated'))?.value || '',
    amount: 0,
  }
  showMove.value = true
}

async function handleMove() {
  if (!moveForm.value.to_bucket || moveForm.value.amount <= 0) return
  if (moveForm.value.from_bucket === moveForm.value.to_bucket) return
  moving.value = true
  try {
    await moveMoney(currencyParam.value, {
      from_bucket: moveForm.value.from_bucket,
      to_bucket: moveForm.value.to_bucket,
      amount: parseFloat(moveForm.value.amount),
    })
    showMove.value = false
    toast.success('Funds moved')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to move money')
  } finally {
    moving.value = false
  }
}

// --- Allocate Unallocated ---
const showAllocate = ref(false)
const allocateAmounts = ref({})
const allocating = ref(false)

const allocateTotal = computed(() =>
  goals.value.reduce((sum, g) => sum + (parseFloat(allocateAmounts.value[g.id]) || 0), 0)
)
const allocateRemaining = computed(() => Math.max(unallocated.value - allocateTotal.value, 0))

function openAllocate() {
  allocateAmounts.value = {}
  showAllocate.value = true
}

async function handleAllocate() {
  const allocations = goals.value
    .map(g => ({ to_bucket: g.id, amount: parseFloat(allocateAmounts.value[g.id]) || 0 }))
    .filter(a => a.amount > 0)
  if (!allocations.length) return
  allocating.value = true
  try {
    await allocateMoney(currencyParam.value, allocations)
    showAllocate.value = false
    toast.success('Unallocated allocated')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Failed to allocate')
  } finally {
    allocating.value = false
  }
}

// --- Load ---
async function load() {
  await fetchPlanner(currencyParam.value)
}

onMounted(load)
watch(currencyParam, load)

const totals = computed(() => ({
  reserves: reserves.value.reduce((s, r) => s + r.allocated, 0),
  goals: goals.value.reduce((s, g) => s + g.allocated, 0),
}))

const activityTypeClass = {
  'Moved Funds': 'bg-blue-100 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400',
  Allocated: 'bg-kangkong-100 text-kangkong-700 dark:bg-kangkong-500/15 dark:text-kangkong-400',
  'Goal Completed': 'bg-kangkong-100 text-kangkong-700 dark:bg-kangkong-500/15 dark:text-kangkong-400',
  'Goal Converted': 'bg-purple-100 text-purple-700 dark:bg-purple-500/15 dark:text-purple-400',
  'Reserve Replenished': 'bg-mango-100 text-mango-700 dark:bg-mango-500/15 dark:text-mango-400',
  'Planner Recalculated': 'bg-carrot-100 text-carrot-700 dark:bg-carrot-500/15 dark:text-carrot-400',
  'Goal Deleted': 'bg-tomato-100 text-tomato-700 dark:bg-tomato-500/15 dark:text-tomato-400',
  'Reserve Deleted': 'bg-tomato-100 text-tomato-700 dark:bg-tomato-500/15 dark:text-tomato-400',
}

function badgeClass(type) {
  return activityTypeClass[type] || 'bg-mushroom-100 text-mushroom-700 dark:bg-mushroom-800 dark:text-mushroom-300'
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-medium text-mushroom-950 dark:text-mushroom-50">{{ viewLabel }} Savings Planner</h2>
      <span v-if="linked && linkedAccount" class="text-xs text-mushroom-600 dark:text-mushroom-300">{{ linkedAccount.name }}</span>
    </div>

    <!-- Setup: not linked -->
    <div v-if="!loading && !linked" class="card-elevated p-6 text-center">
      <h3 class="font-medium text-mushroom-950 dark:text-mushroom-50 mb-1">Link a savings account</h3>
      <p class="text-sm text-mushroom-600 dark:text-mushroom-300 mb-4">Pick the savings account this planner organizes. Every plan lives on top of this one balance.</p>
      <div class="flex items-center justify-center gap-2">
        <select v-model="selectedAccount" class="select-field max-w-xs">
          <option value="">Select savings account...</option>
          <option v-for="acc in savingsAccounts" :key="acc.id" :value="acc.id">{{ acc.name }}</option>
        </select>
        <button @click="handleLink" :disabled="!selectedAccount || linking" class="btn-primary text-xs">
          {{ linking ? 'Linking...' : 'Link Account' }}
        </button>
      </div>
    </div>

    <template v-else-if="linked">
      <!-- Summary -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="card-elevated p-4">
          <div class="text-xs text-mushroom-600 dark:text-mushroom-300 mb-1">Savings Balance</div>
          <div class="text-2xl font-semibold text-mushroom-950 dark:text-mushroom-50">{{ fmt(balance) }}</div>
        </div>
        <div class="card-elevated p-4">
          <div class="text-xs text-mushroom-600 dark:text-mushroom-300 mb-1">Reserves</div>
          <div class="text-2xl font-semibold text-kangkong-600 dark:text-kangkong-400">{{ fmt(totals.reserves) }}</div>
        </div>
        <div class="card-elevated p-4">
          <div class="text-xs text-mushroom-600 dark:text-mushroom-300 mb-1">Goals</div>
          <div class="text-2xl font-semibold text-mango-600 dark:text-mango-400">{{ fmt(totals.goals) }}</div>
        </div>
        <div class="card-elevated p-4">
          <div class="text-xs text-mushroom-600 dark:text-mushroom-300 mb-1">Unallocated</div>
          <div class="text-2xl font-semibold" :class="unallocated >= 0 ? 'text-mushroom-950 dark:text-mushroom-50' : 'text-tomato-600 dark:text-tomato-400'">{{ fmt(unallocated) }}</div>
        </div>
      </div>

      <div v-if="underfunded" class="rounded-lg bg-tomato-100 dark:bg-tomato-500/15 border border-tomato-200 dark:border-tomato-500/30 p-4 text-sm text-tomato-800 dark:text-tomato-300">
        The planner is underfunded by {{ fmt(-Math.min(unallocated, 0)) }}. Reduce goals, raise funds, or resolve the shortfall to balance the equation.
      </div>

      <!-- Allocate Unallocated banner -->
      <div v-if="unallocated > 0 && goals.length" class="flex items-center justify-between rounded-lg bg-kangkong-100 dark:bg-kangkong-500/15 border border-kangkong-200 dark:border-kangkong-500/30 p-4">
        <p class="text-sm text-kangkong-800 dark:text-kangkong-300">
          <span class="font-medium">{{ fmt(unallocated) }}</span> is unallocated. Give it a purpose across your goals.
        </p>
        <button @click="openAllocate" class="btn-secondary text-xs">Allocate Unallocated</button>
      </div>

      <!-- Reserves -->
      <section class="card-elevated p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-mushroom-600 dark:text-mushroom-300">Reserves</h3>
          <button @click="showAddReserve = !showAddReserve" class="btn-secondary text-xs">
            {{ showAddReserve ? 'Cancel' : '+ Add Reserve' }}
          </button>
        </div>

        <form v-if="showAddReserve" @submit.prevent="handleCreateReserve" class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <input v-model="reserveForm.name" placeholder="Name (e.g. Emergency Fund)" class="input-field" required />
          <input v-model="reserveForm.icon" placeholder="Icon (emoji)" class="input-field" />
          <input v-model="reserveForm.allocated" type="number" step="0.01" min="0" placeholder="Allocated (optional)" class="input-field" />
          <input v-model="reserveForm.floor" type="number" step="0.01" min="0" placeholder="Floor (optional)" class="input-field" />
          <button type="submit" :disabled="creatingReserve" class="btn-secondary text-xs">
            {{ creatingReserve ? 'Adding...' : 'Add' }}
          </button>
        </form>

        <div v-if="!reserves.length" class="text-sm text-mushroom-500 dark:text-mushroom-500 py-2">
          No reserves yet. Reserves are money already committed to an ongoing purpose.
        </div>
        <div v-else class="space-y-2.5">
          <div v-for="r in reserves" :key="r.id" class="flex items-center justify-between rounded-lg border border-mushroom-200 dark:border-mushroom-700/60 p-3">
            <div class="flex items-center gap-3 min-w-0">
              <span class="text-xl flex-shrink-0">{{ r.icon || '🛡️' }}</span>
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50 truncate">{{ r.name }}</span>
                  <button @click="openMove(r.id)" class="text-[10px] uppercase tracking-wide text-mushroom-500 dark:text-mushroom-400 hover:text-kangkong-600 dark:hover:text-kangkong-400">Move</button>
                </div>
                <div class="text-xs text-mushroom-600 dark:text-mushroom-300">
                  <template v-if="editingFloor === r.id">
                    <div class="flex items-center gap-1.5 mt-1">
                      <input v-model.number="floorValue" @keyup.enter="saveFloor(r)" @keyup.escape="cancelFloor" type="number" step="0.01" min="0" class="input-field text-xs py-0.5 px-1.5 w-24" autofocus />
                      <button @click="saveFloor(r)" class="text-kangkong-600 hover:text-kangkong-800 text-xs font-medium">Save</button>
                    </div>
                  </template>
                  <template v-else>
                    <span v-if="r.floor" @click="startEditFloor(r)" class="cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400">
                      Floor: {{ fmt(r.floor) }}
                    </span>
                    <span v-else @click="startEditFloor(r)" class="cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400">No floor</span>
                  </template>
                </div>
              </div>
            </div>
            <div class="text-right flex items-center gap-2 flex-shrink-0">
              <template v-if="editingAllocated === r.id">
                <div class="flex items-center gap-1.5">
                  <input v-model.number="allocatedValue" @keyup.enter="saveAllocated(r)" @keyup.escape="cancelAllocated" type="number" step="0.01" min="0" class="input-field text-xs py-0.5 px-1.5 w-24 text-right" autofocus />
                  <button @click="saveAllocated(r)" class="text-kangkong-600 hover:text-kangkong-800 text-xs font-medium">Save</button>
                </div>
              </template>
              <span v-else @click="startEditAllocated(r)" class="text-base font-semibold text-mushroom-950 dark:text-mushroom-50 cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400" title="Edit amount">{{ fmt(r.allocated) }}</span>
              <button v-if="confirmingDelete?.id === r.id && confirmingDelete?.type === 'reserve'" @click="handleDelete" class="text-tomato-600 hover:text-tomato-800 text-xs font-medium">Confirm?</button>
              <button v-else @click="confirmingDelete = { type: 'reserve', id: r.id }" class="text-mushroom-500 dark:text-mushroom-500 hover:text-tomato-500 dark:hover:text-tomato-400" title="Delete reserve">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Goals -->
      <section class="card-elevated p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-mushroom-600 dark:text-mushroom-300">Goals</h3>
          <button @click="showAddGoal = !showAddGoal" class="btn-secondary text-xs">
            {{ showAddGoal ? 'Cancel' : '+ Add Goal' }}
          </button>
        </div>

        <form v-if="showAddGoal" @submit.prevent="handleCreateGoal" class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
          <input v-model="goalForm.name" placeholder="Name (e.g. Japan)" class="input-field" required />
          <input v-model="goalForm.icon" placeholder="Icon (emoji)" class="input-field" />
          <input v-model="goalForm.target" type="number" step="0.01" min="0" placeholder="Target" class="input-field" required />
          <input v-model="goalForm.allocated" type="number" step="0.01" min="0" placeholder="Allocated (optional)" class="input-field" />
          <button type="submit" :disabled="creatingGoal" class="btn-secondary text-xs">
            {{ creatingGoal ? 'Adding...' : 'Add' }}
          </button>
        </form>

        <div v-if="!goals.length" class="text-sm text-mushroom-500 dark:text-mushroom-500 py-2">
          No goals yet. Goals are future savings targets. Drag priority arrows to set which goal loses money first.
        </div>
        <div v-else class="space-y-2.5">
          <div v-for="(g, idx) in goals" :key="g.id" class="rounded-lg border border-mushroom-200 dark:border-mushroom-700/60 p-3">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-3 min-w-0">
                <div class="flex flex-col flex-shrink-0">
                  <button @click="movePriority(g, -1)" :disabled="idx === 0" class="text-mushroom-500 dark:text-mushroom-400 hover:text-kangkong-600 dark:hover:text-kangkong-400 disabled:opacity-30" title="Higher priority">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 15l-6-6-6 6"/></svg>
                  </button>
                  <button @click="movePriority(g, 1)" :disabled="idx === goals.length - 1" class="text-mushroom-500 dark:text-mushroom-400 hover:text-kangkong-600 dark:hover:text-kangkong-400 disabled:opacity-30" title="Lower priority">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
                  </button>
                </div>
                <span class="text-xl flex-shrink-0">{{ g.icon || '🎯' }}</span>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50 truncate">{{ g.name }}</span>
                    <button @click="openMove(g.id)" class="text-[10px] uppercase tracking-wide text-mushroom-500 dark:text-mushroom-400 hover:text-kangkong-600 dark:hover:text-kangkong-400">Move</button>
                    <button v-if="confirmingConvert === g.id" @click="handleConvert" class="text-kangkong-600 hover:text-kangkong-800 text-xs font-medium">Convert?</button>
                    <button v-else @click="confirmingConvert = g.id" class="text-[10px] uppercase tracking-wide text-mushroom-500 dark:text-mushroom-400 hover:text-kangkong-600 dark:hover:text-kangkong-400">Convert</button>
                  </div>
                  <div class="text-xs text-mushroom-600 dark:text-mushroom-300">
                    <template v-if="editingTarget === g.id">
                      <span class="flex items-center gap-1.5 mt-1">
                        <input v-model.number="targetValue" @keyup.enter="saveTarget(g)" @keyup.escape="cancelTarget" type="number" step="0.01" min="0" class="input-field text-xs py-0.5 px-1.5 w-24" autofocus />
                        <button @click="saveTarget(g)" class="text-kangkong-600 hover:text-kangkong-800 text-xs font-medium">Save</button>
                      </span>
                    </template>
                    <span v-else @click="startEditTarget(g)" class="cursor-pointer hover:text-kangkong-600 dark:hover:text-kangkong-400">Target: {{ fmt(g.target) }}</span>
                  </div>
                </div>
              </div>
              <div class="text-right flex items-center gap-2 flex-shrink-0">
                <span class="text-base font-semibold text-mushroom-950 dark:text-mushroom-50">{{ fmt(g.allocated) }}</span>
                <button v-if="confirmingDelete?.id === g.id && confirmingDelete?.type === 'goal'" @click="handleDelete" class="text-tomato-600 hover:text-tomato-800 text-xs font-medium">Confirm?</button>
                <button v-else @click="confirmingDelete = { type: 'goal', id: g.id }" class="text-mushroom-500 dark:text-mushroom-500 hover:text-tomato-500 dark:hover:text-tomato-400" title="Delete goal">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                </button>
              </div>
            </div>
            <BudgetProgressBar :spent="g.allocated" :budget="g.target" :invert="true" class="mt-2" />
            <div class="mt-1 text-[11px] text-mushroom-500 dark:text-mushroom-400">
              {{ g.target > 0 ? Math.min((g.allocated / g.target) * 100, 100).toFixed(1) : 0 }}% of target
            </div>
          </div>
        </div>
      </section>

      <!-- Activity feed -->
      <section class="card-elevated p-5">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-mushroom-600 dark:text-mushroom-300 mb-3">Activity</h3>
        <div v-if="!activity.length" class="text-sm text-mushroom-500 dark:text-mushroom-500 py-2">No activity yet.</div>
        <div v-else class="space-y-2">
          <div v-for="a in activity" :key="a.id" class="flex items-start justify-between gap-3 py-1.5 border-b border-mushroom-100 dark:border-mushroom-700/40 last:border-0">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-medium uppercase tracking-wide rounded-full px-2 py-0.5" :class="badgeClass(a.type)">{{ a.type }}</span>
              </div>
              <p class="text-sm text-mushroom-700 dark:text-mushroom-300 mt-1">{{ a.description }}</p>
            </div>
            <div class="text-right flex-shrink-0">
              <div v-if="a.amount" class="text-sm font-medium text-mushroom-950 dark:text-mushroom-50">{{ fmt(a.amount) }}</div>
              <div class="text-[11px] text-mushroom-500 dark:text-mushroom-400">{{ fmtDateTime(a.created_at) }}</div>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- Skeleton loading -->
    <div v-else class="space-y-4">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Skeleton v-for="n in 4" :key="n" height="72px" rounded="rounded-lg" />
      </div>
      <Skeleton height="120px" rounded="rounded-lg" />
      <Skeleton height="120px" rounded="rounded-lg" />
    </div>

    <!-- Move Money modal -->
    <Teleport to="body">
      <div v-if="showMove" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="showMove = false">
        <div class="card-elevated w-full max-w-sm p-5">
          <h3 class="font-medium text-mushroom-950 dark:text-mushroom-50 mb-4">Move Money</h3>
          <div class="space-y-3">
            <div>
              <label class="label-text">From</label>
              <select v-model="moveForm.from_bucket" class="select-field">
                <option v-for="o in bucketOptions" :key="'f' + o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
            <div>
              <label class="label-text">To</label>
              <select v-model="moveForm.to_bucket" class="select-field">
                <option v-for="o in bucketOptions" :key="'t' + o.value" :value="o.value">{{ o.label }}</option>
              </select>
            </div>
            <div>
              <label class="label-text">Amount</label>
              <input v-model.number="moveForm.amount" type="number" step="0.01" min="0" placeholder="0.00" class="input-field" />
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button @click="showMove = false" class="btn-secondary text-xs">Cancel</button>
            <button @click="handleMove" :disabled="moving || moveForm.amount <= 0 || moveForm.from_bucket === moveForm.to_bucket || !moveForm.to_bucket" class="btn-primary text-xs">
              {{ moving ? 'Moving...' : 'Move Funds' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Allocate Unallocated modal -->
    <Teleport to="body">
      <div v-if="showAllocate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="showAllocate = false">
        <div class="card-elevated w-full max-w-sm p-5">
          <h3 class="font-medium text-mushroom-950 dark:text-mushroom-50 mb-1">Allocate Unallocated</h3>
          <p class="text-xs text-mushroom-600 dark:text-mushroom-300 mb-4">{{ fmt(unallocated) }} available to distribute.</p>
          <div v-if="!goals.length" class="text-sm text-mushroom-500 dark:text-mushroom-500">Add a goal first to allocate into.</div>
          <div v-else class="space-y-3">
            <div v-for="g in goals" :key="g.id">
              <label class="label-text">{{ g.icon || '🎯' }} {{ g.name }}</label>
              <input v-model="allocateAmounts[g.id]" type="number" step="0.01" min="0" placeholder="0.00" class="input-field" />
            </div>
            <div class="flex justify-between text-sm text-mushroom-700 dark:text-mushroom-300 pt-2 border-t border-mushroom-100 dark:border-mushroom-700/50">
              <span>Remaining unallocated</span>
              <span class="font-medium">{{ fmt(allocateRemaining) }}</span>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button @click="showAllocate = false" class="btn-secondary text-xs">Cancel</button>
            <button @click="handleAllocate" :disabled="allocating || allocateTotal <= 0 || allocateTotal > unallocated" class="btn-primary text-xs">
              {{ allocating ? 'Allocating...' : 'Allocate' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
