<template>
  <section class="tab-body">
    <div class="card-info">
      Заявки из окна «Заказать» на сайте. О каждой новой заявке сразу приходит уведомление в CRM всем Руководителям студии.
      Обработанную заявку отметьте — она уйдёт из списка новых.
    </div>

    <div class="card">
      <div class="leads-filter">
        <button v-for="f in FILTERS" :key="f.value" :class="['btn-sm', { 'btn-active': filter === f.value }]" @click="setFilter(f.value)">
          {{ f.label }}
        </button>
        <button class="btn-sm" :disabled="loading" @click="load">Обновить</button>
      </div>

      <p v-if="loading" class="hint">Загрузка…</p>
      <p v-else-if="!leads.length" class="hint">Заявок нет.</p>

      <div v-for="item in leads" :key="item.id" :class="['lead-row', { 'lead-row--done': item.status === 'done' }]">
        <div class="lead-row__main">
          <div class="lead-row__head">
            <strong>{{ item.name }}</strong>
            <a :href="`tel:${item.phone.replace(/[^\d+]/g, '')}`">{{ item.phone }}</a>
            <span class="lead-row__method">{{ METHODS[item.contact_method] || 'звонок' }}</span>
            <span class="lead-row__date">{{ fmt(item.created_at) }}</span>
          </div>
          <div v-for="line in contextLines(item)" :key="line" class="lead-row__ctx">{{ line }}</div>
          <div v-if="item.comment" class="lead-row__comment">{{ item.comment }}</div>
        </div>
        <button class="btn-sm" @click="toggle(item)">
          {{ item.status === 'done' ? 'Вернуть в новые' : 'Обработана' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from './api.js'

const props = defineProps({ toast: Function })

const FILTERS = [
  { value: 'new', label: 'Новые' },
  { value: 'done', label: 'Обработанные' },
  { value: '', label: 'Все' },
]
const METHODS = { call: 'звонок', whatsapp: 'WhatsApp', telegram: 'Telegram', max: 'MAX' }
const CONTEXT = [['design', ''], ['plan', ''], ['city', 'Город'], ['area', 'Площадь, м²'], ['price', 'Цена'], ['days', 'Срок']]

const leads = ref([])
const filter = ref('new')
const loading = ref(false)

function contextLines(item) {
  let ctx = {}
  try { ctx = JSON.parse(item.context || '{}') } catch { /* старая запись без контекста */ }
  return CONTEXT.filter(([key]) => ctx[key]).map(([key, label]) => (label ? `${label}: ${ctx[key]}` : ctx[key]))
}

function fmt(value) {
  if (!value) return ''
  // Сервер хранит время в UTC без пометки зоны
  const date = new Date(/Z|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`)
  return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  try { leads.value = await api.leads.list(filter.value) }
  catch (e) { if (e.message !== '401') props.toast('Не удалось загрузить заявки: ' + e.message, 'error') }
  finally { loading.value = false }
}

function setFilter(value) {
  filter.value = value
  load()
}

async function toggle(item) {
  try {
    const updated = await api.leads.setStatus(item.id, item.status === 'done' ? 'new' : 'done')
    if (filter.value && updated.status !== filter.value) leads.value = leads.value.filter(l => l.id !== item.id)
    else Object.assign(item, updated)
  } catch (e) { props.toast(e.message, 'error') }
}

onMounted(load)
</script>

<style scoped>
.leads-filter { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.btn-active { background: #c0392b; border-color: #c0392b; color: #fff; }
.btn-active:hover { background: #a93226; }
.lead-row { display: flex; gap: 16px; align-items: flex-start; justify-content: space-between; padding: 14px 0; border-top: 1px solid #eee; }
.lead-row--done { opacity: 0.6; }
.lead-row__main { min-width: 0; flex: 1; }
.lead-row__head { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: baseline; margin-bottom: 4px; }
.lead-row__head a { color: #c0392b; text-decoration: none; font-weight: 500; }
.lead-row__method { font-size: 0.8rem; background: #f3f4f6; border-radius: 4px; padding: 1px 8px; }
.lead-row__date { font-size: 0.8rem; color: #6b7280; }
.lead-row__ctx { font-size: 0.85rem; color: #374151; }
.lead-row__comment { margin-top: 6px; font-size: 0.85rem; color: #374151; white-space: pre-line; background: #fafafa; border-left: 3px solid #e5e7eb; padding: 6px 10px; }
</style>
