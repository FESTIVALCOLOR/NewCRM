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
        <q-item-section avatar>
          <q-skeleton type="circle" size="36px" />
        </q-item-section>
        <q-item-section>
          <q-skeleton type="text" width="60%" />
          <q-skeleton type="text" width="30%" />
        </q-item-section>
      </q-item>
    </div>

    <!-- Содержимое папки -->
    <q-card v-else-if="items.length > 0" class="is-card">
      <q-list separator>
        <!-- Папки -->
        <q-item
          v-for="item in folders"
          :key="item.path"
          v-ripple
          clickable
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
          v-ripple
          clickable
          @click="openFile(item)"
        >
          <q-item-section avatar>
            <q-icon :name="fileIcon(item.name)" :color="fileColor(item.name)" size="28px" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ item.name }}</q-item-label>
            <q-item-label caption>
              {{ formatSize(item.size) }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-icon :name="isImage(item.name, item.media_type) ? 'photo_library' : 'open_in_new'" color="grey-5" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <div v-else class="text-center q-pa-xl text-grey-5">
      <q-icon name="folder_open" size="48px" class="q-mb-sm" />
      <div>Папка пуста</div>
    </div>

    <!-- Галерея превью изображений -->
    <q-dialog v-model="previewVisible" maximized transition-show="fade" transition-hide="fade">
      <div class="column" style="background: rgba(0,0,0,0.95); height: 100dvh; min-height: 100dvh">
        <!-- Шапка -->
        <div class="row items-center q-pa-sm no-wrap">
          <q-btn
            flat
            round
            dense
            icon="close"
            color="white"
            @click="previewVisible = false"
          />
          <div class="col text-center text-white q-px-sm" style="font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
            {{ currentPreviewFile?.name }}
          </div>
          <div class="text-white text-caption" style="min-width: 44px; text-align: right">
            {{ previewIdx + 1 }}/{{ imageFiles.length }}
          </div>
        </div>

        <!-- Изображение -->
        <div
          v-touch-swipe.mouse="handleImageSwipe"
          class="col flex flex-center"
          style="position: relative; overflow: hidden"
        >
          <q-btn
            v-if="previewIdx > 0"
            flat
            round
            icon="chevron_left"
            color="white"
            style="position: absolute; left: 4px; z-index: 2; opacity: 0.8; background: rgba(0,0,0,0.3)"
            @click="prevImage"
          />

          <div class="flex flex-center" style="width: 100%; height: 100%; padding: 8px">
            <q-spinner v-if="currentPreviewState?.loading" color="white" size="48px" />
            <q-icon
              v-else-if="currentPreviewState?.error || !currentPreviewState?.url"
              name="broken_image"
              size="64px"
              color="grey-5"
            />
            <img
              v-else
              :src="currentPreviewState.url"
              style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px"
            >
          </div>

          <q-btn
            v-if="previewIdx < imageFiles.length - 1"
            flat
            round
            icon="chevron_right"
            color="white"
            style="position: absolute; right: 4px; z-index: 2; opacity: 0.8; background: rgba(0,0,0,0.3)"
            @click="nextImage"
          />
        </div>

        <!-- Нижняя панель -->
        <div class="row justify-center q-pa-sm">
          <q-btn
            flat
            no-caps
            icon="open_in_new"
            label="Открыть в браузере"
            color="white"
            size="sm"
            @click="openCurrentInBrowser"
          />
        </div>
      </div>
    </q-dialog>

    <!-- FAB загрузки файла -->
    <q-page-sticky position="bottom-right" :offset="[18, 80]">
      <q-btn fab icon="upload_file" color="primary" @click="triggerUpload">
        <q-tooltip>Загрузить файл</q-tooltip>
      </q-btn>
      <input
        ref="fileInput"
        type="file"
        style="display: none"
        accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.dwg,.zip"
        @change="handleUpload"
      >
    </q-page-sticky>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

const $q = useQuasar()
const currentPath = ref('/CRM')
const items = ref([])
const loading = ref(false)
const fileInput = ref(null)

const folders = computed(() => items.value.filter(i => i.type === 'dir'))
const files = computed(() => items.value.filter(i => i.type === 'file'))

// === Галерея превью ===
const previewVisible = ref(false)
const previewIdx = ref(0)
const imageUrls = ref({})  // path -> { url, loading, error }

const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic']
function isImage(name, mediaType) {
  if (mediaType === 'image') return true
  return IMAGE_EXTS.includes((name || '').split('.').pop()?.toLowerCase() || '')
}

const imageFiles = computed(() => files.value.filter(f => isImage(f.name, f.media_type)))
const currentPreviewFile = computed(() => imageFiles.value[previewIdx.value] || null)
const currentPreviewState = computed(() =>
  currentPreviewFile.value ? (imageUrls.value[currentPreviewFile.value.path] || null) : null,
)

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
    zip: 'folder_zip', rar: 'folder_zip', '7z': 'folder_zip',
  }
  return icons[ext] || 'insert_drive_file'
}

function fileColor(name) {
  const ext = (name || '').split('.').pop()?.toLowerCase()
  const colors = {
    pdf: 'red', jpg: 'green', jpeg: 'green', png: 'green',
    doc: 'blue', docx: 'blue', xls: 'teal', xlsx: 'teal',
    dwg: 'purple', zip: 'orange',
  }
  return colors[ext] || 'grey-7'
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} КБ`
  return `${(bytes / 1048576).toFixed(1)} МБ`
}

async function resolveImageUrl(item) {
  if (!item || imageUrls.value[item.path]) return
  if (item.public_url) {
    imageUrls.value[item.path] = { url: item.public_url, loading: false, error: false }
    return
  }
  imageUrls.value[item.path] = { url: null, loading: true, error: false }
  try {
    const { data } = await filesApi.getPublicLink(item.path)
    imageUrls.value[item.path] = { url: data.public_link || null, loading: false, error: !data.public_link }
  } catch {
    imageUrls.value[item.path] = { url: null, loading: false, error: true }
  }
}

async function openImagePreview(item) {
  const idx = imageFiles.value.findIndex(f => f.path === item.path)
  if (idx < 0) return
  previewIdx.value = idx
  previewVisible.value = true
  resolveImageUrl(imageFiles.value[idx])
  if (imageFiles.value[idx + 1]) resolveImageUrl(imageFiles.value[idx + 1])
  if (imageFiles.value[idx - 1]) resolveImageUrl(imageFiles.value[idx - 1])
}

watch(previewIdx, (idx) => {
  const imgs = imageFiles.value
  if (imgs[idx]) resolveImageUrl(imgs[idx])
  if (imgs[idx + 1]) resolveImageUrl(imgs[idx + 1])
  if (imgs[idx - 1]) resolveImageUrl(imgs[idx - 1])
})

function prevImage() { if (previewIdx.value > 0) previewIdx.value-- }
function nextImage() { if (previewIdx.value < imageFiles.value.length - 1) previewIdx.value++ }
function handleImageSwipe({ direction }) {
  if (direction === 'right') prevImage()
  else if (direction === 'left') nextImage()
}
function openCurrentInBrowser() {
  const url = currentPreviewState.value?.url
  if (url) window.open(url, '_blank')
}

async function navigateTo(path) {
  currentPath.value = path
  imageUrls.value = {}
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
  // Изображения — открываем в галерее
  if (isImage(item.name, item.media_type)) {
    await openImagePreview(item)
    return
  }
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
