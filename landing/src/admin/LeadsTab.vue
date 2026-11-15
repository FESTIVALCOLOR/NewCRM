<template>
  <section class="tab-body">
    <div class="card-info">
      Заявки из окна «Заказать» на сайте. О каждой новой заявке сразу приходит уведомление в CRM (и в Telegram)
      всем, у кого есть доступ к странице «Заявки» в CRM — по умолчанию Руководителю студии, Старшему менеджеру и Менеджеру.
      Те же заявки видны и обрабатываются в CRM. Отмечая заявку обработанной, опишите результат.
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
          <div v-if="item.result" class="lead-row__result">
            <div class="lead-row__result-title">
              Результат обработки<span v-if="item.processed_by_name || item.processed_at" class="lead-row__result-who">
                — {{ item.processed_by_name || 'сотрудник' }}<template v-if="item.processed_at">, {{ fmt(item.processed_at) }}</template></span>
            </div>
            {{ item.result }}
          </div>
          <div v-if="processingId === item.id" class="lead-row__process">
            <textarea v-model="resultText" rows="3" maxlength="2000" placeholder="Результат обработки: созвонились, назначили замер, клиент думает…" />
            <div class="lead-row__process-actions">
              <button class="btn-sm btn-active" :disabled="!resultText.trim()" @click="submitDone(item)">Отметить обработанной</button>
              <button class="btn-sm" @click="processingId = null">Отмена</button>
            </div>
          </div>
        </div>
        <div class="lead-row__actions">
          <button v-if="item.status === 'done'" class="btn-sm" @click="reopen(item)">Вернуть в новые</button>
          <button v-else-if="processingId !== item.id" class="btn-sm" @click="startProcess(item)">Обработать</button>
          <button class="btn-sm btn-danger-text" @click="remove(item)">Удалить</button>
        </div>
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
const processingId = ref(null)
const resultText = ref('')

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

function applyUpdated(item, updated) {
  if (filter.value && updated.status !== filter.value) leads.value = leads.value.filter(l => l.id !== item.id)
  else Object.assign(item, updated)
}

function startProcess(item) {
  processingId.value = item.id
  resultText.value = item.result || ''
}

async function submitDone(item) {
  try {
    applyUpdated(item, await api.leads.setStatus(item.id, 'done', resultText.value.trim()))
    processingId.value = null
    props.toast('Заявка обработана')
  } catch (e) { props.toast(e.message, 'error') }
}

async function reopen(item) {
  try { applyUpdated(item, await api.leads.setStatus(item.id, 'new')) }
  catch (e) { props.toast(e.message, 'error') }
}

async function remove(item) {
  if (!confirm(`Удалить заявку «${item.name}, ${item.phone}»? Она исчезнет и в CRM.`)) return
  try {
    await api.leads.delete(item.id)
    leads.value = leads.value.filter(l => l.id !== item.id)
    props.toast('Заявка удалена')
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
.lead-row__actions { display: flex; flex-direction: column; gap: 6px; align-items: stretch; }
.btn-danger-text { color: #c0392b; }
.lead-row__result { margin-top: 6px; font-size: 0.85rem; color: #374151; white-space: pre-line; background: #f1f8f2; border-left: 3px solid #66bb6a; padding: 6px 10px; }
.lead-row__result-title { font-weight: 600; color: #2e7d32; white-space: normal; }
.lead-row__result-who { font-weight: 400; color: #6b7280; }
.lead-row__process { margin-top: 8px; }
.lead-row__process textarea { width: 100%; box-sizing: border-box; font: inherit; font-size: 0.9rem; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; resize: vertical; }
.lead-row__process-actions { display: flex; gap: 8px; margin-top: 6px; }
.lead-row__comment { margin-top: 6px; font-size: 0.85rem; color: #374151; white-space: pre-line; background: #fafafa; border-left: 3px solid #e5e7eb; padding: 6px 10px; }
</style>
