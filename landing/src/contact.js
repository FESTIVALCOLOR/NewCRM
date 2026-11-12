const DEFAULT_WHATSAPP = '79062003365'

export function whatsappUrl(settings, text) {
  const phone = String(settings?.whatsapp_phone || DEFAULT_WHATSAPP).replace(/\D/g, '')
  const query = text ? `?text=${encodeURIComponent(text)}` : ''
  return `https://wa.clck.bar/${phone}${query}`
}

// Ссылка для кнопок «Написать нам» — зависит от способа связи, выбранного в админке
export function ctaUrl(settings, text) {
  const s = settings || {}
  if (s.cta_method === 'telegram' && s.telegram) return `https://t.me/${s.telegram.replace(/^@/, '')}`
  if (s.cta_method === 'phone' && s.phone) return `tel:${s.phone.replace(/[^\d+]/g, '')}`
  if (s.cta_method === 'email' && s.email) {
    return `mailto:${s.email}${text ? `?subject=${encodeURIComponent(text)}` : ''}`
  }
  return whatsappUrl(s, text)
}
