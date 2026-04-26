// PDF-thumbnail: рендерит первую страницу PDF в JPEG через PDF.js
// Используется для превью PDF при загрузке и в пузырях сообщений

// Полифилл для Map.prototype.getOrInsertComputed (TC39, pdfjs-dist 5.x, нет в Chrome<136/Safari<18)
if (typeof Map !== 'undefined' && !Map.prototype.getOrInsertComputed) {
  Map.prototype.getOrInsertComputed = function (key, compute) {
    if (!this.has(key)) this.set(key, compute(key))
    return this.get(key)
  }
}

let pdfjsLib = null
let workerBlobUrl = null
const cache = new Map()

async function ensurePdfJs() {
  if (pdfjsLib) return pdfjsLib
  const mod = await import('pdfjs-dist')

  if (!workerBlobUrl) {
    // Браузерный HTTP-кеш может хранить воркер с application/octet-stream (immutable, 1 год).
    // fetch() читает тело без MIME-проверки; Blob с явным type обходит ограничение модульных воркеров.
    const rawUrl = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()
    try {
      const resp = await fetch(rawUrl)
      if (resp.ok) {
        const buf = await resp.arrayBuffer()
        workerBlobUrl = URL.createObjectURL(new Blob([buf], { type: 'application/javascript' }))
      }
    } catch (e) {
      console.warn('[PdfThumbnail] Worker blob failed, fallback to URL:', e)
    }
    if (!workerBlobUrl) workerBlobUrl = rawUrl
  }

  mod.GlobalWorkerOptions.workerSrc = workerBlobUrl
  pdfjsLib = mod
  return pdfjsLib
}

export async function getPdfThumbnail(source, cacheKey) {
  const key = cacheKey || (typeof source === 'string' ? source : null)
  if (key && cache.has(key)) return cache.get(key)

  try {
    const lib = await ensurePdfJs()
    const loadingTask =
      typeof source === 'string'
        ? lib.getDocument({ url: source, withCredentials: false, disableRange: true, disableStream: true })
        : source instanceof ArrayBuffer
          ? lib.getDocument({ data: source })
          : lib.getDocument({ data: await source.arrayBuffer() })

    const pdf = await loadingTask.promise
    const page = await pdf.getPage(1)
    const viewport = page.getViewport({ scale: 0.6 })

    const canvas = document.createElement('canvas')
    canvas.width = viewport.width
    canvas.height = viewport.height
    await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise

    const result = canvas.toDataURL('image/jpeg', 0.75)
    if (key) cache.set(key, result)
    return result
  } catch (e) {
    console.warn('[PdfThumbnail] Error:', e?.message || e)
    return null
  }
}

export function clearPdfCache() {
  cache.clear()
}
