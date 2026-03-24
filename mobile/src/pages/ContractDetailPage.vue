<template>
  <q-page padding>
    <template v-if="contract">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-center justify-between q-mb-xs">
            <div class="text-subtitle1 text-weight-bold" style="color: #333">{{ contract.contract_number }}</div>
            <div class="text-right">
              <q-badge :color="statusColor(contract.status)" :label="contract.status" />
              <div v-if="contract.agent_type" class="q-mt-xs">
                <span class="agent-badge" :style="{ background: agentColor }">{{ contract.agent_type }}</span>
              </div>
            </div>
          </div>
          <div class="text-body2 q-mb-xs" style="color: #333">{{ contract.address }}</div>
          <div class="row q-gutter-sm text-caption" style="color: #888">
            <span>{{ contract.project_type }}</span>
            <span v-if="contract.area">{{ contract.area }} м²</span>
            <span v-if="contract.city">{{ contract.city }}</span>
            <span v-if="contract.floors">{{ contract.floors }} эт.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Вкладки -->
      <q-tabs v-model="tab" dense active-color="dark" indicator-color="accent" no-caps class="q-mb-md" style="color: #666" align="left">
        <q-tab name="info" label="Информация" />
        <q-tab name="finance" label="Финансы" />
        <q-tab name="timeline" label="Сроки" />
        <q-tab name="files" label="Файлы" />
      </q-tabs>

      <q-tab-panels v-model="tab" animated class="bg-transparent">
        <!-- Информация -->
        <q-tab-panel name="info" class="q-pa-none">
          <q-card class="is-card q-mb-md">
            <q-list dense>
              <q-item v-if="contract.contract_date">
                <q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Дата договора</q-item-label>
                  <q-item-label>{{ fmtDate(contract.contract_date) }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="contract.contract_period">
                <q-item-section avatar><q-icon name="schedule" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Срок выполнения</q-item-label>
                  <q-item-label>{{ contract.contract_period }} дней</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="contract.agent_type">
                <q-item-section avatar><q-icon name="business" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Тип агента</q-item-label>
                  <q-item-label>{{ contract.agent_type }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="contract.project_subtype">
                <q-item-section avatar><q-icon name="category" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Подтип проекта</q-item-label>
                  <q-item-label>{{ contract.project_subtype }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="contract.status_changed_date">
                <q-item-section avatar><q-icon name="update" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Дата смены статуса</q-item-label>
                  <q-item-label>{{ fmtDate(contract.status_changed_date) }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="contract.comments">
                <q-item-section avatar><q-icon name="comment" color="grey-7" /></q-item-section>
                <q-item-section>
                  <q-item-label caption>Комментарий</q-item-label>
                  <q-item-label>{{ contract.comments }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Кнопки редактирования и удаления -->
          <div class="row q-col-gutter-sm q-mb-md">
            <div class="col">
              <q-btn color="accent" text-color="dark" label="Редактировать" icon="edit" no-caps unelevated class="full-width" style="border-radius: 4px" @click="showEdit = true" />
            </div>
            <div class="col-auto">
              <q-btn outline color="negative" icon="delete" no-caps @click="deleteContract" style="border-radius: 4px" />
            </div>
          </div>
          <contract-form-dialog v-model="showEdit" :contract="contract" @saved="reload" />
        </q-tab-panel>

        <!-- Финансы -->
        <q-tab-panel name="finance" class="q-pa-none">
          <q-card class="is-card q-mb-md">
            <q-card-section>
              <div class="row q-col-gutter-sm">
                <div class="col-6" v-for="f in financeCards" :key="f.label">
                  <div :style="{ borderLeft: `3px solid ${f.color}`, paddingLeft: '8px' }">
                    <div class="text-caption" style="color: #888">{{ f.label }}</div>
                    <div class="text-weight-bold">{{ f.value }}</div>
                  </div>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <!-- Платежи по договору -->
          <q-card class="is-card" v-if="payments.length > 0">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold">Платежи ({{ payments.length }})</div>
            </q-card-section>
            <q-list dense separator>
              <q-item v-for="p in payments" :key="p.id">
                <q-item-section>
                  <q-item-label>{{ p.employee_name || '—' }}</q-item-label>
                  <q-item-label caption>{{ p.stage_name || p.payment_subtype || '' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <div class="text-weight-bold" :class="p.is_paid ? 'text-positive' : ''" style="color: #333">
                    {{ fmtMoney(p.final_amount || p.amount) }}
                  </div>
                  <q-badge :color="p.is_paid ? 'positive' : 'warning'" :label="p.is_paid ? 'Оплачено' : 'Ожидает'" dense />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </q-tab-panel>

        <!-- Таблица сроков -->
        <q-tab-panel name="timeline" class="q-pa-none">
          <q-card class="is-card">
            <q-list dense separator v-if="timeline.length > 0">
              <q-item v-for="entry in timeline" :key="entry.id" :class="{ 'bg-green-1': entry.actual_date }">
                <q-item-section avatar>
                  <q-icon
                    :name="entry.actual_date ? 'check_circle' : 'radio_button_unchecked'"
                    :color="entry.actual_date ? 'positive' : 'grey-5'"
                    size="18px"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label style="font-size: 12px" :class="{ 'text-weight-bold': !entry.stage_code?.includes('.') }">
                    {{ entry.stage_name }}
                  </q-item-label>
                  <q-item-label caption>
                    <span v-if="entry.norm_days">Норма: {{ entry.custom_norm_days || entry.norm_days }} дн.</span>
                    <span v-if="entry.actual_days"> | Факт: {{ entry.actual_days }} дн.</span>
                    <span v-if="entry.executor_role && entry.executor_role !== 'header'"> | {{ entry.executor_role }}</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side v-if="entry.actual_date">
                  <div class="text-caption text-positive">{{ fmtDateShort(entry.actual_date) }}</div>
                </q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999">
              Таблица сроков не инициализирована
            </q-card-section>
          </q-card>
        </q-tab-panel>

        <!-- Файлы -->
        <q-tab-panel name="files" class="q-pa-none">
          <q-card class="is-card q-mb-md">
            <q-list dense v-if="files.length > 0">
              <q-item v-for="file in files" :key="file.id" clickable @click="openFile(file)">
                <q-item-section avatar>
                  <q-icon :name="fileIcon(file.file_type)" :color="fileColor(file.file_type)" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>{{ file.file_name }}</q-item-label>
                  <q-item-label caption>{{ stageLabel(file.stage) }}</q-item-label>
                </q-item-section>
                <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
              </q-item>
            </q-list>
            <q-card-section v-else class="text-center" style="color: #999">Нет файлов</q-card-section>
          </q-card>

          <!-- Загрузка файлов (все типы как в десктопе) -->
          <div class="text-subtitle2 text-weight-bold q-mb-sm" style="color: #333">Загрузить файл</div>
          <div class="row q-col-gutter-xs">
            <div class="col-6" v-for="btn in fileUploadButtons" :key="btn.stage">
              <q-btn outline color="grey-7" :icon="btn.icon" :label="btn.label" no-caps class="full-width q-mb-xs" dense style="font-size: 10px; border-radius: 4px" @click="uploadFor(btn.stage)" />
            </div>
          </div>
          <input ref="fileInput" type="file" style="display: none" @change="handleFileUpload" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.dwg" />
        </q-tab-panel>
      </q-tab-panels>
    </template>

    <div v-else-if="!loading" class="text-center q-pa-xl" style="color: #999">
      <q-icon name="description" size="48px" class="q-mb-sm" />
      <div>Договор не найден</div>
    </div>
    <div v-else class="text-center q-pa-xl"><q-spinner size="40px" color="accent" /></div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { contractsApi, filesApi, paymentsApi, crmApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'

const route = useRoute()
const $q = useQuasar()
const refs = useReferencesStore()
const contract = ref(null)
const files = ref([])
const payments = ref([])
const timeline = ref([])
const loading = ref(true)
const showEdit = ref(false)
const tab = ref('info')
const fileInput = ref(null)
const uploadStage = ref('')

const agentColor = computed(() => {
  const agent = refs.agentByName(contract.value?.agent_type)
  return agent?.color || '#95A5A6'
})

const financeCards = computed(() => {
  const c = contract.value || {}
  return [
    { label: 'Общая сумма', value: fmtMoney(c.total_amount), color: '#ffd93c' },
    { label: 'Аванс', value: fmtMoney(c.advance_payment), color: '#27AE60' },
    { label: 'Доп. оплата', value: fmtMoney(c.additional_payment), color: '#85C1E9' },
    { label: 'Третий платёж', value: fmtMoney(c.third_payment), color: '#F39C12' }
  ]
})

const fileUploadButtons = [
  { stage: 'tech_task', label: 'Тех. задание', icon: 'description' },
  { stage: 'measurement', label: 'Замер', icon: 'straighten' },
  { stage: 'stage1', label: 'Планировка', icon: 'architecture' },
  { stage: 'stage2_concept', label: 'Концепция', icon: 'palette' },
  { stage: 'stage3', label: 'Чертежи', icon: 'draw' },
  { stage: 'documents', label: 'Договор/Допсогл.', icon: 'gavel' },
  { stage: 'questionnaire', label: 'Опрос', icon: 'quiz' },
  { stage: 'references', label: 'Референсы', icon: 'collections' },
  { stage: 'photo_documentation', label: 'Фотофиксация', icon: 'photo_camera' },
  { stage: 'supervision', label: 'Акты', icon: 'verified' }
]

const STAGE_LABELS = {
  stage1: 'Планировочное решение', stage2_concept: 'Концепция',
  stage2_3d: '3D визуализация', stage3: 'Чертёжный проект',
  references: 'Референсы', photo_documentation: 'Фотофиксация',
  tech_task: 'Техническое задание', documents: 'Документы',
  measurement: 'Замер', supervision: 'Авторский надзор'
}

function stageLabel(s) { return STAGE_LABELS[s] || s || '' }
function statusColor(s) { if (!s) return 'grey'; if (s === 'В работе') return 'orange'; if (s.includes('СДАН')) return 'positive'; if (s.includes('РАСТОРГНУТ')) return 'negative'; if (s.includes('НАДЗОР')) return 'purple'; return 'blue' }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }
function fileIcon(t) { return { image: 'image', pdf: 'picture_as_pdf', excel: 'table_chart', word: 'article', cad: 'architecture' }[t] || 'insert_drive_file' }
function fileColor(t) { return { image: 'green', pdf: 'red', excel: 'teal', word: 'blue', cad: 'purple' }[t] || 'grey-7' }
function openFile(f) { if (f.public_link) window.open(f.public_link, '_blank') }

function uploadFor(stage) {
  uploadStage.value = stage
  fileInput.value?.click()
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !contract.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const yandexPath = `/CRM/Проекты/${contract.value.contract_number}/${uploadStage.value}/${file.name}`
    await filesApi.upload(file, yandexPath)
    $q.notify({ type: 'positive', message: 'Файл загружен' })
    // Перезагрузить файлы
    const { data } = await filesApi.getContractFiles(contract.value.id)
    files.value = data || []
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки' })
  } finally {
    $q.loading.hide()
    event.target.value = ''
  }
}

async function deleteContract() {
  $q.dialog({
    title: 'Удалить договор?',
    message: contract.value?.contract_number || '',
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await contractsApi.delete(contract.value.id)
      $q.notify({ type: 'positive', message: 'Договор удалён' })
      window.history.back()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка удаления' })
    }
  })
}

async function reload() {
  const id = route.params.id
  const { data } = await contractsApi.getById(id)
  contract.value = data
}

onMounted(async () => {
  const id = route.params.id
  try {
    const [cRes, fRes, pRes, tRes] = await Promise.allSettled([
      contractsApi.getById(id),
      filesApi.getContractFiles(id),
      paymentsApi.getList({ contract_id: id }),
      crmApi.getTimeline(id)
    ])
    if (cRes.status === 'fulfilled') contract.value = cRes.value.data
    if (fRes.status === 'fulfilled') files.value = fRes.value.data || []
    if (pRes.status === 'fulfilled') payments.value = pRes.value.data || []
    if (tRes.status === 'fulfilled') timeline.value = tRes.value.data || []
  } finally { loading.value = false }
})
</script>
