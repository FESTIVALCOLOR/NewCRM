<template>
  <section class="tab-body">
    <div class="card-info">
      Заявки из окна «Заказать» на сайте. О каждой новой заявке сразу приходит уведомление в CRM (и в Telegram)
      всем, у кого есть доступ к странице «Заявки» в CRM — по умолчанию Руководителю студии, Старшему менеджеру и Менеджеру.
      Те же заявки видны и обрабатываются в CRM. Порядок: новая → «Обработать» (опишите результат, заявка уходит в «Обработанные»:
      ждём клиента, перезвон…) → «Закрыть» с итогом — положительным или отрицательным.
      Таймер у новых заявок — время на принятие в рабочих часах (будни 10:00–19:00): 12 ч, затем 3 напоминания каждые 3 ч
      и 6 напоминаний каждый час; после этого заявка просрочена.
    </div>

    <div class="card">
      <div class="leads-filter">
        <button v-for="f in FILTERS" :key="f.value" :class="['btn-sm', { 'btn-active': filter === f.value }]" @click="setFilter(f.value)">
          {{ f.label }}<span v-if="f.count && counts[f.value]" :class="['leads-count', `leads-count--${f.value}`]">{{ counts[f.value] }}</span>
        </button>
        <button class="btn-sm" :disabled="loading" @click="load()">Обновить</button>
      </div>

      <p v-if="loading && !leads.length" class="hint">Загрузка…</p>

      <!-- Два столбца: индивидуальный дизайн (тарифы) и готовый дизайн -->
      <div v-else class="leads-cols">
        <div v-for="col in columns" :key="col.key" class="leads-col">
          <div class="leads-col__title">{{ col.title }} <span class="leads-col__count">{{ col.items.length }}</span></div>
          <p v-if="!col.items.length" class="hint">Заявок нет.</p>

          <div v-for="item in col.items" :key="item.id" :class="['lead-row', rowClass(item)]">
            <div class="lead-row__main">
              <div class="lead-row__head">
                <strong>{{ item.name }}</strong>
                <a :href="`tel:${item.phone.replace(/[^\d+]/g, '')}`">{{ item.phone }}</a>
                <span class="lead-row__method">{{ METHODS[item.contact_method] || 'звонок' }}</span>
              </div>
              <div v-for="line in contextLines(item)" :key="line" class="lead-row__ctx">{{ line }}</div>
              <div v-if="item.comment" class="lead-row__comment">{{ item.comment }}</div>
              <div v-if="item.result" class="lead-row__result">
                <div class="lead-row__result-title">
                  Результат обработки<span v-if="item.processed_by_name || item.processed_at" class="lead-row__result-who">
                    — {{ item.processed_by_name || 'сотрудник' }}<template v-if="item.processed_at">, {{ fmt(item.processed_at) }}</template></span>
                </div>
                {{ item.result }}
                <!-- Дальнейшие действия по заявке в работе (журнал) -->
                <div v-for="(act, idx) in item.actions || []" :key="act.id" class="lead-row__action">
                  <div class="lead-row__result-title">
                    Действие {{ idx + 2 }}<span class="lead-row__result-who">
                      — {{ act.employee_name || 'сотрудник' }}<template v-if="act.created_at">, {{ fmt(act.created_at) }}</template></span>
                  </div>
                  {{ act.text }}
                </div>
              </div>
              <div v-if="item.status === 'closed'" :class="['lead-row__close', `lead-row__close--${item.outcome}`]">
                <div class="lead-row__close-title">
                  {{ item.outcome === 'negative' ? 'Закрыта: отрицательный итог' : 'Закрыта: положительный итог' }}<span v-if="item.closed_by_name || item.closed_at" class="lead-row__result-who">
                    — {{ item.closed_by_name || 'сотрудник' }}<template v-if="item.closed_at">, {{ fmt(item.closed_at) }}</template></span>
                </div>
                <template v-if="item.close_comment">{{ item.close_comment }}</template>
              </div>
              <div v-if="item.contract_number" class="lead-row__ctx">Договор № {{ item.contract_number }}</div>

              <!-- Обработка: результат -->
              <div v-if="editing.id === item.id && editing.mode === 'process'" class="lead-row__process">
                <textarea v-model="editing.text" rows="3" maxlength="2000" placeholder="Результат обработки: созвонились, назначили замер, клиент думает…" />
                <div class="lead-row__process-actions">
                  <button class="btn-sm btn-active" :disabled="!editing.text.trim()" @click="submitDone(item)">Отметить обработанной</button>
                  <button class="btn-sm" @click="editing.id = null">Отмена</button>
                </div>
              </div>
              <!-- Ещё одно действие по заявке в работе -->
              <div v-if="editing.id === item.id && editing.mode === 'action'" class="lead-row__process">
                <textarea v-model="editing.text" rows="3" maxlength="2000" placeholder="Что сделано и результат: перезвонил — клиент согласовал замер; провели замер, готовим КП…" />
                <div class="lead-row__process-actions">
                  <button class="btn-sm btn-active" :disabled="!editing.text.trim()" @click="submitAction(item)">Добавить действие</button>
                  <button class="btn-sm" @click="editing.id = null">Отмена</button>
                </div>
              </div>
              <!-- Закрытие: итог + комментарий -->
              <div v-if="editing.id === item.id && editing.mode === 'close'" class="lead-row__process">
                <div class="lead-outcome">
                  <button :class="['lead-outcome__btn', 'lead-outcome__btn--positive', { 'is-active': editing.outcome === 'positive' }]" @click="editing.outcome = 'positive'">Положительный</button>
                  <button :class="['lead-outcome__btn', 'lead-outcome__btn--negative', { 'is-active': editing.outcome === 'negative' }]" @click="editing.outcome = 'negative'">Отрицательный</button>
                </div>
                <textarea v-model="editing.text" rows="2" maxlength="2000" placeholder="Комментарий (необязательно): заключили договор, клиент отказался — дорого…" />
                <div class="lead-row__process-actions">
                  <button class="btn-sm btn-active" :disabled="!editing.outcome" @click="submitClose(item)">Закрыть заявку</button>
                  <button class="btn-sm" @click="editing.id = null">Отмена</button>
                </div>
              </div>
            </div>
            <div class="lead-row__actions">
              <!-- Таймер на принятие (рабочее время) — тот же расчёт, что и в CRM -->
              <div v-if="timer(item)" :class="['lead-timer', `lead-timer--${timer(item).phase}`, { 'lead-timer--paused': timer(item).paused }]" :title="timer(item).hint">
                <div class="lead-timer__value">{{ timer(item).text }}</div>
                <div class="lead-timer__caption">{{ timer(item).caption }}</div>
              </div>
              <!-- Дата поступления — под таймером, по центру -->
              <span class="lead-row__date">{{ fmt(item.created_at) }}</span>
              <template v-if="editing.id !== item.id">
                <button v-if="item.status === 'new'" class="btn-sm" @click="startEdit(item, 'process')">Обработать</button>
                <button v-if="item.status === 'done'" class="btn-sm" @click="startEdit(item, 'action')">Добавить действие</button>
                <button v-if="item.status === 'done'" class="btn-sm" @click="startEdit(item, 'close')">Закрыть</button>
                <button v-if="item.status === 'done'" class="btn-sm" @click="setStatus(item, 'new')">Вернуть в новые</button>
                <button v-if="item.status === 'closed'" class="btn-sm" @click="setStatus(item, 'done')">Вернуть в работу</button>
              </template>
              <button class="btn-sm btn-danger-text" @click="remove(item)">Удалить</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, onMounted, onUnmounted } from 'vue'
