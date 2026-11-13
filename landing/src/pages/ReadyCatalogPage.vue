<template>
  <div>
    <section class="page-head">
      <div class="container">
        <h1>{{ site.settings.ready_title || 'ГОТОВЫЙ ДИЗАЙН' }}</h1>
        <p>{{ site.settings.ready_subtitle || 'Выберите готовое решение из каталога — мы адаптируем его под планировку вашей квартиры.' }}</p>
      </div>
    </section>

    <section id="catalog" class="section">
      <div class="container">
        <h2 class="section-title">КАТАЛОГ ДИЗАЙНОВ</h2>
        <div v-if="ready.designs.length" class="catalog__grid">
          <router-link v-for="design in ready.designs" :key="design.id" :to="`/ready/${design.id}`" class="design-card reveal">
            <div class="design-card__cover">
              <img v-if="designCover(design)" :src="designCover(design)" :alt="design.title" loading="lazy" />
              <span v-if="design.images.length" class="design-card__count">{{ design.images.length }} фото</span>
            </div>
            <div class="design-card__body">
              <h3>{{ design.title }}</h3>
              <p v-if="design.tagline">{{ design.tagline }}</p>
              <div class="design-card__foot">
                <span class="design-card__price">от {{ formatPrice(minPrice) }}</span>
                <span class="design-card__more">Подробнее →</span>
              </div>
            </div>
          </router-link>
        </div>
        <p v-else-if="ready.loaded" class="catalog__empty">Каталог готовых дизайнов наполняется. Напишите нам — пришлём подборку.</p>
      </div>
    </section>

    <section v-if="drawings.length" id="ready-drawings" class="section section--alt">
      <div class="container">
        <h2 class="section-title">{{ site.settings.ready_drawings_title || 'ЧТО ВХОДИТ В КОМПЛЕКТ ЧЕРТЕЖЕЙ' }}</h2>
        <p class="drawings__lead">{{ site.settings.ready_drawings_text || 'К выбранному дизайну мы готовим рабочие чертежи под вашу квартиру — по ним строители выполнят ремонт без лишних вопросов.' }}</p>
        <div class="drawings__grid">
          <article v-for="(item, index) in drawings" :key="index" class="drawing reveal">
            <span class="drawing__num">{{ String(index + 1).padStart(2, '0') }}</span>
            <h3>{{ item.title }}</h3>
            <p v-if="item.text">{{ item.text }}</p>
          </article>
        </div>
        <p v-if="drawingsNote" class="drawings__note">{{ drawingsNote }}</p>
      </div>
    </section>

    <section id="ready-pricing" class="section">
      <div class="container">
        <h2 class="section-title">ЦЕНЫ И СРОКИ</h2>
        <div class="pricing">
          <div class="pricing__info">
            <div class="pricing__tiles">
              <div v-for="tile in tiles" :key="tile.label" class="tile">
                <span>{{ tile.label }}</span>
                <strong>{{ formatPrice(tile.price) }}</strong>
              </div>
            </div>
            <ul class="pricing__rules">
              <li>Цена действует для объекта площадью до {{ config.ready_area_base }} м².</li>
              <li>Свыше {{ config.ready_area_base }} м² — плюс {{ formatPrice(config.ready_area_step_price) }} за каждые {{ config.ready_area_step }} м².</li>
              <li>Срок — {{ formatDays(config.ready_days_base) }}, плюс {{ config.ready_days_step }} дней за каждые {{ config.ready_area_step }} м² свыше {{ config.ready_area_base }} м².</li>
            </ul>
          </div>
          <ReadyCalculator :settings="site.settings" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import ReadyCalculator from '../components/ReadyCalculator.vue'
import { site, ready, loadReadyDesigns, designCover } from '../store.js'
import { REGIONS, readyConfig, minReadyPrice, formatPrice, formatDays } from '../readyPricing.js'
import { scheduleReveal } from '../reveal.js'
import { parseDrawings, DEFAULT_DRAWINGS_NOTE } from '../readyDrawings.js'

const config = computed(() => readyConfig(site.settings))
const drawings = computed(() => parseDrawings(site.settings))
// Сноска к рубрикам со звёздочкой; своя из настроек, пустая строка — без сноски
const drawingsNote = computed(() => site.settings.ready_drawings_note ?? (drawings.value.some(item => item.text.includes('*')) ? DEFAULT_DRAWINGS_NOTE : ''))
const minPrice = computed(() => minReadyPrice(site.settings))
const tiles = computed(() => REGIONS.map(region => ({
  label: region.key === 'region' ? 'Другие города' : region.label,
  price: config.value[region.priceKey],
})))

