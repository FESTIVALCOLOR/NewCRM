/**
 * Optimistic Updates — обновляем UI мгновенно, откатываем при ошибке
 * Важно: при откате показываем уведомление пользователю
 */
import { useQuasar } from 'quasar'

export function useOptimistic() {
  const $q = useQuasar()

  /**
   * Выполнить действие оптимистично
   * @param {Function} optimisticFn - немедленное обновление UI (возвращает snapshot для отката)
   * @param {Function} apiFn - API вызов (async)
   * @param {Function} rollbackFn - откат при ошибке (получает snapshot)
   * @param {string} successMsg - сообщение при успехе (опционально)
   * @returns {Promise<boolean>} true если API успешен, false если откат
   */
  async function optimistic(optimisticFn, apiFn, rollbackFn, successMsg) {
    const snapshot = optimisticFn()
    try {
      await apiFn()
      if (successMsg) $q.notify({ type: 'positive', message: successMsg })
      return true
    } catch (err) {
      rollbackFn(snapshot)
      const detail = err.response?.data?.detail
      const msg = typeof detail === 'string' ? detail : 'сервер недоступен'
      $q.notify({ type: 'negative', message: `Ошибка: ${msg}. Изменения отменены.` })
      return false
    }
  }

  return { optimistic }
}
