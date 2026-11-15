<template>
  <q-page padding class="leads-page">
    <q-pull-to-refresh @refresh="onRefresh">
      <div class="row items-center justify-between q-mb-md q-gutter-y-sm">
        <q-btn-toggle
          v-model="filter"
          no-caps
          dense
          unelevated
          toggle-color="grey-4"
          toggle-text-color="dark"
          text-color="grey-8"
          :options="FILTERS"
          @update:model-value="load"
        />
        <q-btn
          flat
          dense
          no-caps
          icon="refresh"
          label="Обновить"
          color="grey-8"
          :loading="loading"
          @click="load"
        />
      </div>

      <div class="leads-hint q-mb-md">
        Заявки из окна «Заказать» на сайте. О новой заявке приходит уведомление всем, у кого есть доступ к этой странице.
        Отмечая заявку обработанной, опишите результат — его увидят коллеги.
      </div>

      <div v-if="loading && !leads.length" class="text-center q-pa-lg">
        <q-spinner size="32px" color="grey-6" />
      </div>
      <div v-else-if="!leads.length" class="text-center text-grey-6 q-pa-lg">
        {{ filter === 'new' ? 'Новых заявок нет' : 'Заявок нет' }}
      </div>

      <div v-for="item in leads" :key="item.id" :class="['lead-card', { 'lead-card--done': item.status === 'done' }]">
        <div class="lead-card__head">
          <div class="lead-card__name">
            {{ item.name }}
          </div>
          <span :class="['lead-status', item.status === 'done' ? 'lead-status--done' : 'lead-status--new']">
            {{ item.status === 'done' ? 'Обработана' : 'Новая' }}
          </span>
        </div>
        <div class="lead-card__meta">
          <a :href="`tel:${phoneDigits(item.phone)}`" class="lead-card__phone">{{ item.phone }}</a>
          <span class="lead-chip">{{ METHODS[item.contact_method] || 'звонок' }}</span>
          <span class="lead-card__date">{{ fmt(item.created_at) }}</span>
        </div>
        <div class="lead-card__links">
          <a :href="`tel:${phoneDigits(item.phone)}`">Позвонить</a>
          <a :href="`https://wa.me/${phoneDigits(item.phone).replace('+', '')}`" target="_blank" rel="noopener">WhatsApp</a>
        </div>

        <div v-for="line in contextLines(item)" :key="line" class="lead-card__ctx">
          {{ line }}
        </div>
        <div v-if="item.comment" class="lead-card__comment">
          {{ item.comment }}
        </div>

        <div v-if="item.result" class="lead-card__result">
          <div class="lead-card__result-title">
            Результат обработки
            <span v-if="item.processed_by_name || item.processed_at" class="lead-card__result-who">
              — {{ item.processed_by_name || 'сотрудник' }}<template v-if="item.processed_at">, {{ fmt(item.processed_at) }}</template>
            </span>
          </div>
          <div class="lead-card__result-text">
            {{ item.result }}
          </div>
        </div>

        <div class="lead-card__actions">
          <q-btn
            v-if="item.status !== 'done'"
            outline
            dense
            no-caps
            color="positive"
            icon="task_alt"
            label="Обработать"
            class="lead-btn"
            @click="openProcess(item)"
          />
          <q-btn
            v-else
            outline
            dense
            no-caps
            color="grey-8"
            icon="undo"
            label="Вернуть в новые"
            class="lead-btn"
            :loading="busyId === item.id"
            @click="reopen(item)"
          />
          <q-btn
            v-if="canDelete"
            flat
            dense
            no-caps
            color="negative"
            icon="delete_outline"
            label="Удалить"
            class="lead-btn"
            :loading="busyId === `del-${item.id}`"
            @click="confirmDelete(item)"
          />
        </div>
      </div>
    </q-pull-to-refresh>

    <!-- Результат обработки -->
    <q-dialog v-model="processDialog" persistent>
      <q-card class="lead-dialog">
        <q-card-section class="lead-dialog__title">
          Результат обработки заявки
        </q-card-section>
        <q-card-section class="q-pt-none">
          <div class="text-grey-8 q-mb-sm">
            {{ processing?.name }}, {{ processing?.phone }}
          </div>
          <q-input
            v-model="resultText"
            type="textarea"
            outlined
            autogrow
            autofocus
            maxlength="2000"
            input-style="min-height: 90px"
            placeholder="Например: созвонились, договорились о замере 20.11; клиент думает, перезвонить через неделю…"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            flat
            no-caps
            label="Отмена"
            color="grey-8"
            @click="processDialog = false"
          />
          <q-btn
            outline
            no-caps
            color="positive"
            label="Отметить обработанной"
            :disable="!resultText.trim()"
            :loading="saving"
            @click="submitProcess"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { leadsApi } from 'src/services/api'
import { usePermissionsStore } from 'src/stores/permissions'

const $q = useQuasar()
const permsStore = usePermissionsStore()

const FILTERS = [
  { label: 'Новые', value: 'new' },
  { label: 'Обработанные', value: 'done' },
  { label: 'Все', value: '' },
]
const METHODS = { call: 'звонок', whatsapp: 'WhatsApp', telegram: 'Telegram', max: 'MAX' }
const CONTEXT = [['design', 'Дизайн'], ['plan', 'Тариф'], ['city', 'Город'], ['area', 'Площадь, м²'], ['price', 'Стоимость'], ['days', 'Срок']]

const leads = ref([])
const filter = ref('new')
const loading = ref(false)
const busyId = ref(null)

