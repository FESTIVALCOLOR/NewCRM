<template>
  <section id="services" class="section">
    <div class="container">
      <h2 class="section-title">ЧТО МЫ ПРЕДЛАГАЕМ</h2>
      <div class="services__grid">
        <div v-for="srv in services" :key="srv.id" class="service-card reveal">
          <div class="service-card__icon">
            <svg viewBox="0 0 24 24"><path :d="serviceIconPath(srv.icon)" /></svg>
          </div>
          <h3>{{ srv.title }}</h3>
          <p>{{ srv.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { serviceIconPath } from '../serviceIcons.js'

defineProps({ services: Array })
</script>

<style scoped>
/* 5 карточек: 3 на первой строке (по 2/6), 2 на второй (по 3/6) */
.services__grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 24px;
  max-width: 1060px;
  margin: 0 auto;
}
.service-card { grid-column: span 2; }
.service-card:nth-child(4) { grid-column: span 3; }
.service-card:nth-child(5) { grid-column: span 3; }
.service-card {
  background: var(--bg-alt); border-radius: 12px; padding: 32px 24px;
  text-align: center; border: 1px solid var(--border);
  transition: box-shadow 0.2s, transform 0.2s;
}
.service-card:hover { box-shadow: 0 8px 32px color-mix(in srgb, var(--accent) 12%, transparent); transform: translateY(-4px); }
.service-card__icon { width: 56px; height: 56px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }
.service-card__icon svg { width: 28px; height: 28px; fill: #fff; }
.service-card h3 { font-size: calc(1rem * var(--ts, 1)); font-weight: 700; margin-bottom: 12px; letter-spacing: 0.03em; }
.service-card p { color: var(--text-light); font-size: calc(0.9rem * var(--ts, 1)); line-height: 1.6; }
@media (max-width: 768px) {
  .services__grid { grid-template-columns: repeat(2, 1fr); }
  .service-card, .service-card:nth-child(4), .service-card:nth-child(5) { grid-column: span 1; }
  /* Если последняя карточка одна в строке (нечётная позиция) — растянуть на всю ширину */
  .service-card:last-child:nth-child(odd) { grid-column: span 2; }
}
@media (max-width: 480px) {
  .services__grid { grid-template-columns: 1fr; }
  .service-card:last-child:nth-child(odd) { grid-column: span 1; }
}
</style>
