<template>
  <q-dialog v-model="show" persistent>
    <q-card style="min-width: 340px; max-width: 500px; width: 100%; border-radius: 10px">
      <q-toolbar style="background: #9B59B6; color: white">
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
          Добавить ТЗ
        </q-toolbar-title>
        <q-btn
          flat
          round
          dense
          icon="close"
          color="white"
          @click="close"
        />
      </q-toolbar>

      <q-card-section>
        <!-- Файл ТЗ -->
        <div class="text-caption text-weight-bold q-mb-xs">
          Файл ТЗ:
        </div>
        <div v-if="selectedFile" class="q-mb-sm" style="background: #F8F9FA; border: 1px solid #E0E0E0; padding: 6px 10px; border-radius: 4px; font-size: 12px">
          {{ selectedFile.name.length > 25 ? selectedFile.name.slice(0, 12) + '...' + selectedFile.name.slice(-10) : selectedFile.name }}
        </div>
        <q-btn
          outline
          color="grey-7"
          icon="upload"
          label="Выбрать файл"
          no-caps
          dense
          style="height: 28px"
          class="q-mb-md"
          @click="fileInput?.click()"
        />
        <input
          ref="fileInput"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.heic,.doc,.docx,.mp4,.mov,.avi,.mkv"
          style="display: none"
          @change="onFileSelected"
        >

        <q-separator class="q-my-sm" />

        <!-- Дата ТЗ -->
        <q-input
          v-model="techTaskDate"
          label="Дата ТЗ"
          outlined
          dense
          type="date"
          class="q-mb-sm"
        />
      </q-card-section>

      <q-card-actions align="right">
        <q-btn v-close-popup flat label="Отмена" no-caps />
        <q-btn
          unelevated
          label="Сохранить"
          no-caps
          style="background: #9B59B6; color: white; border-radius: 4px"
          :loading="saving"
          :disable="!selectedFile"
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { filesApi, contractsApi, crmApi } from 'src/services/api'

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
const selectedFile = ref(null)
const fileInput = ref(null)
const techTaskDate = ref(new Date().toISOString().slice(0, 10))

watch(() => props.modelValue, v => { show.value = v; if (v) { selectedFile.value = null } })
watch(show, v => emit('update:modelValue', v))

function close() { show.value = false }
function onFileSelected(e) { selectedFile.value = e.target.files?.[0] || null }

async function save() {
  if (!selectedFile.value) return
  saving.value = true
  try {
    const { api: ax } = await import('src/boot/axios')
    const contractFolder = (props.contractData?.yandex_folder_path || '').replace(/^disk:/, '')

    if (contractFolder) {
      // Загружаем файл в папку Анкета (как десктоп)
      const ankFolder = `${contractFolder}/Анкета`
      const ydPath = `${ankFolder}/${selectedFile.value.name}`
      await filesApi.upload(selectedFile.value, ydPath)

      // Получаем публичную ссылку на папку
      let folderLink = ''
      try {
        const { data: fl } = await filesApi.getPublicLink(ankFolder)
        folderLink = fl.public_link || ''
      } catch {}

      // Обновляем contracts
      if (props.contractId) {
        await contractsApi.update(props.contractId, {
          tech_task_link: folderLink,
          tech_task_yandex_path: ankFolder,
          tech_task_file_name: selectedFile.value.name,
        })
        // Создаём запись в project_files + scan
        try {
          await ax.post('/api/v1/files/', {
            contract_id: props.contractId, stage: 'tech_task',
            file_type: selectedFile.value.type?.includes('image') ? 'image' : 'pdf',
            public_link: folderLink, yandex_path: ydPath, file_name: selectedFile.value.name,
            file_order: 0, variation: 1,
          })
        } catch {}
        try { await ax.post(`/api/v1/files/scan/${props.contractId}`) } catch {}
      }
    }

    // Обновляем crm_cards (tech_task_date + tech_task_file)
    if (props.cardId) {
      await crmApi.updateCard(props.cardId, {
        tech_task_date: techTaskDate.value,
        tech_task_file: selectedFile.value.name,
      })

      // ActionHistory
      try {
        const { api: ax2 } = await import('src/boot/axios')
        await ax2.post('/api/v1/action-history', {
          action_type: 'tech_task_date_changed',
          entity_type: 'crm_card',
          entity_id: props.cardId,
          description: `ТЗ загружено: ${techTaskDate.value} | ${selectedFile.value.name}`,
        })
      } catch {}
    }

    $q.notify({ type: 'positive', message: 'ТЗ загружено' })
    emit('saved')
    close()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения' })
  } finally { saving.value = false }
}
</script>
