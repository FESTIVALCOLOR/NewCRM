<template>
  <section class="tab-body">
    <div class="card-info">
      Страница «Готовый дизайн» — каталог готовых решений. У каждого дизайна своё название, описание и галерея; на фото можно отметить мебель и предметы.
      Цена и срок считаются на сайте по городу и площади, которые выбирает посетитель. Кнопка «Заказать» отправляет заявку выбранным в «Настройках» способом связи — с названием дизайна, городом, площадью и ценой.
    </div>

    <!-- ── Каталог ── -->
    <div class="card">
      <h3>Каталог дизайнов</h3>
      <div class="list-toolbar" style="margin-bottom:14px">
        <button class="btn-primary" @click="openDesign(null)">+ Добавить дизайн</button>
        <span class="hint" style="margin:0">Порядок в каталоге меняется перетаскиванием.</span>
      </div>
      <div v-if="!designs.length" class="empty-state">Дизайнов пока нет — нажмите «Добавить дизайн»</div>
      <div class="rd-list">
        <div v-for="(design, index) in designs" :key="design.id" class="rd-item" :class="{ muted: !design.is_visible }"
          draggable="true" @dragstart="dragStart($event, index, 'designs')" @dragover.prevent @drop.prevent="dropOn(index, 'designs')">
          <div class="rd-item__cover"><img v-if="coverOf(design)" :src="coverOf(design)" alt="" /></div>
          <div class="rd-item__body">
            <strong>{{ design.title }}</strong>
            <span>{{ design.images.length }} фото · {{ markerCount(design) }} отметок</span>
          </div>
          <label class="toggle" title="Показывать в каталоге">
            <input type="checkbox" :checked="design.is_visible" @change="toggleDesign(design, $event.target.checked)" />
            <span class="toggle-track"></span>
          </label>
          <button class="btn-sm" @click="openDesign(design)">✏ Изменить</button>
          <button class="btn-sm btn-danger" @click="removeDesign(design)">✕</button>
        </div>
      </div>
    </div>

    <!-- ── Цены и сроки ── -->
    <div class="card">
      <h3>Цены и сроки</h3>
      <p class="hint">Базовая цена зависит от города. Если площадь объекта больше базовой, за каждый начатый шаг площади добавляется доплата и дни к сроку: при настройках по умолчанию 91–140 м² — один шаг, 141–190 м² — два.</p>
      <div class="form-grid rd-prices">
        <label v-for="field in priceFields" :key="field.key">{{ field.label }}
          <input v-model="form[field.key]" type="number" min="1" :placeholder="String(READY_DEFAULTS[field.key])" />
        </label>
      </div>
      <p class="hint">Пример для проверки: Москва, 120 м² — <strong>{{ formatPrice(example.price) }}</strong>, {{ formatDays(example.days) }}.</p>
      <label>Города для списка «Другой город» — по одному в строке
        <textarea v-model="form.ready_region_cities" rows="6" placeholder="Пусто — стандартный список региональных центров России"></textarea>
      </label>
      <div class="list-toolbar" style="margin:10px 0 16px">
        <button class="btn-sm" @click="form.ready_region_cities = DEFAULT_REGION_CITIES.join('\n')">Вставить стандартный список ({{ DEFAULT_REGION_CITIES.length }})</button>
        <span class="hint" style="margin:0">Москва и Санкт-Петербург выбираются отдельными кнопками — в список их добавлять не нужно.</span>
      </div>
      <button class="btn-primary" @click="saveSettings">Сохранить цены и сроки</button>
    </div>

    <!-- ── Тексты ── -->
    <div class="card">
      <h3>Тексты страницы и карточки на главной</h3>
      <div class="form-grid">
        <label>Заголовок страницы<input v-model="form.ready_title" placeholder="ГОТОВЫЙ ДИЗАЙН" /></label>
        <label>Заголовок блока направлений на главной<input v-model="form.directions_title" placeholder="ВЫБЕРИТЕ СВОЙ ФОРМАТ" /></label>
      </div>
      <label>Подзаголовок страницы<input v-model="form.ready_subtitle" placeholder="Выберите готовое решение из каталога — мы адаптируем его под планировку вашей квартиры." /></label>
      <label style="margin-top:12px">Текст карточки «Готовый дизайн» на главной<input v-model="form.ready_card_text" placeholder="Выберите готовое решение из каталога — мы адаптируем его под вашу квартиру." /></label>
      <label style="margin-top:12px">Фото карточки на главной (пусто — обложка первого дизайна)
        <div class="upload-row">
          <input v-model="form.ready_cover_url" placeholder="https://... или загрузите" />
          <button class="btn-sm" @click.prevent="$refs.cardCoverInput.click()">Загрузить</button>
          <input ref="cardCoverInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="uploadTo($event, url => form.ready_cover_url = url)" />
        </div>
      </label>
      <button class="btn-primary" style="margin-top:16px" @click="saveSettings">Сохранить тексты</button>
    </div>

    <!-- ── Редактор дизайна ── -->
    <div v-if="editing" class="modal-overlay" @click.self="closeDesign">
      <div class="modal modal--wide">
        <h3>{{ editing.id ? 'Дизайн: ' + (editing.title || 'без названия') : 'Новый дизайн' }}</h3>
        <div class="form-grid">
          <label>Название<input v-model="editing.title" maxlength="200" placeholder="Скандинавская двушка" /></label>
          <label>Короткая подпись для карточки каталога<input v-model="editing.tagline" maxlength="300" placeholder="Светлый интерьер для семьи с ребёнком" /></label>
        </div>
        <label>Описание
          <textarea v-model="editing.description" rows="5" maxlength="5000" placeholder="Что входит в дизайн, для каких квартир подходит, стиль и материалы"></textarea>
        </label>
        <div class="modal-footer" style="justify-content:flex-start">
          <button class="btn-primary" @click="saveDesign">{{ editing.id ? 'Сохранить описание' : 'Создать и перейти к фото' }}</button>
        </div>

        <template v-if="editing.id">
          <h3 style="margin-top:8px">Галерея</h3>
          <div class="list-toolbar">
            <button class="btn-primary" @click="$refs.imagesInput.click()">+ Загрузить фото</button>
            <span v-if="uploading" class="upload-progress">Загрузка {{ uploadDone }}/{{ uploadTotal }}…</span>
            <input ref="imagesInput" type="file" accept="image/jpeg,image/png,image/webp" multiple style="display:none" @change="uploadImages" />
            <span class="hint" style="margin:0">JPEG, PNG или WebP до 10 МБ. Порядок меняется перетаскиванием. Обложка каталога — отмеченное фото, иначе первое.</span>
          </div>
          <div v-if="!editing.images.length" class="empty-state" style="padding:28px">Фото ещё не загружены</div>
          <div class="rd-images">
            <div v-for="(image, index) in editing.images" :key="image.id" class="rd-image" :class="{ cover: editing.cover_url === image.url }"
              draggable="true" @dragstart="dragStart($event, index, 'images')" @dragover.prevent @drop.prevent="dropOn(index, 'images')">
              <img :src="image.url" alt="" />
              <span v-if="editing.cover_url === image.url" class="rd-image__badge">Обложка</span>
              <div class="rd-image__actions">
                <button class="btn-sm" @click="openMarkers(image)">📍 Отметки ({{ image.markers.length }})</button>
                <button class="btn-sm" @click="setCover(image)">{{ editing.cover_url === image.url ? 'Снять обложку' : 'Обложка' }}</button>
                <button class="btn-sm btn-danger" @click="removeImage(image)">✕</button>
              </div>
            </div>
          </div>
        </template>
        <div class="modal-footer">
          <button class="btn-ghost" @click="closeDesign">Закрыть</button>
        </div>
      </div>
    </div>

    <!-- ── Редактор отметок ── -->
    <div v-if="marking" class="modal-overlay" style="z-index:1100">
      <div class="modal modal--wide">
        <h3>Отметки мебели на фото</h3>
        <p class="hint" style="margin:0">Нажмите на предмет на фото, чтобы поставить отметку, затем впишите название. Отметку можно перетащить. Вставьте ссылку на товар и нажмите «Заполнить по ссылке» — панель сама найдёт на странице магазина фото, артикул, описание, цвет, форму и размеры; найденное можно поправить. На сайте посетитель видит номер на фото и карточку товара при наведении или касании.</p>
        <div class="mk">
          <div class="mk__stage">
            <div class="mk__photo" ref="photoEl" @click="addMarker" @pointermove="dragMove" @pointerup="dragEnd" @pointerleave="dragEnd">
              <img :src="marking.url" alt="" draggable="false" />
              <button v-for="(marker, index) in marking.markers" :key="index" type="button" class="mk__dot" :class="{ active: selected === index }"
                :style="{ left: marker.x + '%', top: marker.y + '%' }" @click.stop="selected = index" @pointerdown.stop.prevent="dragBegin(index)">{{ index + 1 }}</button>
            </div>
          </div>
          <div class="mk__list">
            <div v-if="!marking.markers.length" class="hint">Отметок пока нет</div>
            <div v-for="(marker, index) in marking.markers" :key="index" class="mk__row" :class="{ active: selected === index }" @click="selected = index">
              <div class="mk__row-head">
                <span class="mk__num">{{ index + 1 }}</span>
                <input v-model="marker.title" :ref="el => setTitleRef(el, index)" maxlength="120" placeholder="Название: диван, торшер…" />
                <button class="btn-sm btn-danger" title="Удалить отметку" @click.stop="removeMarker(index)">✕</button>
              </div>
              <template v-if="selected === index">
                <div class="mk__link">
                  <input v-model="marker.url" maxlength="500" placeholder="Ссылка на товар в магазине, https://…" @keyup.enter="fillFromLink(marker)" />
                  <button class="btn-sm" :disabled="fetching || !marker.url" title="Найти на странице магазина фото, артикул, описание, цвет, форму и размеры" @click.stop="fillFromLink(marker)">{{ fetching ? 'Загрузка…' : 'Заполнить по ссылке' }}</button>
                </div>
                <div class="mk__product">
                  <div class="mk__pic" :class="{ empty: !marker.image_url }" title="Фото товара" @click.stop="pickPhoto(marker)">
                    <img v-if="marker.image_url" :src="marker.image_url" alt="" />
                    <span v-else>+ фото</span>
                  </div>
                  <div class="mk__fields">
                    <input v-model="marker.sku" maxlength="100" placeholder="Артикул" />
                    <input v-model="marker.color" maxlength="120" placeholder="Цвет" />
                    <input v-model="marker.shape" maxlength="120" placeholder="Форма" />
                    <input v-model="marker.size" maxlength="200" placeholder="Размеры" />
                  </div>
                </div>
                <div v-if="marker.image_url" class="mk__pic-actions">
                  <button class="btn-sm" @click.stop="pickPhoto(marker)">Заменить фото</button>
                  <button class="btn-sm btn-danger" @click.stop="marker.image_url = ''">Убрать фото</button>
                </div>
                <textarea v-model="marker.description" rows="3" maxlength="500" placeholder="Описание: производитель, модель, материал"></textarea>
              </template>
            </div>
          </div>
        </div>
        <input ref="markerPhotoInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="uploadMarkerPhoto" />
        <div class="modal-footer">
          <button class="btn-ghost" @click="marking = null">Отмена</button>
          <button class="btn-primary" @click="saveMarkers">Сохранить отметки</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import * as api from './api.js'
