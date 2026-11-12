<template>
  <section id="portfolio" class="section section--alt">
    <div class="container">
      <h2 class="section-title">НАШИ РАБОТЫ</h2>
    </div>
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
  </section>
</template>

<script setup>
import { ref } from 'vue'
defineProps({ portfolio: Array })
const lightbox = ref(null)
function openLightbox(img) { lightbox.value = img }
</script>

<style scoped>
.portfolio__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 2px; background: #c8c8c8; width: 100%; }
.portfolio__item { overflow: hidden; cursor: pointer; aspect-ratio: 4/3; background: #c8c8c8; }
.portfolio__item img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.4s; }
.portfolio__item:hover img { transform: scale(1.05); }
.lightbox { position: fixed; inset: 0; background: rgba(0,0,0,0.92); z-index: 200; display: flex; align-items: center; justify-content: center; padding: 4px; }
.lightbox img { width: 98vw; height: 96vh; object-fit: contain; border-radius: 2px; box-shadow: 0 4px 40px rgba(0,0,0,0.6); }
.lightbox__close { position: absolute; top: 12px; right: 16px; background: rgba(0,0,0,0.5); border: none; color: #fff; font-size: 1.6rem; cursor: pointer; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; line-height: 1; }
.lightbox__close:hover { background: rgba(255,255,255,0.15); }
</style>
