<template>
  <section id="pricing" class="section">
    <div class="container">
      <h2 class="section-title">НАШИ ЦЕНЫ</h2>
      <p class="pricing__sub">Для точного расчёта и консультации — напишите нам</p>
      <div class="pricing__grid">
        <div
          v-for="plan in pricing"
          :key="plan.id"
          class="pricing-card reveal"
          :class="{ featured: plan.is_featured }"
        >
          <div class="pricing-card__title">{{ plan.title }}</div>
          <div v-if="plan.price_label" class="pricing-card__price">{{ plan.price_label }}</div>
          <ul class="pricing-card__list">
            <li v-for="item in plan.items" :key="item.id" class="pricing-item">
              <div class="pricing-item__row" @click="item.subitems && item.subitems.length && toggle(item.id)" :class="{ clickable: item.subitems && item.subitems.length }">
                <span class="pricing-item__text">{{ item.text }}</span>
                <span v-if="item.subitems && item.subitems.length" class="pricing-item__toggle" :class="{ open: expanded[item.id] }">▼</span>
              </div>
              <ul v-if="item.subitems && item.subitems.length && expanded[item.id]" class="pricing-item__sub">
                <li v-for="(sub, si) in item.subitems" :key="si">{{ sub }}</li>
              </ul>
            </li>
          </ul>
          <a :href="buildWhatsApp(plan)" target="_blank" rel="noopener" class="btn" :class="plan.is_featured ? 'btn--accent' : 'btn--outline'">
            Заказать
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { ctaUrl } from '../contact.js'
const props = defineProps({ pricing: Array, settings: Object })
const expanded = ref({})

function toggle(id) {
  expanded.value[id] = !expanded.value[id]
}

function buildWhatsApp(plan) {
  return ctaUrl(props.settings, plan.whatsapp_text || `Здравствуйте, интересует тариф: ${plan.title}`)
}
</script>

<style scoped>
.pricing__sub { text-align: center; color: var(--text-light); margin-bottom: 40px; }
.pricing__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
@media (max-width: 900px) { .pricing__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) { .pricing__grid { grid-template-columns: 1fr; } }
.pricing-card { background: var(--bg-alt); border: 2px solid var(--border); border-radius: 12px; padding: 28px 24px; display: flex; flex-direction: column; gap: 16px; transition: transform 0.2s, box-shadow 0.2s; }
.pricing-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
.pricing-card.featured { border-color: var(--accent); background: #fff; box-shadow: 0 4px 24px color-mix(in srgb, var(--accent) 15%, transparent); }
.pricing-card__title { font-family: var(--font-head); font-weight: 700; font-size: 1rem; letter-spacing: 0.04em; text-align: center; }
.featured .pricing-card__title { color: var(--accent); }
.pricing-card__price { text-align: center; font-size: 1.1rem; font-weight: 700; color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 6px; padding: 6px 12px; }
.pricing-card__list { list-style: none; display: flex; flex-direction: column; gap: 2px; flex: 1; }
.pricing-item { display: flex; flex-direction: column; }
.pricing-item__row { display: flex; align-items: center; gap: 6px; padding: 4px 0 4px 18px; position: relative; }
.pricing-item__row::before { content: '✓'; position: absolute; left: 0; color: var(--accent); font-weight: 700; font-size: 0.88rem; }
.pricing-item__row.clickable { cursor: pointer; }
.pricing-item__row.clickable:hover .pricing-item__text { color: var(--accent); }
.pricing-item__text { font-size: 0.88rem; color: var(--text-light); line-height: 1.5; flex: 1; transition: color 0.15s; }
.pricing-item__toggle {
  color: var(--accent); font-size: 0.6rem; padding: 2px 4px;
  line-height: 1; transition: transform 0.2s; flex-shrink: 0; display: inline-block;
}
.pricing-item__toggle.open { transform: rotate(180deg); }
.pricing-item__sub {
  list-style: none; margin: 2px 0 4px 18px;
  background: color-mix(in srgb, var(--accent) 6%, transparent); border-left: 2px solid var(--accent);
  border-radius: 0 4px 4px 0; padding: 6px 10px; display: flex; flex-direction: column; gap: 3px;
}
.pricing-item__sub li { font-size: 0.8rem; color: var(--text-light); padding-left: 10px; position: relative; }
.pricing-item__sub li::before { content: '—'; position: absolute; left: 0; color: var(--accent); }
.btn { text-align: center; }
</style>
