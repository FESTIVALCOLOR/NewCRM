<template>
  <header class="header" :class="{ scrolled }">
    <div class="container header__inner">
      <a href="#hero" class="header__logo">
        <span class="logo-festival">FESTIVAL</span><span class="logo-color">COLOR</span>
      </a>
      <nav class="header__nav">
        <a href="#hero">Главная</a>
        <a href="#about">О нас</a>
        <a href="#services">Услуги</a>
        <a href="#pricing">Цены</a>
        <a href="#portfolio">Портфолио</a>
        <a href="#contacts">Контакты</a>
      </nav>
      <a :href="whatsappUrl" target="_blank" rel="noopener" class="btn btn--accent header__cta">Написать нам</a>
      <button class="header__burger" @click="menuOpen = !menuOpen" aria-label="Меню">
        <span /><span /><span />
      </button>
    </div>
    <div class="header__mobile-nav" :class="{ open: menuOpen }" @click="menuOpen = false">
      <a href="#hero">Главная</a>
      <a href="#about">О нас</a>
      <a href="#services">Услуги</a>
      <a href="#pricing">Цены</a>
      <a href="#portfolio">Портфолио</a>
      <a href="#contacts">Контакты</a>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps({ settings: Object })
const scrolled = ref(false)
const menuOpen = ref(false)

const whatsappUrl = computed(() => {
  const phone = props.settings?.whatsapp_phone || '79062003365'
  return `https://wa.clck.bar/${phone}`
})

function onScroll() { scrolled.value = window.scrollY > 60 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(8px);
  transition: box-shadow 0.3s;
}
.header.scrolled { box-shadow: 0 2px 16px rgba(0,0,0,0.1); }
.header__inner {
  display: flex; align-items: center; gap: 24px;
  height: 68px;
}
.header__logo { text-decoration: none; font-family: var(--font-head); font-weight: 800; font-size: 1.1rem; letter-spacing: 0.08em; }
.logo-festival { color: var(--dark); }
.logo-color { color: var(--accent); }
.header__nav { display: flex; gap: 24px; margin: 0 auto; }
.header__nav a { text-decoration: none; color: var(--text); font-size: 0.9rem; font-weight: 500; transition: color 0.2s; }
.header__nav a:hover { color: var(--accent); }
.header__cta { padding: 10px 22px; font-size: 0.85rem; }
.header__burger { display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; padding: 4px; }
.header__burger span { display: block; width: 24px; height: 2px; background: var(--dark); border-radius: 2px; }
.header__mobile-nav { display: none; flex-direction: column; background: #fff; padding: 16px 20px; border-top: 1px solid var(--border); }
.header__mobile-nav a { padding: 12px 0; text-decoration: none; color: var(--text); font-weight: 500; border-bottom: 1px solid var(--border); }
.header__mobile-nav.open { display: flex; }
@media (max-width: 768px) {
  .header__nav, .header__cta { display: none; }
  .header__burger { display: flex; margin-left: auto; }
}
</style>
