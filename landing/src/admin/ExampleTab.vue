<template>
  <section class="tab-body">
    <div class="card-info">
      Блок «Посмотреть пример проекта» на главной — после «Услуг». Посетитель нажимает кнопку, и под ней открывается дизайн-проект, который листается как книга.
      Загрузите PDF проекта: страницы один раз подготовятся на сервере, и на сайте они подгружаются по мере листания. Пока файл не загружен, блок на сайте не показывается.
    </div>

    <div class="card">
      <h3>PDF проекта</h3>
      <div v-if="project" class="ex-current">
        <div class="ex-thumbs">
          <img v-for="(url, i) in project.pages.slice(0, 6)" :key="url" :src="url" :alt="`Страница ${i + 1}`" loading="lazy" />
        </div>
        <p class="hint" style="margin:10px 0 0">
          <strong>{{ project.name }}</strong> — {{ project.pages.length }} стр., загружен {{ formatDate(project.uploaded_at) }} ·
          <a :href="project.pdf" target="_blank" rel="noopener">Открыть PDF</a>
        </p>
      </div>
      <div v-else-if="!busy" class="empty-state" style="padding:28px">Пример ещё не загружен</div>

      <div v-if="busy" class="ex-progress">
        <div class="ex-progress__bar"><span :style="{ width: progressPercent + '%' }" /></div>
        <p class="hint" style="margin:6px 0 0">{{ progressText }}</p>
      </div>
      <p v-if="job && job.status === 'error'" class="alert-err" style="margin-top:12px">{{ job.error }}</p>

      <div class="list-toolbar" style="margin-top:14px">
        <button class="btn-primary" :disabled="busy" @click="$refs.pdfInput.click()">{{ project ? 'Заменить PDF' : 'Загрузить PDF' }}</button>
        <button v-if="project && !busy" class="btn-sm btn-danger" @click="remove">Убрать пример с сайта</button>
        <input ref="pdfInput" type="file" accept="application/pdf,.pdf" style="display:none" @change="upload" />
      </div>
      <p class="hint" style="margin:10px 0 0">PDF до 200 МБ и до 150 страниц. Большой файл с чертежами готовится несколько минут — страницу панели можно не держать открытой. Пока новый файл готовится, на сайте остаётся прежний пример.</p>
    </div>

    <div class="card">
      <h3>Тексты блока</h3>
      <label>Заголовок<input v-model="form.example_title" placeholder="ПОСМОТРЕТЬ ПРИМЕР ПРОЕКТА" /></label>
      <label style="margin-top:12px">Текст под заголовком
        <textarea v-model="form.example_text" rows="3" placeholder="Так выглядит дизайн-проект, который вы получите: планировочные решения, визуализации и рабочие чертежи. Листайте страницы, как в настоящем альбоме."></textarea>
      </label>
      <label style="margin-top:12px">Надпись на кнопке<input v-model="form.example_button" placeholder="Посмотреть пример проекта" /></label>
      <button class="btn-primary" style="margin-top:16px" @click="saveTexts">Сохранить тексты</button>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as api from './api.js'

const props = defineProps({ toast: { type: Function, required: true } })

const project = ref(null)
const job = ref(null)
const uploadPercent = ref(null)
const form = reactive({ example_title: '', example_text: '', example_button: '' })
let pollTimer = null

const processing = computed(() => job.value?.status === 'processing')
const busy = computed(() => uploadPercent.value !== null || processing.value)
const progressPercent = computed(() => {
  if (uploadPercent.value !== null) return Math.round(uploadPercent.value * 0.3)
  if (processing.value && job.value.total) return 30 + Math.round((job.value.done / job.value.total) * 70)
  return 0
})
const progressText = computed(() => {
  if (uploadPercent.value !== null) return `Отправка файла: ${uploadPercent.value}%`
  if (processing.value) return `Подготовка страниц: ${job.value.done} из ${job.value.total}`
  return ''
})

function formatDate(value) {
  try { return new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) } catch { return '' }
}

async function load() {
  try {
    const result = await api.example.get()
    project.value = result.project
    job.value = result.job
    clearTimeout(pollTimer)
    // Пока страницы готовятся, состояние обновляется само
    if (processing.value) pollTimer = setTimeout(load, 2000)
    else if (job.value?.status === 'done' && wasProcessing) props.toast('Пример проекта готов и показан на сайте')
    wasProcessing = processing.value
  } catch (e) { if (e.message !== '401') props.toast('Не удалось загрузить данные: ' + e.message, 'error') }
}
let wasProcessing = false

async function loadTexts() {
  try {
    const rows = await api.settings.list()
    rows.forEach(row => { if (row.key in form) form[row.key] = row.value || '' })
  } catch { /* тексты необязательны */ }
}

async function upload(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') { props.toast('Нужен файл PDF', 'error'); return }
  if (file.size > 200 * 1024 * 1024) { props.toast('Файл больше 200 МБ', 'error'); return }
  uploadPercent.value = 0
  try {
    const result = await api.example.upload(file, (percent) => { uploadPercent.value = percent })
    uploadPercent.value = null
    project.value = result.project
    job.value = result.job
    wasProcessing = true
    load()
  } catch (err) {
    uploadPercent.value = null
    props.toast(err.message, 'error')
  }
}

async function remove() {
  if (!confirm('Убрать пример проекта с сайта? Файл и подготовленные страницы будут удалены.')) return
  try { await api.example.delete(); project.value = null; job.value = null; props.toast('Пример убран с сайта') }
  catch (e) { props.toast(e.message, 'error') }
}

async function saveTexts() {
  try {
    for (const key of Object.keys(form)) await api.settings.update(key, form[key].trim())
    props.toast('Тексты сохранены')
  } catch (e) { props.toast(e.message, 'error') }
}

onMounted(() => { load(); loadTexts() })
onBeforeUnmount(() => clearTimeout(pollTimer))
</script>

<style scoped>
.ex-thumbs { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.ex-thumbs img { height: 110px; width: auto; border-radius: 4px; border: 1px solid #e8eaed; flex-shrink: 0; }
.ex-progress { margin-top: 12px; }
.ex-progress__bar { height: 8px; border-radius: 4px; background: #f0f1f3; overflow: hidden; }
.ex-progress__bar span { display: block; height: 100%; background: #c0392b; transition: width 0.4s; }
</style>
