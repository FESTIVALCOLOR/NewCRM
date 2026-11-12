<template>
  <section id="about" class="section section--alt">
    <div class="container about">
      <div class="about__photo reveal">
        <img :src="member.photo_url || '/team-placeholder.jpg'" :alt="member.name" />
      </div>
      <div class="about__text reveal">
        <h2 class="about__heading">О НАШЕЙ КОМАНДЕ</h2>
        <p class="about__desc">{{ member.description }}</p>
        <div class="about__person">
          <strong>{{ member.name }}</strong>
          <span>{{ member.position }}</span>
          <span class="about__role">{{ member.role_label }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const props = defineProps({ team: Array })
const member = computed(() => props.team?.[0] || {})
import { computed } from 'vue'
</script>

<style scoped>
.about { display: grid; grid-template-columns: 320px 1fr; gap: 60px; align-items: center; }
.about__photo img { width: 100%; border-radius: 12px; object-fit: cover; aspect-ratio: 3/4; box-shadow: 0 8px 32px rgba(0,0,0,0.12); }
.about__heading { font-size: 1.8rem; font-weight: 700; margin-bottom: 20px; letter-spacing: 0.05em; }
.about__desc { color: var(--text-light); line-height: 1.8; margin-bottom: 24px; }
.about__person { display: flex; flex-direction: column; gap: 4px; }
.about__person strong { font-size: 1.1rem; font-weight: 700; font-family: var(--font-head); }
.about__person span { color: var(--text-light); font-size: 0.9rem; }
.about__role { color: var(--accent); font-weight: 600; }
@media (max-width: 768px) {
  .about { grid-template-columns: 1fr; }
  .about__photo img { max-width: 280px; margin: 0 auto; }
  .about__photo { display: flex; justify-content: center; }
}
</style>
