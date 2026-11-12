<template>
  <section id="portfolio" class="section section--alt">
    <div class="container">
      <h2 class="section-title">НАШИ РАБОТЫ</h2>
      <div class="portfolio__grid">
        <div
          v-for="img in portfolio"
          :key="img.id"
          class="portfolio__item reveal"
          @click="openLightbox(img)"
        >
          <img :src="img.url" :alt="img.alt || 'Проект студии FESTIVAL COLOR'" loading="lazy" />
        </div>
      </div>
      <!-- Lightbox -->
      <div v-if="lightbox" class="lightbox" @click.self="lightbox = null">
        <button class="lightbox__close" @click="lightbox = null">✕</button>
        <img :src="lightbox.url" :alt="lightbox.alt" />
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
defineProps({ portfolio: Array })
const lightbox = ref(null)
function openLightbox(img) { lightbox.value = img }
</script>

<style scoped>
.portfolio__grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; background: #c8c8c8; }
.portfolio__item { overflow: hidden; border-radius: 0; cursor: pointer; aspect-ratio: 4/3; background: #c8c8c8; }
.portfolio__item img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }
.portfolio__item:hover img { transform: scale(1.05); }
.lightbox { position: fixed; inset: 0; background: rgba(0,0,0,0.9); z-index: 200; display: flex; align-items: center; justify-content: center; padding: 20px; }
.lightbox img { max-width: 90vw; max-height: 90vh; object-fit: contain; border-radius: 4px; }
.lightbox__close { position: absolute; top: 20px; right: 24px; background: none; border: none; color: #fff; font-size: 1.8rem; cursor: pointer; }
@media (max-width: 768px) { .portfolio__grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 480px) { .portfolio__grid { grid-template-columns: 1fr; } }
</style>
