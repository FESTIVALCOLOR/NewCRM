import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

/**
 * Единая загрузка файлов с общим прогресс-баром.
 * ЯД: файл идёт браузер → ЯД напрямую, сервер только выдаёт upload URL.
 * Сервер: файл отправляется на эндпоинт CRM (чаты, визиты), прогресс — по onUploadProgress.
 */

const MB = 1024 * 1024
const fmtMB = (bytes) => (bytes / MB).toFixed(1)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#39;' }
const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => HTML_ESCAPES[c])

function isRetryable(err) {
  if (!err) return false
  if (err.message === 'network') return true
  const status = err.status ?? err.response?.status
  if (status) return status >= 500 || status === 429 || status === 408
  // axios без ответа сервера: обрыв сети или таймаут
  return err.isAxiosError === true || err.code === 'ECONNABORTED'
}

function errorText(err) {
  const d = err?.response?.data?.detail
  if (typeof d === 'string') return d
  if (err?.response?.status) return `HTTP ${err.response.status}`
  if (err?.message === 'network') return 'нет связи'
  return err?.message || 'ошибка'
}

async function withRetry(fn, attempts = 3) {
  let lastErr
  for (let i = 0; i < attempts; i++) {
    if (i > 0) await sleep(1000 * i)
    try {
      return await fn()
    } catch (err) {
      lastErr = err
      if (!isRetryable(err)) break
    }
  }
  throw lastErr
}

/** PUT файла на ЯД через XHR (для прогресса отправки) */
function xhrPut(file, uploadUrl, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', uploadUrl)
    xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded, e.total)
    })
    xhr.addEventListener('load', () => {
      if (xhr.status === 200 || xhr.status === 201 || xhr.status === 202) return resolve()
      const err = new Error(`ЯД PUT: ${xhr.status}`)
      err.status = xhr.status
      reject(err)
    })
    xhr.addEventListener('error', () => reject(new Error('network')))
    xhr.addEventListener('abort', () => reject(new Error('Загрузка отменена')))
    xhr.send(file)
  })
}

/** Получить upload URL и залить файл; повтор при сетевых сбоях */
async function uploadFileToYd(file, yandexPath, { onProgress, onRetry } = {}) {
  let info = (await withRetry(() => filesApi.getUploadUrl(yandexPath))).data || {}
  if (!info.upload_url) throw new Error('Нет URL загрузки от ЯД')

  let lastErr = null
  for (let attempt = 0; attempt < 3; attempt++) {
    if (attempt > 0) {
      onRetry?.(attempt)
      await sleep(1500 * attempt)
      try {
        const retry = (await filesApi.getUploadUrl(yandexPath)).data
        if (retry?.upload_url) info = retry
      } catch { /* оставляем прежний URL */ }
    }
    try {
      await xhrPut(file, info.upload_url, onProgress)
      lastErr = null
      break
    } catch (err) {
      lastErr = err
      if (!isRetryable(err)) throw err
    }
  }
  if (lastErr) throw lastErr

  return {
    yandex_path: info.yandex_path || yandexPath,
    file_name: info.file_name || file.name,
    folder_created: !!info.folder_created,
  }
}

/** Публичная ссылка; ЯД может ещё обрабатывать только что залитый файл — пробуем дважды */
async function fetchPublicLink(yandexPath) {
  for (let attempt = 0; attempt < 2; attempt++) {
    if (attempt > 0) await sleep(1500)
    try {
      const { data } = await filesApi.getPublicLink(yandexPath)
      if (data?.public_link) return data.public_link
    } catch { /* повторим, а потом дозаполним через fill-links */ }
  }
  return ''
}

const PHASES = {
  prepare: () => 'подготовка…',
  upload: (st) => `${fmtMB(st.loaded)} / ${fmtMB(st.size)} МБ`,
  retry: () => 'повтор загрузки…',
  link: () => 'получение ссылки…',
  save: () => 'сохранение…',
  server: () => 'обработка на сервере…',
  copy: () => 'копирование на Яндекс.Диск…',
}

