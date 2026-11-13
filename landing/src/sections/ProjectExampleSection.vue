<template>
  <section v-if="project" id="project_example" ref="root" class="section example" v-bind="$attrs">
    <div class="container example__intro">
      <h2 class="section-title">{{ settings?.example_title || 'ПОСМОТРЕТЬ ПРИМЕР ПРОЕКТА' }}</h2>
      <p class="example__text">{{ settings?.example_text || DEFAULT_TEXT }}</p>
      <button v-if="!open" type="button" class="example__cover" :aria-label="buttonLabel" @click="toggle">
        <img :src="project.pages[0]" alt="Обложка примера дизайн-проекта" loading="lazy" />
        <span class="example__cover-badge">{{ project.pages.length }} {{ pagesWord }}</span>
      </button>
      <button type="button" class="btn" :class="open ? 'btn--outline' : 'btn--accent'" @click="toggle">
        {{ open ? 'Свернуть пример' : buttonLabel }}
      </button>
    </div>

    <div v-if="open" class="container example__viewer">
      <!-- Книгу создаёт библиотека перелистывания: она удаляет свой элемент при закрытии, поэтому внутри отдельной обёртки -->
      <div ref="bookHost" class="example__book" :style="{ '--ratio': ratio }" />
      <div class="example__controls">
        <button type="button" class="example__nav" :disabled="page <= 0" aria-label="Предыдущая страница" @click="book?.flipPrev()">‹</button>
        <span class="example__counter">{{ pageLabel }}</span>
        <button type="button" class="example__nav" :disabled="page >= project.pages.length - 1" aria-label="Следующая страница" @click="book?.flipNext()">›</button>
      </div>
      <p class="example__hint">
        Листайте, потянув за угол страницы или кнопками.
        <a :href="project.pdf" target="_blank" rel="noopener">Открыть PDF целиком</a>
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

defineOptions({ inheritAttrs: false })
const props = defineProps({ settings: Object })

const DEFAULT_TEXT = 'Так выглядит дизайн-проект, который вы получите: планировочные решения, визуализации и рабочие чертежи. Листайте страницы, как в настоящем альбоме.'
// Сколько страниц вокруг текущей подгружать заранее: листать без ожидания, но не качать весь альбом сразу
const PRELOAD = 3

const root = ref(null)
const bookHost = ref(null)
const open = ref(false)
const page = ref(0)
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
const ratio = computed(() => (project.value ? `${project.value.width} / ${project.value.height}` : '4 / 3'))
const buttonLabel = computed(() => props.settings?.example_button || 'Посмотреть пример проекта')
const pagesWord = computed(() => {
  const n = project.value?.pages.length || 0
  const last = n % 10
  if (n % 100 > 10 && n % 100 < 20) return 'страниц'
  return last === 1 ? 'страница' : last >= 2 && last <= 4 ? 'страницы' : 'страниц'
})

function loadAround(index) {
  for (let i = Math.max(0, index - 1); i <= Math.min(pageElements.length - 1, index + PRELOAD); i++) {
    const img = pageElements[i].firstChild
    if (!img.src) img.src = img.dataset.src
  }
}
function updateCounter() {
  const total = project.value.pages.length
  const current = book.getCurrentPageIndex()
  page.value = current
  // В развороте видны две страницы — показываем обе
  const second = book.getOrientation?.() === 'landscape' && current > 0 && current + 1 < total ? `–${current + 2}` : ''
  pageLabel.value = `${current + 1}${second} из ${total}`
}

async function openBook() {
  const [{ PageFlip }] = await Promise.all([import('page-flip')])
  if (!open.value || !bookHost.value) return
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
  // Размер книги задаём сами: страница целиком помещается в окно, и под ней видны кнопки листания
  const hostWidth = bookHost.value.clientWidth
  const ratioWH = width / height
  const maxPageHeight = Math.max(240, Math.min(height, window.innerHeight - 250))
  // Альбомные листы (чертежи) — по одному, в развороте они слишком мелкие.
  // Вертикальные страницы — разворотом по две, если на экране хватает места
  const spread = width <= height && hostWidth / 2 >= 260
  const pageWidth = Math.floor(Math.min(spread ? hostWidth / 2 : hostWidth, maxPageHeight * ratioWH))
  frame.style.width = `${spread ? pageWidth * 2 : pageWidth}px`
  book = new PageFlip(element, {
    width,
    height,
    size: 'stretch',
    // Одностраничный режим включается, когда ширина книги меньше двух минимальных страниц
    minWidth: spread ? 200 : Math.ceil(pageWidth * 0.51),
    maxWidth: pageWidth,
    minHeight: 160,
    maxHeight: Math.ceil(pageWidth / ratioWH),
    showCover: true,
    usePortrait: true,
    mobileScrollSupport: true,
    maxShadowOpacity: 0.35,
    flippingTime: 800,
  })
  book.loadFromHTML(pageElements)
  book.on('flip', () => { loadAround(book.getCurrentPageIndex()); updateCounter() })
  book.on('changeOrientation', updateCounter)
  loadAround(0)
  updateCounter()
}

function closeBook() {
  book?.destroy()
  book = null
  pageElements = []
  if (bookHost.value) bookHost.value.innerHTML = ''
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    root.value?.querySelector('.example__viewer')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    openBook()
  } else {
    closeBook()
    root.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function onKey(event) {
  if (!book) return
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
/* Обложка-превью: альбом с тенью, по нажатию открывается книга */
.example__cover {
  position: relative; display: block; width: min(460px, 100%); padding: 0; border: none; background: none; cursor: pointer;
  border-radius: 6px; overflow: hidden; box-shadow: 0 18px 40px rgba(0, 0, 0, 0.18), 0 2px 6px rgba(0, 0, 0, 0.12);
  transform: perspective(1200px) rotateX(4deg); transition: transform 0.35s, box-shadow 0.35s;
}
.example__cover:hover { transform: perspective(1200px) rotateX(0deg) translateY(-4px); box-shadow: 0 24px 50px rgba(0, 0, 0, 0.22), 0 2px 6px rgba(0, 0, 0, 0.12); }
.example__cover img { display: block; width: 100%; height: auto; }
.example__cover-badge { position: absolute; right: 12px; bottom: 12px; background: rgba(0, 0, 0, 0.6); color: #fff; font-size: 0.78rem; padding: 4px 10px; border-radius: 12px; }
.example__viewer { margin-top: 36px; display: flex; flex-direction: column; align-items: center; gap: 16px; }
.example__book { width: 100%; display: flex; justify-content: center; }
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
.example__hint a { color: var(--accent); text-decoration: none; font-weight: 600; white-space: nowrap; }
.example__hint a:hover { text-decoration: underline; }
</style>
