<template>
  <section id="services" class="section">
    <div class="container">
      <h2 class="section-title">ЧТО МЫ ПРЕДЛАГАЕМ</h2>
      <div class="services__grid">
        <div v-for="srv in services" :key="srv.id" class="service-card reveal">
          <div class="service-card__icon">
            <svg v-if="srv.icon === 'consultation'" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
            <svg v-else-if="srv.icon === 'design'" viewBox="0 0 24 24"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 000-1.41l-2.34-2.34a1 1 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
            <svg v-else-if="srv.icon === 'supervision'" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8a3 3 0 100 6 3 3 0 000-6z"/></svg>
            <svg v-else-if="srv.icon === 'equipment'" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14H7v-2h5v2zm5-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
            <svg v-else viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
          </div>
          <h3>{{ srv.title }}</h3>
          <p>{{ srv.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({ services: Array })
</script>

<style scoped>
.services__grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 24px; }
.service-card { background: var(--bg-alt); border-radius: 12px; padding: 32px 24px; text-align: center; border: 1px solid var(--border); transition: box-shadow 0.2s, transform 0.2s; flex: 0 0 220px; max-width: 240px; }
.service-card:hover { box-shadow: 0 8px 32px rgba(232,98,42,0.12); transform: translateY(-4px); }
.service-card__icon { width: 56px; height: 56px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; }
.service-card__icon svg { width: 28px; height: 28px; fill: #fff; }
.service-card h3 { font-size: 1rem; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.03em; }
.service-card p { color: var(--text-light); font-size: 0.9rem; line-height: 1.6; }
</style>
