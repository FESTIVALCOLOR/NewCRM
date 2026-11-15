<template>
  <Teleport to="body">
    <div v-if="lead.open" class="lead-overlay" @click.self="close">
      <div class="lead" role="dialog" aria-modal="true" :aria-label="lead.title">
        <button type="button" class="lead__close" aria-label="Закрыть" @click="close">×</button>

        <template v-if="sent">
          <h3 class="lead__title">Спасибо, заявка отправлена!</h3>
          <p class="lead__text">Мы свяжемся с вами в ближайшее рабочее время{{ methodHint }}.</p>
          <button type="button" class="btn btn--accent lead__submit" @click="close">Хорошо</button>
        </template>

        <form v-else novalidate @submit.prevent="submit">
          <h3 class="lead__title">{{ lead.title }}</h3>
          <p v-if="summary" class="lead__summary">{{ summary }}</p>

          <label class="lead__field">
            <span>Ваше имя</span>
            <input v-model.trim="form.name" maxlength="100" autocomplete="name" required />
          </label>
          <label class="lead__field">
            <span>Телефон</span>
            <input v-model.trim="form.phone" type="tel" maxlength="40" autocomplete="tel" placeholder="+7 900 000-00-00" required />
          </label>

          <div class="lead__field">
            <span>Как с вами удобнее связаться</span>
            <div class="lead__methods">
              <button v-for="m in METHODS" :key="m.value" type="button" :class="{ active: form.contact_method === m.value }" @click="form.contact_method = m.value">
                {{ m.label }}
              </button>
            </div>
          </div>

          <label class="lead__field">
            <span>Комментарий <em>(необязательно)</em></span>
            <textarea v-model="form.comment" rows="3" maxlength="1000" />
          </label>

          <!-- Поле-ловушка: скрыто от людей, боты его заполняют -->
          <input v-model="form.website" class="lead__trap" tabindex="-1" autocomplete="off" aria-hidden="true" />

          <label class="lead__consent">
            <input v-model="form.consent" type="checkbox" />
            <span>Я согласен(на) на обработку персональных данных для связи со мной по заявке</span>
          </label>

          <p v-if="error" class="lead__error">{{ error }}</p>
          <button type="submit" class="btn btn--accent lead__submit" :disabled="sending">
            {{ sending ? 'Отправляем…' : 'Отправить заявку' }}
          </button>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { reactive, ref, computed, watch } from 'vue'
import { lead, closeLead, sendLead } from '../lead.js'

const METHODS = [
  { value: 'call', label: 'Звонок' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'max', label: 'MAX' },
]
const METHOD_HINTS = { call: ' — позвоним', whatsapp: ' — напишем в WhatsApp', telegram: ' — напишем в Telegram', max: ' — напишем в MAX' }

const form = reactive({ name: '', phone: '', contact_method: 'call', comment: '', consent: false, website: '' })
const sending = ref(false)
const sent = ref(false)
const error = ref('')

const summary = computed(() => {
  const c = lead.context || {}
  return [c.design || c.plan, c.city, c.area && `${c.area} м²`, c.price, c.days].filter(Boolean).join(' · ')
})
const methodHint = computed(() => METHOD_HINTS[form.contact_method] || '')

watch(() => lead.open, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) { sent.value = false; error.value = '' }
})

function close() {
  closeLead()
}

async function submit() {
  error.value = ''
  if (!form.name) { error.value = 'Укажите, как к вам обращаться'; return }
  if (form.phone.replace(/\D/g, '').length < 10) { error.value = 'Укажите телефон полностью, например +7 900 000-00-00'; return }
  if (!form.consent) { error.value = 'Нужно согласие на обработку персональных данных'; return }
  sending.value = true
  try {
    await sendLead({ ...form })
    sent.value = true
    form.comment = ''
  } catch (e) {
    error.value = e.message
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.lead-overlay {
  position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center;
  padding: 16px; background: rgba(0, 0, 0, 0.45);
}
.lead {
  position: relative; width: 100%; max-width: 460px; max-height: calc(100vh - 32px); overflow-y: auto;
  background: #fff; border-radius: 14px; padding: 28px; color: var(--text); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}
.lead__close {
  position: absolute; top: 10px; right: 12px; width: 32px; height: 32px; border: none; background: none;
  font-size: 26px; line-height: 1; color: var(--text-light); cursor: pointer;
}
.lead__title { font-family: var(--font-head); font-size: calc(1.3rem * var(--ts, 1)); color: var(--dark); margin: 0 32px 8px 0; }
.lead__summary { font-size: calc(0.85rem * var(--ts, 1)); color: var(--text-light); margin: 0 0 16px; }
.lead__text { color: var(--text); margin: 0 0 20px; }
.lead__field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.lead__field > span { font-size: calc(0.78rem * var(--ts, 1)); text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-light); }
.lead__field em { text-transform: none; letter-spacing: 0; font-style: normal; }
.lead__field input, .lead__field textarea {
  width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 11px 14px; background: #fff; color: var(--text);
  font-family: inherit; font-size: calc(0.95rem * var(--ts, 1)); outline: none; resize: vertical;
}
.lead__field input:focus, .lead__field textarea:focus { border-color: var(--accent); }
.lead__methods { display: flex; flex-wrap: wrap; gap: 8px; }
.lead__methods button {
  flex: 1 1 auto; border: 1px solid var(--border); background: #fff; color: var(--text); border-radius: 8px; padding: 9px 12px;
  cursor: pointer; font-family: inherit; font-size: calc(0.88rem * var(--ts, 1));
}
.lead__methods button.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.lead__trap { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }
.lead__consent { display: flex; gap: 10px; align-items: flex-start; font-size: calc(0.82rem * var(--ts, 1)); color: var(--text-light); margin-bottom: 14px; cursor: pointer; }
.lead__consent input { margin-top: 3px; flex-shrink: 0; }
.lead__error { color: #d32f2f; font-size: calc(0.85rem * var(--ts, 1)); margin: 0 0 12px; }
.lead__submit { width: 100%; justify-content: center; text-align: center; }
.lead__submit:disabled { opacity: 0.7; cursor: default; }
@media (max-width: 480px) {
  .lead { padding: 22px 18px; }
}
</style>