import { READY_DEFAULTS, DEFAULT_REGION_CITIES, calcReady, formatPrice, formatDays } from '../readyPricing.js'

const props = defineProps({ toast: { type: Function, required: true } })

const MAX_MARKERS = 30
const priceFields = [
  { key: 'ready_price_msk', label: 'Цена — Москва, ₽' },
  { key: 'ready_price_spb', label: 'Цена — Санкт-Петербург, ₽' },
  { key: 'ready_price_region', label: 'Цена — другие города, ₽' },
  { key: 'ready_area_base', label: 'Площадь, входящая в цену, м²' },
  { key: 'ready_area_step', label: 'Шаг площади сверх неё, м²' },
  { key: 'ready_area_step_price', label: 'Доплата за каждый шаг, ₽' },
  { key: 'ready_days_base', label: 'Срок, рабочих дней' },
  { key: 'ready_days_step', label: 'Плюс дней за каждый шаг' },
]
const textKeys = ['ready_region_cities', 'ready_title', 'ready_subtitle', 'ready_card_text', 'ready_cover_url', 'directions_title']

const form = reactive(Object.fromEntries([...priceFields.map(f => [f.key, '']), ...textKeys.map(key => [key, ''])]))
const example = computed(() => calcReady('msk', 120, form))

const designs = ref([])
const editing = ref(null)
const uploading = ref(false)
const uploadDone = ref(0)
const uploadTotal = ref(0)

