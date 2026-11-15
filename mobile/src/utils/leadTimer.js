// Таймер на принятие заявки с сайта — отображение.
// Расчёт контрольных точек делает сервер (server/services/lead_sla.py) и присылает поле `sla`;
// здесь только «дотикиваем» остаток между обновлениями списка (раз в минуту) с учётом рабочего времени.
// Копия файла: landing/src/admin/leadTimer.js — держать одинаковыми.

const MSK_MS = 3 * 3600 * 1000
const HOUR_MS = 3600 * 1000
const WORK_START_H = 10
const WORK_END_H = 19

function mskDayStart(ms) {
  const d = new Date(ms + MSK_MS)
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) - MSK_MS
}

function isWeekday(ms) {
  const day = new Date(ms + MSK_MS).getUTCDay()
  return day >= 1 && day <= 5
}

export function isWorkingMoment(ms) {
  const offset = ms - mskDayStart(ms)
  return isWeekday(ms) && offset >= WORK_START_H * HOUR_MS && offset < WORK_END_H * HOUR_MS
}

// Рабочие миллисекунды между двумя моментами (будни 10:00–19:00 МСК; праздники знает только сервер)
function workingMsBetween(from, to) {
  let total = 0
  for (let t = from; t < to;) {
    const dayStart = mskDayStart(t)
    if (isWeekday(t)) {
      const start = Math.max(t, dayStart + WORK_START_H * HOUR_MS)
      const end = Math.min(to, dayStart + WORK_END_H * HOUR_MS)
      if (end > start) total += end - start
    }
    t = dayStart + 24 * HOUR_MS
  }
  return total
}

function fmtDuration(seconds) {
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

function fmtMoment(iso) {
  return new Date(iso).toLocaleString('ru-RU', { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow' })
}

/**
 * Что показать в углу карточки.
 * @param {object|null} sla — поле заявки от сервера
 * @param {number} fetchedAt — когда получен список (мс)
 * @param {number} now — текущее время (мс)
 * @returns {{phase, text, caption, hint, paused, expired}|null}
 */
export function leadTimerView(sla, fetchedAt, now) {
  if (!sla) return null
  if (sla.overdue) {
    return { phase: 'overdue', text: 'Просрочена', caption: 'не обработана за 27 раб. ч', hint: '', paused: false, expired: false }
  }
  const startsAt = Date.parse(sla.starts_at)
  // Сервер в момент загрузки видел нерабочее время, а по часам клиента оно рабочее — значит праздник, не тикаем
  const holiday = !sla.working_now && isWorkingMoment(fetchedAt) && fetchedAt >= startsAt
  const spentSec = holiday ? 0 : workingMsBetween(Math.max(fetchedAt, startsAt), now) / 1000
  const left = Math.max(0, sla.remaining_seconds - spentSec)
  const started = now >= startsAt
  const paused = !started || holiday || !isWorkingMoment(now)
  let caption = sla.label
  if (!started) caption = `старт ${fmtMoment(sla.starts_at)}`
  else if (paused) caption += ' · пауза'
  const hint = sla.next_at ? `Следующее напоминание: ${fmtMoment(sla.next_at)} (МСК). Считается только рабочее время: будни 10:00–19:00.` : ''
  return { phase: sla.phase, text: fmtDuration(left), caption, hint, paused, expired: left <= 0 }
}
