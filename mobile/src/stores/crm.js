import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { crmApi } from 'src/services/api'

// Колонки CRM доски — ТОЧНЫЕ названия из десктопа
const COLUMNS_INDIVIDUAL = [
  'Новый заказ',
  'В ожидании',
  'Стадия 1: планировочные решения',
  'Стадия 2: концепция дизайна',
  'Стадия 3: рабочие чертежи',
  'Выполненный проект'
]

const COLUMNS_TEMPLATE = [
  'Новый заказ',
  'В ожидании',
  'Стадия 1: планировочные решения',
  'Стадия 2: рабочие чертежи',
  'Стадия 3: 3д визуализация (Дополнительная)',
  'Выполненный проект'
]

export const useCrmStore = defineStore('crm', () => {
  const cards = ref([])
  const loading = ref(false)
  const projectType = ref('Индивидуальный')
  const showArchive = ref(false)
  const selectedCard = ref(null)
  const cardLoading = ref(false)

  // Актуальный порядок колонок зависит от типа проекта
  const columnOrder = computed(() =>
    projectType.value === 'Шаблонный' ? COLUMNS_TEMPLATE : COLUMNS_INDIVIDUAL
  )

  // Группировка карточек по колонкам
  const columns = computed(() => {
    const order = columnOrder.value
    const grouped = {}

    for (const col of order) {
      grouped[col] = []
    }

    for (const card of cards.value) {
      const col = card.column_name || 'Новый заказ'
      if (!grouped[col]) {
        grouped[col] = []
      }
      grouped[col].push(card)
    }

    return order
      .filter(col => grouped[col])
      .map(col => ({
        name: col,
        shortName: col.replace(/^Стадия \d+: /, ''),
        cards: grouped[col],
        count: grouped[col].length
      }))
  })

  const totalCards = computed(() => cards.value.length)

  async function loadCards() {
    loading.value = true
    try {
      const { data } = await crmApi.getCards(projectType.value, showArchive.value)
      cards.value = data
    } catch {
      cards.value = []
    } finally {
      loading.value = false
    }
  }

  async function loadCard(cardId) {
    cardLoading.value = true
    try {
      const { data } = await crmApi.getCard(cardId)
      selectedCard.value = data
    } catch {
      selectedCard.value = null
    } finally {
      cardLoading.value = false
    }
  }

  function setProjectType(type) {
    projectType.value = type
    loadCards()
  }

  function toggleArchive() {
    showArchive.value = !showArchive.value
    loadCards()
  }

  return {
    cards, loading, projectType, showArchive, selectedCard, cardLoading,
    columns, totalCards,
    loadCards, loadCard, setProjectType, toggleArchive,
    columnOrder, COLUMNS_INDIVIDUAL, COLUMNS_TEMPLATE
  }
})
