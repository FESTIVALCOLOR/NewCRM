<template>
  <div>
    <NavHeader :settings="site.settings" :section-keys="homeSectionKeys" />
    <main>
      <router-view />
    </main>
    <FooterSection :settings="site.settings" />
  </div>
</template>

<script setup>
import { onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavHeader      from './sections/NavHeader.vue'
import FooterSection   from './sections/FooterSection.vue'
import { site, homeSectionKeys, loadSite } from './store.js'
import { rememberHomeTitle, setPageTitle } from './router.js'
import { scheduleReveal } from './reveal.js'
import { watchDecor } from './decor.js'

const route = useRoute()
const router = useRouter()

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

