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
          <ul class="pricing-card__list">
            <li v-for="item in plan.items" :key="item.id">{{ item.text }}</li>
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
const props = defineProps({ pricing: Array, settings: Object })

function buildWhatsApp(plan) {
  const phone = props.settings?.whatsapp_phone || '79062003365'
  const text = encodeURIComponent(plan.whatsapp_text || `Здравствуйте, интересует тариф: ${plan.title}`)
  return `https://wa.clck.bar/${phone}?text=${text}`
}
</script>

<style scoped>
.pricing__sub { text-align: center; color: var(--text-light); margin-bottom: 40px; }
.pricing__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; }
.pricing-card { background: var(--bg-alt); border: 2px solid var(--border); border-radius: 12px; padding: 28px 24px; display: flex; flex-direction: column; gap: 20px; transition: transform 0.2s, box-shadow 0.2s; }
.pricing-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
.pricing-card.featured { border-color: var(--accent); background: #fff; box-shadow: 0 4px 24px rgba(232,98,42,0.15); }
.pricing-card__title { font-family: var(--font-head); font-weight: 700; font-size: 1rem; letter-spacing: 0.04em; text-align: center; }
.featured .pricing-card__title { color: var(--accent); }
.pricing-card__list { list-style: none; display: flex; flex-direction: column; gap: 8px; flex: 1; }
.pricing-card__list li { font-size: 0.88rem; color: var(--text-light); padding-left: 18px; position: relative; line-height: 1.5; }
.pricing-card__list li::before { content: '✓'; position: absolute; left: 0; color: var(--accent); font-weight: 700; }
.btn { text-align: center; }
</style>
