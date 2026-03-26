<template>
  <q-dialog v-model="show" persistent>
    <q-card style="min-width: 340px; max-width: 500px; border-radius: 10px">
      <q-toolbar style="background: #F39C12; color: white">
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Добавить замер</q-toolbar-title>
        <q-btn flat round dense icon="close" color="white" @click="close" />
      </q-toolbar>

      <q-card-section>
        <!-- Режим загрузки -->
        <q-option-group v-model="uploadMode" :options="[
          { label: 'Загрузить файл', value: 'file' },
          { label: 'По ссылке от замерщика', value: 'link' }
        ]" inline dense class="q-mb-md" />

        <!-- Замерщик -->
        <q-select v-model="surveyorId" :options="surveyorOptions" option-value="id" option-label="label"
          label="Замерщик" outlined dense emit-value map-options class="q-mb-sm" />

        <!-- Дата замера -->
        <q-input v-model="measurementDate" label="Дата замера" outlined dense type="date" class="q-mb-sm" />

        <!-- Режим: Загрузить файл -->
        <template v-if="uploadMode === 'file'">
          <q-btn outline color="grey-7" icon="photo_camera" label="Выбрать файл" no-caps class="full-width q-mb-sm" @click="fileInput?.click()" />
          <div v-if="selectedFile" class="text-caption q-mb-sm" style="color: #333">{{ selectedFile.name }}</div>
          <input ref="fileInput" type="file" accept="image/*,.pdf" style="display: none" @change="onFileSelected" />
        </template>

        <!-- Режим: По ссылке -->
        <template v-if="uploadMode === 'link'">
          <q-input v-model="publicLink" label="Публичная ссылка (Яндекс.Диск / Google Drive)" outlined dense class="q-mb-sm" placeholder="https://disk.yandex.ru/d/..." />
        </template>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="Отмена" no-caps v-close-popup />
        <q-btn unelevated label="Сохранить" no-caps style="background: #F39C12; color: white; border-radius: 4px"
          :loading="saving" @click="save" :disable="!canSave" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
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
const uploadMode = ref('file')
const surveyorId = ref(null)
const measurementDate = ref(new Date().toISOString().slice(0, 10))
const selectedFile = ref(null)
const publicLink = ref('')
const fileInput = ref(null)
const surveyorOptions = ref([])

watch(() => props.modelValue, v => { show.value = v; if (v) loadSurveyors() })
watch(show, v => emit('update:modelValue', v))

const canSave = computed(() => {
  if (!surveyorId.value || !measurementDate.value) return false
  if (uploadMode.value === 'file' && !selectedFile.value) return false
  if (uploadMode.value === 'link' && !publicLink.value) return false
  return true
})

function close() { show.value = false }

function onFileSelected(e) {
  selectedFile.value = e.target.files?.[0] || null
}

async function loadSurveyors() {
  try {
    const { data } = await employeesApi.getList()
    surveyorOptions.value = (data || [])
      .filter(e => e.status === 'активный' && (e.position === 'Замерщик' || e.secondary_position === 'Замерщик'))
      .map(e => ({ id: e.id, label: e.full_name }))
  } catch {}
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    let measurementLink = ''
    let measurementPath = ''
    let measurementFileName = ''

    if (uploadMode.value === 'file' && selectedFile.value) {
      // Загружаем файл на ЯД в папку Замер
      const contractFolder = props.contractData?.yandex_folder_path?.replace(/^disk:/, '') || ''
      if (contractFolder) {
        const ydPath = `${contractFolder}/Замер/${selectedFile.value.name}`
        const uploadRes = await filesApi.upload(selectedFile.value, ydPath)
        measurementLink = uploadRes.data?.public_link || ''
        measurementPath = ydPath
        measurementFileName = selectedFile.value.name
      }
    } else if (uploadMode.value === 'link') {
      measurementLink = publicLink.value
    }

    // Обновляем договор
    if (props.contractId) {
      const contractUpdate = {
        measurement_image_link: measurementLink,
        measurement_yandex_path: measurementPath,
        measurement_file_name: measurementFileName,
      }
      await contractsApi.update(props.contractId, contractUpdate)
    }

    // Обновляем CRM карточку
    if (props.cardId) {
      await crmApi.updateCard(props.cardId, {
        surveyor_id: surveyorId.value,
        survey_date: measurementDate.value,
      })

      // Обновляем report_month в оплате замерщика (как десктоп MeasurementDialog.save)
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

    $q.notify({ type: 'positive', message: 'Замер загружен' })
    emit('saved')
    close()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка загрузки замера' })
  } finally {
    saving.value = false
  }
}
</script>
