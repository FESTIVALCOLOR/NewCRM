// Каналы связи для кнопок «Написать нам», «Заказать» и плавающей кнопки.
// Канал выбирается в панели («Настройки» → «Способ связи»).

const DEFAULT_WHATSAPP = '79062003365'
// Та же почта, что показана в блоке «Контакты», если своя не указана
export const DEFAULT_EMAIL = 'festivalcolor@mail.ru'

export const CHANNELS = {
  whatsapp: {
    label: 'WhatsApp',
    color: '#25D366',
    icon: 'M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z',
  },
  telegram: {
    label: 'Telegram',
    color: '#229ED9',
    icon: 'M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z',
  },
  phone: {
    label: 'Позвонить',
    color: 'var(--accent)',
    icon: 'M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z',
  },
  email: {
    label: 'Написать на почту',
    color: 'var(--accent)',
    icon: 'M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z',
  },
}

export function whatsappUrl(settings, text) {
  const phone = String(settings?.whatsapp_phone || DEFAULT_WHATSAPP).replace(/\D/g, '')
  const query = text ? `?text=${encodeURIComponent(text)}` : ''
  return `https://wa.clck.bar/${phone}${query}`
}

function telegramName(settings) {
  return String(settings?.telegram || '').trim().replace(/^@/, '').replace(/^https?:\/\/t\.me\//i, '')
}

// Чего не хватает выбранному каналу; пустая строка — данных достаточно
export function missingFor(method, settings) {
  if (method === 'telegram' && !telegramName(settings)) return 'не указан ник Telegram'
  if (method === 'phone' && !String(settings?.phone || '').replace(/[^\d+]/g, '')) return 'не указан телефон'
  return ''
}

// Канал, который реально используется: выбранный, а если для него нет данных — WhatsApp
export function ctaChannel(settings) {
  const chosen = CHANNELS[settings?.cta_method] ? settings.cta_method : 'whatsapp'
  return missingFor(chosen, settings) ? 'whatsapp' : chosen
}

// Ссылка для кнопок «Написать нам» — зависит от способа связи, выбранного в админке
export function ctaUrl(settings, text) {
  const s = settings || {}
  const method = ctaChannel(s)
  if (method === 'telegram') return `https://t.me/${telegramName(s)}`
  if (method === 'phone') return `tel:${s.phone.replace(/[^\d+]/g, '')}`
  if (method === 'email') return `mailto:${s.email || DEFAULT_EMAIL}${text ? `?subject=${encodeURIComponent(text)}` : ''}`
  return whatsappUrl(s, text)
}

// Мессенджеры открываются в новой вкладке, а звонок и письмо — без неё: иначе остаётся пустая вкладка
export function linkTarget(url) {
  return /^https?:/i.test(String(url || '')) ? '_blank' : null
}
