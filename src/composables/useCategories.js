import { ref } from 'vue'
import api from '../api'

const categories = ref([])
const loading = ref(false)
let fetched = false

export function useCategories() {
  async function fetchCategories() {
    if (fetched) return
    loading.value = true
    try {
      const { data } = await api.get('/categories')
      categories.value = data
      fetched = true
    } catch (e) {
      console.warn('Failed to fetch categories:', e)
    } finally {
      loading.value = false
    }
  }

  return { categories, loading, fetchCategories }
}
