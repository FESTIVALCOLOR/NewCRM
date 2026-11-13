<template>
  <section v-if="points.length" id="objects_map" ref="root" class="section objects-map" v-bind="$attrs">
    <div class="container">
      <h2 class="section-title">{{ title }}</h2>
      <p v-if="subtitle" class="objects-map__sub">{{ subtitle }}</p>
      <div class="objects-map__bar">
        <div v-if="cities.length > 1" class="objects-map__cities">
          <button type="button" :class="{ active: activeCity === '' }" @click="showCity('')">
            Все города<span v-if="showCounts"> · {{ points.length }}</span>
          </button>
          <button v-for="city in cities" :key="city.name" type="button" :class="{ active: activeCity === city.name }" @click="showCity(city.name)">
            {{ city.name }}<span v-if="showCounts"> · {{ city.count }}</span>
          </button>
        </div>
        <div class="objects-map__legend">
          <span v-for="item in legend" :key="item.kind"><i :style="{ background: item.color }" />{{ item.label }}</span>
        </div>
      </div>
    </div>
    <div ref="mapEl" class="objects-map__map" />
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

// Пока точки не загружены, блока нет вовсе — стиль блока передаётся на <section> явно
defineOptions({ inheritAttrs: false })
const props = defineProps({ settings: Object })

// Ближе этого масштаба карта не приближается: точки намеренно сдвинуты и показывают район, а не дом
const MAX_ZOOM = 14
const HEX = /^#[0-9a-f]{6}$/i
const KINDS = [
  { kind: 'done', label: 'Сданные проекты', setting: 'map_color_done', fallback: 'var(--accent)' },
  { kind: 'work', label: 'В работе', setting: 'map_color_work', fallback: '#2b6cb0' },
  { kind: 'supervision', label: 'Авторский надзор', setting: 'map_color_supervision', fallback: '#2f9e6b' },
]

const points = ref([])
const cities = ref([])
const activeCity = ref('')
const root = ref(null)
const mapEl = ref(null)

let L = null
let map = null
let layer = null
let observer = null

const title = computed(() => props.settings?.map_title || 'ГЕОГРАФИЯ НАШИХ ПРОЕКТОВ')
const subtitle = computed(() => props.settings?.map_subtitle || '')
const showCounts = computed(() => props.settings?.map_show_counts === '1')

function kindColor(item) {
  const custom = props.settings?.[item.setting]
  return HEX.test(custom || '') ? custom : item.fallback
}
// В легенде только те состояния, которые реально есть на карте
const legend = computed(() =>
  KINDS.filter(item => points.value.some(p => p.kind === item.kind)).map(item => ({ ...item, color: kindColor(item) })),
)

// Кружки рисуются в SVG, где var(--accent) не работает, поэтому цвет берётся уже вычисленным
function resolvedColors() {
  const accent = getComputedStyle(root.value).getPropertyValue('--accent').trim() || '#E8622A'
  return Object.fromEntries(KINDS.map(item => [item.kind, kindColor(item).startsWith('var(') ? accent : kindColor(item)]))
}

function draw() {
  if (!map) return
  layer.clearLayers()
  const colors = resolvedColors()
  for (const p of points.value) {
    L.circleMarker([p.lat, p.lon], {
      radius: 7, weight: 2, color: '#ffffff', fillColor: colors[p.kind] || colors.work, fillOpacity: 0.92, interactive: false,
    }).addTo(layer)
  }
}

function showCity(name, animate = true) {
  activeCity.value = name
  if (!map) return
  const coords = points.value.filter(p => !name || p.city === name).map(p => [p.lat, p.lon])
  if (coords.length) map.fitBounds(L.latLngBounds(coords), { padding: [50, 50], maxZoom: 11, animate })
}

async function initMap() {
  if (map || !mapEl.value) return
  const [leaflet] = await Promise.all([import('leaflet'), import('leaflet/dist/leaflet.css')])
  if (map || !mapEl.value) return
  L = leaflet.default ?? leaflet
  // На сенсорных экранах карта не перехватывает прокрутку страницы: двигается и приближается двумя пальцами
  const touch = window.matchMedia('(pointer: coarse)').matches
  map = L.map(mapEl.value, { scrollWheelZoom: false, dragging: !touch, minZoom: 3, maxZoom: MAX_ZOOM, zoomSnap: 0.5 })
  map.attributionControl.setPrefix(false)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: MAX_ZOOM,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
  }).addTo(map)
  layer = L.layerGroup().addTo(map)
  // Колесо мыши приближает карту только после клика по ней — иначе карта «ловит» прокрутку страницы
  map.on('click', () => map.scrollWheelZoom.enable())
  mapEl.value.addEventListener('mouseleave', () => map.scrollWheelZoom.disable())
  draw()
  showCity(activeCity.value, false)
}

async function loadPoints() {
  try {
    const res = await fetch('/api/v1/site/map-points')
    if (!res.ok) return
    const data = await res.json()
    cities.value = data.cities || []
    points.value = data.points || []
  } catch (e) {
    console.warn('Не удалось загрузить карту объектов:', e)
  }
}

// Библиотека карты и плитки загружаются, только когда посетитель долистал почти до блока
watch(() => points.value.length, async (count) => {
  if (!count || observer) return
  await nextTick()
  observer = new IntersectionObserver((entries) => {
    if (entries.some(e => e.isIntersecting)) { observer.disconnect(); initMap() }
  }, { rootMargin: '600px' })
  observer.observe(root.value)
})

watch(() => [props.settings?.map_color_done, props.settings?.map_color_work, props.settings?.map_color_supervision, props.settings?.style_accent], draw)

onMounted(loadPoints)
onBeforeUnmount(() => {
  observer?.disconnect()
  map?.remove()
  map = null
})
</script>

<style scoped>
.objects-map { padding-bottom: 0; }
.objects-map .section-title { margin-bottom: 20px; }
.objects-map__sub { text-align: center; color: var(--text-light); max-width: 720px; margin: 0 auto 8px; }
.objects-map__bar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px 28px; margin: 28px 0 24px; }
.objects-map__cities { display: flex; flex-wrap: wrap; gap: 8px; }
.objects-map__cities button {
  border: 1px solid var(--border); background: #fff; color: var(--text);
  border-radius: 18px; padding: 7px 16px; cursor: pointer;
  font-family: inherit; font-size: calc(0.88rem * var(--ts, 1)); transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.objects-map__cities button:hover { border-color: var(--accent); color: var(--accent); }
.objects-map__cities button.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.objects-map__legend { display: flex; flex-wrap: wrap; gap: 8px 20px; margin-left: auto; color: var(--text-light); font-size: calc(0.85rem * var(--ts, 1)); }
.objects-map__legend i { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; vertical-align: -1px; box-shadow: 0 0 0 2px #fff, 0 0 0 3px var(--border); }
/* z-index создаёт свой слой наложения: иначе панели карты перекрывают шапку сайта и кнопку WhatsApp */
.objects-map__map { position: relative; z-index: 0; width: 100%; height: clamp(380px, 62vh, 640px); background: #ececec; }
/* Монохромной делается только подложка — кружки объектов остаются цветными */
.objects-map__map :deep(.leaflet-tile-pane) { filter: grayscale(1) contrast(0.9) brightness(1.07); }
.objects-map__map :deep(.leaflet-container) { font-family: inherit; }
@media (max-width: 700px) {
  .objects-map__legend { margin-left: 0; }
  .objects-map__map { height: 420px; }
}
</style>
