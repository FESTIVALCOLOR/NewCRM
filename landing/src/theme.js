// Оформление сайта: шрифты, цвета и размеры из вкладки «Стиль» админки.
// Значения хранятся в настройках сайта (ключи style_*), пустое значение = по умолчанию.

// Шрифты Google Fonts с кириллицей; weights — начертания, которые у шрифта реально есть
export const FONTS = [
  { name: 'Montserrat', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Open Sans', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Inter', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Roboto', fallback: 'sans-serif', weights: '400;500;700;900' },
  { name: 'Manrope', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Raleway', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Rubik', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Nunito', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Jost', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'Golos Text', fallback: 'sans-serif', weights: '400;500;600;700;800' },
  { name: 'PT Sans', fallback: 'sans-serif', weights: '400;700' },
  { name: 'Oswald', fallback: 'sans-serif', weights: '400;500;600;700' },
  { name: 'Playfair Display', fallback: 'serif', weights: '400;500;600;700;800' },
  { name: 'Cormorant Garamond', fallback: 'serif', weights: '400;500;600;700' },
  { name: 'PT Serif', fallback: 'serif', weights: '400;700' },
  { name: 'Lora', fallback: 'serif', weights: '400;500;600;700' },
]

export const STYLE_DEFAULTS = {
  style_font_head: 'Montserrat',
  style_font_body: 'Open Sans',
  style_accent: '#E8622A',
  style_head_color: '#333333',
  style_text_color: '#333333',
  style_text_light_color: '#666666',
  style_head_size: '100',
  style_text_size: '100',
  // Предметы интерьера в боковых полях на широких экранах: '1' — показывать, '0' — скрыть
  style_decor: '1',
  style_decor_color: '#cfc8c0',
}

export const SIZE_MIN = 80
export const SIZE_MAX = 140

const HEX = /^#[0-9a-f]{6}$/i

function validFont(name, fallbackName) {
  return FONTS.find(f => f.name === name) || FONTS.find(f => f.name === fallbackName)
}
function validColor(value, fallback) {
  return HEX.test(value || '') ? value : fallback
}
function validSize(value) {
  const n = parseInt(value, 10)
  return Number.isFinite(n) ? Math.min(SIZE_MAX, Math.max(SIZE_MIN, n)) : 100
}
function darken(hex, factor = 0.88) {
  const parts = [1, 3, 5].map(i => Math.round(parseInt(hex.slice(i, i + 2), 16) * factor))
  return '#' + parts.map(p => p.toString(16).padStart(2, '0')).join('')
}

export function loadFont(name) {
  const font = validFont(name)
  if (!font) return
  const id = 'font-' + font.name.replace(/\s+/g, '-')
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = `https://fonts.googleapis.com/css2?family=${font.name.replace(/\s+/g, '+')}:wght@${font.weights}&display=swap`
  document.head.appendChild(link)
}

// CSS-переменные для набора настроек; используется и сайтом, и предпросмотром в админке
export function themeVars(settings) {
  const s = settings || {}
  const d = STYLE_DEFAULTS
  const head = validFont(s.style_font_head, d.style_font_head)
  const body = validFont(s.style_font_body, d.style_font_body)
  const accent = validColor(s.style_accent, d.style_accent)
  const textSize = validSize(s.style_text_size)
  const headSize = validSize(s.style_head_size)
  return {
    fonts: [head.name, body.name],
    textSize,
    vars: {
      '--font-head': `'${head.name}', ${head.fallback}`,
      '--font-body': `'${body.name}', ${body.fallback}`,
      '--accent': accent,
      '--accent-hover': darken(accent),
      '--head-color': validColor(s.style_head_color, d.style_head_color),
      '--text': validColor(s.style_text_color, d.style_text_color),
      '--text-light': validColor(s.style_text_light_color, d.style_text_light_color),
      // Размер текста задаёт базу для всей страницы, поэтому заголовки делятся на него — так два ползунка независимы
      '--head-scale': String(headSize / textSize),
      '--decor-color': validColor(s.style_decor_color, d.style_decor_color),
    },
  }
}

// ── Стиль отдельных блоков ──
// Хранится одной настройкой style_sections в виде JSON: { about: { accent: '#...', head_size: '120' }, ... }.
// В блоке задаётся только то, что отличается от общего стиля.
export const SECTION_STYLE_KEY = 'style_sections'
export const SECTION_KEYS = ['hero', 'about', 'stats', 'services', 'portfolio', 'pricing', 'reviews', 'contacts']

export function parseSectionStyles(settings) {
  try {
    const value = JSON.parse(settings?.[SECTION_STYLE_KEY] || '{}')
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  } catch {
    return {}
  }
}

// Inline-стиль для <section>: переменные действуют только внутри блока
export function sectionStyle(key, sec, settings) {
  const style = {}
  if (!sec) return style
  const globalText = validSize(settings?.style_text_size)
  const head = validFont(sec.font_head)
  const body = validFont(sec.font_body)
  if (head) { style['--font-head'] = `'${head.name}', ${head.fallback}`; loadFont(head.name) }
  if (body) { style['--font-body'] = `'${body.name}', ${body.fallback}`; loadFont(body.name) }
  if (HEX.test(sec.accent || '')) { style['--accent'] = sec.accent; style['--accent-hover'] = darken(sec.accent) }
  if (HEX.test(sec.head_color || '')) { style['--head-color'] = sec.head_color; style['--h1-color'] = sec.head_color }
  if (HEX.test(sec.text_color || '')) {
    style['--text'] = sec.text_color; style['--sec-text'] = sec.text_color; style['--hero-text'] = sec.text_color
  }
  if (HEX.test(sec.text_light_color || '')) { style['--text-light'] = sec.text_light_color; style['--sec-text-light'] = sec.text_light_color }
  // Базовый размер страницы уже умножен на общий размер текста, поэтому делим на него
  if (sec.head_size) style['--head-scale'] = String(validSize(sec.head_size) / globalText)
  if (sec.text_size) style['--ts'] = String(validSize(sec.text_size) / globalText)
  // У главного экрана фон — фотография, цвет фона для него не задаётся
  if (key !== 'hero' && HEX.test(sec.bg || '')) style.background = sec.bg
  return style
}

export function allSectionStyles(settings) {
  const parsed = parseSectionStyles(settings)
  return Object.fromEntries(SECTION_KEYS.map(key => [key, sectionStyle(key, parsed[key], settings)]))
}

const CACHE_KEY = 'site_style'

export function applyTheme(settings) {
  const { fonts, textSize, vars } = themeVars(settings)
  fonts.forEach(loadFont)
  const root = document.documentElement
  for (const [key, value] of Object.entries(vars)) root.style.setProperty(key, value)
  root.style.fontSize = textSize + '%'
  root.classList.toggle('no-decor', settings?.style_decor === '0')
}

// Стиль прошлого визита применяется до ответа сервера, чтобы страница не «прыгала» при загрузке
export function applyCachedTheme() {
  try {
    const cached = JSON.parse(localStorage.getItem(CACHE_KEY) || 'null')
    if (cached) { applyTheme(cached); return cached }
  } catch { /* повреждённый кэш игнорируется */ }
  return {}
}
export function cacheTheme(settings) {
  const style = {}
  for (const key of [...Object.keys(STYLE_DEFAULTS), SECTION_STYLE_KEY]) if (settings?.[key]) style[key] = settings[key]
  try { localStorage.setItem(CACHE_KEY, JSON.stringify(style)) } catch { /* хранилище недоступно */ }
}
