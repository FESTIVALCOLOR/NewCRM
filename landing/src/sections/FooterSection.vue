<template>
  <footer class="footer">
    <div class="container footer__inner">
      <router-link :to="{ path: '/' }" class="footer__logo">
        <span class="logo-festival">FESTIVAL</span><span class="logo-color">COLOR</span>
      </router-link>
      <p class="footer__copy">{{ settings.copyright || `Copyright © FESTIVAL COLOR ${new Date().getFullYear()}. Все права защищены.` }}</p>
      <div class="footer__socials">
        <a v-if="settings.vk_url" :href="settings.vk_url" target="_blank" rel="noopener" class="footer__social-btn" aria-label="ВКонтакте">
          <svg viewBox="0 0 24 24"><path d="M15.07 2H8.93C3.33 2 2 3.33 2 8.93v6.14C2 20.67 3.33 22 8.93 22h6.14C20.67 22 22 20.67 22 15.07V8.93C22 3.33 20.67 2 15.07 2zm3.08 13.35h-1.57c-.59 0-.77-.47-1.83-1.54-.92-.9-1.33-.9-1.33 0v1.42c0 .11-.09.12-.38.12-1.47 0-3.1-.89-4.25-2.55-1.72-2.42-2.19-4.23-2.19-4.6 0-.19.07-.37.26-.37h1.57c.19 0 .26.09.33.3.36 1.03.96 1.93 1.21 1.93.09 0 .14-.04.14-.26V8.63c-.03-.73-.43-.79-.43-.79 0-.19.06-.27.19-.27h2.47c.16 0 .22.09.22.28v2.68c0 .16.07.22.12.22.09 0 .18-.06.37-.25 1.14-1.28 1.95-3.24 1.95-3.24.05-.11.16-.22.35-.22h1.57c.47 0 .57.24.47.56-.8 1.86-1.74 2.9-1.74 2.9-.09.14-.12.21 0 .37.09.11.38.37.57.59.56.59.99 1.09 1.1 1.44.14.47-.09.69-.38.69z"/></svg>
        </a>
        <a v-if="settings.instagram_url" :href="settings.instagram_url" target="_blank" rel="noopener" class="footer__social-btn footer__social-btn--ig" aria-label="Instagram">
          <svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
        </a>
      </div>
    </div>
  </footer>
</template>

<script setup>
defineProps({ settings: Object })
</script>

<style scoped>
.footer { background: var(--dark); color: rgba(255,255,255,0.7); padding: 28px 0; }
.footer__inner { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.footer__logo { text-decoration: none; font-family: var(--font-head); font-weight: 800; font-size: calc(1rem * var(--ts, 1)); letter-spacing: 0.08em; display: flex; align-items: center; }
.logo-festival { color: #fff; }
.logo-color { color: var(--accent); }
.footer__copy { font-size: calc(0.82rem * var(--ts, 1)); flex: 1; text-align: center; color: rgba(255,255,255,0.5); }
.footer__socials { display: flex; gap: 10px; }
.footer__social-btn {
  width: 36px; height: 36px; border-radius: 50%;
  background: rgba(255,255,255,0.12); display: flex; align-items: center; justify-content: center;
  transition: background 0.2s, transform 0.2s; text-decoration: none;
}
.footer__social-btn:hover { background: var(--accent); transform: translateY(-2px); }
.footer__social-btn--ig:hover { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); }
.footer__social-btn svg { width: 18px; height: 18px; fill: #fff; }
@media (max-width: 600px) { .footer__inner { flex-direction: column; text-align: center; } .footer__copy { order: 3; } }
</style>
