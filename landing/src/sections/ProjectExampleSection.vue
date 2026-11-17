<template>
  <section v-if="project" id="project_example" ref="root" class="section example" v-bind="$attrs">
    <div class="container example__intro">
      <h2 class="section-title">{{ settings?.example_title || 'ПОСМОТРЕТЬ ПРИМЕР ПРОЕКТА' }}</h2>
      <p class="example__text">{{ settings?.example_text || DEFAULT_TEXT }}</p>
      <button type="button" class="btn" :class="open ? 'btn--outline' : 'btn--accent'" :aria-expanded="open" @click="toggle">
        {{ open ? 'Свернуть пример' : buttonLabel }}
      </button>
    </div>

    <!-- Блок с книгой плавно раскрывается по высоте -->
    <div class="example__expand" :class="{ 'is-open': open }" @transitionend.self="onTransitionEnd">
      <div class="example__expand-inner">
        <div class="container example__viewer">
          <!-- Книгу создаёт библиотека перелистывания: она удаляет свой элемент при закрытии, поэтому внутри отдельной обёртки -->
          <div ref="bookHost" class="example__book" />
          <div class="example__controls">
            <button type="button" class="example__nav" :disabled="page <= 0" aria-label="Предыдущая страница" @click="book?.flipPrev()">‹</button>
            <span class="example__counter">{{ pageLabel }}</span>
            <button type="button" class="example__nav" :disabled="atEnd" aria-label="Следующая страница" @click="book?.flipNext()">›</button>
          </div>
          <p class="example__hint">Листайте, потянув за угол страницы, кнопками или стрелками на клавиатуре.</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

defineOptions({ inheritAttrs: false })
const props = defineProps({ settings: Object })

const DEFAULT_TEXT = 'Так выглядит дизайн-проект, который вы получите: планировочные решения, визуализации и рабочие чертежи. Листайте страницы, как в настоящем альбоме.'
// Сколько страниц вокруг текущей подгружать заранее: листать без ожидания, но не качать весь альбом сразу
const PRELOAD = 4

const root = ref(null)
const bookHost = ref(null)
const open = ref(false)
const page = ref(0)
const atEnd = ref(false)
const pageLabel = ref('')
let book = null
let pageElements = []

const project = computed(() => {
  try {
    const value = JSON.parse(props.settings?.example_project || 'null')
    return value && Array.isArray(value.pages) && value.pages.length && value.width && value.height ? value : null
  } catch {
    return null
  }
})
const buttonLabel = computed(() => props.settings?.example_button || 'Посмотреть пример проекта')

function loadAround(index) {
  for (let i = Math.max(0, index - 1); i <= Math.min(pageElements.length - 1, index + PRELOAD); i++) {
    const img = pageElements[i].firstChild
    if (!img.src) img.src = img.dataset.src
  }
}
function updateCounter() {
  const total = project.value.pages.length
  const current = book.getCurrentPageIndex()
  const spread = book.getOrientation() === 'landscape'
  // В развороте видны две страницы — показываем обе
  const second = spread && current > 0 && current + 1 < total ? current + 2 : 0
  page.value = current
  atEnd.value = (second || current + 1) >= total
  pageLabel.value = `${current + 1}${second ? `–${second}` : ''} из ${total}`
}
// Обложку библиотека делает «жёсткой»: она поворачивается как картон, рывком. Делаем её мягкой,
// как остальные страницы, — тогда она плавно изгибается при перевороте
function softenCover() {
  const total = book.getPageCount()
  for (const index of [0, total - 1]) book.getPage(index)?.setDensity('soft')
}

