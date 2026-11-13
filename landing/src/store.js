// Общие данные сайта: загружаются один раз и используются всеми страницами
import { reactive, computed, watch } from 'vue'
import { applyAnalytics } from './analytics.js'
import { applyTheme, applyCachedTheme, cacheTheme, allSectionStyles } from './theme.js'

// Секции главной страницы. Портфолио и цены живут на странице «Индивидуальный дизайн»
export const HOME_SECTIONS = ['hero', 'about', 'stats', 'services', 'directions', 'reviews', 'contacts', 'objects_map']

export const site = reactive({
  settings: applyCachedTheme(),
  sections: [],
  team: [],
  stats: [],
  services: [],
  pricing: [],
  reviews: [],
  portfolio: [],
  loaded: false,
})

// Порядок и видимость секций главной задаются в админке (вкладка «Секции меню»)
export const homeSectionKeys = computed(() => {
  if (!site.sections.length) return HOME_SECTIONS
  const keys = site.sections.filter(s => s.is_visible && HOME_SECTIONS.includes(s.key)).map(s => s.key)
  // Сервер, который ещё не знает о секции направлений, не должен оставить главную без неё
  if (!site.sections.some(s => s.key === 'directions')) {
    const after = keys.indexOf('services')
    keys.splice(after >= 0 ? after + 1 : keys.length, 0, 'directions')
  }
  return keys
})

// Свои шрифты, цвета и размеры отдельных блоков (вкладка «Стиль» → блок)
export const sectionStyles = computed(() => allSectionStyles(site.settings))

// Блок, скрытый в «Секциях меню», не показывается и на внутренних страницах
export function sectionVisible(key) {
  const section = site.sections.find(s => s.key === key)
  return section ? section.is_visible : true
}

export async function loadSite() {
  try {
    const res = await fetch('/api/v1/site/public')
    if (!res.ok) return
    const json = await res.json()
    Object.assign(site, json)
    applyTheme(json.settings)
    cacheTheme(json.settings)
    applyAnalytics(json.analytics)
  } catch (e) {
    console.warn('Не удалось загрузить данные сайта:', e)
  } finally {
    site.loaded = true
  }
}

// ── Готовые дизайны ──
export const ready = reactive({ designs: [], loaded: false })
let readyRequest = null

export function loadReadyDesigns() {
  if (!readyRequest) {
    readyRequest = fetch('/api/v1/site/ready-designs')
      .then(res => (res.ok ? res.json() : []))
      .then(list => { ready.designs = Array.isArray(list) ? list : [] })
      .catch(e => console.warn('Не удалось загрузить готовые дизайны:', e))
      .finally(() => { ready.loaded = true })
  }
  return readyRequest
}

export function designCover(design) {
  return design?.cover_url || design?.images?.[0]?.url || ''
}

// ── Выбор посетителя в калькуляторе: сохраняется при переходе между страницами и визитами ──
const CHOICE_KEY = 'ready_choice'
function savedChoice() {
  try {
    const value = JSON.parse(localStorage.getItem(CHOICE_KEY) || 'null')
    if (value && typeof value === 'object') return value
  } catch { /* повреждённое значение игнорируется */ }
  return {}
}
const saved = savedChoice()
export const choice = reactive({
  region: ['msk', 'spb', 'region'].includes(saved.region) ? saved.region : 'msk',
  city: typeof saved.city === 'string' ? saved.city : '',
  area: typeof saved.area === 'string' || typeof saved.area === 'number' ? saved.area : '',
  // Откуда город: 'user' — выбрал сам, 'auto' — определили по местоположению, '' — ещё не известно.
  // Сохранённый раньше выбор без этой пометки считается выбором посетителя
  source: 'source' in saved ? (['user', 'auto'].includes(saved.source) ? saved.source : '') : (saved.region ? 'user' : ''),
})

// Город посетителя определяется один раз — и только если он ещё ничего не выбирал сам
let detecting = null
export function detectVisitorRegion() {
  if (choice.source || detecting) return detecting
  detecting = fetch('/api/v1/site/visitor-region')
    .then(res => (res.ok ? res.json() : {}))
    .then((found) => {
      if (choice.source || !['msk', 'spb', 'region'].includes(found?.region)) return
      choice.region = found.region
      choice.city = found.region === 'region' && typeof found.city === 'string' ? found.city : ''
      choice.source = 'auto'
    })
    .catch(() => { /* не определили — остаётся город по умолчанию */ })
  return detecting
}
watch(choice, (value) => {
  try { localStorage.setItem(CHOICE_KEY, JSON.stringify(value)) } catch { /* хранилище недоступно */ }
})
