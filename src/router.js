import { createRouter, createWebHistory } from 'vue-router'

const Dashboard = () => import('./views/Dashboard.vue')
const Transactions = () => import('./views/Transactions.vue')
const TransactionForm = () => import('./views/TransactionForm.vue')
const Budgets = () => import('./views/Budgets.vue')
const Accounts = () => import('./views/Accounts.vue')
const Upload = () => import('./views/Upload.vue')
const Recurring = () => import('./views/Recurring.vue')
const Transfers = () => import('./views/Transfers.vue')
const Reports = () => import('./views/Reports.vue')
const SavingsPlanner = () => import('./views/SavingsPlanner.vue')

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
  { path: `/${currency}/savings-planner`, name: `${currency}-SavingsPlanner`, component: SavingsPlanner, props: { currency } },
]

const routes = [
  ...currencyRoutes('php'),
  ...currencyRoutes('usd'),
  { path: '/', redirect: '/usd' },
  { path: '/:pathMatch(.*)*', redirect: '/usd' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
