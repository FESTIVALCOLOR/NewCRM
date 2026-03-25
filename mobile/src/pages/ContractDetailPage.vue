<template>
  <q-page padding>
    <template v-if="contract">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md">
        <q-card-section>
          <div class="row items-start justify-between q-mb-xs">
            <div style="flex: 1">
              <div class="text-subtitle1 text-weight-bold" style="color: #333">{{ contract.contract_number }}</div>
              <div class="row items-center q-mt-xs">
            <div class="text-body2" style="color: #333; flex: 1">{{ contract.address }}</div>
            <q-btn v-if="contract.address" flat round dense size="sm" icon="location_on" style="color: #333" @click="openMap(contract.address)"><q-tooltip>На карте</q-tooltip></q-btn>
          </div>
            </div>
            <div class="column items-end q-gutter-xs q-ml-sm" style="flex-shrink: 0">
              <q-badge :color="statusColor(contract.status)" :label="contract.status" style="min-width: 100px; justify-content: center; padding: 5px 8px; font-size: 11px" />
              <q-badge v-if="contract.agent_type" text-color="white" :style="{ background: agentColor, minWidth: '100px', justifyContent: 'center', padding: '5px 8px', fontSize: '11px' }" :label="contract.agent_type" />
            </div>
          </div>
          <div class="row q-gutter-sm text-caption q-mt-xs" style="color: #888">
            <span>{{ contract.project_type }}</span>
            <span v-if="contract.project_subtype"> · {{ contract.project_subtype }}</span>
            <span v-if="contract.area">{{ contract.area }} м²</span>
            <span v-if="contract.city">{{ contract.city }}</span>
            <span v-if="contract.floors">{{ contract.floors }} эт.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Клиент (ФИО со ссылкой) -->
      <q-card class="is-card q-mb-md" v-if="contract.client_name || contract.client_id">
        <q-item clickable v-ripple @click="goToClient">
          <q-item-section avatar><q-icon name="person" color="grey-7" /></q-item-section>
          <q-item-section>
            <q-item-label caption>Клиент</q-item-label>
            <q-item-label class="text-weight-bold" style="color: #333">{{ clientDisplayName }}</q-item-label>
          </q-item-section>
          <q-item-section side><q-icon name="chevron_right" color="grey-5" /></q-item-section>
        </q-item>
      </q-card>

      <!-- Основные данные (порядок: дата, срок, сумма, город, площадь, комментарий) -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Основные данные</div>
        </q-card-section>
        <q-list dense>
          <q-item v-if="contract.contract_date">
            <q-item-section avatar><q-icon name="event" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Дата договора</q-item-label><q-item-label>{{ fmtDate(contract.contract_date) }}</q-item-label></q-item-section>
          </q-item>
          <q-item v-if="contract.contract_period">
            <q-item-section avatar><q-icon name="schedule" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Срок договора</q-item-label><q-item-label>{{ contract.contract_period }} рабочих дней</q-item-label></q-item-section>
          </q-item>
          <q-item v-if="contract.total_amount">
            <q-item-section avatar><q-icon name="payments" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Сумма договора</q-item-label><q-item-label class="text-weight-bold">{{ fmtMoney(contract.total_amount) }}</q-item-label></q-item-section>
          </q-item>
          <q-item v-if="contract.city">
            <q-item-section avatar><q-icon name="location_city" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Город</q-item-label><q-item-label>{{ contract.city }}</q-item-label></q-item-section>
          </q-item>
          <q-item v-if="contract.area">
            <q-item-section avatar><q-icon name="square_foot" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Площадь</q-item-label><q-item-label>{{ contract.area }} м²</q-item-label></q-item-section>
          </q-item>
          <q-item v-if="contract.comments">
            <q-item-section avatar><q-icon name="comment" color="grey-7" /></q-item-section>
            <q-item-section><q-item-label caption>Комментарий</q-item-label><q-item-label>{{ contract.comments }}</q-item-label></q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Платежи от клиента (индивидуальный) -->
      <q-card class="is-card q-mb-md" v-if="contract.project_type === 'Индивидуальный'">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">Платежи от клиента</div>
        </q-card-section>
        <q-list dense separator>
          <q-item v-for="pay in clientPayments" :key="pay.key">
            <q-item-section>
              <q-item-label class="text-weight-medium">{{ pay.label }}</q-item-label>
              <q-item-label class="text-weight-bold" style="color: #333">{{ fmtMoney(pay.amount) }}</q-item-label>
              <q-item-label caption :style="{ color: pay.paidDate ? '#27AE60' : '#888' }">
                {{ pay.paidDate ? `Оплачено ${fmtDate(pay.paidDate)}` : 'Не оплачено' }}
              </q-item-label>
            </q-item-section>
            <q-item-section side style="min-width: 110px">
              <div class="column q-gutter-xs items-stretch">
                <q-btn v-if="!pay.paidDate" outline dense size="sm" icon="check_circle" label="Оплатить" color="positive" no-caps @click="pickPayDate(pay.key)" style="border-radius: 4px; min-width: 105px; height: 30px" />
                <q-badge v-else color="positive" style="padding: 6px 12px; font-size: 11px; border-radius: 4px; min-width: 105px; justify-content: center; height: 30px; display: flex; align-items: center">
                  Оплачено
                  <q-btn flat round dense size="xs" icon="close" color="white" class="q-ml-xs" @click.stop="cancelPayment(pay.key)" style="margin: -4px -4px -4px 0" />
                </q-badge>
                <q-btn outline dense size="sm" icon="upload_file" label="Чек" no-caps style="color: #333; border-color: #ffd93c; border-radius: 4px; min-width: 105px; height: 30px" @click="uploadReceipt(pay.key)" />
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
            <q-item-section side style="min-width: 110px">
              <q-btn v-if="!contract.advance_payment_paid_date" outline dense size="sm" icon="check_circle" label="Оплатить" color="positive" no-caps @click="pickPayDate('advance')" style="border-radius: 4px; min-width: 105px" />
              <q-badge v-else color="positive" style="padding: 5px 12px; font-size: 11px; border-radius: 4px; min-width: 105px; justify-content: center">
                Оплачено
                <q-btn flat round dense size="xs" icon="close" color="white" class="q-ml-xs" @click.stop="cancelPayment('advance')" />
              </q-badge>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Таблица сроков -->
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

      <!-- Файлы: Договор -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Договор</div></q-card-section>
        <q-list dense v-if="filesByGroup.documents.length > 0">
          <q-item v-for="f in filesByGroup.documents" :key="f.id" clickable @click="openFile(f)">
            <q-item-section avatar><q-icon :name="fileIconByName(f.file_name)" :color="fileColorByName(f.file_name)" /></q-item-section>
            <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
        <q-card-section class="q-pt-xs"><q-btn outline color="grey-7" icon="gavel" label="Загрузить договор" no-caps class="full-width" dense @click="uploadFor('documents')" /></q-card-section>
      </q-card>

      <!-- Файлы: ТЗ -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Техническое задание</div></q-card-section>
        <q-list dense v-if="filesByGroup.tech_task.length > 0">
          <q-item v-for="f in filesByGroup.tech_task" :key="f.id" clickable @click="openFile(f)">
            <q-item-section avatar><q-icon :name="fileIconByName(f.file_name)" :color="fileColorByName(f.file_name)" /></q-item-section>
            <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
        <q-card-section class="q-pt-xs"><q-btn outline color="grey-7" icon="description" label="Загрузить ТЗ" no-caps class="full-width" dense @click="uploadFor('tech_task')" /></q-card-section>
      </q-card>

      <!-- Файлы: Доп. соглашения -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Доп. соглашения</div></q-card-section>
        <q-list dense v-if="filesByGroup.supervision.length > 0">
          <q-item v-for="f in filesByGroup.supervision" :key="f.id" clickable @click="openFile(f)">
            <q-item-section avatar><q-icon :name="fileIconByName(f.file_name)" :color="fileColorByName(f.file_name)" /></q-item-section>
            <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
        <q-card-section class="q-pt-xs"><q-btn outline color="grey-7" icon="handshake" label="Загрузить доп. соглашение" no-caps class="full-width" dense @click="uploadFor('supervision')" /></q-card-section>
      </q-card>

      <!-- Файлы: Акты без подписи -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Акты (без подписи)</div></q-card-section>
        <q-list dense v-if="filesByGroup.acts.length > 0">
          <q-item v-for="f in filesByGroup.acts" :key="f.id" clickable @click="openFile(f)">
            <q-item-section avatar><q-icon name="verified" color="orange" /></q-item-section>
            <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label><q-item-label caption>{{ stageLabel(f.stage) }}</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
        <q-card-section class="q-pt-xs">
          <div class="row q-col-gutter-xs">
            <div class="col-4"><q-btn outline color="grey-7" label="Акт ПР" no-caps class="full-width" dense @click="uploadFor('stage1')" /></div>
            <div class="col-4"><q-btn outline color="grey-7" label="Акт КД" no-caps class="full-width" dense @click="uploadFor('stage2_concept')" /></div>
            <div class="col-4"><q-btn outline color="grey-7" label="Акт РЧ" no-caps class="full-width" dense @click="uploadFor('stage3')" /></div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Файлы: Акты с подписью -->
      <q-card class="is-card q-mb-md">
        <q-card-section class="q-pb-none"><div class="text-subtitle2 text-weight-bold" style="color: #333">Акты (с подписью)</div></q-card-section>
        <q-list dense v-if="filesByGroup.actsSigned.length > 0">
          <q-item v-for="f in filesByGroup.actsSigned" :key="f.id" clickable @click="openFile(f)">
            <q-item-section avatar><q-icon name="verified_user" color="positive" /></q-item-section>
            <q-item-section><q-item-label style="font-size: 12px">{{ f.file_name }}</q-item-label><q-item-label caption>{{ stageLabel(f.stage) }}</q-item-label></q-item-section>
            <q-item-section side><q-icon name="open_in_new" color="grey-5" /></q-item-section>
          </q-item>
        </q-list>
        <q-card-section class="q-pt-xs">
          <div class="row q-col-gutter-xs">
            <div class="col-4"><q-btn outline color="grey-7" label="ПР подп." no-caps class="full-width" dense @click="uploadFor('stage1_signed')" /></div>
            <div class="col-4"><q-btn outline color="grey-7" label="КД подп." no-caps class="full-width" dense @click="uploadFor('stage2_signed')" /></div>
            <div class="col-4"><q-btn outline color="grey-7" label="РЧ подп." no-caps class="full-width" dense @click="uploadFor('stage3_signed')" /></div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Кнопка удаления -->
      <q-btn flat color="negative" icon="delete" label="Удалить договор" no-caps class="full-width q-mb-md" @click="deleteContract" />

      <!-- FAB редактирования -->
      <q-page-sticky position="bottom-right" :offset="[18, 18]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" @click="showEdit = true" />
      </q-page-sticky>

      <contract-form-dialog v-model="showEdit" :contract="contract" @saved="reload" />

      <!-- Скрытые инпуты для загрузки -->
      <input ref="fileInput" type="file" style="position: absolute; left: -9999px; opacity: 0" @change="handleFileUpload" accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx,.dwg" />
      <input ref="receiptInput" type="file" style="position: absolute; left: -9999px; opacity: 0" @change="handleReceiptUpload" accept=".pdf,.jpg,.jpeg,.png" />
    </template>

    <div v-else-if="!loading" class="text-center q-pa-xl" style="color: #999">
      <q-icon name="description" size="48px" class="q-mb-sm" /><div>Договор не найден</div>
    </div>
    <div v-else class="text-center q-pa-xl"><q-spinner size="40px" color="accent" /></div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { contractsApi, filesApi, crmApi, clientsApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'
import ContractFormDialog from 'src/components/ContractFormDialog.vue'

const route = useRoute()
const router = useRouter()
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

// ФИО клиента — из contract.client_name или загрузим отдельно
const clientName = ref(null)
const clientDisplayName = computed(() => {
  if (contract.value?.client_name) return contract.value.client_name
  if (clientName.value) return clientName.value
  return contract.value?.client_id ? `Клиент #${contract.value.client_id}` : 'Неизвестен'
})

// Платежи клиента (массив для удобства итерации)
const clientPayments = computed(() => {
  if (!contract.value) return []
  return [
    { key: 'advance', label: '1 платёж (Аванс)', amount: contract.value.advance_payment, paidDate: contract.value.advance_payment_paid_date },
    { key: 'additional', label: '2 платёж (Доплата)', amount: contract.value.additional_payment, paidDate: contract.value.additional_payment_paid_date },
    { key: 'third', label: '3 платёж (Доплата)', amount: contract.value.third_payment, paidDate: contract.value.third_payment_paid_date }
  ]
})

// Файлы, сгруппированные по блокам
const filesByGroup = computed(() => {
  const groups = { documents: [], tech_task: [], supervision: [], acts: [], actsSigned: [] }
  for (const f of files.value) {
    if (f.stage === 'documents') groups.documents.push(f)
    else if (f.stage === 'tech_task') groups.tech_task.push(f)
    else if (f.stage === 'supervision') groups.supervision.push(f)
    else if (['stage1_signed', 'stage2_signed', 'stage3_signed'].includes(f.stage)) groups.actsSigned.push(f)
    else if (['stage1', 'stage2_concept', 'stage3'].includes(f.stage)) groups.acts.push(f)
  }
  return groups
})

const STAGE_LABELS = {
  stage1: 'Акт ПР', stage1_signed: 'Акт ПР (подписанный)',
  stage2_concept: 'Акт КД', stage2_signed: 'Акт КД (подписанный)',
  stage3: 'Акт РЧ', stage3_signed: 'Акт РЧ (подписанный)',
  tech_task: 'Тех. задание', documents: 'Договор',
  supervision: 'Доп. соглашение'
}
function stageLabel(s) { return STAGE_LABELS[s] || s || '' }
function statusColor(s) { if (!s) return 'grey'; if (s === 'В работе') return 'orange'; if (s.includes('СДАН')) return 'positive'; if (s.includes('РАСТОРГНУТ')) return 'negative'; if (s.includes('НАДЗОР')) return 'purple'; return 'blue' }
function fmtDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) }
function fmtDateShort(d) { if (!d) return ''; return new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) }
function fmtMoney(v) { if (!v) return '0 ₽'; return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(v) }

