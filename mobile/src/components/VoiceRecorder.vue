<template>
  <!-- Голосовая заметка — запись через MediaRecorder API -->
  <div class="voice-recorder">
    <!-- Кнопка записи -->
    <q-btn
      v-if="!isRecording && !audioBlob"
      round
      :icon="'mic'"
      color="grey-7"
      size="sm"
      @click="startRecording"
    >
      <q-tooltip>Голосовая заметка</q-tooltip>
    </q-btn>

    <!-- Индикатор записи: пульсирующий круг + таймер -->
    <div v-if="isRecording" class="row items-center q-gutter-sm">
      <div class="recording-pulse" />
      <span class="text-caption text-weight-medium" style="color: #E74C3C; min-width: 36px">{{ formattedTime }}</span>
      <q-btn round icon="stop" color="negative" size="sm" @click="stopRecording">
        <q-tooltip>Остановить</q-tooltip>
      </q-btn>
    </div>

    <!-- Превью записанного аудио -->
    <div v-if="audioBlob && !isRecording" class="row items-center q-gutter-sm" style="flex-wrap: nowrap">
      <audio ref="audioPlayer" :src="audioUrl" controls style="height: 32px; max-width: 180px" />
      <q-btn round icon="send" color="positive" size="sm" @click="uploadAndSend" :loading="uploading">
        <q-tooltip>Отправить</q-tooltip>
      </q-btn>
      <q-btn round icon="delete" color="negative" size="sm" @click="discardRecording">
        <q-tooltip>Удалить</q-tooltip>
      </q-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

const props = defineProps({
  /** Путь к папке на Яндекс.Диске (без disk: префикса) для загрузки заметок */
  yandexFolderPath: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['recorded'])

const $q = useQuasar()

const isRecording = ref(false)
const audioBlob = ref(null)
const audioUrl = ref(null)
const uploading = ref(false)
const seconds = ref(0)

let mediaRecorder = null
let audioChunks = []
let timerInterval = null

/** Форматирование таймера "0:05" */
const formattedTime = computed(() => {
  const m = Math.floor(seconds.value / 60)
  const s = seconds.value % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

/** Начать запись */
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

    // Определяем поддерживаемый формат
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : ''

    mediaRecorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream)

    audioChunks = []

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' })
      audioBlob.value = blob
      audioUrl.value = URL.createObjectURL(blob)
      // Останавливаем все треки микрофона
      stream.getTracks().forEach(track => track.stop())
    }

    mediaRecorder.start()
    isRecording.value = true
    seconds.value = 0
    timerInterval = setInterval(() => { seconds.value++ }, 1000)
  } catch (err) {
    console.error('Ошибка доступа к микрофону:', err)
    $q.notify({ type: 'negative', message: 'Нет доступа к микрофону. Разрешите доступ в настройках браузера.' })
  }
}

/** Остановить запись */
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  clearInterval(timerInterval)
  timerInterval = null
}

/** Загрузить на ЯД и отправить emit */
async function uploadAndSend() {
  if (!audioBlob.value) return

  uploading.value = true
  try {
    // Формируем имя файла: дата_время.webm
    const now = new Date()
    const dateStr = now.toISOString().slice(0, 10) // 2026-03-27
    const timeStr = now.toTimeString().slice(0, 8).replace(/:/g, '-') // 14-30-05
    const fileName = `${dateStr}_${timeStr}.webm`

    // Путь загрузки: {yandex_folder_path}/Заметки/{файл}
    const basePath = (props.yandexFolderPath || '').replace(/^disk:/, '').replace(/\/$/, '')
    const uploadPath = basePath
      ? `${basePath}/Заметки/${fileName}`
      : `/CRM/Заметки/${fileName}`

    // Создаём File из Blob
    const file = new File([audioBlob.value], fileName, { type: audioBlob.value.type })

    // Загружаем на Яндекс.Диск
    const response = await filesApi.upload(file, uploadPath)
    const uploadedUrl = response.data?.public_url || response.data?.url || uploadPath

    const duration = seconds.value

    emit('recorded', {
      url: uploadedUrl,
      duration,
      fileName,
      path: uploadPath
    })

    $q.notify({ type: 'positive', message: 'Голосовая заметка загружена' })
    discardRecording()
  } catch (err) {
    console.error('Ошибка загрузки голосовой заметки:', err)
    $q.notify({ type: 'negative', message: 'Ошибка загрузки: ' + (err.response?.data?.detail || err.message) })
  } finally {
    uploading.value = false
  }
}

/** Удалить запись без отправки */
function discardRecording() {
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
  audioBlob.value = null
  audioUrl.value = null
  seconds.value = 0
}

onBeforeUnmount(() => {
  // Останавливаем запись при уходе со страницы
  if (isRecording.value) stopRecording()
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  clearInterval(timerInterval)
})
</script>

<style scoped>
.voice-recorder {
  display: inline-flex;
  align-items: center;
}

/* Пульсирующий красный круг — индикатор записи */
.recording-pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #E74C3C;
  animation: pulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}
</style>
