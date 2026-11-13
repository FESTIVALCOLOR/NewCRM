<template>
  <div>
    <section class="page-head">
      <div class="container">
        <h1>{{ site.settings.individual_title || 'ИНДИВИДУАЛЬНЫЙ ДИЗАЙН' }}</h1>
        <p>{{ site.settings.individual_subtitle || 'Проект, который создаётся с нуля под вашу квартиру, привычки и бюджет.' }}</p>
      </div>
    </section>

    <section v-if="advantages.length" id="advantages" class="section">
      <div class="container">
        <h2 class="section-title">ПОЧЕМУ ИНДИВИДУАЛЬНЫЙ ПРОЕКТ</h2>
        <div class="adv__grid">
          <div v-for="(item, index) in advantages" :key="index" class="adv reveal">
            <span class="adv__num">{{ String(index + 1).padStart(2, '0') }}</span>
            <h3>{{ item.title }}</h3>
            <p v-if="item.text">{{ item.text }}</p>
          </div>
        </div>
      </div>
    </section>

    <PortfolioSection v-if="sectionVisible('portfolio') && site.portfolio.length" :style="sectionStyles.portfolio" :portfolio="site.portfolio" />
    <PricingSection v-if="sectionVisible('pricing') && site.pricing.length" :style="sectionStyles.pricing" :pricing="site.pricing" :settings="site.settings" />

    <section class="section section--alt next">
      <div class="container next__inner">
        <div>
          <h2>Обсудим ваш проект?</h2>
          <p>Расскажите о квартире — рассчитаем стоимость и сроки.</p>
        </div>
        <div class="next__actions">
          <a :href="contactUrl" :target="linkTarget(contactUrl)" rel="noopener" class="btn btn--accent">Написать нам</a>
          <router-link to="/ready" class="btn btn--outline">Готовые дизайны — от {{ formatPrice(minReadyPrice(site.settings)) }}</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import PortfolioSection from '../sections/PortfolioSection.vue'
import PricingSection from '../sections/PricingSection.vue'
import { site, sectionStyles, sectionVisible } from '../store.js'
import { ctaUrl, linkTarget } from '../contact.js'
import { minReadyPrice, formatPrice } from '../readyPricing.js'
import { parseAdvantages } from '../advantages.js'
import { scheduleReveal } from '../reveal.js'

const advantages = computed(() => parseAdvantages(site.settings))
const contactUrl = computed(() => ctaUrl(site.settings, 'Здравствуйте! Интересует индивидуальный дизайн-проект.'))

// Портфолио и цены приходят с сервера уже после появления страницы
watch(() => site.loaded, () => scheduleReveal())
</script>

<style scoped>
.adv__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.adv { background: var(--bg-alt); border-radius: 12px; padding: 26px 24px; display: flex; flex-direction: column; gap: 8px; }
.adv__num { font-family: var(--font-head); font-weight: 800; font-size: calc(1.5rem * var(--ts, 1)); color: var(--accent); line-height: 1; }
.adv h3 { font-size: calc(1.02rem * var(--head-scale, 1)); font-weight: 700; }
.adv p { font-size: calc(0.9rem * var(--ts, 1)); color: var(--text-light); }
.next__inner { display: flex; align-items: center; justify-content: space-between; gap: 28px; flex-wrap: wrap; }
.next h2 { font-size: calc(1.5rem * var(--head-scale, 1)); margin-bottom: 6px; }
.next p { color: var(--text-light); }
.next__actions { display: flex; gap: 12px; flex-wrap: wrap; }
@media (max-width: 900px) { .adv__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 560px) {
  .adv__grid { grid-template-columns: 1fr; }
  .next__actions .btn { width: 100%; text-align: center; }
}
</style>