function coverOf(design) { return design.cover_url || design.images[0]?.url || '' }
function markerCount(design) { return design.images.reduce((sum, image) => sum + image.markers.length, 0) }

async function load() {
  try {
    const [rows, list] = await Promise.all([api.settings.list(), api.ready.list()])
    rows.forEach(row => { if (row.key in form) form[row.key] = row.value || '' })
    designs.value = list
  } catch (e) { if (e.message !== '401') props.toast('Не удалось загрузить данные: ' + e.message, 'error') }
}

async function saveSettings() {
  const bad = priceFields.find(f => form[f.key] !== '' && !(Number(form[f.key]) > 0))
  if (bad) { props.toast(`«${bad.label}»: нужно число больше нуля (или оставьте поле пустым — подставится значение по умолчанию)`, 'error'); return }
  try {
    for (const key of Object.keys(form)) await api.settings.update(key, String(form[key] ?? '').trim())
    props.toast('Сохранено — обновите страницу сайта, чтобы увидеть изменения')
  } catch (e) { props.toast(e.message, 'error') }
}

async function uploadTo(e, setter) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  try { setter((await api.portfolio.upload(file)).url) } catch (err) { props.toast('Ошибка загрузки: ' + err.message, 'error') }
}

// ── Дизайны ──
function openDesign(design) {
  editing.value = design
    ? { ...design, images: design.images.map(image => ({ ...image, markers: image.markers.map(m => ({ ...m })) })) }
    : { id: null, title: '', tagline: '', description: '', cover_url: null, is_visible: true, images: [] }
}
function closeDesign() { editing.value = null }
function replaceDesign(design) {
  const index = designs.value.findIndex(item => item.id === design.id)
  if (index >= 0) designs.value[index] = design
  else designs.value.push(design)
}
async function saveDesign() {
  const data = { title: editing.value.title.trim(), tagline: editing.value.tagline.trim(), description: editing.value.description.trim() }
  if (!data.title) { props.toast('Введите название дизайна', 'error'); return }
  try {
    const saved = editing.value.id ? await api.ready.update(editing.value.id, data) : await api.ready.create(data)
    replaceDesign(saved)
    openDesign(saved)
    props.toast('Сохранено')
  } catch (e) { props.toast(e.message, 'error') }
}
async function toggleDesign(design, visible) {
  try { replaceDesign(await api.ready.update(design.id, { is_visible: visible })) } catch (e) { props.toast(e.message, 'error'); load() }
}
async function removeDesign(design) {
  if (!confirm(`Удалить дизайн «${design.title}» вместе с его фото и отметками?`)) return
  try { await api.ready.delete(design.id); designs.value = designs.value.filter(item => item.id !== design.id); props.toast('Удалено') }
  catch (e) { props.toast(e.message, 'error') }
}

