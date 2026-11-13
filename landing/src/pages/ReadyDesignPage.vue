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
          <div v-if="current" :ref="observeStage" class="stage" @click="active = -1" @touchstart.passive="swipeStart" @touchend="swipeEnd">
            <div class="stage__bg" aria-hidden="true">
              <span :style="{ backgroundImage: `url('${neighbours.prev.url}')` }" />
              <span :style="{ backgroundImage: `url('${neighbours.next.url}')` }" />
            </div>
          <div class="photo" :class="{ 'photo--ready': photoBox }" :style="photoBox || null">
            <img :key="current.id" :src="current.url" :alt="current.alt || design.title" @load="remember(current.url, $event.target)" />
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
                <img v-if="activeMarker.image_url" :src="activeMarker.image_url" :alt="activeMarker.title" class="tip__photo" />
                <strong>{{ activeMarker.title }}</strong>
                <span v-if="activeMarker.sku" class="tip__sku">Артикул: {{ activeMarker.sku }}</span>
                <p v-if="activeMarker.description">{{ activeMarker.description }}</p>
                <dl v-if="specs(activeMarker).length" class="tip__specs">
                  <template v-for="spec in specs(activeMarker)" :key="spec.label">
                    <dt>{{ spec.label }}</dt><dd>{{ spec.value }}</dd>
                  </template>
                </dl>
                <a v-if="activeMarker.url" :href="activeMarker.url" target="_blank" rel="noopener nofollow">Подробнее о предмете →</a>
              </div>
            </template>
          </div>
            <template v-if="design.images.length > 1">
              <button type="button" class="photo__nav photo__nav--prev" aria-label="Предыдущее фото" @click.stop="step(-1)">‹</button>
              <button type="button" class="photo__nav photo__nav--next" aria-label="Следующее фото" @click.stop="step(1)">›</button>
              <span class="stage__count">{{ currentIndex + 1 }} / {{ design.images.length }}</span>
            </template>
          </div>
          <div v-else class="stage stage--empty">Фото этого дизайна скоро появятся</div>

          <div v-if="design.images.length > 1" ref="thumbsEl" class="thumbs">
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
                <img v-if="marker.image_url" :src="marker.image_url" alt="" class="items__photo" loading="lazy" />
                <span class="items__text">
                  <span>
                    <strong>{{ marker.title }}</strong>
                    <a v-if="marker.url" :href="marker.url" target="_blank" rel="noopener nofollow" title="Открыть страницу товара" @click.stop> ↗</a>
                  </span>
                  <span v-if="marker.sku" class="items__meta">Артикул: {{ marker.sku }}</span>
                  <span v-if="specs(marker).length" class="items__meta">{{ specs(marker).map(spec => `${spec.label.toLowerCase()}: ${spec.value}`).join(' · ') }}</span>
                  <span v-if="marker.description" class="items__desc">{{ marker.description }}</span>
                </span>
              </li>
            </ol>
          </div>
          <!-- Описание дизайна: по комнатам. Калькулятор справа остаётся рядом, пока читаешь -->
          <div v-if="about.cards.length || about.lead" class="design-about">
            <h2 class="design-about__title">О дизайне</h2>
            <p v-if="about.lead" class="design-about__lead"><strong>{{ about.lead.title }}.</strong> {{ about.lead.text }}</p>
            <div class="design-about__body" :class="[`design-about__body--${about.mode}`, { 'is-collapsed': collapsible && !expanded }]">
              <article v-for="(card, index) in about.cards" :key="index" class="design-about__card">
                <h3 v-if="card.title">{{ card.title }}</h3>
                <p>{{ card.text }}</p>
              </article>
            </div>
            <button v-if="collapsible" type="button" class="design-about__more" @click="expanded = !expanded">{{ expanded ? 'Свернуть' : 'Читать полностью' }}</button>
          </div>
        </div>

        <aside class="design__side">
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
import { computed, nextTick, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import ReadyCalculator from '../components/ReadyCalculator.vue'
import { site, ready, loadReadyDesigns } from '../store.js'
import { setPageTitle } from '../router.js'
import { parseDescription } from '../designDescription.js'

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

// ── Сцена галереи ──
// Высота сцены постоянная, поэтому страница не скачет при смене фото. Фото вписывается в сцену целиком,
// а рамка с отметками получает ровно его размер: отметки хранятся в процентах от самого фото
const stage = reactive({ w: 0, h: 0 })
const sizes = reactive({})
let stageEl = null
let resizeObserver = null

function observeStage(el) {
  if (el === stageEl) return
  resizeObserver?.disconnect()
  stageEl = el
  if (!el) return
  resizeObserver = new ResizeObserver(([entry]) => {
    stage.w = entry.contentRect.width
    stage.h = entry.contentRect.height
  })
  resizeObserver.observe(el)
}
function remember(url, img) {
  if (img?.naturalWidth && !sizes[url]) sizes[url] = [img.naturalWidth, img.naturalHeight]
}
// Размеры всех фото дизайна узнаём заранее: при переключении фото сразу встаёт на место
function measure(images) {
  for (const image of images) {
    if (sizes[image.url]) continue
    const probe = new Image()
    probe.onload = () => remember(image.url, probe)
    probe.src = image.url
  }
}
const photoBox = computed(() => {
  const size = current.value && sizes[current.value.url]
  if (!size || !stage.w || !stage.h) return null
  const scale = Math.min(stage.w / size[0], stage.h / size[1])
  return { width: `${Math.round(size[0] * scale)}px`, height: `${Math.round(size[1] * scale)}px` }
})
// Слева — предыдущее фото, справа — следующее; если фото одно, по бокам оно же
const neighbours = computed(() => {
  const images = design.value?.images || []
  const count = images.length
  if (!count) return { prev: {}, next: {} }
  return { prev: images[(currentIndex.value - 1 + count) % count], next: images[(currentIndex.value + 1) % count] }
})

// Пролистывание пальцем на телефоне
let touchX = null
function swipeStart(e) { touchX = e.changedTouches[0].clientX }
function swipeEnd(e) {
  if (touchX === null) return
  const dx = e.changedTouches[0].clientX - touchX
  touchX = null
  if (Math.abs(dx) > 50) step(dx < 0 ? 1 : -1)
}

// Характеристики товара: показываются только заполненные
const SPEC_LABELS = [['color', 'Цвет'], ['shape', 'Форма'], ['size', 'Размеры']]
function specs(marker) {
  return SPEC_LABELS.filter(([field]) => marker[field]).map(([field, label]) => ({ label, value: marker[field] }))
}

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

// Описание дизайна по комнатам; длинное сначала показывается свёрнутым
const COLLAPSE_FROM = 1600
const about = computed(() => parseDescription(design.value?.description))
const collapsible = computed(() => about.value.length > COLLAPSE_FROM)
const expanded = ref(false)

watch(() => route.params.id, () => { select(0); expanded.value = false })

// Лента миниатюр сама прокручивается к активному фото (прокручивается только лента, не страница)
const thumbsEl = ref(null)
watch(currentIndex, (index) => nextTick(() => {
  const strip = thumbsEl.value
  const thumb = strip?.children[index]
  if (!thumb) return
  const left = thumb.offsetLeft - (strip.clientWidth - thumb.offsetWidth) / 2
  strip.scrollTo({ left: Math.max(0, left), behavior: 'smooth' })
}))
watch(design, (value) => {
  if (!value) return
  setPageTitle(`${value.title} — готовый дизайн`)
  measure(value.images)
}, { immediate: true })

onMounted(() => {
  loadReadyDesigns()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.design { display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 400px); gap: 36px; align-items: start; }
.design__gallery { min-width: 0; }
/* Сцена: постоянная высота, фото по центру. Подсказки товаров могут выходить за край фото, поэтому обрезается только фон */
.stage { position: relative; height: clamp(340px, 68vh, 620px); display: flex; align-items: center; justify-content: center; border-radius: 12px; background: #f4f4f4; touch-action: pan-y; }
.stage--empty { background: #ececec; color: var(--text-light); }
.stage__bg { position: absolute; inset: 0; display: flex; overflow: hidden; border-radius: 12px; }
.stage__bg span { flex: 1; background: center / cover no-repeat; filter: blur(26px) brightness(1.08) saturate(0.95); transform: scale(1.25); }
/* Светлая вуаль поверх размытых соседних фото: фон остаётся живым, но не спорит с самим фото */
.stage__bg::after { content: ''; position: absolute; inset: 0; background: rgba(255, 255, 255, 0.45); }
.stage__bg span:first-child { background-position: right center; }
.stage__bg span:last-child { background-position: left center; }
.stage__count { position: absolute; right: 12px; bottom: 12px; z-index: 2; background: rgba(0, 0, 0, 0.5); color: #fff; font-size: 0.78rem; line-height: 1; padding: 5px 10px; border-radius: 12px; pointer-events: none; }
.photo { position: relative; line-height: 0; visibility: hidden; }
.photo--ready { visibility: visible; }
.photo > img { width: 100%; height: 100%; display: block; border-radius: 4px; box-shadow: 0 6px 24px rgba(0, 0, 0, 0.14); }

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
.tip__photo { width: 100%; height: 130px; object-fit: contain; background: #fff; border-radius: 6px; margin-bottom: 4px; }
.tip__sku { font-size: calc(0.76rem * var(--ts, 1)); color: var(--text-light); }
.tip__specs { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; margin: 2px 0; font-size: calc(0.8rem * var(--ts, 1)); }
.tip__specs dt { color: var(--text-light); }
.tip__specs dd { color: var(--text); }
.tip strong { font-family: var(--font-head); font-size: calc(0.92rem * var(--ts, 1)); color: var(--dark); }
/* Длинное описание не должно раздувать карточку: полный текст есть в списке под фото */
.tip p { color: var(--text-light); display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
.tip a { color: var(--accent); text-decoration: none; font-weight: 600; }
.tip a:hover { text-decoration: underline; }
.tip--right { transform: translateX(22px); }
.tip--left { transform: translateX(calc(-100% - 22px)); }
.tip--down { margin-top: -14px; }
.tip--up.tip--right { transform: translate(22px, -100%); margin-top: 14px; }
.tip--up.tip--left { transform: translate(calc(-100% - 22px), -100%); margin-top: 14px; }

.photo__nav {
  position: absolute; top: 50%; transform: translateY(-50%); z-index: 2; width: 40px; height: 40px; border-radius: 50%; border: none; cursor: pointer;
  background: rgba(0, 0, 0, 0.45); color: #fff; font-size: 1.5rem; line-height: 1; display: flex; align-items: center; justify-content: center; padding: 0 0 3px;
}
.photo__nav:hover { background: rgba(0, 0, 0, 0.7); }
.photo__nav--prev { left: 12px; }
.photo__nav--next { right: 12px; }

.thumbs { position: relative; display: flex; gap: 8px; margin-top: 10px; overflow-x: auto; padding-bottom: 4px; }
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
.items ol { list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 6px 20px; }
.items__photo { flex: 0 0 64px; width: 64px; height: 64px; object-fit: contain; background: #fff; border: 1px solid var(--border); border-radius: 6px; }
.items__text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.items__meta { font-size: calc(0.8rem * var(--ts, 1)); color: var(--text-light); }
.items__desc { font-size: calc(0.84rem * var(--ts, 1)); color: var(--text-light); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.items li { display: flex; gap: 10px; align-items: flex-start; padding: 6px 8px; border-radius: 8px; cursor: pointer; font-size: calc(0.9rem * var(--ts, 1)); color: var(--text-light); }
.items li:hover, .items li.active { background: var(--bg-alt); }
.items li strong { color: var(--text); }
.items li a { color: var(--accent); text-decoration: none; }
.items__num { flex: 0 0 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 0.72rem; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-top: 1px; }

.design__side { display: flex; flex-direction: column; gap: 20px; position: sticky; top: 88px; }
.design-about { margin-top: 40px; }
.design-about__title { font-size: calc(1.4rem * var(--head-scale, 1)); margin-bottom: 14px; }
.design-about__lead { font-size: calc(1.02rem * var(--ts, 1)); line-height: 1.65; color: var(--text); margin-bottom: 20px; }
.design-about__lead strong { color: var(--accent); font-weight: 600; }
.design-about__body { position: relative; }
/* Короткие карточки по комнатам — в две колонки: разная длина не оставляет дыр, как в сетке с рядами */
.design-about__body--labeled { column-count: 2; column-gap: 16px; }
/* Длинные абзацы — одной колонкой, как статья: так их удобно читать */
.design-about__body--paragraphs { display: flex; flex-direction: column; gap: 14px; }
.design-about__card { break-inside: avoid; margin-bottom: 16px; padding: 20px 22px; background: var(--bg-alt); border-radius: 12px; }
.design-about__body--paragraphs .design-about__card { margin-bottom: 0; }
.design-about__card h3 { font-size: calc(1rem * var(--head-scale, 1)); margin-bottom: 8px; color: var(--dark); }
.design-about__card p { font-size: calc(0.92rem * var(--ts, 1)); line-height: 1.7; color: var(--text-light); }
/* Свёрнутое длинное описание: видно начало, низ плавно растворяется */
.design-about__body.is-collapsed { max-height: 560px; overflow: hidden; }
.design-about__body.is-collapsed::after { content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 160px; background: linear-gradient(rgba(255, 255, 255, 0), var(--bg)); pointer-events: none; }
.design-about__more { margin-top: 14px; background: none; border: 1px solid var(--accent); color: var(--accent); border-radius: 8px; padding: 10px 22px; cursor: pointer; font-family: inherit; font-size: calc(0.9rem * var(--ts, 1)); font-weight: 600; }
.design-about__more:hover { background: var(--accent); color: #fff; }
@media (max-width: 600px) {
  .design-about__body--labeled { column-count: 1; }
}
.design__back { color: var(--text-light); text-decoration: none; font-size: calc(0.9rem * var(--ts, 1)); }
.design__back:hover { color: var(--accent); }
.missing { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 20px; }
/* На узком экране сбоку от отметки места нет: карточка встаёт по центру фото, под отметкой или над ней */
@media (max-width: 700px) {
  .stage { height: clamp(280px, 100vw, 460px); }
  .tip { left: 50% !important; width: min(280px, 86vw); }
  .tip--right, .tip--left { transform: translateX(-50%); }
  .tip--down { margin-top: 22px; }
  .tip--up.tip--right, .tip--up.tip--left { transform: translate(-50%, -100%); margin-top: -22px; }
}
@media (max-width: 1000px) {
  .design { grid-template-columns: 1fr; }
  .design__side { position: static; }
}
</style>
