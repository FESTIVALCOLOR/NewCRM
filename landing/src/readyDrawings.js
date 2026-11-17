// «Что входит в комплект чертежей» для готового дизайна: рубрики хранятся одной настройкой ready_drawings (JSON).
// Состав взят из шаблона состава «Шаблонный — Стандарт» в CRM (Приложение № 2 к договору).
export const DRAWINGS_KEY = 'ready_drawings'
export const MAX_DRAWINGS = 12

export const DEFAULT_DRAWINGS = [
  { title: 'Планировочное решение', text: 'Три варианта планировки на выбор и утверждённая расстановка мебели с размерами' },
  { title: 'Монтаж и демонтаж стен', text: 'Какие перегородки снести, а какие построить, — с привязками и размерами' },
  { title: 'Электрооборудование', text: 'Розетки и выключатели с высотами и привязками к стенам' },
  { title: 'Освещение', text: 'Где стоит каждый светильник и как он подключается к выключателям' },
  { title: 'Сантехническое оборудование', text: 'Расположение сантехники с размерами для разводки воды и канализации' },
  { title: 'Полы', text: 'Покрытия по помещениям и тёплые полы с размерами*' },
  { title: 'Потолки', text: 'Уровни, конструкции и размеры потолков в каждой комнате' },
  { title: 'Отделочные работы', text: 'Черновая и чистовая отделка стен — что и где выполняется' },
  { title: 'Развёртки стен', text: 'Каждая стена по помещениям, в ванной и санузле — с раскладкой плитки' },
  { title: 'Мебель и декор', text: 'Ведомость мебели и материалов выбранного дизайна и смета товаров' },
]
export const DEFAULT_DRAWINGS_NOTE = '* При необходимости'

// Пустая настройка — рубрики по умолчанию; сохранённый пустой список («[]») — блок скрыт
export function parseDrawings(settings) {
  const raw = settings?.[DRAWINGS_KEY]
  if (!raw) return DEFAULT_DRAWINGS
  try {
    const list = JSON.parse(raw)
    if (!Array.isArray(list)) return DEFAULT_DRAWINGS
    return list
      .filter(item => item && typeof item.title === 'string' && item.title.trim())
      .slice(0, MAX_DRAWINGS)
      .map(item => ({ title: item.title.trim(), text: typeof item.text === 'string' ? item.text.trim() : '' }))
  } catch {
    return DEFAULT_DRAWINGS
  }
}
