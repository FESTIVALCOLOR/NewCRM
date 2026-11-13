<template>
  <div>
    <NavHeader :settings="site.settings" :section-keys="homeSectionKeys" />
    <main>
      <router-view />
    </main>
    <FooterSection :settings="site.settings" />

    <!-- Плавающая кнопка: канал связи, выбранный в панели -->
    <a :href="fabUrl" :target="linkTarget(fabUrl)" rel="noopener" class="wa-fab" :style="{ background: fab.color }" :aria-label="fab.label" :title="fab.label">
      <svg viewBox="0 0 24 24"><path :d="fab.icon" /></svg>
    </a>
  </div>
</template>

<script setup>
import { computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavHeader      from './sections/NavHeader.vue'
import FooterSection   from './sections/FooterSection.vue'
import { ctaUrl, ctaChannel, linkTarget, CHANNELS } from './contact.js'
import { site, homeSectionKeys, loadSite } from './store.js'
import { rememberHomeTitle, setPageTitle } from './router.js'
import { scheduleReveal } from './reveal.js'
import { watchDecor } from './decor.js'

const route = useRoute()
const router = useRouter()
const fab = computed(() => CHANNELS[ctaChannel(site.settings)])
const fabUrl = computed(() => ctaUrl(site.settings))

// Блоки новой страницы появляются плавно так же, как блоки главной
router.afterEach(() => nextTick(() => scheduleReveal()))

onMounted(async () => {
  watchDecor(document.querySelector('main'))
  await loadSite()
  // Заголовок из настроек SEO относится к главной; у внутренних страниц он свой
  rememberHomeTitle()
  setPageTitle(route.meta.title)
  scheduleReveal()
})
</script>

<style>
.wa-fab {
  position: fixed; bottom: 28px; right: 28px; z-index: 90;
  width: 56px; height: 56px;
  background: #25D366; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 16px rgba(0,0,0,0.22);
  transition: transform 0.2s;
}
.wa-fab:hover { transform: scale(1.1); }
.wa-fab svg { width: 30px; height: 30px; fill: #fff; }
</style>
