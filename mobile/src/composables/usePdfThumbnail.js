// PDF-thumbnail: рендерит первую страницу PDF в JPEG через PDF.js
// Используется для превью PDF при загрузке и в пузырях сообщений
let pdfjsLib = null
const cache = new Map()

async function ensurePdfJs() {
  if (pdfjsLib) return pdfjsLib
  const mod = await import('pdfjs-dist')
  mod.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString()
  pdfjsLib = mod
  return pdfjsLib
}

/**
 * Рендерит первую страницу PDF в base64 JPEG.
 * @param {File|string} source - File-объект или URL (строка)
 * @param {string} [cacheKey] - ключ кэша (опционально)
 * @returns {Promise<string|null>} data URL или null при ошибке
 */
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

/**
 * Очищает кэш (вызывать при необходимости освободить память)
 */
export function clearPdfCache() {
  cache.clear()
}
