<template>
  <section id="hero" class="hero" :style="heroBg">
    <div class="hero__overlay" />
    <div class="container hero__content">
      <h1 class="hero__title reveal">{{ settings.hero_title || 'Дизайн интерьеров вашей мечты' }}</h1>
      <p class="hero__sub reveal">{{ settings.hero_subtitle || 'Создаём уникальные пространства для жизни и работы' }}</p>
      <a :href="whatsappUrl" target="_blank" rel="noopener" class="btn btn--accent reveal">
        {{ settings.hero_cta || 'Свяжитесь с нами' }}
      </a>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ settings: Object })
const whatsappUrl = computed(() => {
  const phone = props.settings?.whatsapp_phone || '79062003365'
  return `https://wa.clck.bar/${phone}`
})
const heroBg = computed(() => {
  const url = props.settings?.hero_bg_url
  return url ? { background: `url('${url}') center/cover no-repeat` } : {}
})
</script>

<style scoped>
.hero {
  position: relative;
  min-height: 100vh;
  display: flex; align-items: center;
  background-color: #2a2a2a;
}
.hero__overlay {
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.35) 100%);
}
.hero__content {
  position: relative; z-index: 1;
  text-align: center; color: #fff;
  padding-top: 68px;
}
.hero__title {
  font-size: clamp(2rem, 5vw, 3.5rem);
  font-weight: 800; letter-spacing: 0.02em;
  margin-bottom: 20px;
  text-shadow: 0 2px 12px rgba(0,0,0,0.3);
}
.hero__sub {
  font-size: clamp(1rem, 2vw, 1.3rem);
  margin-bottom: 36px;
  opacity: 0.9;
  max-width: 640px; margin-left: auto; margin-right: auto;
}
.reveal { transition-delay: 0.1s; }
.reveal + .reveal { transition-delay: 0.2s; }
.reveal + .reveal + .reveal { transition-delay: 0.3s; }
</style>
