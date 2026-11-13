// Цена и срок готового дизайна: зависят от города и площади объекта.
// Значения по умолчанию можно изменить в панели управления (вкладка «Готовый дизайн»).

export const READY_DEFAULTS = {
  ready_price_msk: 45990,
  ready_price_spb: 42990,
  ready_price_region: 40990,
  ready_area_base: 90, // площадь, входящая в базовую цену, м²
  ready_area_step: 50, // шаг площади сверх базовой, м²
  ready_area_step_price: 23990, // доплата за каждый шаг
  ready_days_base: 20, // срок в рабочих днях
  ready_days_step: 10, // плюс к сроку за каждый шаг площади
}

export const REGIONS = [
  { key: 'msk', label: 'Москва', priceKey: 'ready_price_msk' },
  { key: 'spb', label: 'Санкт-Петербург', priceKey: 'ready_price_spb' },
  { key: 'region', label: 'Другой город', priceKey: 'ready_price_region' },
]

// Региональные центры России (без Москвы и Санкт-Петербурга — для них свои цены)
export const DEFAULT_REGION_CITIES = [
  'Абакан', 'Анадырь', 'Архангельск', 'Астрахань', 'Барнаул', 'Белгород', 'Биробиджан', 'Благовещенск', 'Брянск',
  'Великий Новгород', 'Владивосток', 'Владикавказ', 'Владимир', 'Волгоград', 'Вологда', 'Воронеж', 'Горно-Алтайск',
  'Грозный', 'Екатеринбург', 'Иваново', 'Ижевск', 'Иркутск', 'Йошкар-Ола', 'Казань', 'Калининград', 'Калуга',
  'Кемерово', 'Киров', 'Кострома', 'Краснодар', 'Красноярск', 'Курган', 'Курск', 'Кызыл', 'Липецк', 'Магадан',
  'Магас', 'Майкоп', 'Махачкала', 'Мурманск', 'Нальчик', 'Нарьян-Мар', 'Нижний Новгород', 'Новосибирск', 'Омск',
  'Орёл', 'Оренбург', 'Пенза', 'Пермь', 'Петрозаводск', 'Петропавловск-Камчатский', 'Псков', 'Ростов-на-Дону',
  'Рязань', 'Салехард', 'Самара', 'Саранск', 'Саратов', 'Севастополь', 'Симферополь', 'Смоленск', 'Ставрополь',
  'Сыктывкар', 'Тамбов', 'Тверь', 'Томск', 'Тула', 'Тюмень', 'Улан-Удэ', 'Ульяновск', 'Уфа', 'Хабаровск',
  'Ханты-Мансийск', 'Чебоксары', 'Челябинск', 'Черкесск', 'Чита', 'Элиста', 'Южно-Сахалинск', 'Якутск', 'Ярославль',
]

function positiveNumber(value, fallback) {
  const number = Number(String(value ?? '').replace(/\s/g, '').replace(',', '.'))
  return Number.isFinite(number) && number > 0 ? number : fallback
}

// Настройки расчёта из настроек сайта; пустые и некорректные значения заменяются значениями по умолчанию
export function readyConfig(settings) {
  return Object.fromEntries(Object.entries(READY_DEFAULTS).map(([key, fallback]) => [key, positiveNumber(settings?.[key], fallback)]))
}

// Список городов для регионов: по одному в строке; пустой список — значения по умолчанию
export function regionCities(settings) {
  const own = String(settings?.ready_region_cities || '').split(/\r?\n/).map(city => city.trim()).filter(Boolean)
  return own.length ? [...new Set(own)] : DEFAULT_REGION_CITIES
}

// Сколько шагов площади набралось сверх базовой: 90 м² — 0, 91–140 м² — 1, 141–190 м² — 2
export function extraSteps(area, config) {
  const over = positiveNumber(area, 0) - config.ready_area_base
  return over > 0 ? Math.ceil(over / config.ready_area_step) : 0
}

export function calcReady(regionKey, area, settings) {
  const config = readyConfig(settings)
  const region = REGIONS.find(item => item.key === regionKey) || REGIONS[0]
  const steps = extraSteps(area, config)
  const base = config[region.priceKey]
  const extra = steps * config.ready_area_step_price
  return { base, extra, steps, price: base + extra, days: config.ready_days_base + steps * config.ready_days_step }
}

export function minReadyPrice(settings) {
  const config = readyConfig(settings)
  return Math.min(...REGIONS.map(region => config[region.priceKey]))
}

export function formatPrice(value) {
  return `${Math.round(value).toLocaleString('ru-RU').replace(/ | /g, ' ')} ₽`
}

// «20 рабочих дней», «21 рабочий день», «22 рабочих дня»
export function formatDays(days) {
  const n = Math.abs(days) % 100
  const last = n % 10
  if (n > 10 && n < 20) return `${days} рабочих дней`
  if (last === 1) return `${days} рабочий день`
  if (last >= 2 && last <= 4) return `${days} рабочих дня`
  return `${days} рабочих дней`
}