function fileIconByName(name) {
  if (!name) return 'insert_drive_file'
  const n = name.toLowerCase()
  if (n.endsWith('.pdf')) return 'picture_as_pdf'
  if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'image'
  if (n.match(/\.(doc|docx)$/)) return 'article'
  if (n.match(/\.(xls|xlsx)$/)) return 'table_chart'
  return 'insert_drive_file'
}
function fileColorByName(name) {
  if (!name) return 'grey-7'
  const n = name.toLowerCase()
  if (n.endsWith('.pdf')) return 'red'
  if (n.match(/\.(jpg|jpeg|png|webp)$/)) return 'green'
  if (n.match(/\.(doc|docx)$/)) return 'blue'
  if (n.match(/\.(xls|xlsx)$/)) return 'teal'
  return 'grey-7'
}

function openFile(f) { if (f.public_link) window.open(f.public_link, '_blank') }
function goToClient() { if (contract.value?.client_id) router.push(`/clients/${contract.value.client_id}`) }
function openMap(address) { window.open(`https://yandex.ru/maps/?text=${encodeURIComponent(address)}`, '_blank') }

function uploadFor(stage) { uploadStage.value = stage; fileInput.value?.click() }
function uploadReceipt(type) { receiptType.value = type; receiptInput.value?.click() }