// ── Фото ──
function syncEditing() {
  const design = designs.value.find(item => item.id === editing.value.id)
  if (design) { design.images = editing.value.images.map(image => ({ ...image })); design.cover_url = editing.value.cover_url }
}
async function uploadImages(e) {
  const files = Array.from(e.target.files)
  e.target.value = ''
  if (!files.length) return
  uploading.value = true; uploadTotal.value = files.length; uploadDone.value = 0
  const failed = []
  for (const file of files) {
    try {
      const uploaded = await api.portfolio.upload(file)
      editing.value.images.push(await api.ready.addImage(editing.value.id, { url: uploaded.url, alt: '' }))
      uploadDone.value++
    } catch (err) { failed.push(`${file.name}: ${err.message}`) }
  }
  uploading.value = false
  syncEditing()
  if (failed.length) props.toast(`Загружено ${uploadDone.value} из ${files.length}. Не загружены — ${failed.join('; ')}`, 'error')
  else props.toast(`Загружено ${files.length} фото`)
}
async function setCover(image) {
  const cover = editing.value.cover_url === image.url ? null : image.url
  try {
    await api.ready.update(editing.value.id, { cover_url: cover })
    editing.value.cover_url = cover
    syncEditing()
  } catch (e) { props.toast(e.message, 'error') }
}
async function removeImage(image) {
  const note = image.markers.length ? ` Вместе с ним удалятся отметки (${image.markers.length}).` : ''
  if (!confirm(`Удалить фото из галереи?${note}`)) return
  try {
    await api.ready.deleteImage(image.id)
    editing.value.images = editing.value.images.filter(item => item.id !== image.id)
    if (editing.value.cover_url === image.url) {
      await api.ready.update(editing.value.id, { cover_url: null })
      editing.value.cover_url = null
    }
    syncEditing()
  } catch (e) { props.toast(e.message, 'error') }
}