import * as api from './api.js'
import { leadTimerView } from './leadTimer.js'

const props = defineProps({ toast: Function })

const FILTERS = [
  { value: 'new', label: 'Новые', count: true },
  { value: 'done', label: 'Обработанные', count: true },
  { value: 'closed', label: 'Закрытые', count: false },
  { value: '', label: 'Все', count: false },
]
const METHODS = { call: 'звонок', whatsapp: 'WhatsApp', telegram: 'Telegram', max: 'MAX' }
const CONTEXT = [['design', ''], ['plan', ''], ['city', 'Город'], ['area', 'Площадь, м²'], ['price', 'Цена'], ['days', 'Срок']]

const leads = ref([])
const counts = ref({ new: 0, done: 0, closed: 0 })
const filter = ref('new')
const loading = ref(false)
const editing = reactive({ id: null, mode: '', text: '', outcome: null })

// Готовый дизайн — заявки из калькулятора готовых проектов; остальное (тарифы и пр.) — индивидуальный дизайн
const columns = computed(() => [
  { key: 'individual', title: 'Индивидуальные', items: leads.value.filter(l => l.source !== 'ready_design') },
  { key: 'ready', title: 'Готовые', items: leads.value.filter(l => l.source === 'ready_design') },
])

function rowClass(item) {
  if (item.status === 'closed') return item.outcome === 'negative' ? 'lead-row--negative' : 'lead-row--positive'
  return item.status === 'done' ? 'lead-row--done' : ''
}

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

