<template>
  <div>
    <section class="page-head">
      <div class="container">
        <div class="page-head__crumbs"><router-link to="/ready">Готовый дизайн</router-link> / {{ design ? design.title : '…' }}</div>
        <h1>{{ design ? design.title : (ready.loaded ? 'Дизайн не найден' : ' ') }}</h1>
        <p v-if="design?.tagline">{{ design.tagline }}</p>
      </div>
    </section>

    <section v-if="design" class="section">
      <div class="container design">
        <div class="design__gallery">
          <div v-if="current" class="photo" @click="active = -1">
            <img :key="current.id" :src="current.url" :alt="current.alt || design.title" />
            <template v-if="showMarkers">
              <button
                v-for="(marker, index) in current.markers" :key="index" type="button"
                class="marker" :class="{ active: active === index }"
                :style="{ left: marker.x + '%', top: marker.y + '%' }"
                :aria-label="marker.title"
                @click.stop="active = active === index ? -1 : index"
                @mouseenter="hover(index)"
              >{{ index + 1 }}</button>
              <div
                v-if="activeMarker" class="tip" :class="tipSide" :style="{ left: activeMarker.x + '%', top: activeMarker.y + '%' }" @click.stop
              >
                <strong>{{ activeMarker.title }}</strong>
                <p v-if="activeMarker.description">{{ activeMarker.description }}</p>
                <a v-if="activeMarker.url" :href="activeMarker.url" target="_blank" rel="noopener nofollow">Подробнее о предмете →</a>
              </div>
            </template>
            <template v-if="design.images.length > 1">
              <button type="button" class="photo__nav photo__nav--prev" aria-label="Предыдущее фото" @click.stop="step(-1)">‹</button>
              <button type="button" class="photo__nav photo__nav--next" aria-label="Следующее фото" @click.stop="step(1)">›</button>
            </template>
          </div>
          <div v-else class="photo photo--empty">Фото этого дизайна скоро появятся</div>

          <div v-if="design.images.length > 1" class="thumbs">
            <button v-for="(image, index) in design.images" :key="image.id" type="button" :class="{ active: index === currentIndex }" @click="select(index)">
              <img :src="image.url" :alt="image.alt || `Фото ${index + 1}`" loading="lazy" />
              <span v-if="image.markers.length" class="thumbs__dot" title="На фото отмечена мебель" />
            </button>
          </div>

          <div v-if="current?.markers.length" class="items">
            <div class="items__head">
              <h3>Мебель и предметы на этом фото</h3>
              <button type="button" class="items__toggle" @click="showMarkers = !showMarkers; active = -1">{{ showMarkers ? 'Скрыть отметки' : 'Показать отметки' }}</button>
            </div>
            <ol>
              <li v-for="(marker, index) in current.markers" :key="index" :class="{ active: active === index }" @mouseenter="hover(index)" @click="showMarkers = true; active = index">
                <span class="items__num">{{ index + 1 }}</span>
                <span>
                  <strong>{{ marker.title }}</strong>
                  <template v-if="marker.description"> — {{ marker.description }}</template>
                  <a v-if="marker.url" :href="marker.url" target="_blank" rel="noopener nofollow" @click.stop> ↗</a>
                </span>
              </li>
            </ol>
          </div>
        </div>

        <aside class="design__side">
          <p v-if="design.description" class="design__text">{{ design.description }}</p>
          <ReadyCalculator :settings="site.settings" :design="design" />
          <router-link to="/ready" class="design__back">← Все готовые дизайны</router-link>
        </aside>
      </div>
    </section>

    <section v-else-if="ready.loaded" class="section">
      <div class="container missing">
        <p>Такого дизайна в каталоге нет — возможно, он снят с публикации.</p>
        <router-link to="/ready" class="btn btn--accent">Перейти в каталог</router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import ReadyCalculator from '../components/ReadyCalculator.vue'
import { site, ready, loadReadyDesigns } from '../store.js'
import { setPageTitle } from '../router.js'

const route = useRoute()
const currentIndex = ref(0)
const active = ref(-1)
const showMarkers = ref(true)

const design = computed(() => ready.designs.find(item => item.id === Number(route.params.id)) || null)
const current = computed(() => design.value?.images[currentIndex.value] || null)
const activeMarker = computed(() => (showMarkers.value && active.value >= 0 ? current.value?.markers[active.value] : null) || null)
// Подсказка раскрывается в ту сторону, где на фото больше места
const tipSide = computed(() => {
  const marker = activeMarker.value
  if (!marker) return ''
  return `${marker.x > 55 ? 'tip--left' : 'tip--right'} ${marker.y > 60 ? 'tip--up' : 'tip--down'}`
})

function select(index) {
  currentIndex.value = index
  active.value = -1
}
function step(delta) {
  const count = design.value?.images.length || 0
  if (count) select((currentIndex.value + delta + count) % count)
}
// Наведение открывает подсказку только там, где есть мышь: на сенсорном экране работает касание
function hover(index) {
  if (window.matchMedia('(hover: hover)').matches) active.value = index
}
function onKey(e) {
  if (e.key === 'ArrowLeft') step(-1)
  else if (e.key === 'ArrowRight') step(1)
  else if (e.key === 'Escape') active.value = -1
}

