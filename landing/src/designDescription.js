// Описание готового дизайна → блоки для страницы.
// Описания пишутся в двух видах:
// - строки «Помещение: описание» («Прихожая: Белая мебель…») — каждая строка становится карточкой с заголовком;
// - абзацы через пустую строку — каждый абзац становится карточкой, заголовок берётся по комнате из первой фразы.

// Вводная строка («Гамма: …») показывается над карточками, а не карточкой
const LEAD_TITLES = /^(гамма|стиль|концепция|цвет(овая гамма)?|общее|идея)$/i

// Комнаты для заголовков абзацев; при совпадении в одном месте выигрывает та, что выше в списке
const ROOMS = [
  [/кухн\S*[-\s]+гостин/i, 'Кухня-гостиная'],
  [/кухн\S*[-\s]+столов/i, 'Кухня-столовая'],
  [/прихож/i, 'Прихожая'],
  [/гостев/i, 'Гостевая комната'],
  [/гостин/i, 'Гостиная'],
  [/кухн/i, 'Кухня'],
  [/спальн/i, 'Спальня'],
  [/детск/i, 'Детская'],
  [/ванн/i, 'Ванная комната'],
  [/санузел|санузл|душев/i, 'Санузел'],
  [/лоджи|балкон/i, 'Лоджия'],
  [/кабинет/i, 'Кабинет'],
  [/гардероб|постироч|кладов|хозяйствен/i, 'Хозяйственная комната'],
]

// Строка «Название: текст». Название — короткое и без точек, иначе это просто предложение с двоеточием
const LABELED = /^([^:.!?\d]{2,40}?)\s*:\s*(?::\s*)?(.+)$/

export function roomTitle(paragraph) {
  const firstSentence = paragraph.split(/(?<=[.!?])\s/)[0]
  let best = null
  ROOMS.forEach(([pattern, title], order) => {
    const match = firstSentence.match(pattern)
    if (match && (!best || match.index < best.index || (match.index === best.index && order < best.order))) {
      best = { index: match.index, order, title }
    }
  })
  return best?.title || ''
}

export function parseDescription(text) {
  const source = String(text || '').replace(/\r/g, '').trim()
  if (!source) return { lead: null, cards: [], mode: 'labeled', length: 0 }
  const lines = source.split('\n').map(line => line.trim()).filter(Boolean)
  const labeled = lines.map(line => line.match(LABELED))
  // Вид «Помещение: описание» — если так оформлено большинство строк
  if (labeled.filter(Boolean).length >= Math.max(2, Math.ceil(lines.length * 0.6))) {
    let lead = null
    const cards = []
    lines.forEach((line, i) => {
      const match = labeled[i]
      const card = match ? { title: match[1].trim(), text: match[2].trim() } : { title: '', text: line }
      if (!lead && !cards.length && match && LEAD_TITLES.test(card.title)) lead = card
      else cards.push(card)
    })
    return { lead, cards, mode: 'labeled', length: source.length }
  }
  // Абзацы через пустую строку (одиночные переносы внутри абзаца — часть текста)
  const paragraphs = source.split(/\n\s*\n/).map(p => p.replace(/\s*\n\s*/g, ' ').trim()).filter(Boolean)
  return { lead: null, cards: paragraphs.map(p => ({ title: roomTitle(p), text: p })), mode: 'paragraphs', length: source.length }
}
