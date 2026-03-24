<template>
  <q-page padding>
    <template v-if="contract">
      <!-- ОДИН СКРОЛЛ — как в десктопе, НЕ вкладки -->

      <!-- Блок: Шапка -->
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
          <div class="text-body2" style="color: #333">{{ contract.address }}</div>
          <div class="row q-gutter-sm text-caption" style="color: #888">
            <span>{{ contract.project_type }}</span>
            <span v-if="contract.project_subtype">{{ contract.project_subtype }}</span>
            <span v-if="contract.area">{{ contract.area }} м²</span>
            <span v-if="contract.city">{{ contract.city }}</span>
            <span v-if="contract.floors">{{ contract.floors }} эт.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Блок: Клиент -->
      <q-card class="is-card q-mb-md" v-if="contract.client_name || contract.client_id">
        <q-card-section>
          <div class="text-caption" style="color: #888">Клиент</div>
          <div class="text-weight-bold" style="color: #333">{{ contract.client_name || `ID: ${contract.client_id}` }}</div>
        </q-card-section>
      </q-card>

      <!-- Блок: Основные данные -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Основные данные</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="contract.contract_date"><q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Дата договора</q-item-label><q-item-label>{{ fmtDate(contract.contract_date) }}</q-item-label></q-item-section></q-item>
          <q-item v-if="contract.total_amount"><q-item-section avatar><q-icon name="payments" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Сумма договора</q-item-label><q-item-label class="text-weight-bold">{{ fmtMoney(contract.total_amount) }}</q-item-label></q-item-section></q-item>
          <q-item v-if="contract.contract_period"><q-item-section avatar><q-icon name="schedule" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Срок выполнения</q-item-label><q-item-label>{{ contract.contract_period }} рабочих дней</q-item-label></q-item-section></q-item>
          <q-item v-if="contract.comments"><q-item-section avatar><q-icon name="comment" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Комментарий</q-item-label><q-item-label>{{ contract.comments }}</q-item-label></q-item-section></q-item>
        </q-list>
      </q-card>

      <!-- Блок: Платежи от клиента (аванс / доплата / третий платёж) -->
      <q-card class="is-card q-mb-md" v-if="contract.project_type === 'Индивидуальный'">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Платежи от клиента</div>
        </q-card-section>
        <q-list dense separator>
          <!-- 1 платёж (Аванс) -->
          <q-item>
            <q-item-section>
              <q-item-label class="text-weight-medium">1 платёж (Аванс)</q-item-label>
              <q-item-label class="text-weight-bold" style="color: #333">{{ fmtMoney(contract.advance_payment) }}</q-item-label>
              <q-item-label caption :style="{ color: contract.advance_payment_paid_date ? '#27AE60' : '#888' }">
                {{ contract.advance_payment_paid_date ? `Оплачено ${fmtDate(contract.advance_payment_paid_date)}` : 'Не оплачено' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="column q-gutter-xs">
                <q-btn v-if="!contract.advance_payment_paid_date" outline dense size="sm" icon="check_circle" label="Оплачено" color="positive" no-caps @click="markClientPaid('advance')" style="border-radius: 4px" />
                <q-btn outline dense size="sm" icon="upload_file" label="Чек" no-caps style="color: #333; border-color: #ffd93c; border-radius: 4px" @click="uploadReceipt('advance')" />
                <q-btn v-if="contract.advance_receipt_link" flat dense size="sm" icon="visibility" label="Просмотр" color="grey-7" no-caps @click="openLink(contract.advance_receipt_link)" />
              </div>
            </q-item-section>
          </q-item>
          <!-- 2 платёж (Доплата) -->
          <q-item>
            <q-item-section>
              <q-item-label class="text-weight-medium">2 платёж (Доплата)</q-item-label>
              <q-item-label class="text-weight-bold" style="color: #333">{{ fmtMoney(contract.additional_payment) }}</q-item-label>
              <q-item-label caption :style="{ color: contract.additional_payment_paid_date ? '#27AE60' : '#888' }">
                {{ contract.additional_payment_paid_date ? `Оплачено ${fmtDate(contract.additional_payment_paid_date)}` : 'Не оплачено' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="column q-gutter-xs">
                <q-btn v-if="!contract.additional_payment_paid_date" outline dense size="sm" icon="check_circle" label="Оплачено" color="positive" no-caps @click="markClientPaid('additional')" style="border-radius: 4px" />
                <q-btn outline dense size="sm" icon="upload_file" label="Чек" no-caps style="color: #333; border-color: #ffd93c; border-radius: 4px" @click="uploadReceipt('additional')" />
              </div>
            </q-item-section>
          </q-item>
          <!-- 3 платёж -->
          <q-item>
            <q-item-section>
              <q-item-label class="text-weight-medium">3 платёж (Доплата)</q-item-label>
              <q-item-label class="text-weight-bold" style="color: #333">{{ fmtMoney(contract.third_payment) }}</q-item-label>
              <q-item-label caption :style="{ color: contract.third_payment_paid_date ? '#27AE60' : '#888' }">
                {{ contract.third_payment_paid_date ? `Оплачено ${fmtDate(contract.third_payment_paid_date)}` : 'Не оплачено' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="column q-gutter-xs">
                <q-btn v-if="!contract.third_payment_paid_date" outline dense size="sm" icon="check_circle" label="Оплачено" color="positive" no-caps @click="markClientPaid('third')" style="border-radius: 4px" />
                <q-btn outline dense size="sm" icon="upload_file" label="Чек" no-caps style="color: #333; border-color: #ffd93c; border-radius: 4px" @click="uploadReceipt('third')" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Шаблонный — 1 платёж -->
      <q-card class="is-card q-mb-md" v-if="contract.project_type === 'Шаблонный'">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Оплата</div>
        </q-card-section>
        <q-list dense>
          <q-item>
            <q-item-section>
              <q-item-label class="text-weight-bold" style="color: #333">{{ fmtMoney(contract.advance_payment || contract.total_amount) }}</q-item-label>
              <q-item-label caption :style="{ color: contract.advance_payment_paid_date ? '#27AE60' : '#888' }">
                {{ contract.advance_payment_paid_date ? `Оплачено ${fmtDate(contract.advance_payment_paid_date)}` : 'Не оплачено' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn v-if="!contract.advance_payment_paid_date" flat dense size="xs" icon="check_circle" color="positive" @click="markClientPaid('advance')"><q-tooltip>Оплачено</q-tooltip></q-btn>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Блок: Таблица сроков -->
      <q-card class="is-card q-mb-md" v-if="timeline.length > 0">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Таблица сроков</div>
        </q-card-section>
        <q-list dense separator>
          <q-item v-for="entry in timeline" :key="entry.id" :class="{ 'bg-green-1': entry.actual_date }">
            <q-item-section avatar>
              <q-icon :name="entry.actual_date ? 'check_circle' : 'radio_button_unchecked'" :color="entry.actual_date ? 'positive' : 'grey-5'" size="16px" />
            </q-item-section>
            <q-item-section>
              <q-item-label style="font-size: 11px; color: #333" :class="{ 'text-weight-bold': !entry.stage_code?.includes('.') }">{{ entry.stage_name }}</q-item-label>
              <q-item-label caption style="color: #888">
                <span v-if="entry.norm_days">Норма: {{ entry.custom_norm_days || entry.norm_days }} дн.</span>
                <span v-if="entry.actual_days"> | Факт: {{ entry.actual_days }} дн.</span>
                <span v-if="entry.executor_role && entry.executor_role !== 'header'"> | {{ entry.executor_role }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side v-if="entry.actual_date">
              <div class="text-caption" style="color: #27AE60">{{ fmtDateShort(entry.actual_date) }}</div>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Блок: Файл договора + Акты -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Файлы и акты</div>
        </q-card-section>
        <!-- Существующие файлы -->
        <q-list dense v-if="files.length > 0">
          <q-item v-for="file in files" :key="file.id" clickable @click="openFile(file)">
            <q-item-section avatar><q-icon :name="fileIcon(file.file_type)" :color="fileColor(file.file_type)" /></q-item-section>
            <q-item-section><q-item-label style="font-size: 12px">{{ file.file_name }}</q-item-label><q-item-label caption>{{ stageLabel(file.stage) }}</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
        <!-- Кнопки загрузки -->
        <q-card-section>
          <div class="row q-col-gutter-xs">
            <div class="col-6" v-for="btn in fileUploadButtons" :key="btn.stage">
              <q-btn outline color="grey-7" :icon="btn.icon" :label="btn.label" no-caps class="full-width q-mb-xs" dense @click="uploadFor(btn.stage)" />
            </div>
          </div>
        </q-card-section>
        <input ref="fileInput" type="file" style="position: absolute; left: -9999px; opacity: 0" @change="handleFileUpload" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.dwg" />
        <input ref="receiptInput" type="file" style="position: absolute; left: -9999px; opacity: 0" @change="handleReceiptUpload" accept=".pdf,.jpg,.jpeg,.png" />
      </q-card>

      <!-- Блок: ТЗ и Комментарий -->
      <q-card class="is-card q-mb-md" v-if="contract.tech_task_link || contract.comments">
        <q-list dense>
          <q-item v-if="contract.tech_task_link" clickable @click="openLink(contract.tech_task_link)">
            <q-item-section avatar><q-icon name="description" color="orange" /></q-item-section>
            <q-item-section><q-item-label>Техническое задание</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Кнопка удаления -->
      <q-btn flat color="negative" icon="delete" label="Удалить договор" no-caps class="full-width q-mb-md" @click="deleteContract" />

      <!-- FAB редактирования -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" @click="showEdit = true" />
      </q-page-sticky>

      <contract-form-dialog v-model="showEdit" :contract="contract" @saved="reload" />
    </template>

    <div v-else-if="!loading" class="text-center q-pa-xl" style="color: #999">
      <q-icon name="description" size="48px" class="q-mb-sm" /><div>Договор не найден</div>
    </div>
    <div v-else class="text-center q-pa-xl"><q-spinner size="40px" color="accent" /></div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { contractsApi, filesApi, crmApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'

const route = useRoute()
const $q = useQuasar()
const refs = useReferencesStore()
const contract = ref(null)
const files = ref([])
const timeline = ref([])
const loading = ref(true)
const showEdit = ref(false)
const fileInput = ref(null)
const receiptInput = ref(null)
const uploadStage = ref('')
const receiptType = ref('')

const agentColor = computed(() => refs.agentByName(contract.value?.agent_type)?.color || '#95A5A6')

const fileUploadButtons = [
  { stage: 'documents', label: 'Договор', icon: 'gavel' },
  { stage: 'tech_task', label: 'ТЗ', icon: 'description' },
  { stage: 'measurement', label: 'Замер', icon: 'straighten' },
  { stage: 'stage1', label: 'Акт ПР', icon: 'verified' },
  { stage: 'stage2_concept', label: 'Акт КД', icon: 'verified' },
  { stage: 'references', label: 'Референсы', icon: 'collections' },
  { stage: 'photo_documentation', label: 'Фотофикс.', icon: 'photo_camera' },
  { stage: 'supervision', label: 'Доп.согл.', icon: 'handshake' }
]

const STAGE_LABELS = {
  stage1: 'Планировочное решение', stage2_concept: 'Концепция', stage2_3d: '3D визуализация',
  stage3: 'Чертёжный проект', references: 'Референсы', photo_documentation: 'Фотофиксация',
  tech_task: 'Тех. задание', documents: 'Договор', measurement: 'Замер', supervision: 'Доп. соглашение'
}

function stageLabel(s) { return STAGE_LABELS[s] || s || '' }
function statusColor(s) { if (!s) return 'grey'; if (s === 'В работе') return 'orange'; if (s.includes('СДАН')) return 'positive'; if (s.includes('РАСТОРГНУТ')) return 'negative'; if (s.includes('НАДЗОР')) return 'purple'; return 'blue' }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }
function fileIcon(t) { return { image: 'image', pdf: 'picture_as_pdf', excel: 'table_chart', word: 'article', cad: 'architecture' }[t] || 'insert_drive_file' }
function fileColor(t) { return { image: 'green', pdf: 'red', excel: 'teal', word: 'blue', cad: 'purple' }[t] || 'grey-7' }
function openFile(f) { if (f.public_link) window.open(f.public_link, '_blank') }
function openLink(url) { if (url) window.open(url, '_blank') }

function uploadFor(stage) { uploadStage.value = stage; fileInput.value?.click() }

function uploadReceipt(type) { receiptType.value = type; receiptInput.value?.click() }

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !contract.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    const yandexPath = `/CRM/Проекты/${contract.value.contract_number}/${uploadStage.value}/${file.name}`
    const uploadRes = await filesApi.upload(file, yandexPath)
    const publicLink = uploadRes.data?.public_link || ''
    // Создаём запись в БД ProjectFile
    const { api: apiInst } = await import('src/boot/axios')
    await apiInst.post('/api/v1/files/', {
      contract_id: contract.value.id,
      stage: uploadStage.value,
      file_type: file.type?.includes('image') ? 'image' : file.name.endsWith('.pdf') ? 'pdf' : 'other',
      public_link: publicLink,
      yandex_path: yandexPath,
      file_name: file.name,
      file_order: files.value.length + 1,
      variation: 1
    })
    $q.notify({ type: 'positive', message: 'Файл загружен' })
    // Перезагрузить список файлов
    const { data } = await filesApi.getContractFiles(contract.value.id)
    files.value = data || []
  } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка загрузки' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

async function handleReceiptUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !contract.value) return
  try {
    $q.loading.show({ message: 'Загрузка чека...' })
    const yandexPath = `/CRM/Чеки/${contract.value.contract_number}/${receiptType.value}_${file.name}`
    await filesApi.upload(file, yandexPath)
    $q.notify({ type: 'positive', message: 'Чек загружен' })
  } catch { $q.notify({ type: 'negative', message: 'Ошибка загрузки' }) }
  finally { $q.loading.hide(); event.target.value = '' }
}

async function markClientPaid(type) {
  const today = new Date().toISOString().split('T')[0]
  try {
    const update = {}
    update[`${type}_payment_paid_date`] = today
    await contractsApi.update(contract.value.id, update)
    contract.value[`${type}_payment_paid_date`] = today
    $q.notify({ type: 'positive', message: 'Оплата проведена' })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  }
}

async function deleteContract() {
  $q.dialog({ title: 'Удалить договор?', message: contract.value?.contract_number || '', cancel: true, persistent: true }).onOk(async () => {
    try {
      await contractsApi.delete(contract.value.id)
      $q.notify({ type: 'positive', message: 'Договор удалён' })
      window.history.back()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

async function reload() {
  const { data } = await contractsApi.getById(route.params.id)
  contract.value = data
}

onMounted(async () => {
  const id = route.params.id
  try {
    const [cRes, fRes, tRes] = await Promise.allSettled([
      contractsApi.getById(id),
      filesApi.getContractFiles(id),
      crmApi.getTimeline(id)
    ])
    if (cRes.status === 'fulfilled') contract.value = cRes.value.data
    if (fRes.status === 'fulfilled') files.value = fRes.value.data || []
    if (tRes.status === 'fulfilled') timeline.value = tRes.value.data || []
  } finally { loading.value = false }
})
</script>
