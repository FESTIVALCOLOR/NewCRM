import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { clientsApi, contractsApi } from 'src/services/api'

export const useClientsStore = defineStore('clients', () => {
  const items = ref([])
  const loading = ref(false)
  const search = ref('')
  const totalCount = ref(0)
  const selectedClient = ref(null)
  const clientContracts = ref([])

  // Фильтрация на клиенте (для мгновенного поиска)
  const filteredItems = computed(() => {
    if (!search.value) return items.value
    const q = search.value.toLowerCase()
    return items.value.filter(c =>
      (c.full_name || '').toLowerCase().includes(q) ||
      (c.organization_name || '').toLowerCase().includes(q) ||
      (c.phone || '').includes(q) ||
      (c.email || '').toLowerCase().includes(q)
    )
  })

  async function loadClients(skip = 0, limit = 100) {
    loading.value = true
    try {
      const params = { skip, limit }
      if (search.value) {
        params.search = search.value
        params.search_type = 'all'
      }
      const response = await clientsApi.getList(params)
      items.value = response.data
      totalCount.value = parseInt(response.headers['x-total-count'] || '0', 10)
    } catch {
      items.value = []
    } finally {
      loading.value = false
    }
  }

  async function loadClient(clientId) {
    try {
      const { data } = await clientsApi.getById(clientId)
      selectedClient.value = data
    } catch {
      selectedClient.value = null
    }
  }

  async function loadClientContracts(clientId) {
    try {
      // API не поддерживает client_id фильтр — фильтруем на клиенте
      const { data } = await contractsApi.getList({ limit: 500 })
      clientContracts.value = (data || []).filter(c => c.client_id === parseInt(clientId))
    } catch {
      clientContracts.value = []
    }
  }

  return {
    items, loading, search, totalCount, selectedClient, clientContracts,
    filteredItems,
    loadClients, loadClient, loadClientContracts
  }
})