// Таймер: тикает каждую секунду, раз в минуту (и когда интервал истёк) сверяемся с сервером
const now = ref(Date.now())
const fetchedAt = ref(Date.now())
let tickTimer = null
let syncTimer = null

function timer(item) {
  return leadTimerView(item.sla, fetchedAt.value, now.value)
}

async function loadCounts() {
  try { counts.value = { ...counts.value, ...(await api.leads.count()) } } catch { /* счётчики не критичны */ }
}

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    leads.value = await api.leads.list(filter.value)
    fetchedAt.value = Date.now()
  } catch (e) { if (!silent && e.message !== '401') props.toast('Не удалось загрузить заявки: ' + e.message, 'error') }
  finally { loading.value = false }
  loadCounts()
}

function tick() {
  now.value = Date.now()
  if (!loading.value && now.value - fetchedAt.value > 5000 && leads.value.some(item => timer(item)?.expired)) load(true)
}

function setFilter(value) {
  filter.value = value
  editing.id = null
  load()
}

function applyUpdated(item, updated) {
  if (filter.value && updated.status !== filter.value) leads.value = leads.value.filter(l => l.id !== item.id)
  else Object.assign(item, updated)
  loadCounts()
}

function startEdit(item, mode) {
  Object.assign(editing, { id: item.id, mode, text: mode === 'process' ? (item.result || '') : '', outcome: null })
}

async function submitDone(item) {
  try {
    applyUpdated(item, await api.leads.setStatus(item.id, 'done', editing.text.trim()))
    editing.id = null
    props.toast('Заявка обработана — она в «Обработанных»')
  } catch (e) { props.toast(e.message, 'error') }
}

async function submitAction(item) {
  try {
    applyUpdated(item, await api.leads.addAction(item.id, editing.text.trim()))
    editing.id = null
    props.toast('Действие добавлено')
  } catch (e) { props.toast(e.message, 'error') }
}

async function submitClose(item) {
  try {
    applyUpdated(item, await api.leads.setStatus(item.id, 'closed', '', editing.outcome, editing.text.trim()))
    editing.id = null
    props.toast('Заявка закрыта')
  } catch (e) { props.toast(e.message, 'error') }
}

async function setStatus(item, status) {
  try { applyUpdated(item, await api.leads.setStatus(item.id, status)) }
  catch (e) { props.toast(e.message, 'error') }
}

async function remove(item) {
  if (!confirm(`Удалить заявку «${item.name}, ${item.phone}»? Она исчезнет и в CRM.`)) return
  try {
    await api.leads.delete(item.id)
    leads.value = leads.value.filter(l => l.id !== item.id)
    loadCounts()
    props.toast('Заявка удалена')
  } catch (e) { props.toast(e.message, 'error') }
}

onMounted(() => {
  load()
  tickTimer = setInterval(tick, 1000)
  syncTimer = setInterval(() => load(true), 60000)
})
onUnmounted(() => {
  clearInterval(tickTimer)
  clearInterval(syncTimer)
})
</script>