const processDialog = ref(false)
const processing = ref(null)
const resultText = ref('')
const saving = ref(false)

const canDelete = computed(() => permsStore.isSuperuser || permsStore.has('leads.delete'))

function phoneDigits(phone) {
  return (phone || '').replace(/[^\d+]/g, '')
}

function contextLines(item) {
  let ctx = {}
  try { ctx = JSON.parse(item.context || '{}') } catch { /* старая запись без контекста */ }
  return CONTEXT.filter(([key]) => ctx[key]).map(([key, label]) => `${label}: ${ctx[key]}`)
}

function fmt(value) {
  if (!value) return ''
  // Сервер хранит время в UTC без пометки зоны
  const date = new Date(/Z|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`)
  return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function errorText(e) {
  return e?.response?.data?.detail || e?.message || 'Ошибка'
}

async function load() {
  loading.value = true
  try {
    const { data } = await leadsApi.getList(filter.value)
    leads.value = data || []
  } catch (e) {
    $q.notify({ type: 'negative', message: `Не удалось загрузить заявки: ${errorText(e)}` })
  } finally {
    loading.value = false
  }
}

async function onRefresh(done) {
  await load()
  done()
}

// Заявка больше не подходит под фильтр — убираем из списка, иначе обновляем на месте
function applyUpdated(item, updated) {
  if (filter.value && updated.status !== filter.value) leads.value = leads.value.filter(l => l.id !== item.id)
  else Object.assign(item, updated)
  window.dispatchEvent(new CustomEvent('leads:changed'))
}

function openProcess(item) {
  processing.value = item
  resultText.value = item.result || ''
  processDialog.value = true
}

async function submitProcess() {
  const item = processing.value
  if (!item || !resultText.value.trim()) return
  saving.value = true
  try {
    const { data } = await leadsApi.setStatus(item.id, 'done', resultText.value.trim())
    applyUpdated(item, data)
    processDialog.value = false
    $q.notify({ type: 'positive', message: 'Заявка обработана' })
  } catch (e) {
    $q.notify({ type: 'negative', message: errorText(e) })
  } finally {
    saving.value = false
  }
}

async function reopen(item) {
  busyId.value = item.id
  try {
    const { data } = await leadsApi.setStatus(item.id, 'new')
    applyUpdated(item, data)
  } catch (e) {
    $q.notify({ type: 'negative', message: errorText(e) })
  } finally {
    busyId.value = null
  }
}

function confirmDelete(item) {
  $q.dialog({
    title: 'Удалить заявку?',
    message: `${item.name}, ${item.phone}. Заявка будет удалена без возможности восстановления — и в CRM, и в панели сайта.`,
    cancel: { label: 'Отмена', flat: true, noCaps: true, color: 'grey-8' },
    ok: { label: 'Удалить', flat: true, noCaps: true, color: 'negative' },
    persistent: true,
  }).onOk(async () => {
    busyId.value = `del-${item.id}`
    try {
      await leadsApi.remove(item.id)
      leads.value = leads.value.filter(l => l.id !== item.id)
      window.dispatchEvent(new CustomEvent('leads:changed'))
      $q.notify({ type: 'positive', message: 'Заявка удалена' })
    } catch (e) {
      $q.notify({ type: 'negative', message: errorText(e) })
    } finally {
      busyId.value = null
    }
  })
}

onMounted(load)
</script>

<style scoped>
.leads-page { max-width: 900px; margin: 0 auto; }
.leads-hint { font-size: 12px; color: #6b7280; background: #f9fafb; border: 1px solid #eee; border-radius: 8px; padding: 8px 12px; }
.lead-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px; }
.lead-card--done { background: #fcfcfc; }
.lead-card__head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.lead-card__name { font-size: 15px; font-weight: 600; color: #222; overflow-wrap: anywhere; }
.lead-status { font-size: 11px; border-radius: 10px; padding: 2px 10px; white-space: nowrap; }
.lead-status--new { background: #fdecea; color: #c0392b; }
.lead-status--done { background: #e8f5e9; color: #2e7d32; }
.lead-card__meta { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; margin-top: 4px; }
.lead-card__phone { color: #c0392b; font-weight: 500; text-decoration: none; }
.lead-chip { font-size: 11px; background: #f3f4f6; border-radius: 4px; padding: 1px 8px; color: #374151; }
.lead-card__date { font-size: 12px; color: #6b7280; }
.lead-card__links { display: flex; gap: 14px; margin: 4px 0 6px; font-size: 12px; }
.lead-card__links a { color: #2563eb; text-decoration: none; }
.lead-card__ctx { font-size: 13px; color: #374151; }
.lead-card__comment { margin-top: 6px; font-size: 13px; color: #374151; white-space: pre-line; background: #fafafa; border-left: 3px solid #e5e7eb; padding: 6px 10px; }
.lead-card__result { margin-top: 8px; background: #f1f8f2; border-left: 3px solid #66bb6a; padding: 6px 10px; border-radius: 0 6px 6px 0; }
.lead-card__result-title { font-size: 12px; font-weight: 600; color: #2e7d32; }
.lead-card__result-who { font-weight: 400; color: #6b7280; }
.lead-card__result-text { font-size: 13px; color: #374151; white-space: pre-line; overflow-wrap: anywhere; }
.lead-card__actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.lead-btn { font-size: 12px; padding: 0 10px; }
.lead-dialog { width: 480px; max-width: 92vw; }
.lead-dialog__title { font-size: 16px; font-weight: 600; }
</style>
