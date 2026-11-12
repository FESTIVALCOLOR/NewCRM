<template>
  <section class="section stats-bg">
    <div class="container">
      <p class="stats__lead">Обращаясь к нам, вы помогаете улучшить эту статистику:</p>
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
defineProps({ stats: Array })
</script>

<style scoped>
.stats-bg { background: var(--dark); color: #fff; }
.stats__lead { text-align: center; color: rgba(255,255,255,0.7); margin-bottom: 40px; font-size: 1.05rem; }
.stats__grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 32px; text-align: center; }
.stats__item strong { display: block; font-family: var(--font-head); font-size: clamp(2rem, 4vw, 3rem); font-weight: 800; color: var(--accent); margin-bottom: 8px; }
.stats__item span { font-size: 0.9rem; color: rgba(255,255,255,0.8); line-height: 1.4; }
@media (max-width: 768px) { .stats__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .stats__grid { grid-template-columns: 1fr 1fr; gap: 20px; } }
</style>
