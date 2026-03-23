import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from 'src/boot/axios'

export const useReferencesStore = defineStore('references', () => {
  const cities = ref([])
  const agents = ref([])
  const rates = ref([])
  const loaded = ref(false)

  // Должности — hardcoded (как в server/constants.py)
  const positions = [
    'Руководитель студии',
    'Старший менеджер проектов',
    'СДП',
    'ГАП',
    'ДАН',
    'Менеджер',
    'Замерщик',
    'Дизайнер',
    'Чертёжник'
  ]

  // Типы проектов
  const projectTypes = ['Индивидуальный', 'Шаблонный', 'Авторский надзор']

  // Подтипы проектов
  const projectSubtypes = [
    'Полный (с 3д визуализацией)',
    'Эскизный (с коллажами)',
    'Планировочный'
  ]

  // Статусы договора
  const contractStatuses = [
    'Новый заказ', 'В ожидании', 'В работе', 'СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'
  ]

  // Типы оплаты
  const paymentTypes = ['Наличными', 'Переводом на карту', 'Переводом по реквизитам']

  // Статусы сотрудника
  const employeeStatuses = ['активный', 'уволен', 'в резерве']

  async function loadAll() {
    if (loaded.value) return
    try {
      const [citiesRes, agentsRes, ratesRes] = await Promise.allSettled([
        api.get('/api/v1/cities'),
        api.get('/api/v1/agents'),
        api.get('/api/v1/rates')
      ])

      if (citiesRes.status === 'fulfilled') {
        cities.value = (citiesRes.value.data || [])
          .filter(c => c.status === 'активный')
          .map(c => c.name)
      }

      if (agentsRes.status === 'fulfilled') {
        agents.value = (agentsRes.value.data || [])
          .filter(a => a.status === 'активный')
      }

      if (ratesRes.status === 'fulfilled') {
        rates.value = ratesRes.value.data || []
      }

      loaded.value = true
    } catch {
      // Справочники не загрузились — работаем с пустыми
    }
  }

  // Имена агентов для select
  function agentNames() {
    return agents.value.map(a => a.name)
  }

  // Агент по имени
  function agentByName(name) {
    return agents.value.find(a => a.name === name)
  }

  return {
    cities, agents, rates, loaded,
    positions, projectTypes, projectSubtypes, contractStatuses, paymentTypes, employeeStatuses,
    loadAll, agentNames, agentByName
  }
})
