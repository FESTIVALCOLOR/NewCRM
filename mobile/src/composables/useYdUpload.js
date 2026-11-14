import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

/**
 * Прямая загрузка файлов в Яндекс.Диск из браузера.
 * Сервер только создаёт папку и выдаёт временный upload URL — файл идёт браузер → ЯД.
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

export function useYdUpload() {
  const $q = useQuasar()

  /**
   * Загрузить один файл с прогрессом.
   * @returns {{ yandex_path: string, public_link: string, file_name: string }}
   */
  async function uploadToYd(file, yandexPath) {
    try {
      $q.loading.show({ message: 'Проверка папки на Яндекс.Диске...', html: true, spinnerSize: 50 })
      const sizeMB = fmtMB(file.size)
      const up = await uploadFileToYd(file, yandexPath, {
        onProgress: (loaded, total) => {
          const pct = Math.round((loaded / total) * 100)
          $q.loading.show({
            message: `${escapeHtml(file.name)}<br><b>${fmtMB(loaded)} / ${sizeMB} МБ</b> (${pct}%)`,
            html: true,
            spinnerSize: 50,
          })
        },
        onRetry: (attempt) => {
          $q.loading.show({ message: `Повтор загрузки (попытка ${attempt + 1}/3)...`, html: true, spinnerSize: 50 })
        },
      })
      $q.loading.show({ message: 'Получение ссылки...', html: true, spinnerSize: 50 })
      const publicLink = await fetchPublicLink(up.yandex_path)
      return { yandex_path: up.yandex_path, public_link: publicLink, file_name: up.file_name }
    } finally {
      $q.loading.hide()
    }
  }

  /**
   * Пакетная загрузка с общим прогрессом.
   * Запись в БД создаётся только для успешно залитых файлов.
   *
   * @param {File[]|FileList} files
   * @param {object} opts
   * @param {(file: File, index: number) => string} opts.buildPath — путь на ЯД для файла
   * @param {(r: {file, index, yandex_path, file_name, public_link}) => Promise} [opts.saveRecord] — запись в БД
   * @param {number} [opts.concurrency=3]
   * @param {string} [opts.title]
   * @returns {Promise<{ ok: object[], failed: {file: File, error: string}[], noLink: number }>}
   */
  async function uploadBatch(files, { buildPath, saveRecord, concurrency = 3, title = 'Загрузка файлов' } = {}) {
    const list = Array.from(files || [])
    const total = list.length
    const ok = []
    const failed = []
    if (!total) return { ok, failed, noLink: 0 }

    const totalBytes = list.reduce((s, f) => s + (f.size || 0), 0) || 1
    const loaded = new Array(total).fill(0)
    const active = new Map()
    let done = 0
    let renderTimer = null

    const PHASES = {
      prepare: () => 'подготовка…',
      upload: (st) => `${fmtMB(st.loaded)} / ${fmtMB(st.size)} МБ`,
      retry: () => 'повтор загрузки…',
      link: () => 'получение ссылки…',
      save: () => 'сохранение…',
    }

    const render = () => {
      renderTimer = null
      const sent = loaded.reduce((s, v) => s + v, 0)
      const pct = Math.min(100, Math.round((sent / totalBytes) * 100))
      const lines = [...active.values()]
        .map((st) => `<div style="font-size:13px;opacity:.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(st.name)} — ${PHASES[st.phase](st)}</div>`)
        .join('')
      const errors = failed.length
        ? `<div style="font-size:13px;color:#ff8a80;margin-top:6px">Ошибок: ${failed.length}</div>`
        : ''
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
              <span>${fmtMB(Math.min(sent, totalBytes))} / ${fmtMB(totalBytes)} МБ</span><span>${pct}%</span>
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
        const file = list[index]
        const st = { name: file.name, size: file.size || 0, loaded: 0, phase: 'prepare' }
        active.set(index, st)
        schedule()
        try {
          const up = await uploadFileToYd(file, buildPath(file, index), {
            onProgress: (l) => { st.phase = 'upload'; st.loaded = l; loaded[index] = l; schedule() },
            onRetry: () => { st.phase = 'retry'; st.loaded = 0; loaded[index] = 0; schedule() },
          })
          loaded[index] = st.size
          st.name = up.file_name
          st.phase = 'link'
          schedule()
          const result = { file, index, ...up, public_link: await fetchPublicLink(up.yandex_path) }
          if (saveRecord) {
            st.phase = 'save'
            schedule()
            try {
              await withRetry(() => saveRecord(result))
            } catch (err) {
              throw new Error(`файл загружен, но не сохранён в CRM: ${errorText(err)}`)
            }
          }
          ok.push(result)
        } catch (err) {
          loaded[index] = st.size
          failed.push({ file, index, error: errorText(err) })
        } finally {
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
    return { ok, failed, noLink: ok.filter((r) => !r.public_link).length }
  }

  /** Итоговое уведомление по результату uploadBatch */
  function notifyBatchResult({ ok, failed }) {
    if (!failed.length) {
      $q.notify({ type: 'positive', message: `Загружено файлов: ${ok.length}` })
      return
    }
    const names = failed.slice(0, 5).map((f) => `${f.file.name} (${f.error})`).join('; ')
    const more = failed.length > 5 ? ` и ещё ${failed.length - 5}` : ''
    $q.notify({
      type: ok.length ? 'warning' : 'negative',
      message: `Загружено ${ok.length} из ${ok.length + failed.length}. Не загружены: ${names}${more}`,
      multiLine: true,
      timeout: 0,
      actions: [{ label: 'OK', color: 'white' }],
    })
  }

  return { uploadToYd, uploadBatch, notifyBatchResult }
}
