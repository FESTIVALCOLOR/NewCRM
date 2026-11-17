// Преимущества индивидуального дизайна: хранятся одной настройкой individual_advantages в виде JSON-списка
export const ADVANTAGES_KEY = 'individual_advantages'
export const MAX_ADVANTAGES = 9

export const DEFAULT_ADVANTAGES = [
  { title: 'Проект под ваш образ жизни', text: 'Планировка, стиль и материалы подбираются под ваши привычки и состав семьи.' },
  { title: 'Визуализация до ремонта', text: 'Вы видите будущий интерьер в деталях до начала работ.' },
  { title: 'Полный комплект чертежей', text: 'Документация, по которой строители работают без лишних вопросов.' },
  { title: 'Подбор мебели и материалов', text: 'Спецификация с конкретными позициями под ваш бюджет.' },
  { title: 'Авторский надзор', text: 'Следим, чтобы результат совпал с проектом.' },
  { title: 'Работаем по всей России', text: 'Ведём проекты дистанционно и с выездом на объект.' },
]

// Пустая настройка — значения по умолчанию; сохранённый пустой список («[]») — блок скрыт
export function parseAdvantages(settings) {
  const raw = settings?.[ADVANTAGES_KEY]
  if (!raw) return DEFAULT_ADVANTAGES
  try {
    const list = JSON.parse(raw)
    if (!Array.isArray(list)) return DEFAULT_ADVANTAGES
    return list
      .filter(item => item && typeof item.title === 'string' && item.title.trim())
      .slice(0, MAX_ADVANTAGES)
      .map(item => ({ title: item.title.trim(), text: typeof item.text === 'string' ? item.text.trim() : '' }))
  } catch {
    return DEFAULT_ADVANTAGES
  }
}
