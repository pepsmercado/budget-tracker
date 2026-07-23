import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Transactions from './views/Transactions.vue'
import TransactionForm from './views/TransactionForm.vue'
import Budgets from './views/Budgets.vue'
import Accounts from './views/Accounts.vue'
import Upload from './views/Upload.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/transactions', name: 'Transactions', component: Transactions },
  { path: '/transactions/new', name: 'NewTransaction', component: TransactionForm },
  { path: '/transactions/:id/edit', name: 'EditTransaction', component: TransactionForm },
  { path: '/upload', name: 'Upload', component: Upload },
  { path: '/budgets', name: 'Budgets', component: Budgets },
  { path: '/accounts', name: 'Accounts', component: Accounts },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
