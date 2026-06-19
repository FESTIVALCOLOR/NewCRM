import { useQuasar } from 'quasar'
import { filesApi } from 'src/services/api'

/**
 * Composable для прямой загрузки файлов в Яндекс.Диск из браузера.
 * Сервер используется только для создания папки и выдачи временного upload URL.
 * Файл идёт напрямую браузер → ЯД, минуя сервер (нет нагрузки на RAM сервера).
 */
export function useYdUpload() {
  const $q = useQuasar()

  /**
   * Загрузить файл на ЯД напрямую из браузера с прогресс-баром.
   * @param {File} file - объект File
   * @param {string} yandexPath - путь на ЯД без "disk:" префикса
   * @returns {{ yandex_path: string, public_link: string, file_name: string }}
   */
  async function uploadToYd(file, yandexPath) {
    // Шаг 1: получить upload URL от сервера (сервер создаёт родительскую папку и проверяет токен)
    const urlRes = await filesApi.getUploadUrl(yandexPath)
    const uploadUrl = urlRes.data?.upload_url
    const actualPath = urlRes.data?.yandex_path || yandexPath
    const actualFileName = urlRes.data?.file_name || file.name

    if (!uploadUrl) throw new Error('Нет URL загрузки от ЯД')

    // Шаг 2: PUT файл напрямую на ЯД из браузера через XHR (с прогрессом)
    const sizeMB = (file.size / 1024 / 1024).toFixed(1)
    await new Promise((resolve, reject) => {
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
      xhr.addEventListener('error', () => reject(new Error('Сетевая ошибка при загрузке')))
      xhr.addEventListener('abort', () => reject(new Error('Загрузка отменена')))
      xhr.send(file)
    })

    // Шаг 3: получить публичную ссылку на файл
    let publicLink = ''
    try {
      const linkRes = await filesApi.getPublicLink(actualPath)
      publicLink = linkRes.data?.public_link || ''
    } catch {
      // ссылку получим при следующем сканировании папки
    }

    return { yandex_path: actualPath, public_link: publicLink, file_name: actualFileName }
  }

  return { uploadToYd }
}
