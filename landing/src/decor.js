// Декор в боковых полях блоков на широких экранах: напольные предметы и подвесные светильники.
// Раскладка выбирается здесь, а рисуется стилями из assets/decor.css.
//
// Правила:
// - с каждой стороны блока стоит либо напольный предмет (на линии пола внизу), либо светильник (с потолка вверху);
// - напольный предмет внизу блока и светильник вверху следующего блока не встают на одну сторону —
//   иначе светильник «висит» прямо под стулом;
// - предметы немного сдвинуты и отличаются размером, соседние блоки не повторяют друг друга;
// - раскладка зависит только от блоков, поэтому одинакова при каждом открытии страницы.
import floorLamp from './assets/decor/floor-lamp.svg'
import armchair from './assets/decor/armchair.svg'
import plant from './assets/decor/plant.svg'
import sideTable from './assets/decor/side-table.svg'
import chair from './assets/decor/chair.svg'
import pendantDome from './assets/decor/pendant-dome.svg'
import pendantCone from './assets/decor/pendant-cone.svg'
import pendantGlobe from './assets/decor/pendant-globe.svg'
import pendantFlat from './assets/decor/pendant-flat.svg'
import pendantTrio from './assets/decor/pendant-trio.svg'

// w — обычная ширина рисунка на сайте, ratio — пропорции его viewBox
const ITEMS = {
  floor: [
    { name: 'floor-lamp', url: floorLamp, w: 160, ratio: '200 / 416.25' },
    { name: 'armchair', url: armchair, w: 200, ratio: '240 / 219.25' },
    { name: 'plant', url: plant, w: 140, ratio: '160 / 291.25' },
    { name: 'side-table', url: sideTable, w: 140, ratio: '160 / 271.25' },
    { name: 'chair', url: chair, w: 120, ratio: '140 / 251.25' },
  ],
  ceiling: [
    { name: 'pendant-dome', url: pendantDome, w: 110, ratio: '120 / 300' },
    { name: 'pendant-cone', url: pendantCone, w: 110, ratio: '120 / 270' },
    { name: 'pendant-globe', url: pendantGlobe, w: 100, ratio: '120 / 286' },
    { name: 'pendant-flat', url: pendantFlat, w: 140, ratio: '160 / 228' },
    { name: 'pendant-trio', url: pendantTrio, w: 170, ratio: '180 / 256' },
  ],
}

// Блоки с содержимым фиксированной ширины — у них по бокам есть пустое поле
const DECORATED = new Set(['about', 'services', 'project_example', 'directions', 'advantages', 'pricing', 'catalog', 'ready-pricing', 'reviews', 'contacts'])
const SIDES = ['left', 'right']
const SHIFT_PX = 70 // насколько предмет может сместиться левее или правее
const ATTRS = ['data-decor-left', 'data-decor-right', 'data-decor-ceiling-line']

// Детерминированное «случайное» число 0…1 по строке: раскладка не меняется от обновления к обновлению
function noise(key) {
  let h = 2166136261
  for (const ch of key) h = Math.imul(h ^ ch.charCodeAt(0), 16777619)
  return ((h >>> 0) % 10000) / 10000
}

function pick(kind, key, avoid) {
  const pool = ITEMS[kind]
  const start = Math.floor(noise(key) * pool.length)
  for (let i = 0; i < pool.length; i++) {
    const item = pool[(start + i) % pool.length]
    if (!avoid.has(item.name)) return item
  }
  return pool[start]
}

function clear(section) {
  ATTRS.forEach(attr => section.removeAttribute(attr))
}

export function applyDecor() {
  if (typeof document === 'undefined') return
  // Состояние предыдущего блока, если он стоит вплотную: что у него внизу с каждой стороны
  let prev = null
  for (const section of document.querySelectorAll('main section')) {
    if (!DECORATED.has(section.id) || !section.classList.contains('section')) {
      if (section.hasAttribute('data-decor-left')) clear(section)
      prev = null
      continue
    }
    const used = new Set()
    const state = { floorAtBottom: { left: false, right: false }, items: new Set() }
    // У «Контактов» внизу карта: напольный предмет стоит на её крае, а не на нижней границе блока
    const floorOnBlockEdge = !section.querySelector('.contacts__map')
    for (const side of SIDES) {
      const key = `${section.id}:${side}`
      let kind = noise(`${key}:kind`) < 0.5 ? 'floor' : 'ceiling'
      // Светильник не должен висеть прямо под напольным предметом предыдущего блока
      if (kind === 'ceiling' && prev?.floorAtBottom[side]) kind = 'floor'
      const avoid = new Set([...used, ...(prev?.items || [])])
      const item = pick(kind, `${key}:item`, avoid)
      used.add(item.name)
      state.items.add(item.name)
      if (kind === 'floor' && floorOnBlockEdge) state.floorAtBottom[side] = true

      const scale = 0.88 + noise(`${key}:size`) * 0.24
      const shift = Math.round((noise(`${key}:shift`) * 2 - 1) * SHIFT_PX)
      const prefix = side === 'left' ? '--dl' : '--dr'
      section.setAttribute(`data-decor-${side}`, kind)
      section.style.setProperty(`${prefix}-img`, `url("${item.url}")`)
      section.style.setProperty(`${prefix}-w`, `${Math.round(item.w * scale)}px`)
      section.style.setProperty(`${prefix}-ratio`, item.ratio)
      section.style.setProperty(`${prefix}-shift`, `${shift}px`)
    }
    // Линия пола предыдущего блока идёт во всю ширину — второй линии потолка под ней не нужно
    const floorLineAbove = Boolean(prev && (prev.floorAtBottom.left || prev.floorAtBottom.right))
    section.setAttribute('data-decor-ceiling-line', floorLineAbove ? '0' : '1')
    prev = state
  }
}

// Блоки появляются и исчезают при переходе между страницами и по мере загрузки данных —
// раскладку пересчитываем, когда меняется набор блоков (а не на каждое изменение страницы)
let observer = null
let pending = 0
function isLayoutNode(node) {
  return node.nodeType === 1 && (node.tagName === 'SECTION' || node.classList.contains('contacts__map') || node.querySelector?.('section, .contacts__map'))
}
export function watchDecor(root) {
  if (observer || !root || typeof MutationObserver === 'undefined') return
  observer = new MutationObserver((records) => {
    const changed = records.some(r => [...r.addedNodes, ...r.removedNodes].some(isLayoutNode))
    if (!changed) return
    cancelAnimationFrame(pending)
    pending = requestAnimationFrame(applyDecor)
  })
  observer.observe(root, { childList: true, subtree: true })
  applyDecor()
}
