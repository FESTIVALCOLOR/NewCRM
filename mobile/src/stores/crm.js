import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { crmApi } from 'src/services/api'
import { useAuthStore } from './auth'

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

  // Фильтрация карточек по роли (без фильтра по типу проекта)
  function hasPos(...positions) {
    const auth = useAuthStore()
    const pos = auth.user?.position || ''
    const secPos = auth.user?.secondary_position || ''
    return positions.includes(pos) || positions.includes(secPos)
  }

  // Карточки видимые текущей роли (ВСЕ типы) — для счётчиков
  const roleFilteredCards = computed(() => {
    const auth = useAuthStore()
    if (!auth.user) return cards.value

    // Руководитель и старший менеджер видят всё
    if (hasPos('Руководитель студии', 'Старший менеджер проектов')) return cards.value

    const empId = auth.user.id
    const empName = auth.user.full_name || ''

    return cards.value.filter(card => {
      // Менеджер — по manager_id
      if (hasPos('Менеджер') && card.manager_id === empId) return true

      // ГАП — по gap_id
      if (hasPos('ГАП') && card.gap_id === empId) return true

      // СДП — по sdp_id
      if (hasPos('СДП') && card.sdp_id === empId) return true

      // Дизайнер — только на Стадии 2 по designer_name
      if (hasPos('Дизайнер')) {
        const col = card.column_name || ''
        if (col.includes('Стадия 2')) {
          if (card.designer_name === empName) return true
        }
      }

      // Чертёжник — по draftsman_name на допустимых стадиях
      if (hasPos('Чертёжник')) {
        const col = card.column_name || ''
        const isTemplate = card.project_type === 'Шаблонный'
        const allowed = isTemplate
          ? ['Стадия 1', 'Стадия 2']
          : ['Стадия 1', 'Стадия 3']
        if (allowed.some(s => col.includes(s)) && card.draftsman_name === empName) return true
      }

      // Замерщик — по surveyor_id, если замер не загружен
      if (hasPos('Замерщик') && card.surveyor_id === empId) {
        if (!card.measurement_image_link && !card.survey_date) return true
      }

      return false
    })
  })

  // Карточки для доски: роль + тип проекта
  const filteredCards = computed(() => {
    const byRole = roleFilteredCards.value
    return byRole.filter(c =>
      projectType.value === 'Шаблонный'
        ? c.project_type === 'Шаблонный'
        : c.project_type !== 'Шаблонный'
    )
  })

  // Группировка карточек по колонкам
  const columns = computed(() => {
    const order = columnOrder.value
    const grouped = {}

    for (const col of order) {
      grouped[col] = []
    }

    for (const card of filteredCards.value) {
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

  // totalCards — карточки текущего вида (тип + роль)
  const totalCards = computed(() => filteredCards.value.length)

  // Счётчики по типу: считаются по roleFilteredCards (все типы, видимые роли)
  const countIndividual = computed(() =>
    roleFilteredCards.value.filter(c => c.project_type !== 'Шаблонный').length
  )
  const countTemplate = computed(() =>
    roleFilteredCards.value.filter(c => c.project_type === 'Шаблонный').length
  )

  // Загружаем ВСЕ карточки (без фильтра по типу) — чтобы счётчики были корректны
  async function loadCards() {
    loading.value = true
    try {
      const { data } = await crmApi.getCards(null, showArchive.value)
      cards.value = data
    } catch {
      cards.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Оптимистичное перемещение карточки — UI обновляется мгновенно,
   * откатывается при ошибке API
   */
  function moveCardOptimistic(cardId, newColumn) {
    const card = cards.value.find(c => c.id === cardId)
    if (!card) return { success: false, oldColumn: null }
    const oldColumn = card.column_name
    card.column_name = newColumn
    return { success: true, oldColumn }
  }

  function rollbackMoveCard(cardId, oldColumn) {
    const card = cards.value.find(c => c.id === cardId)
    if (card) card.column_name = oldColumn
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
    // Перезагрузка не нужна — все карточки уже загружены
  }

  function toggleArchive() {
    showArchive.value = !showArchive.value
    loadCards()
  }

  return {
    cards, filteredCards, loading, projectType, showArchive, selectedCard, cardLoading,
    columns, totalCards, countIndividual, countTemplate,
    loadCards, loadCard, setProjectType, toggleArchive,
    moveCardOptimistic, rollbackMoveCard,
    columnOrder, COLUMNS_INDIVIDUAL, COLUMNS_TEMPLATE
  }
})
