<template>
  <section id="contacts" class="section contacts-section">
    <div class="container">
      <h2 class="section-title">КОНТАКТЫ</h2>
      <div class="contacts__info reveal">
        <div class="contacts__col" v-if="settings.address">
          <div class="contacts__icon">
            <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
          </div>
          <div class="contacts__col-body">
            <span class="contacts__label">Адрес:</span>
            <span class="contacts__val">{{ settings.address }}</span>
          </div>
        </div>
        <div class="contacts__col" v-if="settings.phone || settings.email">
          <div class="contacts__icon">
            <svg viewBox="0 0 24 24"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>
          </div>
          <div class="contacts__col-body">
            <span class="contacts__label">Связь с нами:</span>
            <a v-if="settings.phone" :href="`tel:${settings.phone}`" class="contacts__val contacts__val--link">{{ settings.phone }}</a>
            <a v-if="settings.email" :href="`mailto:${settings.email}`" class="contacts__val contacts__val--link">{{ settings.email }}</a>
          </div>
        </div>
        <div class="contacts__col contacts__col--cooperation">
          <div class="contacts__icon">
            <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
          </div>
          <div class="contacts__col-body">
            <span class="contacts__label">Сотрудничество:</span>
            <a href="mailto:festivalcolor@mail.ru?subject=Сотрудничество" class="contacts__val contacts__val--link">festivalcolor@mail.ru</a>
            <span class="contacts__val contacts__hint">Тема письма: «Сотрудничество»</span>
          </div>
        </div>
      </div>
      <div class="contacts__wa-row reveal">
        <div class="contacts__socials">
          <a v-if="settings.vk_url" :href="settings.vk_url" target="_blank" rel="noopener" class="social-link social-link--vk">ВКонтакте</a>
          <a v-if="settings.instagram_url" :href="settings.instagram_url" target="_blank" rel="noopener" class="social-link social-link--ig">Instagram</a>
        </div>
        <a :href="whatsappUrl" target="_blank" rel="noopener" class="btn btn--accent">
          Написать в WhatsApp
        </a>
      </div>
    </div>
    <div class="contacts__map" v-if="mapSrc">
      <iframe
        :src="mapSrc"
        width="100%" height="420"
        frameborder="0"
        allowfullscreen
        loading="lazy"
        style="border:0; display:block;"
      />
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
const mapSrc = computed(() => props.settings?.google_map_src || props.settings?.yandex_map_src || null)
</script>

<style scoped>
.contacts-section { padding-bottom: 0; }
.contacts__info { display: flex; justify-content: center; gap: 60px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 32px; }
.contacts__col { display: flex; align-items: flex-start; gap: 14px; min-width: 220px; }
.contacts__icon { width: 40px; height: 40px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.contacts__icon svg { width: 20px; height: 20px; fill: #fff; }
.contacts__col-body { display: flex; flex-direction: column; gap: 4px; }
.contacts__label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-light); }
.contacts__val { font-size: 0.95rem; color: var(--dark); line-height: 1.4; }
.contacts__val--link { color: var(--accent); text-decoration: none; font-weight: 500; }
.contacts__val--link:hover { text-decoration: underline; }
.contacts__hint { font-size: 0.8rem; color: var(--text-light); font-style: italic; }
.contacts__wa-row { display: flex; align-items: center; gap: 20px; justify-content: center; flex-wrap: wrap; margin-bottom: 40px; }
.contacts__socials { display: flex; gap: 12px; }
.social-link { padding: 8px 18px; border-radius: 6px; text-decoration: none; font-size: 0.85rem; font-weight: 600; }
.social-link--vk { background: #0077ff; color: #fff; }
.social-link--ig { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color: #fff; }
.contacts__map { width: 100%; }
.contacts__map iframe {
  width: 100%; height: 420px; display: block;
  filter: grayscale(100%) contrast(1.1);
  -webkit-filter: grayscale(100%) contrast(1.1);
}
@media (max-width: 768px) {
  .contacts__info { flex-direction: column; align-items: center; }
  .contacts__col { min-width: auto; }
}
</style>