// ── Перетаскивание: порядок дизайнов и фото ──
let dragFrom = null
let dragList = null
function dragStart(e, index, list) {
  dragFrom = index; dragList = list
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(index))
}
async function dropOn(index, list) {
  const from = dragFrom
  const same = dragList === list
  dragFrom = null; dragList = null
  if (!same || from === null || from === index) return
  const items = list === 'designs' ? designs.value : editing.value.images
  const [moved] = items.splice(from, 1)
  items.splice(index, 0, moved)
  const order = items.map((item, i) => ({ id: item.id, sort_order: i }))
  try {
    if (list === 'designs') await api.ready.reorder(order)
    else { await api.ready.reorderImages(order); syncEditing() }
    props.toast('Порядок сохранён')
  } catch (e) { props.toast('Не удалось сохранить порядок: ' + e.message, 'error'); load() }
}

// ── Отметки ──
const marking = ref(null)
const selected = ref(-1)
const photoEl = ref(null)
const titleRefs = {}
let dragging = -1
let justDragged = false

function setTitleRef(el, index) { if (el) titleRefs[index] = el; else delete titleRefs[index] }
const PRODUCT_FIELDS = ['description', 'url', 'image_url', 'sku', 'color', 'shape', 'size']
const emptyProduct = () => Object.fromEntries(PRODUCT_FIELDS.map(field => [field, '']))
const fetching = ref(false)
const markerPhotoInput = ref(null)
let photoTarget = null