onMounted(loadReadyDesigns)
watch(() => ready.designs.length, () => scheduleReveal())
</script>

<style scoped>
.catalog__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }
.catalog__empty { text-align: center; color: var(--text-light); padding: 24px 0; }
.design-card { display: flex; flex-direction: column; background: #fff; border: 1px solid var(--border); border-radius: 14px; overflow: hidden; text-decoration: none; color: var(--text); transition: transform 0.25s, box-shadow 0.25s; }
.design-card:hover { transform: translateY(-4px); box-shadow: 0 12px 30px rgba(0, 0, 0, 0.1); }
.design-card__cover { position: relative; aspect-ratio: 4 / 3; background: #e4e4e4; overflow: hidden; }
.design-card__cover img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.4s; }
.design-card:hover .design-card__cover img { transform: scale(1.04); }
.design-card__count { position: absolute; left: 12px; bottom: 12px; background: rgba(0, 0, 0, 0.6); color: #fff; font-size: 0.78rem; padding: 3px 10px; border-radius: 12px; }
.design-card__body { padding: 20px 22px 22px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.design-card h3 { font-size: calc(1.15rem * var(--head-scale, 1)); font-weight: 700; }
.design-card p { font-size: calc(0.9rem * var(--ts, 1)); color: var(--text-light); }
.design-card__foot { margin-top: auto; padding-top: 10px; display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.design-card__price { font-family: var(--font-head); font-weight: 700; font-size: calc(1.1rem * var(--ts, 1)); color: var(--accent); white-space: nowrap; }
.design-card__more { font-size: calc(0.85rem * var(--ts, 1)); color: var(--text-light); white-space: nowrap; }
.design-card:hover .design-card__more { color: var(--accent); }

.drawings__lead { max-width: 720px; margin: -28px auto 36px; text-align: center; color: var(--text-light); font-size: calc(1rem * var(--ts, 1)); line-height: 1.6; }
.drawings__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(205px, 1fr)); gap: 16px; }
.drawing {
  position: relative; background: #fff; border-radius: 12px; padding: 22px 20px 20px; display: flex; flex-direction: column; gap: 6px;
  box-shadow: 0 2px 14px rgba(0, 0, 0, 0.05); border-top: 3px solid transparent; transition: border-color 0.25s, transform 0.25s, box-shadow 0.25s;
}
.drawing:hover { border-top-color: var(--accent); transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }
.drawing__num { font-family: var(--font-head); font-weight: 800; font-size: calc(0.85rem * var(--ts, 1)); color: var(--accent); letter-spacing: 0.04em; }
.drawing h3 { font-size: calc(0.98rem * var(--head-scale, 1)); line-height: 1.3; color: var(--dark); }
.drawing p { font-size: calc(0.86rem * var(--ts, 1)); line-height: 1.55; color: var(--text-light); }
.drawings__note { margin-top: 14px; font-size: calc(0.8rem * var(--ts, 1)); color: var(--text-light); }
@media (max-width: 560px) {
  .drawings__lead { margin-top: -16px; }
  .drawings__grid { grid-template-columns: 1fr 1fr; gap: 10px; }
  .drawing { padding: 16px 14px; }
}
.pricing { display: grid; grid-template-columns: 1fr minmax(340px, 440px); gap: 36px; align-items: start; }
.pricing__tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
.tile { background: #fff; border: 1px solid var(--border); border-radius: 12px; padding: 18px 16px; display: flex; flex-direction: column; gap: 6px; }
.tile span { font-size: calc(0.85rem * var(--ts, 1)); color: var(--text-light); }
.tile strong { font-family: var(--font-head); font-size: calc(1.3rem * var(--ts, 1)); color: var(--dark); white-space: nowrap; }
.pricing__rules { list-style: none; display: flex; flex-direction: column; gap: 10px; }
.pricing__rules li { position: relative; padding-left: 22px; font-size: calc(0.95rem * var(--ts, 1)); }
.pricing__rules li::before { content: '✓'; position: absolute; left: 0; color: var(--accent); font-weight: 700; }
@media (max-width: 900px) { .pricing { grid-template-columns: 1fr; } }
@media (max-width: 560px) {
  .pricing__tiles { grid-template-columns: 1fr; }
  .catalog__grid { grid-template-columns: 1fr; }
}
</style>
