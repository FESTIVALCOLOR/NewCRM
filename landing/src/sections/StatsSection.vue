<template>
  <section id="stats" class="section stats-bg">
    <div class="container">
      <p v-if="lead" class="stats__lead">{{ lead }}</p>
      <div class="stats__grid">
        <div v-for="item in stats" :key="item.id" class="stats__item reveal">
          <strong>{{ item.value }}</strong>
          <span>{{ item.label }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ stats: Array, settings: Object })
// Пустая строка в настройке скрывает заголовок; если настройки нет вовсе — текст по умолчанию
const lead = computed(() => props.settings?.stats_title ?? 'Обращаясь к нам, вы помогаете улучшить эту статистику:')
</script>

<style scoped>
/* Блок тёмный, поэтому общий цвет текста сайта здесь не действует — только цвет, заданный самому блоку (--sec-text) */
.stats-bg { background: var(--dark); color: var(--sec-text, #fff); }
.stats__lead { text-align: center; color: var(--sec-text-light, rgba(255,255,255,0.7)); margin-bottom: 40px; font-size: calc(1.05rem * var(--ts, 1)); }
.stats__grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 32px; text-align: center; }
.stats__item strong { display: block; font-family: var(--font-head); font-size: calc(clamp(2rem, 4vw, 3rem) * var(--head-scale, 1)); font-weight: 800; color: var(--accent); margin-bottom: 8px; }
.stats__item span { font-size: calc(0.9rem * var(--ts, 1)); color: var(--sec-text, rgba(255,255,255,0.8)); line-height: 1.4; }
@media (max-width: 768px) { .stats__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .stats__grid { grid-template-columns: 1fr 1fr; gap: 20px; } }
</style>
