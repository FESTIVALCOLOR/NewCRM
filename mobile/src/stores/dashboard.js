import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi, statisticsApi } from 'src/services/api'

export const useDashboardStore = defineStore('dashboard', () => {
  const loading = ref(false)
  const stats = ref(null)
  const clientsStats = ref(null)
  const contractsStats = ref(null)
  const crmStats = ref(null)
  const employeesStats = ref(null)

  async function loadAll() {
    loading.value = true
    try {
      const year = new Date().getFullYear()
      const [clients, contracts, crmIndiv, employees, general] = await Promise.allSettled([
        dashboardApi.getClients({ year }),
        dashboardApi.getContracts({ year }),
        dashboardApi.getCrm({ project_type: 'Индивидуальный' }),
        dashboardApi.getEmployees(),
        statisticsApi.getGeneral({ year })
      ])

      if (clients.status === 'fulfilled') clientsStats.value = clients.value.data
      if (contracts.status === 'fulfilled') contractsStats.value = contracts.value.data
      if (crmIndiv.status === 'fulfilled') crmStats.value = crmIndiv.value.data
      if (employees.status === 'fulfilled') employeesStats.value = employees.value.data
      if (general.status === 'fulfilled') stats.value = general.value.data
    } finally {
      loading.value = false
    }
  }

  return { loading, stats, clientsStats, contractsStats, crmStats, employeesStats, loadAll }
})
