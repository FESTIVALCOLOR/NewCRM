// Окно заявки для кнопок «Заказать» / «Заказать готовый дизайн»: одно на весь сайт
import { reactive } from 'vue'

export const lead = reactive({ open: false, title: '', source: '', context: {} })

// context — что выбрал посетитель (дизайн, тариф, город, площадь, цена, срок): менеджеру не придётся переспрашивать
export function openLead({ title = 'Оставить заявку', source = '', context = {} } = {}) {
  Object.assign(lead, { open: true, title, source, context: { ...context, page: window.location.href } })
}

export function closeLead() {
  lead.open = false
}

export async function sendLead(form) {
  const res = await fetch('/api/v1/site/leads', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...form, source: lead.source, context: lead.context }),
  })
  if (res.status === 429) throw new Error('Слишком много заявок подряд. Попробуйте через минуту.')
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Не удалось отправить заявку. Попробуйте ещё раз или позвоните нам.')
  }
}