function openMarkers(image) {
  marking.value = { id: image.id, url: image.url, markers: image.markers.map(m => ({ ...emptyProduct(), ...m })) }
  selected.value = -1
}
function pointerPosition(e) {
  const rect = photoEl.value.querySelector('img').getBoundingClientRect()
  const clamp = value => Math.min(100, Math.max(0, Math.round(value * 10) / 10))
  return { x: clamp(((e.clientX - rect.left) / rect.width) * 100), y: clamp(((e.clientY - rect.top) / rect.height) * 100) }
}
function addMarker(e) {
  // Клик, которым закончилось перетаскивание, новой отметки не ставит
  if (justDragged) { justDragged = false; return }
  if (marking.value.markers.length >= MAX_MARKERS) { props.toast(`На одном фото не больше ${MAX_MARKERS} отметок`, 'error'); return }
  marking.value.markers.push({ ...pointerPosition(e), title: '', ...emptyProduct() })
  selected.value = marking.value.markers.length - 1
  nextTick(() => titleRefs[selected.value]?.focus())
}
function removeMarker(index) {
  marking.value.markers.splice(index, 1)
  selected.value = -1
}
function dragBegin(index) { dragging = index; selected.value = index; justDragged = false }
function dragMove(e) {
  if (dragging < 0) return
  Object.assign(marking.value.markers[dragging], pointerPosition(e))
  justDragged = true
}
function dragEnd() {
  dragging = -1
  // Если клика после перетаскивания не последует, признак не должен «съесть» следующий клик
  setTimeout(() => { justDragged = false }, 0)
}
// Данные товара со страницы магазина: заполняются найденные поля, остальные остаются как были
async function fillFromLink(marker) {
  const url = (marker.url || '').trim()
  if (!url || fetching.value) return
  if (!/^https?:\/\//i.test(url)) { props.toast('Ссылка должна начинаться с http:// или https://', 'error'); return }
  fetching.value = true
  try {
    const product = await api.ready.productPreview(url)
    const labels = { title: 'название', image_url: 'фото', sku: 'артикул', description: 'описание', color: 'цвет', shape: 'форма', size: 'размеры' }
    const found = []
    for (const [field, label] of Object.entries(labels)) {
      if (!product[field]) continue
      // Название, вписанное вручную, ссылка не затирает
      if (field === 'title' && marker.title.trim()) continue
      marker[field] = product[field]
      found.push(label)
    }
    const missing = Object.entries(labels).filter(([field]) => field !== 'title' && !product[field]).map(([, label]) => label)
    const tail = missing.length ? ` Не найдено: ${missing.join(', ')} — впишите вручную.` : ''
    if (found.length) props.toast(`Найдено: ${found.join(', ')}.${tail}`)
    else props.toast('На странице ничего не нашлось — заполните поля вручную', 'error')
  } catch (e) { props.toast(e.message, 'error') }
  fetching.value = false
}
function pickPhoto(marker) {
  photoTarget = marker
  markerPhotoInput.value.click()
}
async function uploadMarkerPhoto(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file || !photoTarget) return
  try { photoTarget.image_url = (await api.portfolio.upload(file)).url } catch (err) { props.toast('Ошибка загрузки: ' + err.message, 'error') }
}
async function saveMarkers() {
  const markers = marking.value.markers.map(m => ({
    x: m.x, y: m.y, title: m.title.trim(),
    ...Object.fromEntries(PRODUCT_FIELDS.map(field => [field, (m[field] || '').trim()])),
  }))
  const untitled = markers.findIndex(m => !m.title)
  if (untitled >= 0) { selected.value = untitled; props.toast(`У отметки ${untitled + 1} нет названия`, 'error'); return }
  const badLink = markers.findIndex(m => m.url && !/^https?:\/\//i.test(m.url))
  if (badLink >= 0) { selected.value = badLink; props.toast(`Ссылка у отметки ${badLink + 1} должна начинаться с http:// или https://`, 'error'); return }
  try {
    const saved = await api.ready.updateImage(marking.value.id, { markers })
    const image = editing.value.images.find(item => item.id === saved.id)
    if (image) image.markers = saved.markers
    syncEditing()
    marking.value = null
    props.toast('Отметки сохранены')
  } catch (e) { props.toast(e.message, 'error') }
}

onMounted(load)
</script>

<style scoped>
.rd-prices { grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
.rd-list { display: flex; flex-direction: column; gap: 8px; }
.rd-item { display: flex; align-items: center; gap: 14px; padding: 8px 12px 8px 8px; border: 1px solid #e8eaed; border-radius: 10px; background: #fff; cursor: grab; }
.rd-item.muted { opacity: 0.6; }
.rd-item__cover { flex: 0 0 84px; height: 62px; border-radius: 7px; overflow: hidden; background: #f3f4f6; }
.rd-item__cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rd-item__body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.rd-item__body strong { font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rd-item__body span { font-size: 0.8rem; color: #6b7280; }

.rd-images { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.rd-image { position: relative; border-radius: 8px; overflow: hidden; background: #f3f4f6; border: 2px solid transparent; cursor: grab; }
.rd-image.cover { border-color: #c0392b; }
.rd-image img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; }
.rd-image__badge { position: absolute; top: 8px; left: 8px; background: #c0392b; color: #fff; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px; }
.rd-image__actions { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px; background: #fff; }

.mk { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 18px; align-items: start; }
.mk__stage { display: flex; justify-content: center; background: #f3f4f6; border-radius: 8px; min-width: 0; }
/* Рамка сжимается точно до размеров снимка: координаты отметок — проценты от самого фото, а не от поля вокруг него */
.mk__photo { position: relative; width: fit-content; max-width: 100%; line-height: 0; cursor: crosshair; user-select: none; touch-action: none; }
.mk__photo img { display: block; width: auto; height: auto; max-width: 100%; max-height: 68vh; }
.mk__dot {
  position: absolute; width: 26px; height: 26px; margin: -13px 0 0 -13px; border-radius: 50%; border: 2px solid #fff; background: #c0392b; color: #fff;
  font-size: 0.75rem; font-weight: 700; line-height: 1; padding: 0; cursor: grab; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
  display: flex; align-items: center; justify-content: center;
}
.mk__dot.active { background: #1a1a1a; transform: scale(1.15); }
.mk__list { display: flex; flex-direction: column; gap: 8px; max-height: 68vh; overflow-y: auto; }
.mk__row { border: 1px solid #e8eaed; border-radius: 8px; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
.mk__row.active { border-color: #c0392b; background: #fff8f7; }
.mk__row-head { display: flex; align-items: center; gap: 8px; }
.mk__num { flex: 0 0 22px; height: 22px; border-radius: 50%; background: #c0392b; color: #fff; font-size: 0.72rem; font-weight: 700; display: flex; align-items: center; justify-content: center; }
.mk__row input, .mk__row textarea { flex: 1; min-width: 0; width: 100%; border: 1px solid #d9d9d9; border-radius: 6px; padding: 6px 10px; font-size: 0.85rem; font-family: inherit; outline: none; }
.mk__row input:focus, .mk__row textarea:focus { border-color: #c0392b; }
.mk__link { display: flex; gap: 6px; }
.mk__product { display: flex; gap: 8px; align-items: stretch; }
.mk__pic { flex: 0 0 96px; min-height: 96px; border-radius: 6px; overflow: hidden; background: #fff; border: 1px solid #d9d9d9; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; color: #6b7280; }
.mk__pic.empty { border-style: dashed; }
.mk__pic:hover { border-color: #c0392b; color: #c0392b; }
.mk__pic img { width: 100%; height: 100%; object-fit: contain; display: block; }
.mk__fields { flex: 1; min-width: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.mk__fields input:last-child { grid-column: 1 / -1; }
.mk__pic-actions { display: flex; gap: 6px; }
@media (max-width: 900px) { .mk { grid-template-columns: 1fr; } }
</style>
