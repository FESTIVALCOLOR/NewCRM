<template>
  <q-dialog v-model="show" persistent>
    <q-card style="min-width: 340px; max-width: 560px; width: 100%; border-radius: 10px">
      <q-toolbar style="background: #F39C12; color: white">
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Добавить замер</q-toolbar-title>
        <q-btn flat round dense icon="close" color="white" @click="close" />
      </q-toolbar>

      <q-card-section>
        <!-- Режим загрузки (как десктоп RadioButtons) -->
        <q-option-group v-model="uploadMode" :options="[
          { label: 'Загрузить файл', value: 'file' },
          { label: 'По ссылке от замерщика', value: 'link' }
        ]" inline dense class="q-mb-md" />

        <!-- === РЕЖИМ 1: Загрузить файл === -->
        <template v-if="uploadMode === 'file'">
          <div class="text-caption text-weight-bold q-mb-xs">Изображение замера:</div>
          <div v-if="selectedFile" class="q-mb-sm" style="background: #F8F9FA; border: 1px solid #E0E0E0; padding: 6px 10px; border-radius: 4px; font-size: 12px">
            {{ selectedFile.name.length > 25 ? selectedFile.name.slice(0, 12) + '...' + selectedFile.name.slice(-10) : selectedFile.name }}
          </div>
          <q-btn outline color="grey-7" icon="upload" label="Загрузить" no-caps dense style="height: 28px" @click="fileInput?.click()" class="q-mb-sm" />
          <input ref="fileInput" type="file" accept="image/png,image/jpg,image/jpeg,image/gif,image/bmp" style="display: none" @change="onFileSelected" />
        </template>

        <!-- === РЕЖИМ 2: По ссылке от замерщика === -->
        <template v-if="uploadMode === 'link'">
          <div class="text-caption text-weight-bold q-mb-xs">Ссылка на папку замерщика:</div>
          <div class="row q-gutter-sm q-mb-sm">
            <q-input v-model="publicLink" placeholder="Вставьте публичную ссылку ЯД или Google Drive..." outlined dense style="flex: 1" />
            <q-btn unelevated no-caps label="Получить файлы" style="background: #E0E0E0; color: #333; height: 40px; border-radius: 4px" @click="fetchFiles" :loading="fetching" />
          </div>

          <!-- Таблица файлов -->
          <q-table v-if="fetchedFiles.length > 0" :rows="fetchedFiles" :columns="fileColumns" row-key="name" dense flat bordered
            class="q-mb-sm" style="max-height: 200px" :pagination="{ rowsPerPage: 0 }" hide-pagination>
            <template v-slot:body-cell-destination="props">
              <q-td :props="props">
                <q-select v-model="props.row.destination" :options="['Замер', 'Фотофиксация']" dense outlined options-dense
                  :style="{ color: props.row.destination === 'Замер' ? '#1677FF' : '#52C41A', fontSize: '11px', width: '130px' }"
                  popup-content-style="font-size: 12px" />
              </q-td>
            </template>
            <template v-slot:body-cell-remove="props">
              <q-td :props="props">
                <q-btn flat round dense size="sm" icon="delete_outline" color="negative" style="border: 1px solid #E57373; width: 28px; height: 28px" @click="fetchedFiles.splice(props.rowIndex, 1)" />
              </q-td>
            </template>
          </q-table>

          <!-- Статус + кнопка загрузки -->
          <div v-if="fetchedFiles.length > 0" class="q-mb-sm">
            <div class="text-caption q-mb-xs" style="color: #888">
              Найдено файлов: {{ fetchedFiles.length }}
              (замер: {{ fetchedFiles.filter(f => f.destination === 'Замер').length }},
              фото: {{ fetchedFiles.filter(f => f.destination === 'Фотофиксация').length }})
            </div>
            <q-btn unelevated no-caps icon="cloud_upload" label="Загрузить на Яндекс.Диск" style="background: #1677FF; color: white; border-radius: 4px; width: 100%; height: 36px"
              @click="uploadFromLink" :loading="uploading" />
            <q-linear-progress v-if="uploading" :value="uploadProgress" color="primary" class="q-mt-xs" />
          </div>
        </template>

        <q-separator class="q-my-sm" />

        <!-- Замерщик -->
        <q-select v-model="surveyorId" :options="surveyorOptions" option-value="id" option-label="label"
          label="Замерщик" outlined dense emit-value map-options class="q-mb-sm" />

        <!-- Дата замера -->
        <q-input v-model="measurementDate" label="Дата замера" outlined dense type="date" class="q-mb-sm" />
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Отмена" no-caps v-close-popup />
        <q-btn unelevated label="Сохранить" no-caps style="background: #ffd93c; color: #333; border-radius: 4px"
          :loading="saving" @click="save" :disable="!canSave" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { employeesApi, filesApi, contractsApi, crmApi, paymentsApi } from 'src/services/api'

