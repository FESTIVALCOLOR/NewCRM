// Тип устройства посетителя: телефон или планшет (сенсорный экран без мыши) либо компьютер.
// От него зависит канал связи на кнопках — на телефоне удобнее сразу позвонить.
import { reactive } from 'vue'

const MOBILE_QUERY = '(hover: none) and (pointer: coarse)'

export const device = reactive({ mobile: false })

if (typeof window !== 'undefined' && window.matchMedia) {
  const query = window.matchMedia(MOBILE_QUERY)
  device.mobile = query.matches
  // Например, планшет с подключённой клавиатурой и мышью
  query.addEventListener?.('change', (event) => { device.mobile = event.matches })
}