// Оплата с выбором даты через календарь
function pickPayDate(payKey) {
  $q.dialog({
    title: 'Дата оплаты',
    message: 'Выберите дату оплаты:',
    prompt: { model: new Date().toISOString().split('T')[0], type: 'date' },
    cancel: { label: 'Отмена', flat: true, noCaps: true },
    ok: { label: 'Подтвердить', noCaps: true, color: 'positive' },
    persistent: true
  }).onOk(async (date) => {
    try {
      const update = {}
      update[`${payKey}_payment_paid_date`] = date
      await contractsApi.update(contract.value.id, update)
      contract.value[`${payKey}_payment_paid_date`] = date
      $q.notify({ type: 'positive', message: 'Оплата проведена' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

// Снять оплату
async function cancelPayment(payKey) {
  $q.dialog({ title: 'Снять оплату?', message: 'Отменить дату оплаты?', cancel: { label: 'Нет', flat: true, noCaps: true }, ok: { label: 'Да, снять', noCaps: true, color: 'negative' } }).onOk(async () => {
    try {
      const update = {}
      update[`${payKey}_payment_paid_date`] = null
      await contractsApi.update(contract.value.id, update)
      contract.value[`${payKey}_payment_paid_date`] = null
      $q.notify({ type: 'positive', message: 'Оплата снята' })
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
    }
  })
}

async function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (!file || !contract.value) return
  try {
    $q.loading.show({ message: 'Загрузка...' })
    // Используем yandex_folder_path контракта (как десктоп), без disk: в пути
    const contractFolder = (contract.value.yandex_folder_path || '').replace(/^disk:/, '')
    const STAGE_FOLDERS = { documents: 'Договор', tech_task: 'ТЗ', measurement: 'Замер', stage1: '1 стадия - Планировочное решение', stage1_signed: 'Акты подписанные/ПР', stage2_concept: '2 стадия - Концепция дизайна', stage2_signed: 'Акты подписанные/КД', stage3: '3 стадия - Чертежный проект', stage3_signed: 'Акты подписанные/РЧ', references: 'Референсы', photo_documentation: 'Фотофиксация', supervision: 'Доп. соглашения' }
    const stageFolder = STAGE_FOLDERS[uploadStage.value] || uploadStage.value
    const ydPath = contractFolder ? `${contractFolder}/${stageFolder}/${file.name}` : `/CRM/Проекты/${contract.value.contract_number}/${stageFolder}/${file.name}`
    const uploadRes = await filesApi.upload(file, ydPath)
    const publicLink = uploadRes.data?.public_link || ''
    const { api: apiInst } = await import('src/boot/axios')
    await apiInst.post('/api/v1/files/', {
      contract_id: contract.value.id, stage: uploadStage.value,
      file_type: file.type?.includes('image') ? 'image' : file.name.endsWith('.pdf') ? 'pdf' : 'other',
      public_link: publicLink, yandex_path: ydPath, file_name: file.name,
      file_order: files.value.length + 1, variation: 1
    })
    $q.notify({ type: 'positive', message: 'Файл загружен' })
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

async function deleteContract() {
  $q.dialog({ title: 'Удалить договор?', message: contract.value?.contract_number || '', cancel: true, persistent: true }).onOk(async () => {
    try {
      await contractsApi.delete(contract.value.id)
      $q.notify({ type: 'positive', message: 'Договор удалён' })
      window.history.back()
    } catch (err) { $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' }) }
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
      contractsApi.getById(id), filesApi.getContractFiles(id), crmApi.getTimeline(id)
    ])
    if (cRes.status === 'fulfilled') contract.value = cRes.value.data
    if (fRes.status === 'fulfilled') files.value = fRes.value.data || []
    if (tRes.status === 'fulfilled') timeline.value = tRes.value.data || []
    // Загрузим ФИО клиента если нет в данных договора
    if (contract.value?.client_id && !contract.value.client_name) {
      try {
        const { data: cl } = await clientsApi.getById(contract.value.client_id)
        if (cl?.full_name) clientName.value = cl.full_name
      } catch {}
    }
  } finally { loading.value = false }
})
</script>