export function useYdUpload() {
  const $q = useQuasar()

  /**
   * Общая очередь загрузки с единой панелью прогресса.
   * task(item, index, ctx) выполняет загрузку одного элемента; ctx:
   *   progress(loadedBytes) — отправлено байт, phase(key) — этап из PHASES, rename(name).
   * @returns {Promise<{ ok: {item, index, value}[], failed: {item, index, name, error, err}[] }>}
   */
  async function runUploadQueue(items, {
    task,
    title = 'Загрузка файлов',
    concurrency = 3,
    nameOf = (x) => x?.name || 'файл',
    sizeOf = (x) => x?.size || 0,
  } = {}) {
    const list = Array.from(items || [])
    const total = list.length
    const ok = []
    const failed = []
    if (!total) return { ok, failed }

    const sizes = list.map((x) => sizeOf(x))
    const totalBytes = sizes.reduce((s, v) => s + v, 0) || 1
    const loaded = new Array(total).fill(0)
    const active = new Map()
    let done = 0
    let renderTimer = null

    const render = () => {
      renderTimer = null
      const sent = loaded.reduce((s, v) => s + v, 0)
      // Без размеров (например, копирование по ссылке) прогресс считаем по количеству
      const pct = totalBytes > 1
        ? Math.min(100, Math.round((sent / totalBytes) * 100))
        : Math.round((done / total) * 100)
      const lines = [...active.values()]
        .map((st) => `<div style="font-size:13px;opacity:.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(st.name)} — ${PHASES[st.phase](st)}</div>`)
        .join('')
      const errors = failed.length
        ? `<div style="font-size:13px;color:#ff8a80;margin-top:6px">Ошибок: ${failed.length}</div>`
        : ''
      const bytesLine = totalBytes > 1 ? `${fmtMB(Math.min(sent, totalBytes))} / ${fmtMB(totalBytes)} МБ` : ''
      $q.loading.show({
        html: true,
        spinnerSize: 40,
        message: `
          <div style="width:min(320px,80vw);text-align:left">
            <div style="font-size:16px;font-weight:600;margin-bottom:8px">${escapeHtml(title)}: ${done} из ${total}</div>
            <div style="height:10px;background:rgba(255,255,255,.25);border-radius:5px;overflow:hidden">
              <div style="height:100%;width:${pct}%;background:#f2c94c;transition:width .2s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:13px;margin:4px 0 10px">
              <span>${bytesLine}</span><span>${pct}%</span>
            </div>
            ${lines}${errors}
          </div>`,
      })
    }
    const schedule = () => {
      if (!renderTimer) renderTimer = setTimeout(render, 120)
    }

    let next = 0
    async function worker() {
      while (next < total) {
        const index = next++
        const item = list[index]
        const st = { name: nameOf(item), size: sizes[index], loaded: 0, phase: 'prepare' }
        const ctx = {
          progress: (l) => { st.phase = 'upload'; st.loaded = Math.min(l, st.size || l); loaded[index] = st.loaded; schedule() },
          phase: (p) => {
            st.phase = p
            if (p === 'retry') { st.loaded = 0; loaded[index] = 0 }
            schedule()
          },
          rename: (n) => { st.name = n; schedule() },
        }
        active.set(index, st)
        schedule()
        try {
          const value = await task(item, index, ctx)
          ok.push({ item, index, value })
        } catch (err) {
          failed.push({ item, index, name: st.name, error: errorText(err), err })
        } finally {
          loaded[index] = st.size
          active.delete(index)
          done++
          schedule()
        }
      }
    }

    render()
    try {
      await Promise.all(Array.from({ length: Math.min(concurrency, total) }, worker))
    } finally {
      clearTimeout(renderTimer)
      $q.loading.hide()
    }
    return { ok, failed }
  }

  /** Задача очереди: файл → ЯД → публичная ссылка → (опционально) запись в БД */
  function ydTask(buildPath, saveRecord) {
    return async (file, index, ctx) => {
      const up = await uploadFileToYd(file, buildPath(file, index), {
        onProgress: (l) => ctx.progress(l),
        onRetry: () => ctx.phase('retry'),
      })
      ctx.rename(up.file_name)
      ctx.phase('link')
      const result = { file, index, ...up, public_link: await fetchPublicLink(up.yandex_path) }
      if (saveRecord) {
        ctx.phase('save')
        try {
          await withRetry(() => saveRecord(result))
        } catch (err) {
          throw new Error(`файл загружен, но не сохранён в CRM: ${errorText(err)}`)
        }
      }
      return result
    }
  }

  /**
   * Загрузить один файл на ЯД (та же панель прогресса). Бросает исходную ошибку при неудаче.
   * @returns {{ yandex_path: string, public_link: string, file_name: string }}
   */
  async function uploadToYd(file, yandexPath) {
    const { ok, failed } = await runUploadQueue([file], {
      title: 'Загрузка файла',
      concurrency: 1,
      task: ydTask(() => yandexPath),
    })
    if (failed.length) throw failed[0].err
    const r = ok[0].value
    return { yandex_path: r.yandex_path, public_link: r.public_link, file_name: r.file_name }
  }

  /**
   * Пакетная загрузка на ЯД. Запись в БД создаётся только для успешно залитых файлов.
   * @param {(file: File, index: number) => string} opts.buildPath — путь на ЯД
   * @param {(r: {file, index, yandex_path, file_name, public_link}) => Promise} [opts.saveRecord]
   * @returns {Promise<{ ok: object[], failed: object[], noLink: number }>}
   */
  async function uploadBatch(files, { buildPath, saveRecord, concurrency = 3, title = 'Загрузка файлов' } = {}) {
    const res = await runUploadQueue(files, { title, concurrency, task: ydTask(buildPath, saveRecord) })
    const ok = res.ok.map((o) => o.value)
    return { ok, failed: res.failed, noLink: ok.filter((r) => !r.public_link).length }
  }

  /**
   * Загрузка через эндпоинт CRM. send(file, onUploadProgress, index) должен вернуть Promise
   * (axios-запрос с переданным onUploadProgress). Без повторов: такие запросы не идемпотентны.
   * concurrency=1 по умолчанию — сохраняет порядок (важно для сообщений чата).
   */
  async function uploadViaServer(files, { send, title = 'Загрузка файлов', concurrency = 1 } = {}) {
    const res = await runUploadQueue(files, {
      title,
      concurrency,
      task: async (file, index, ctx) => send(file, (e) => {
        ctx.progress(e.loaded || 0)
        if (e.total && e.loaded >= e.total) ctx.phase('server')
      }, index),
    })
    return { ok: res.ok.map((o) => ({ file: o.item, index: o.index, data: o.value })), failed: res.failed }
  }

  /** Итоговое уведомление по результату uploadBatch / uploadViaServer / runUploadQueue */
  function notifyBatchResult({ ok, failed }) {
    if (!failed.length) {
      $q.notify({ type: 'positive', message: `Загружено файлов: ${ok.length}` })
      return
    }
    const names = failed.slice(0, 5).map((f) => `${f.name} (${f.error})`).join('; ')
    const more = failed.length > 5 ? ` и ещё ${failed.length - 5}` : ''
    $q.notify({
      type: ok.length ? 'warning' : 'negative',
      message: `Загружено ${ok.length} из ${ok.length + failed.length}. Не загружены: ${names}${more}`,
      multiLine: true,
      timeout: 0,
      actions: [{ label: 'OK', color: 'white' }],
    })
  }

  return { uploadToYd, uploadBatch, uploadViaServer, runUploadQueue, notifyBatchResult }
}
