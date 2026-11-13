// Запуск: npm test (в папке landing)
import test from 'node:test'
import assert from 'node:assert/strict'

import { ctaChannel, ctaUrl, linkTarget, missingFor, DEFAULT_EMAIL } from '../src/contact.js'

const full = { whatsapp_phone: '79992800700', telegram: '@festivalcolor', phone: '+7 (999) 2 800 700', email: 'info@example.ru' }

test('выбранный канал используется, если для него есть данные', () => {
  assert.equal(ctaUrl({ ...full, cta_method: 'telegram' }), 'https://t.me/festivalcolor')
  assert.equal(ctaUrl({ ...full, cta_method: 'phone' }), 'tel:+79992800700')
  assert.equal(ctaUrl({ ...full, cta_method: 'email' }, 'Заказ'), 'mailto:info@example.ru?subject=%D0%97%D0%B0%D0%BA%D0%B0%D0%B7')
  assert.equal(ctaUrl({ ...full, cta_method: 'whatsapp' }, 'Привет'), 'https://wa.clck.bar/79992800700?text=%D0%9F%D1%80%D0%B8%D0%B2%D0%B5%D1%82')
})

test('без ника Telegram или телефона кнопки ведут в WhatsApp, и панель знает почему', () => {
  const noTelegram = { ...full, telegram: '', cta_method: 'telegram' }
  assert.equal(ctaChannel(noTelegram), 'whatsapp')
  assert.equal(missingFor('telegram', noTelegram), 'не указан ник Telegram')
  assert.equal(ctaChannel({ ...full, phone: '', cta_method: 'phone' }), 'whatsapp')
})

test('почта без своего адреса берётся та же, что в блоке «Контакты»', () => {
  const settings = { ...full, email: '', cta_method: 'email' }
  assert.equal(ctaChannel(settings), 'email')
  assert.equal(ctaUrl(settings), `mailto:${DEFAULT_EMAIL}`)
})

test('ник Telegram записан ссылкой или с @', () => {
  assert.equal(ctaUrl({ telegram: 'https://t.me/studio', cta_method: 'telegram' }), 'https://t.me/studio')
  assert.equal(ctaUrl({ telegram: ' @studio ', cta_method: 'telegram' }), 'https://t.me/studio')
})

test('неизвестный канал — WhatsApp', () => {
  assert.equal(ctaChannel({ cta_method: 'pigeon' }), 'whatsapp')
  assert.equal(ctaChannel(undefined), 'whatsapp')
})

test('звонок и письмо открываются без новой вкладки', () => {
  assert.equal(linkTarget('https://t.me/x'), '_blank')
  assert.equal(linkTarget('tel:+7999'), null)
  assert.equal(linkTarget('mailto:a@b.ru'), null)
})
