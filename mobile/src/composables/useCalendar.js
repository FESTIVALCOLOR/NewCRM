/**
 * Генерация .ics файлов для добавления в календарь
 * Используется для дедлайнов проектов и выездов надзора
 * Формат: iCalendar RFC 5545
 */

/**
 * Форматирует дату в формат iCalendar (YYYYMMDD)
 * @param {string|Date} date — дата
 * @returns {string} — дата в формате YYYYMMDD
 */
function formatICSDate(date) {
  const d = typeof date === 'string' ? new Date(date) : date
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}${m}${day}`
}

/**
 * Форматирует дату+время в формат iCalendar (YYYYMMDDTHHMMSS)
 * @param {string|Date} date — дата
 * @returns {string} — дата-время в формате YYYYMMDDTHHMMSS
 */
function formatICSDateTime(date) {
  const d = typeof date === 'string' ? new Date(date) : date
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${y}${m}${day}T${h}${min}${s}`
}

/**
 * Экранирование текста для iCalendar — спец. символы
 * @param {string} text
 * @returns {string}
 */
function escapeICS(text) {
  if (!text) return ''
  return text
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\n/g, '\\n')
}

/**
 * Генерация содержимого .ics файла
 * @param {Object} event — параметры события
 * @param {string} event.title — название события
 * @param {string} [event.description] — описание
 * @param {string|Date} event.startDate — дата начала
 * @param {string|Date} [event.endDate] — дата окончания (по умолчанию = startDate + 1 день)
 * @param {string} [event.location] — место
 * @param {number} [event.reminder] — напоминание в минутах (по умолчанию 1440 = 1 день)
 * @returns {Blob} — Blob с содержимым .ics
 */
export function generateICS(event) {
  const {
    title,
    description = '',
    startDate,
    endDate,
    location = '',
    reminder = 1440 // 1 день = 1440 минут
  } = event

  const dtStart = formatICSDate(startDate)
  // Если endDate не указан — событие на весь день (start + 1)
  const end = endDate || new Date(new Date(startDate).getTime() + 86400000)
  const dtEnd = formatICSDate(end)

  const now = formatICSDateTime(new Date())
  // Уникальный идентификатор события
  const uid = `${now}-${Math.random().toString(36).slice(2, 10)}@interior-studio`

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Interior Studio CRM//Mobile PWA//RU',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${uid}`,
    `DTSTAMP:${now}`,
    `DTSTART;VALUE=DATE:${dtStart}`,
    `DTEND;VALUE=DATE:${dtEnd}`,
    `SUMMARY:${escapeICS(title)}`,
  ]

  if (description) {
    lines.push(`DESCRIPTION:${escapeICS(description)}`)
  }
  if (location) {
    lines.push(`LOCATION:${escapeICS(location)}`)
  }

  // Напоминание (VALARM)
  if (reminder > 0) {
    lines.push(
      'BEGIN:VALARM',
      'ACTION:DISPLAY',
      `DESCRIPTION:${escapeICS(title)}`,
      `TRIGGER:-PT${reminder}M`,
      'END:VALARM'
    )
  }

  lines.push('END:VEVENT', 'END:VCALENDAR')

  const content = lines.join('\r\n')
  return new Blob([content], { type: 'text/calendar;charset=utf-8' })
}

/**
 * Скачать .ics файл
 * @param {Object} event — параметры события (см. generateICS)
 */
export function downloadICS(event) {
  const blob = generateICS(event)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  // Имя файла: транслитерированный заголовок
  const safeName = (event.title || 'event')
    .replace(/[^a-zA-Zа-яА-ЯёЁ0-9 _-]/g, '')
    .replace(/\s+/g, '_')
    .slice(0, 50)
  link.download = `${safeName}.ics`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Генерация URL для Google Calendar
 * @param {Object} event — параметры события
 * @returns {string} — URL для Google Calendar
 */
export function googleCalendarUrl(event) {
  const start = formatICSDate(event.startDate)
  const end = event.endDate
    ? formatICSDate(event.endDate)
    : formatICSDate(new Date(new Date(event.startDate).getTime() + 86400000))

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title || '',
    dates: `${start}/${end}`,
    details: event.description || '',
    location: event.location || ''
  })

  return `https://www.google.com/calendar/render?${params.toString()}`
}

/**
 * Добавить событие в календарь — показывает выбор: скачать .ics или Google Calendar
 * @param {Object} event — параметры события
 * @param {Object} $q — экземпляр Quasar (useQuasar())
 */
export function addToCalendar(event, $q) {
  if (!$q) {
    // Если Quasar не передан — просто скачиваем .ics
    downloadICS(event)
    return
  }

  $q.dialog({
    title: 'Добавить в календарь',
    message: 'Выберите способ добавления:',
    options: {
      type: 'radio',
      model: 'ics',
      items: [
        { label: 'Скачать .ics (универсальный)', value: 'ics' },
        { label: 'Google Calendar', value: 'google' }
      ]
    },
    cancel: { label: 'Отмена', flat: true, noCaps: true },
    ok: { label: 'Добавить', noCaps: true, color: 'primary' },
    persistent: false
  }).onOk((choice) => {
    if (choice === 'google') {
      window.open(googleCalendarUrl(event), '_blank')
    } else {
      downloadICS(event)
    }
  })
}
