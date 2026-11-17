<template>
  <section id="directions" class="section section--alt directions">
    <div class="container">
      <h2 class="section-title">{{ settings?.directions_title || 'ВЫБЕРИТЕ СВОЙ ФОРМАТ' }}</h2>
      <div class="directions__grid">
        <router-link v-for="card in cards" :key="card.to" :to="card.to" class="direction reveal" :style="card.image ? { backgroundImage: `url('${card.image}')` } : null">
          <div class="direction__shade" />
          <div class="direction__body">
            <h3>{{ card.title }}</h3>
            <p>{{ card.text }}</p>
            <ul>
              <li v-for="line in card.points" :key="line">{{ line }}</li>
            </ul>
            <span class="btn btn--accent">{{ card.button }}</span>
          </div>
        </router-link>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ready, loadReadyDesigns, designCover } from '../store.js'
import { calcReady, minReadyPrice, formatPrice, formatDays } from '../readyPricing.js'

const props = defineProps({ settings: Object, portfolio: { type: Array, default: () => [] } })

// Обложки берутся из настроек; если не заданы — из портфолио и из первого готового дизайна
const cards = computed(() => [
  {
    to: '/individual',
    title: 'Индивидуальный дизайн',
    text: props.settings?.individual_card_text || 'Проект с нуля под ваш образ жизни, планировку и бюджет.',
    points: ['Авторская концепция и визуализация', 'Полный комплект рабочих чертежей'],
    button: 'Портфолио и цены',
    image: props.settings?.individual_cover_url || props.portfolio[0]?.url || '',
  },
  {
    to: '/ready',
    title: 'Готовый дизайн',
    text: props.settings?.ready_card_text || 'Выберите готовое решение из каталога — мы адаптируем его под вашу квартиру.',
    points: [`От ${formatPrice(minReadyPrice(props.settings))}`, `Срок — от ${formatDays(calcReady('msk', 0, props.settings).days)}`],
    button: 'Смотреть каталог',
    image: props.settings?.ready_cover_url || designCover(ready.designs[0]) || props.portfolio[1]?.url || '',
  },
])

onMounted(loadReadyDesigns)
</script>

<style scoped>
.directions__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.direction {
  position: relative; display: flex; align-items: flex-end; min-height: 440px; overflow: hidden;
  border-radius: 14px; background: #2a2a2a center / cover no-repeat; color: #fff; text-decoration: none;
  transition: transform 0.25s, box-shadow 0.25s;
}
.direction:hover { transform: translateY(-4px); box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22); }
.direction__shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0, 0, 0, 0.1) 0%, rgba(0, 0, 0, 0.78) 78%); }
.direction__body { position: relative; padding: 32px; display: flex; flex-direction: column; gap: 12px; align-items: flex-start; }
.direction h3 { color: #fff; font-size: calc(1.6rem * var(--head-scale, 1)); font-weight: 700; letter-spacing: 0.02em; }
.direction p { font-size: calc(1rem * var(--ts, 1)); opacity: 0.92; max-width: 440px; }
.direction ul { list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: calc(0.9rem * var(--ts, 1)); opacity: 0.88; }
.direction li { padding-left: 18px; position: relative; }
.direction li::before { content: ''; position: absolute; left: 0; top: 0.6em; width: 8px; height: 2px; background: var(--accent); }
.direction .btn { margin-top: 8px; padding: 12px 26px; }
@media (max-width: 800px) {
  .directions__grid { grid-template-columns: 1fr; }
  .direction { min-height: 340px; }
  .direction__body { padding: 24px; }
}
</style>
