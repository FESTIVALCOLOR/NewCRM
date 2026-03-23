<template>
  <q-page padding>
    <!-- Путь (breadcrumbs) -->
    <div class="row items-center q-mb-md q-gutter-xs">
      <q-btn
        flat
        dense
        icon="home"
        size="sm"
        color="primary"
        @click="navigateTo('/CRM')"
      />
      <template v-for="(part, idx) in breadcrumbs" :key="idx">
        <q-icon name="chevron_right" size="16px" color="grey-5" />
        <q-btn
          flat
          dense
          :label="part.name"
          size="sm"
          no-caps
          :color="idx === breadcrumbs.length - 1 ? 'dark' : 'primary'"
          @click="navigateTo(part.path)"
        />
      </template>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="q-pa-md">
      <q-item v-for="n in 6" :key="n">
        <q-item-section avatar><q-skeleton type="circle" size="36px" /></q-item-section>
        <q-item-section>
          <q-skeleton type="text" width="60%" />
          <q-skeleton type="text" width="30%" />
        </q-item-section>
      </q-item>
    </div>

    <!-- Содержимое папки -->
    <q-card class="is-card" v-else-if="items.length > 0">
      <q-list separator>
        <!-- Папки -->
        <q-item
          v-for="item in folders"
          :key="item.path"
          clickable
          v-ripple
          @click="navigateTo(item.path)"
        >
          <q-item-section avatar>
            <q-icon name="folder" color="amber-7" size="28px" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ item.name }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-5" />
          </q-item-section>
        </q-item>

        <!-- Файлы -->
        <q-item
          v-for="item in files"
          :key="item.path"
          clickable
          v-ripple
          @click="openFile(item)"
        >
          <q-item-section avatar>
            <q-icon :name="fileIcon(item.name)" :color="fileColor(item.name)" size="28px" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ item.name }}</q-item-label>
            <q-item-label caption>{{ formatSize(item.size) }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon name="open_in_new" color="grey-5" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="folder_open" size="48px" class="q-mb-sm" />
      <div>Папка пуста</div>
    </div>

    <!-- FAB загрузки файла -->
    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab icon="upload_file" color="primary" @click="triggerUpload">
        <q-tooltip>Загрузить файл</q-tooltip>
      </q-btn>
      <input
        ref="fileInput"
        type="file"
        style="display: none"
        @change="handleUpload"
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.dwg,.zip"
      />
    </q-page-sticky>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

const $q = useQuasar()
const currentPath = ref('/CRM')
const items = ref([])
const loading = ref(false)
const fileInput = ref(null)

const folders = computed(() => items.value.filter(i => i.type === 'dir'))
const files = computed(() => items.value.filter(i => i.type === 'file'))

const breadcrumbs = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  const crumbs = []
  let path = ''
  for (const part of parts) {
    path += '/' + part
    crumbs.push({ name: part, path })
  }
  return crumbs
})

function fileIcon(name) {
  const ext = (name || '').split('.').pop()?.toLowerCase()
  const icons = {
    pdf: 'picture_as_pdf', jpg: 'image', jpeg: 'image', png: 'image', gif: 'image',
    doc: 'article', docx: 'article', xls: 'table_chart', xlsx: 'table_chart',
    dwg: 'architecture', dxf: 'architecture', skp: 'view_in_ar',
    zip: 'folder_zip', rar: 'folder_zip', '7z': 'folder_zip'
  }
  return icons[ext] || 'insert_drive_file'
}

function fileColor(name) {
  const ext = (name || '').split('.').pop()?.toLowerCase()
  const colors = {
    pdf: 'red', jpg: 'green', jpeg: 'green', png: 'green',
    doc: 'blue', docx: 'blue', xls: 'teal', xlsx: 'teal',
    dwg: 'purple', zip: 'orange'
  }
  return colors[ext] || 'grey-7'
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / 1048576).toFixed(1)} МБ`
}

async function navigateTo(path) {
  currentPath.value = path
  await loadFolder()
}

async function loadFolder() {
  loading.value = true
  try {
    const { data } = await filesApi.listFolder(currentPath.value)
    items.value = data.files || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function openFile(item) {
  if (item.public_url) {
    window.open(item.public_url, '_blank')
    return
  }
  // Получить публичную ссылку
  try {
    $q.loading.show({ message: 'Получаю ссылку...' })
    const { data } = await filesApi.getPublicLink(item.path)
    if (data.public_link) window.open(data.public_link, '_blank')
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось получить ссылку' })
  } finally {
    $q.loading.hide()
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  const yandexPath = `${currentPath.value}/${file.name}`
  try {
    $q.loading.show({ message: 'Загрузка...' })
    await filesApi.upload(file, yandexPath)
    $q.notify({ type: 'positive', message: 'Файл загружен' })
    await loadFolder()
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки' })
  } finally {
    $q.loading.hide()
    event.target.value = ''
  }
}

onMounted(() => loadFolder())
</script>
