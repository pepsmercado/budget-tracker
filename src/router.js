import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import Transactions from './views/Transactions.vue'
import TransactionForm from './views/TransactionForm.vue'
import Budgets from './views/Budgets.vue'
import Accounts from './views/Accounts.vue'
import Upload from './views/Upload.vue'
import Recurring from './views/Recurring.vue'
import Transfers from './views/Transfers.vue'
import Reports from './views/Reports.vue'

const currencyRoutes = (currency) => [
  { path: `/${currency}`, name: `${currency}-Dashboard`, component: Dashboard, props: { currency } },
  { path: `/${currency}/transactions`, name: `${currency}-Transactions`, component: Transactions, props: { currency } },
  { path: `/${currency}/transactions/new`, name: `${currency}-NewTransaction`, component: TransactionForm, props: { currency } },
  { path: `/${currency}/transactions/:id/edit`, name: `${currency}-EditTransaction`, component: TransactionForm, props: { currency } },
  { path: `/${currency}/budgets`, name: `${currency}-Budgets`, component: Budgets, props: { currency } },
  { path: `/${currency}/accounts`, name: `${currency}-Accounts`, component: Accounts, props: { currency } },
  { path: `/${currency}/upload`, name: `${currency}-Upload`, component: Upload, props: { currency } },
  { path: `/${currency}/recurring`, name: `${currency}-Recurring`, component: Recurring, props: { currency } },
  { path: `/${currency}/transfers`, name: `${currency}-Transfers`, component: Transfers, props: { currency } },
  { path: `/${currency}/reports`, name: `${currency}-Reports`, component: Reports, props: { currency } },
]

const routes = [
  ...currencyRoutes('php'),
  ...currencyRoutes('usd'),
  { path: '/', redirect: '/php' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
