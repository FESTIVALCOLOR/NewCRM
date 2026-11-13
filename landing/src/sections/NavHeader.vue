<template>
  <header class="header" :class="{ scrolled }">
    <div class="container header__inner">
      <router-link :to="{ path: '/' }" class="header__logo" @click="onNav({ to: { path: '/' } })">
        <img v-if="logoSrc" :src="logoSrc" alt="FESTIVAL COLOR" class="header__logo-img" />
        <template v-else>
          <span class="logo-festival">FESTIVAL</span><span class="logo-color">COLOR</span>
        </template>
      </router-link>
      <nav class="header__nav">
        <router-link v-for="item in menu" :key="item.key" :to="item.to" :class="{ 'is-page': item.page }" @click="onNav(item)">{{ item.label }}</router-link>
      </nav>
      <a :href="contactUrl" :target="linkTarget(contactUrl)" rel="noopener" class="btn btn--accent header__cta">{{ contactLabel }}</a>
      <button class="header__burger" @click="menuOpen = !menuOpen" aria-label="Меню">
        <span /><span /><span />
      </button>
    </div>
    <div class="header__mobile-nav" :class="{ open: menuOpen }" @click="menuOpen = false">
      <router-link v-for="item in menu" :key="item.key" :to="item.to" :class="{ 'is-page': item.page }" @click="onNav(item)">{{ item.label }}</router-link>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

import { useRoute, useRouter } from 'vue-router'
import { ctaUrl, ctaLabel, linkTarget } from '../contact.js'
import { HEADER_HEIGHT } from '../router.js'

const MENU_LABELS = { hero: 'Главная', about: 'О нас', services: 'Услуги', reviews: 'Отзывы', contacts: 'Контакты' }
// Отдельные страницы сайта; в меню стоят на месте блока «Направления» главной
const PAGES = [
  { key: 'individual', label: 'Индивидуальный дизайн', to: { path: '/individual' }, page: true },
  { key: 'ready', label: 'Готовый дизайн', to: { path: '/ready' }, page: true },
]

const props = defineProps({ settings: Object, sectionKeys: { type: Array, default: () => [] } })
const scrolled = ref(false)
const menuOpen = ref(false)

// Пункты меню идут в том же порядке, что и секции на странице; скрытые секции в меню не попадают
const route = useRoute()
const router = useRouter()
const menu = computed(() => {
  const items = []
  let pagesAt = -1
  for (const key of props.sectionKeys) {
    if (key === 'directions') pagesAt = items.length
    else if (MENU_LABELS[key]) items.push({ key, label: MENU_LABELS[key], to: key === 'hero' ? { path: '/' } : { path: '/', hash: `#${key}` } })
  }
  // Если блок направлений на главной скрыт, страницы всё равно остаются в меню — после «Услуг»
  if (pagesAt < 0) pagesAt = items.findIndex(item => item.key === 'services') + 1 || items.length
  items.splice(pagesAt, 0, ...PAGES)
  return items
})

// Повторный клик по пункту, который уже открыт, маршрутизатор пропускает — прокручиваем сами
function onNav(item) {
  if (router.resolve(item.to).fullPath !== route.fullPath) return
  const el = item.to.hash ? document.querySelector(item.to.hash) : null
  window.scrollTo({ top: el ? el.getBoundingClientRect().top + window.scrollY - HEADER_HEIGHT + 1 : 0, behavior: 'smooth' })
}
const contactUrl = computed(() => ctaUrl(props.settings))
const contactLabel = computed(() => ctaLabel(props.settings))
const logoSrc = computed(() => {
  if (props.settings?.logo_url) return props.settings.logo_url
  return import.meta.env.BASE_URL + 'media/logo/logo.png'
})

function onScroll() { scrolled.value = window.scrollY > 60 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: #fff;
  transition: box-shadow 0.3s;
}
.header.scrolled { box-shadow: 0 2px 16px rgba(0,0,0,0.1); }
.header__inner {
  display: flex; align-items: center; gap: 24px;
  height: 68px;
}
.header__logo { text-decoration: none; font-family: var(--font-head); font-weight: 800; font-size: calc(1.1rem * var(--ts, 1)); letter-spacing: 0.08em; display: flex; align-items: center; }
.header__logo-img { height: 40px; width: auto; object-fit: contain; }
.logo-festival { color: var(--dark); }
.logo-color { color: var(--accent); }
.header__nav { display: flex; gap: 22px; margin: 0 auto; white-space: nowrap; }
.header__nav a { text-decoration: none; color: var(--text); font-size: calc(0.9rem * var(--ts, 1)); font-weight: 500; transition: color 0.2s; }
.header__nav a:hover, .header__nav a.is-page.router-link-active { color: var(--accent); }
.header__cta { padding: 10px 22px; font-size: calc(0.85rem * var(--ts, 1)); }
.header__burger { display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; padding: 4px; }
.header__burger span { display: block; width: 24px; height: 2px; background: var(--dark); border-radius: 2px; }
.header__mobile-nav { display: none; flex-direction: column; background: #fff; padding: 16px 20px; border-top: 1px solid var(--border); }
.header__mobile-nav a { padding: 12px 0; text-decoration: none; color: var(--text); font-weight: 500; border-bottom: 1px solid var(--border); }
.header__mobile-nav a.is-page.router-link-active { color: var(--accent); }
.header__mobile-nav.open { display: flex; }
/* Пунктов в меню семь, поэтому на планшетах оно сворачивается раньше */
@media (max-width: 1100px) {
  .header__nav, .header__cta { display: none; }
  .header__burger { display: flex; margin-left: auto; }
}
</style>
