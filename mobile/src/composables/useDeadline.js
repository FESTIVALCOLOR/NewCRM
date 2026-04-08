/**
 * Composable для расчёта дедлайнов с учётом рабочих дней и праздников РФ.
 * Порт с десктопа: utils/calendar_helpers.py + utils/date_utils.py
 */

// Государственные праздники РФ (месяц, день)
const RUSSIAN_HOLIDAYS = [
  [1, 1], [1, 2], [1, 3], [1, 4], [1, 5], [1, 6], [1, 7], [1, 8], // Новогодние
  [2, 23], // День защитника Отечества
  [3, 8],  // Международный женский день
  [5, 1],  // Праздник Весны и Труда
  [5, 9],  // День Победы
  [6, 12], // День России
  [11, 4]  // День народного единства
]

/**
 * Рабочий ли день (Пн-Пт, не праздник РФ)
 */
function isWorkingDay(date) {
  const dow = date.getDay() // 0=Вс, 6=Сб
  if (dow === 0 || dow === 6) return false
  const m = date.getMonth() + 1
  const d = date.getDate()
  return !RUSSIAN_HOLIDAYS.some(([hm, hd]) => hm === m && hd === d)
}

/**
 * Подсчитать рабочие дни между сегодня и датой дедлайна.
 * Положительное = дней осталось, отрицательное = просрочка.
 * @param {string} deadlineDateStr - 'YYYY-MM-DD'
 * @returns {number} рабочих дней (+ или -)
 */
export function countWorkingDaysUntil(deadlineDateStr) {
  if (!deadlineDateStr) return 0
  const parts = deadlineDateStr.split('-')
  if (parts.length !== 3) return 0
  const deadline = new Date(+parts[0], +parts[1] - 1, +parts[2])
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  deadline.setHours(0, 0, 0, 0)

  if (deadline.getTime() === today.getTime()) return 0

  const forward = deadline > today
  const start = forward ? new Date(today) : new Date(deadline)
  const end = forward ? deadline : today
  let count = 0
  const current = new Date(start)
  current.setDate(current.getDate() + 1)
  while (current <= end) {
    if (isWorkingDay(current)) count++
    current.setDate(current.getDate() + 1)
  }
  return forward ? count : -count
}

/**
 * Добавить рабочие дни к дате (пропуская выходные и праздники РФ).
 * @param {string} startDateStr - 'YYYY-MM-DD'
 * @param {number} workingDays - количество рабочих дней
 * @returns {string} 'YYYY-MM-DD'
 */
export function addWorkingDays(startDateStr, workingDays) {
  if (!startDateStr || workingDays <= 0) return startDateStr || ''
  const parts = startDateStr.split('-')
  if (parts.length !== 3) return startDateStr
  const current = new Date(+parts[0], +parts[1] - 1, +parts[2])
  if (isNaN(current.getTime())) return startDateStr

  let added = 0
  while (added < workingDays) {
    current.setDate(current.getDate() + 1)
    if (isWorkingDay(current)) added++
  }

  const y = current.getFullYear()
  const m = String(current.getMonth() + 1).padStart(2, '0')
  const d = String(current.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * Маппинг column_name → stage_group для поиска в timeline.
 */
function columnToStageGroup(columnName) {
  if (!columnName) return null
  const col = columnName.toLowerCase()
  if (col.includes('стадия 1') || col.includes('планировочн')) return 'STAGE1'
  if (col.includes('стадия 2') || col.includes('концепция') || col.includes('дизайн') || col.includes('визуализац')) return 'STAGE2'
  if (col.includes('стадия 3') || col.includes('чертеж') || col.includes('чертёж')) return 'STAGE3'
  return null
}

/**
 * Рассчитать дедлайн из timeline для данной стадии.
 * Алгоритм (как в десктопе crm_dialogs.py):
 *   1. Сортируем entries по sort_order
 *   2. Идём сквозным проходом, запоминая prev_actual_date
 *   3. Ищем первый незаполненный подэтап в нужной stage_group с norm_days > 0
 *   4. deadline = addWorkingDays(prev_actual_date || today, norm_days)
 *
 * @param {Array} entries - записи timeline (от API)
 * @param {string} columnName - название стадии ('Стадия 2: концепция дизайна')
 * @returns {string} 'YYYY-MM-DD' или '' если не удалось рассчитать
 */
export function calcDeadlineFromTimeline(entries, columnName) {
  if (!entries || entries.length === 0 || !columnName) return ''
  const stageGroup = columnToStageGroup(columnName)
  if (!stageGroup) return ''

  const sorted = [...entries].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))

  let prevDate = ''
  let normDays = 0

  for (const e of sorted) {
    if ((e.executor_role || '') === 'header') continue

    // Нашли первый незаполненный подэтап в нужной стадии (как в desktop: берём norm_days)
    if (e.stage_group === stageGroup && !e.actual_date && (e.norm_days || 0) > 0) {
      normDays = e.norm_days
      break
    }

    // Обновляем prev_date (сквозной по всем стадиям)
    if (e.actual_date) prevDate = e.actual_date
  }

  if (normDays <= 0) return ''

  // Базовая дата: prev_actual_date или сегодня
  if (!prevDate) {
    const now = new Date()
    prevDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  }

  return addWorkingDays(prevDate, normDays)
}
