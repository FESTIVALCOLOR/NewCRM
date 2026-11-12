<template>
  <section id="contacts" class="section contacts-section">
    <div class="container">
      <h2 class="section-title">КОНТАКТЫ</h2>
      <div class="contacts__grid reveal">

        <!-- Левая колонка: телефон / адрес / сотрудничество -->
        <div class="contacts__left">
          <div class="contacts__item" v-if="settings.phone">
            <div class="contacts__icon">
              <svg viewBox="0 0 24 24"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>
            </div>
            <div class="contacts__item-body">
              <span class="contacts__label">Телефон:</span>
              <a :href="`tel:${settings.phone}`" class="contacts__val contacts__val--link">{{ settings.phone }}</a>
            </div>
          </div>
          <div class="contacts__item" v-if="settings.address">
            <div class="contacts__icon">
              <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
            </div>
            <div class="contacts__item-body">
              <span class="contacts__label">Адрес:</span>
              <span class="contacts__val">{{ settings.address }}</span>
            </div>
          </div>
          <div class="contacts__item">
            <div class="contacts__icon">
              <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
            </div>
            <div class="contacts__item-body">
              <span class="contacts__label">Сотрудничество:</span>
              <a :href="`mailto:${email}?subject=Сотрудничество`" class="contacts__val contacts__val--link">{{ email }}</a>
              <span class="contacts__hint">Тема письма: «Сотрудничество»</span>
            </div>
          </div>
        </div>

        <!-- Правая колонка: соцсети + WhatsApp -->
        <div class="contacts__right">
          <div class="contacts__socials">
            <a v-if="settings.vk_url" :href="settings.vk_url" target="_blank" rel="noopener" class="social-btn social-btn--vk">
              <svg viewBox="0 0 24 24"><path d="M15.07 2H8.93C3.33 2 2 3.33 2 8.93v6.14C2 20.67 3.33 22 8.93 22h6.14C20.67 22 22 20.67 22 15.07V8.93C22 3.33 20.67 2 15.07 2zm3.08 13.35h-1.57c-.59 0-.77-.47-1.83-1.54-.92-.9-1.33-.9-1.33 0v1.42c0 .11-.09.12-.38.12-1.47 0-3.1-.89-4.25-2.55-1.72-2.42-2.19-4.23-2.19-4.6 0-.19.07-.37.26-.37h1.57c.19 0 .26.09.33.3.36 1.03.96 1.93 1.21 1.93.09 0 .14-.04.14-.26V8.63c-.03-.73-.43-.79-.43-.79 0-.19.06-.27.19-.27h2.47c.16 0 .22.09.22.28v2.68c0 .16.07.22.12.22.09 0 .18-.06.37-.25 1.14-1.28 1.95-3.24 1.95-3.24.05-.11.16-.22.35-.22h1.57c.47 0 .57.24.47.56-.8 1.86-1.74 2.9-1.74 2.9-.09.14-.12.21 0 .37.09.11.38.37.57.59.56.59.99 1.09 1.1 1.44.14.47-.09.69-.38.69z"/></svg>
              ВКонтакте
            </a>
            <a v-if="settings.instagram_url" :href="settings.instagram_url" target="_blank" rel="noopener" class="social-btn social-btn--ig">
              <svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
              Instagram
            </a>
          </div>
          <a :href="whatsappUrl" target="_blank" rel="noopener" class="btn btn--accent btn--wa">
            <svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
            Написать в WhatsApp
          </a>
        </div>
      </div>
    </div>

    <div class="contacts__map" v-if="mapSrc">
      <iframe :src="mapSrc" width="100%" height="420" frameborder="0" allowfullscreen loading="lazy" style="border:0;display:block;" />
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { whatsappUrl as buildWhatsappUrl } from '../contact.js'
const props = defineProps({ settings: Object })
const whatsappUrl = computed(() => buildWhatsappUrl(props.settings))
const email = computed(() => props.settings?.email || 'festivalcolor@mail.ru')
const mapSrc = computed(() => props.settings?.google_map_src || props.settings?.yandex_map_src || null)
</script>

<style scoped>
.contacts-section { padding-bottom: 0; }
.contacts__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: start; max-width: 860px; margin: 0 auto 40px; }
.contacts__left { display: flex; flex-direction: column; gap: 24px; }
.contacts__item { display: flex; align-items: flex-start; gap: 14px; }
.contacts__icon { width: 40px; height: 40px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.contacts__icon svg { width: 20px; height: 20px; fill: #fff; }
.contacts__item-body { display: flex; flex-direction: column; gap: 3px; }
.contacts__label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-light); }
.contacts__val { font-size: 0.95rem; color: var(--dark); line-height: 1.4; }
.contacts__val--link { color: var(--accent); text-decoration: none; font-weight: 500; }
.contacts__val--link:hover { text-decoration: underline; }
.contacts__hint { font-size: 0.78rem; color: var(--text-light); font-style: italic; }
.contacts__right { display: flex; flex-direction: column; gap: 20px; justify-content: center; padding-top: 8px; }
.contacts__socials { display: flex; flex-direction: column; gap: 12px; }
.social-btn { display: inline-flex; align-items: center; gap: 10px; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-size: 0.9rem; font-weight: 600; transition: opacity 0.2s, transform 0.2s; width: 100%; }
.social-btn:hover { opacity: 0.85; transform: translateX(3px); }
.social-btn svg { width: 20px; height: 20px; flex-shrink: 0; }
.social-btn--vk { background: #0077ff; color: #fff; }
.social-btn--vk svg { fill: #fff; }
.social-btn--ig { background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888); color: #fff; }
.social-btn--ig svg { fill: #fff; }
.btn--wa { display: inline-flex; align-items: center; gap: 10px; font-size: 0.9rem; padding: 12px 20px; width: 100%; justify-content: center; }
.btn--wa svg { width: 20px; height: 20px; fill: #fff; }
.contacts__map iframe { filter: grayscale(100%) contrast(1.1); -webkit-filter: grayscale(100%) contrast(1.1); }
@media (max-width: 700px) {
  .contacts__grid { grid-template-columns: 1fr; gap: 32px; }
  .social-btn { width: auto; }
  .btn--wa { width: auto; }
}
</style>
