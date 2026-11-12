<template>
  <section id="contacts" class="section">
    <div class="container contacts">
      <div class="contacts__info reveal">
        <h2 class="contacts__title">Контакты</h2>
        <div class="contacts__row">
          <span class="contacts__label">Адрес:</span>
          <span>{{ settings.address || 'г. Санкт-Петербург' }}</span>
        </div>
        <div class="contacts__row" v-if="settings.phone">
          <span class="contacts__label">Телефон:</span>
          <a :href="`tel:${settings.phone}`">{{ settings.phone }}</a>
        </div>
        <div class="contacts__row" v-if="settings.email">
          <span class="contacts__label">Email:</span>
          <a :href="`mailto:${settings.email}`">{{ settings.email }}</a>
        </div>
        <div class="contacts__socials">
          <a v-if="settings.vk_url" :href="settings.vk_url" target="_blank" rel="noopener" class="social-link social-link--vk">ВКонтакте</a>
          <a v-if="settings.instagram_url" :href="settings.instagram_url" target="_blank" rel="noopener" class="social-link social-link--ig">Instagram</a>
        </div>
        <a :href="whatsappUrl" target="_blank" rel="noopener" class="btn btn--accent contacts__wa">
          Написать в WhatsApp
        </a>
      </div>
      <div class="contacts__map reveal">
        <iframe
          v-if="settings.yandex_map_src"
          :src="settings.yandex_map_src"
          width="100%" height="400"
          frameborder="0"
          allowfullscreen
          loading="lazy"
        />
      </div>
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
</script>

<style scoped>
.contacts { display: grid; grid-template-columns: 380px 1fr; gap: 60px; align-items: start; }
.contacts__title { font-size: 1.8rem; font-weight: 700; margin-bottom: 28px; }
.contacts__row { display: flex; flex-direction: column; gap: 4px; margin-bottom: 16px; }
.contacts__label { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-light); }
.contacts__row a { color: var(--accent); text-decoration: none; font-weight: 500; }
.contacts__socials { display: flex; gap: 12px; margin: 20px 0 24px; }
.social-link { padding: 8px 18px; border-radius: 6px; text-decoration: none; font-size: 0.85rem; font-weight: 600; }
.social-link--vk { background: #0077ff; color: #fff; }
.social-link--ig { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color: #fff; }
.contacts__wa { width: 100%; text-align: center; }
.contacts__map iframe { border-radius: 12px; }
@media (max-width: 768px) { .contacts { grid-template-columns: 1fr; } }
</style>