<style scoped>
.leads-filter { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
.btn-active { background: #c0392b; border-color: #c0392b; color: #fff; }
.btn-active:hover { background: #a93226; }
.leads-count { display: inline-block; min-width: 18px; margin-left: 6px; padding: 0 5px; border-radius: 9px; font-size: 0.72rem; line-height: 18px; text-align: center; color: #fff; background: #c0392b; }
.leads-count--done { background: #e67e22; }
.btn-active .leads-count { background: #fff; color: #c0392b; }
/* Два столбца: индивидуальные и готовые (на узком экране — друг под другом) */
.leads-cols { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px; align-items: start; }
@media (max-width: 900px) { .leads-cols { grid-template-columns: minmax(0, 1fr); } }
.leads-col__title { font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
.leads-col__count { font-size: 0.78rem; font-weight: 500; color: #6b7280; background: #f3f4f6; border-radius: 9px; padding: 0 8px; }
.lead-row { display: flex; gap: 16px; align-items: flex-start; justify-content: space-between; padding: 14px 10px; border-top: 1px solid #eee; border-radius: 6px; }
.lead-row--done { background: #fafafa; }
/* Закрытые: светло-зелёные (положительно) и светло-красные (отрицательно) */
.lead-row--positive { background: #eaf7ee; border-top-color: #cdebd6; }
.lead-row--negative { background: #fdeeee; border-top-color: #f5d0cd; }
.lead-row__main { min-width: 0; flex: 1; }
.lead-row__head { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: baseline; margin-bottom: 4px; }
.lead-row__head a { color: #c0392b; text-decoration: none; font-weight: 500; }
.lead-row__method { font-size: 0.8rem; background: #f3f4f6; border-radius: 4px; padding: 1px 8px; }
.lead-row__date { font-size: 0.75rem; color: #6b7280; text-align: center; white-space: nowrap; }
.lead-row__ctx { font-size: 0.85rem; color: #374151; }
.lead-row__actions { display: flex; flex-direction: column; gap: 6px; align-items: stretch; }
.lead-timer { text-align: right; border-radius: 8px; padding: 4px 10px; line-height: 1.25; white-space: nowrap; cursor: default; }
.lead-timer__value { font-size: 0.95rem; font-weight: 600; font-variant-numeric: tabular-nums; }
.lead-timer__caption { font-size: 0.7rem; opacity: 0.85; }
.lead-timer--first { background: #e8f1fb; color: #1d4f91; }
.lead-timer--three { background: #fff3e0; color: #b45309; }
.lead-timer--hour { background: #fdecea; color: #c0392b; }
.lead-timer--overdue { background: #c0392b; color: #fff; }
.lead-timer--paused .lead-timer__value { opacity: 0.6; }
.btn-danger-text { color: #c0392b; }
.lead-row__result { margin-top: 6px; font-size: 0.85rem; color: #374151; white-space: pre-line; background: #f1f8f2; border-left: 3px solid #66bb6a; padding: 6px 10px; }
.lead-row__result-title { font-weight: 600; color: #2e7d32; white-space: normal; }
.lead-row__result-who { font-weight: 400; color: #6b7280; }
.lead-row__action { margin-top: 6px; padding-top: 6px; border-top: 1px dashed #a5d6a7; }
.lead-row__close { margin-top: 6px; font-size: 0.85rem; color: #374151; white-space: pre-line; padding: 6px 10px; background: rgba(255, 255, 255, 0.6); }
.lead-row__close--positive { border-left: 3px solid #27ae60; }
.lead-row__close--negative { border-left: 3px solid #c0392b; }
.lead-row__close-title { font-weight: 600; white-space: normal; }
.lead-row__process { margin-top: 8px; }
.lead-row__process textarea { width: 100%; box-sizing: border-box; font: inherit; font-size: 0.9rem; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; resize: vertical; margin-top: 6px; }
.lead-row__process-actions { display: flex; gap: 8px; margin-top: 6px; }
.lead-row__comment { margin-top: 6px; font-size: 0.85rem; color: #374151; white-space: pre-line; background: #fafafa; border-left: 3px solid #e5e7eb; padding: 6px 10px; }
.lead-outcome { display: flex; gap: 8px; }
.lead-outcome__btn { flex: 1; height: 36px; border-radius: 6px; cursor: pointer; font: inherit; font-size: 0.9rem; background: #fff; color: #374151; border: 1px solid #d1d5db; }
.lead-outcome__btn--positive.is-active { background: #eaf7ee; border-color: #27ae60; color: #1e8449; font-weight: 600; }
.lead-outcome__btn--negative.is-active { background: #fdeeee; border-color: #c0392b; color: #c0392b; font-weight: 600; }
</style>
