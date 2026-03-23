import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { crmApi } from 'src/services/api'

// Порядок колонок CRM доски
const COLUMN_ORDER = [
  'Новый заказ',
  'Стадия 1: планировочное решение',
  'Стадия 2: концепция дизайна',
  'Стадия 3: рабочая документация',
  'На согласовании',
  'Согласовано'
]

export const useCrmStore = defineStore('crm', () => {
  const cards = ref([])
  const loading = ref(false)
  const projectType = ref('Индивидуальный')
  const showArchive = ref(false)
  const selectedCard = ref(null)
  const cardLoading = ref(false)

  // Группировка карточек по колонкам
  const columns = computed(() => {
    const grouped = {}

    // Инициализация всех колонок
    for (const col of COLUMN_ORDER) {
      grouped[col] = []
    }

    // Распределение карточек по колонкам
    for (const card of cards.value) {
      const col = card.column_name || 'Новый заказ'
      if (!grouped[col]) {
        grouped[col] = []
      }
      grouped[col].push(card)
    }

    // Конвертация в массив для отображения
    return COLUMN_ORDER
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
    COLUMN_ORDER
  }
})