async function openBook() {
  const { PageFlip } = await import('page-flip')
  if (!open.value || !bookHost.value || book) return
  const { width, height, pages } = project.value
  // Рамка задаёт ширину книги: свой элемент библиотека растягивает на 100% родителя
  const frame = document.createElement('div')
  frame.style.maxWidth = '100%'
  const element = document.createElement('div')
  frame.appendChild(element)
  bookHost.value.appendChild(frame)
  pageElements = pages.map((url, index) => {
    const pageEl = document.createElement('div')
    pageEl.className = 'example__page'
    const img = document.createElement('img')
    img.dataset.src = url
    img.alt = `Страница ${index + 1}`
    img.draggable = false
    pageEl.appendChild(img)
    return pageEl
  })
  // Книга — разворот из двух страниц, если на экране хватает ширины; на телефоне — по одной странице.
  // Высота подбирается так, чтобы страница целиком и кнопки помещались в окно
  const hostWidth = bookHost.value.clientWidth
  const ratio = width / height
  const maxPageHeight = Math.max(220, Math.min(height, window.innerHeight - 250))
  const spread = hostWidth / 2 >= 260
  const pageWidth = Math.floor(Math.min(spread ? hostWidth / 2 : hostWidth, maxPageHeight * ratio))
  frame.style.width = `${spread ? pageWidth * 2 : pageWidth}px`
  book = new PageFlip(element, {
    width,
    height,
    size: 'stretch',
    // Одностраничный режим включается, когда ширина книги меньше двух минимальных страниц
    minWidth: spread ? Math.min(200, pageWidth) : Math.ceil(pageWidth * 0.51),
    maxWidth: pageWidth,
    minHeight: 160,
    maxHeight: Math.ceil(pageWidth / ratio),
    showCover: true,
    usePortrait: true,
    mobileScrollSupport: true,
    maxShadowOpacity: 0.35,
    flippingTime: 900,
  })
  book.loadFromHTML(pageElements)
  softenCover()
  book.on('flip', () => { loadAround(book.getCurrentPageIndex() + 1); updateCounter() })
  book.on('changeOrientation', () => { softenCover(); updateCounter() })
  loadAround(0)
  updateCounter()
}

function closeBook() {
  book?.destroy()
  book = null
  pageElements = []
  if (bookHost.value) bookHost.value.innerHTML = ''
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    // Книга создаётся сразу: размер по ширине известен и у ещё свёрнутого блока
    openBook()
    setTimeout(() => root.value?.querySelector('.example__viewer')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 250)
  } else {
    root.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}
// Книга удаляется после того, как блок свернулся, — иначе он схлопнется рывком
function onTransitionEnd(event) {
  if (event.propertyName === 'grid-template-rows' && !open.value) closeBook()
}

function onKey(event) {
  if (!book || !open.value) return
  if (event.key === 'ArrowLeft') book.flipPrev()
  else if (event.key === 'ArrowRight') book.flipNext()
}
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  closeBook()
})
</script>

<style scoped>
.example__intro { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 24px; }
.example .section-title { margin-bottom: 0; }
.example__text { max-width: 680px; color: var(--text-light); font-size: calc(1rem * var(--ts, 1)); line-height: 1.65; }
/* Раскрытие по высоте: строка сетки плавно растёт от 0 до высоты содержимого */
.example__expand { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows 0.7s ease, opacity 0.5s ease; }
.example__expand.is-open { grid-template-rows: 1fr; opacity: 1; }
.example__expand-inner { overflow: hidden; min-height: 0; }
.example__viewer { padding-top: 36px; display: flex; flex-direction: column; align-items: center; gap: 16px; }
.example__book { width: 100%; display: flex; justify-content: center; min-height: 160px; }
.example__book :deep(.example__page) { background: #fff; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.04); }
.example__book :deep(.example__page img) { width: 100%; height: 100%; object-fit: contain; display: block; user-select: none; }
.example__controls { display: flex; align-items: center; gap: 18px; }
.example__nav {
  width: 42px; height: 42px; border-radius: 50%; border: 1px solid var(--border); background: #fff; color: var(--text);
  font-size: 1.5rem; line-height: 1; padding: 0 0 3px; cursor: pointer; transition: border-color 0.2s, color 0.2s;
}
.example__nav:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.example__nav:disabled { opacity: 0.35; cursor: default; }
.example__counter { min-width: 110px; text-align: center; font-size: calc(0.92rem * var(--ts, 1)); color: var(--text-light); }
.example__hint { font-size: calc(0.85rem * var(--ts, 1)); color: var(--text-light); text-align: center; }
@media (prefers-reduced-motion: reduce) {
  .example__expand { transition: none; }
}
</style>