const props = defineProps({
  modelValue: Boolean,
  cardId: { type: Number, default: null },
  contractId: { type: Number, default: null },
  contractData: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const show = ref(false)
const saving = ref(false)
const fetching = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadMode = ref('file')
const surveyorId = ref(null)
const measurementDate = ref(new Date().toISOString().slice(0, 10))
const selectedFile = ref(null)
const publicLink = ref('')
const fileInput = ref(null)
const surveyorOptions = ref([])
const fetchedFiles = ref([])
const uploadedMeasLink = ref('')
const uploadedPhotoLink = ref('')

const fileColumns = [
  { name: 'name', label: 'Файл', field: 'name', align: 'left', style: 'font-size: 11px' },
  { name: 'size_display', label: 'Размер', field: 'size_display', align: 'right', style: 'font-size: 11px; width: 80px' },
  { name: 'destination', label: 'Назначение', field: 'destination', align: 'center', style: 'width: 130px' },
  { name: 'remove', label: '', field: '', align: 'center', style: 'width: 30px' },
]

watch(() => props.modelValue, v => { show.value = v; if (v) { loadSurveyors(); resetFields() } })
watch(show, v => emit('update:modelValue', v))

const canSave = computed(() => {
  if (!measurementDate.value) return false
  if (uploadMode.value === 'file' && !selectedFile.value) return false
  if (uploadMode.value === 'link' && !uploadedMeasLink.value && fetchedFiles.value.length === 0) return false
  return true
})

function close() { show.value = false }

function resetFields() {
  selectedFile.value = null
  publicLink.value = ''
  fetchedFiles.value = []
  uploadedMeasLink.value = ''
  uploadedPhotoLink.value = ''
  uploadProgress.value = 0
  uploadMode.value = 'file'
}

function onFileSelected(e) { selectedFile.value = e.target.files?.[0] || null }

async function loadSurveyors() {
  try {
    const { data } = await employeesApi.getList()
    surveyorOptions.value = [
      { id: null, label: 'Не назначен' },
      ...(data || [])
        .filter(e => e.status === 'активный' && (e.position === 'Замерщик' || e.secondary_position === 'Замерщик'))
        .map(e => ({ id: e.id, label: e.full_name }))
    ]
  } catch {}
}

// === Режим 2: Получить файлы из публичной ссылки (как десктоп _fetch_files_from_link) ===
async function fetchFiles() {
  if (!publicLink.value) return
  fetching.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const { data } = await ax.get('/api/v1/files/public-folder', { params: { url: publicLink.value } })
    fetchedFiles.value = (data.files || []).map(f => ({ ...f, destination: f.destination || 'Фотофиксация' }))
    if (fetchedFiles.value.length === 0) {
      $q.notify({ type: 'warning', message: 'Файлы не найдены по ссылке' })
    }
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка получения файлов' })
  } finally { fetching.value = false }
}

// === Режим 2: Загрузить файлы из публичной ссылки на свой ЯД ===
async function uploadFromLink() {
  if (fetchedFiles.value.length === 0) return
  uploading.value = true
  uploadProgress.value = 0
  try {
    const { api: ax } = await import('src/boot/axios')
    const contractFolder = props.contractData?.yandex_folder_path || ''
    if (!contractFolder) {
      $q.notify({ type: 'warning', message: 'Папка договора не создана на ЯД' }); return
    }
    const cfClean = contractFolder.replace(/^disk:/, '')
    const total = fetchedFiles.value.length
    let measLink = ''
    let photoLink = ''

    for (let i = 0; i < total; i++) {
      const f = fetchedFiles.value[i]
      const dest = f.destination === 'Замер' ? 'Замер' : 'Фотофиксация'
      const destPath = `${cfClean}/${dest}/${f.name}`

      try {
        const res = await ax.post('/api/v1/files/download-public', null, {
          params: { public_url: publicLink.value, file_path: f.path || `/${f.name}`, dest_path: destPath },
          timeout: 120000
        })
        if (res.data?.public_link) {
          if (dest === 'Замер') measLink = res.data.public_link
          else photoLink = res.data.public_link
        }
      } catch (e) { console.warn(`Ошибка загрузки ${f.name}:`, e) }
      uploadProgress.value = (i + 1) / total
    }

    // Получаем публичные ссылки на папки Замер и Фотофиксация
    const hasMeas = fetchedFiles.value.some(f => f.destination === 'Замер')
    const hasPhoto = fetchedFiles.value.some(f => f.destination === 'Фотофиксация')
    try {
      if (hasMeas) {
        const { data: ml } = await filesApi.getPublicLink(`${cfClean}/Замер`)
        measLink = ml.public_link || ''
      }
      if (hasPhoto) {
        const { data: pl } = await filesApi.getPublicLink(`${cfClean}/Фотофиксация`)
        photoLink = pl.public_link || ''
      }
    } catch {}

    uploadedMeasLink.value = measLink
    uploadedPhotoLink.value = photoLink

    // Обновляем contracts (как десктоп)
    if (props.contractId) {
      const update = {}
      if (measLink) {
        update.measurement_image_link = measLink
        update.measurement_folder_public_link = measLink
      }
      if (photoLink) update.photo_folder_public_link = photoLink
      if (Object.keys(update).length > 0) {
        await contractsApi.update(props.contractId, update)
      }
    }

    // Автоматический scan — чтобы файлы появились в project_files (синхронизация)
    if (props.contractId) {
      try { await ax.post(`/api/v1/files/scan/${props.contractId}`) } catch {}
    }

    $q.notify({ type: 'positive', message: `Загружено ${total} файл(ов) на ЯД` })
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка загрузки' })
  } finally { uploading.value = false }
}

// === Сохранение (как десктоп MeasurementDialog.save) ===
async function save() {
  saving.value = true
  try {
    const { api: ax } = await import('src/boot/axios')

    // Режим 1: загрузка файла
    if (uploadMode.value === 'file' && selectedFile.value) {
      const contractFolder = (props.contractData?.yandex_folder_path || '').replace(/^disk:/, '')
      if (contractFolder) {
        const ydPath = `${contractFolder}/Замер/${selectedFile.value.name}`
        const uploadRes = await filesApi.upload(selectedFile.value, ydPath)
        const pubLink = uploadRes.data?.public_link || ''

        // Обновляем contracts (как десктоп _on_image_uploaded)
        if (props.contractId) {
          await contractsApi.update(props.contractId, {
            measurement_image_link: pubLink,
            measurement_yandex_path: ydPath,
            measurement_file_name: selectedFile.value.name,
          })
          // Создаём запись в project_files + scan для синхронизации
          try {
            await ax.post('/api/v1/files/', {
              contract_id: props.contractId, stage: 'measurement',
              file_type: selectedFile.value.type?.includes('image') ? 'image' : 'pdf',
              public_link: pubLink, yandex_path: ydPath, file_name: selectedFile.value.name,
              file_order: 0, variation: 1
            })
          } catch {}
          try { await ax.post(`/api/v1/files/scan/${props.contractId}`) } catch {}
        }
      }
    }

    // Обновляем CRM карточку (surveyor_id + survey_date)
    if (props.cardId) {
      await crmApi.updateCard(props.cardId, {
        surveyor_id: surveyorId.value,
        survey_date: measurementDate.value,
      })

      // Обновляем report_month в оплате замерщика (как десктоп)
      if (surveyorId.value) {
        try {
          const { data: payments } = await crmApi.getPayments(props.cardId)
          const survPayment = (payments || []).find(p =>
            p.employee_id === surveyorId.value && p.role === 'Замерщик' && !p.reassigned
          )
          if (survPayment) {
            const reportMonth = measurementDate.value.slice(0, 7)
            await paymentsApi.update(survPayment.id, { report_month: reportMonth })
          }
        } catch {}
      }

      // ActionHistory (как десктоп)
      try {
        const survName = surveyorOptions.value.find(s => s.id === surveyorId.value)?.label || ''
        await ax.post('/api/v1/action-history', {
          action_type: 'survey_complete',
          entity_type: 'crm_card',
          entity_id: props.cardId,
          description: `Замер выполнен: ${measurementDate.value} | Замерщик: ${survName}`
        })
      } catch {}
    }

    $q.notify({ type: 'positive', message: 'Замер сохранён' })
    emit('saved')
    resetFields()
    close()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения' })
  } finally { saving.value = false }
}
</script>