watch(() => route.params.id, () => select(0))
watch(design, (value) => { if (value) setPageTitle(`${value.title} — готовый дизайн`) }, { immediate: true })

onMounted(() => {
  loadReadyDesigns()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.design { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 400px); gap: 36px; align-items: start; }
.design__gallery { min-width: 0; }
.photo { position: relative; border-radius: 12px; background: #ececec; line-height: 0; }
.photo > img { width: 100%; height: auto; display: block; border-radius: 12px; }
.photo--empty { aspect-ratio: 4 / 3; display: flex; align-items: center; justify-content: center; color: var(--text-light); line-height: 1.6; }

.marker {
  position: absolute; width: 28px; height: 28px; margin: -14px 0 0 -14px; border-radius: 50%; cursor: pointer; z-index: 2;
  background: var(--accent); color: #fff; border: 2px solid #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
  font-family: var(--font-head); font-size: 0.78rem; font-weight: 700; line-height: 1; padding: 0;
  display: flex; align-items: center; justify-content: center; transition: transform 0.15s;
}
.marker::after { content: ''; position: absolute; inset: -6px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, 0.7); animation: marker-pulse 2.2s ease-out infinite; }
.marker:hover, .marker.active { transform: scale(1.15); }
.marker.active::after { animation: none; opacity: 0; }
@keyframes marker-pulse { 0% { transform: scale(0.7); opacity: 0.9; } 70%, 100% { transform: scale(1.5); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .marker::after { animation: none; opacity: 0; } }

.tip {
  position: absolute; z-index: 3; width: min(260px, 70vw); background: #fff; color: var(--text); border-radius: 10px; padding: 12px 14px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28); line-height: 1.45; font-size: calc(0.85rem * var(--ts, 1)); display: flex; flex-direction: column; gap: 4px;
}
.tip strong { font-family: var(--font-head); font-size: calc(0.92rem * var(--ts, 1)); color: var(--dark); }
.tip p { color: var(--text-light); }
.tip a { color: var(--accent); text-decoration: none; font-weight: 600; }
.tip a:hover { text-decoration: underline; }
.tip--right { transform: translateX(22px); }
.tip--left { transform: translateX(calc(-100% - 22px)); }
.tip--down { margin-top: -14px; }
.tip--up.tip--right { transform: translate(22px, -100%); margin-top: 14px; }
.tip--up.tip--left { transform: translate(calc(-100% - 22px), -100%); margin-top: 14px; }

.photo__nav {
  position: absolute; top: 50%; transform: translateY(-50%); z-index: 1; width: 40px; height: 40px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(0, 0, 0, 0.45); color: #fff; font-size: 1.5rem; line-height: 1; display: flex; align-items: center; justify-content: center; padding: 0 0 3px;
}
.photo__nav:hover { background: rgba(0, 0, 0, 0.7); }
.photo__nav--prev { left: 12px; }
.photo__nav--next { right: 12px; }

.thumbs { display: flex; gap: 8px; margin-top: 10px; overflow-x: auto; padding-bottom: 4px; }
.thumbs button { position: relative; flex: 0 0 96px; height: 72px; padding: 0; border: 2px solid transparent; border-radius: 8px; overflow: hidden; cursor: pointer; background: #e4e4e4; opacity: 0.75; transition: opacity 0.2s, border-color 0.2s; }
.thumbs button:hover { opacity: 1; }
.thumbs button.active { border-color: var(--accent); opacity: 1; }
.thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }
.thumbs__dot { position: absolute; top: 5px; right: 5px; width: 10px; height: 10px; border-radius: 50%; background: var(--accent); border: 2px solid #fff; }

.items { margin-top: 24px; }
.items__head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.items h3 { font-size: calc(1.05rem * var(--head-scale, 1)); }
.items__toggle { background: none; border: none; color: var(--accent); cursor: pointer; font-family: inherit; font-size: calc(0.85rem * var(--ts, 1)); padding: 0; }
.items__toggle:hover { text-decoration: underline; }
.items ol { list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 6px 20px; }
.items li { display: flex; gap: 10px; align-items: flex-start; padding: 6px 8px; border-radius: 8px; cursor: pointer; font-size: calc(0.9rem * var(--ts, 1)); color: var(--text-light); }
.items li:hover, .items li.active { background: var(--bg-alt); }
.items li strong { color: var(--text); }
.items li a { color: var(--accent); text-decoration: none; }
.items__num { flex: 0 0 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 0.72rem; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-top: 1px; }

.design__side { display: flex; flex-direction: column; gap: 20px; position: sticky; top: 88px; }
.design__text { white-space: pre-line; color: var(--text); font-size: calc(0.95rem * var(--ts, 1)); }
.design__back { color: var(--text-light); text-decoration: none; font-size: calc(0.9rem * var(--ts, 1)); }
.design__back:hover { color: var(--accent); }
.missing { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 20px; }
@media (max-width: 1000px) {
  .design { grid-template-columns: 1fr; }
  .design__side { position: static; }
}
</style>
