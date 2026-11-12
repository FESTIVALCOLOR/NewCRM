<template>
  <footer class="footer">
    <div class="container footer__inner">
      <span class="footer__logo">
        <span>FESTIVAL</span><span class="accent">COLOR</span>
      </span>
      <p class="footer__copy">{{ settings.copyright || `Copyright © FESTIVAL COLOR ${new Date().getFullYear()}. Все права защищены.` }}</p>
      <div class="footer__socials">
        <a v-if="settings.vk_url" :href="settings.vk_url" target="_blank" rel="noopener">ВК</a>
        <a v-if="settings.instagram_url" :href="settings.instagram_url" target="_blank" rel="noopener">IG</a>
      </div>
    </div>
  </footer>
</template>

<script setup>
defineProps({ settings: Object })
</script>

<style scoped>
.footer { background: var(--dark); color: rgba(255,255,255,0.7); padding: 32px 0; }
.footer__inner { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.footer__logo { font-family: var(--font-head); font-weight: 800; font-size: 1rem; letter-spacing: 0.08em; color: #fff; }
.accent { color: var(--accent); }
.footer__copy { font-size: 0.85rem; flex: 1; text-align: center; }
.footer__socials { display: flex; gap: 12px; }
.footer__socials a { color: rgba(255,255,255,0.6); text-decoration: none; font-size: 0.85rem; font-weight: 600; transition: color 0.2s; }
.footer__socials a:hover { color: var(--accent); }
@media (max-width: 600px) { .footer__inner { flex-direction: column; text-align: center; } .footer__copy { order: 3; } }
</style>
