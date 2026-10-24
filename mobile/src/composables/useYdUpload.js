import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

/**
 * Composable для прямой загрузки файлов в Яндекс.Диск из браузера.
 * Сервер используется только для создания папки и выдачи временного upload URL.
 * Файл идёт напрямую браузер → ЯД, минуя сервер (нет нагрузки на RAM сервера).
 */
export function useYdUpload() {
  const $q = useQuasar()

  /** PUT файл на YD через XHR с отображением прогресса */
  function _xhrPut(file, uploadUrl, actualFileName, sizeMB) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('PUT', uploadUrl)
      xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100)
          const loadedMB = (e.loaded / 1024 / 1024).toFixed(1)
          $q.loading.show({
            message: `${actualFileName}<br><b>${loadedMB} / ${sizeMB} МБ</b> (${pct}%)`,
            html: true,
            spinnerSize: 50,
          })
        }
      })

      xhr.addEventListener('load', () => {
        if (xhr.status === 200 || xhr.status === 201) resolve()
        else reject(new Error(`ЯД PUT: ${xhr.status}`))
      })
      // 'network' — маркер для retry; остальные ошибки бросаем как есть
      xhr.addEventListener('error', () => reject(new Error('network')))
      xhr.addEventListener('abort', () => reject(new Error('Загрузка отменена')))
      xhr.send(file)
    })
  }

  /**
   * Загрузить файл на ЯД напрямую из браузера с прогресс-баром.
   * @param {File} file - объект File
   * @param {string} yandexPath - путь на ЯД без "disk:" префикса
   * @returns {{ yandex_path: string, public_link: string, file_name: string }}
   */
  async function uploadToYd(file, yandexPath) {
    // Шаг 1: сервер проверяет папку / создаёт при необходимости / возвращает upload URL
    $q.loading.show({ message: 'Проверка папки на Яндекс.Диске...', html: true, spinnerSize: 50 })

    const urlRes = await filesApi.getUploadUrl(yandexPath)
    const actualPath = urlRes.data?.yandex_path || yandexPath
    const actualFileName = urlRes.data?.file_name || file.name
    const folderCreated = urlRes.data?.folder_created || false
    let currentUploadUrl = urlRes.data?.upload_url

    if (!currentUploadUrl) throw new Error('Нет URL загрузки от ЯД')

    if (folderCreated) {
      $q.loading.show({ message: 'Папка создана, начинаю загрузку...', html: true, spinnerSize: 50 })
    }

    const sizeMB = (file.size / 1024 / 1024).toFixed(1)

    // Шаг 2: PUT файл напрямую на ЯД из браузера; retry при сетевой ошибке (ERR_CONNECTION_RESET)
    let lastErr = null
    for (let attempt = 0; attempt < 3; attempt++) {
      if (attempt > 0) {
        $q.loading.show({
          message: `Повтор загрузки (попытка ${attempt + 1}/3)...`,
          html: true,
          spinnerSize: 50,
        })
        await new Promise(r => setTimeout(r, 1500 * attempt))
        // Перезапрашиваем upload URL — папка уже точно есть, только URL обновляем
        try {
          const retryRes = await filesApi.getUploadUrl(yandexPath)
          currentUploadUrl = retryRes.data?.upload_url || currentUploadUrl
        } catch {}
      }

      try {
        await _xhrPut(file, currentUploadUrl, actualFileName, sizeMB)
        lastErr = null
        break
      } catch (err) {
        lastErr = err
        if (err.message !== 'network') throw err // Только сетевые ошибки повторяем
      }
    }

    if (lastErr) throw lastErr

    // Шаг 3: получить публичную ссылку на файл
    let publicLink = ''
    try {
      const linkRes = await filesApi.getPublicLink(actualPath)
      publicLink = linkRes.data?.public_link || ''
    } catch {}

    return { yandex_path: actualPath, public_link: publicLink, file_name: actualFileName }
  }

  return { uploadToYd }
}
