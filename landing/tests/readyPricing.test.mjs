// Запуск: node --test landing/tests/
import test from 'node:test'
import assert from 'node:assert/strict'

import { calcReady, extraSteps, formatDays, formatPrice, minReadyPrice, readyConfig, regionCities, DEFAULT_REGION_CITIES } from '../src/readyPricing.js'

test('базовая цена зависит от города', () => {
  assert.equal(calcReady('msk', 60).price, 45990)
  assert.equal(calcReady('spb', 60).price, 42990)
  assert.equal(calcReady('region', 60).price, 40990)
})

test('до 90 м² включительно доплаты нет, срок 20 рабочих дней', () => {
  for (const area of [1, 45, 89.9, 90]) {
    const result = calcReady('msk', area)
    assert.equal(result.extra, 0)
    assert.equal(result.days, 20)
  }
})

test('свыше 90 м²: 23 990 ₽ и 10 дней за каждые начатые 50 м²', () => {
  assert.deepEqual(calcReady('msk', 91), { base: 45990, extra: 23990, steps: 1, price: 69980, days: 30 })
  assert.equal(calcReady('msk', 140).steps, 1)
  assert.equal(calcReady('msk', 141).steps, 2)
  assert.deepEqual(calcReady('region', 190), { base: 40990, extra: 47980, steps: 2, price: 88970, days: 40 })
  assert.equal(calcReady('spb', 240.5).price, 42990 + 4 * 23990)
})

test('пустая или некорректная площадь считается как базовая', () => {
  for (const area of ['', null, undefined, 'abc', -5, 0]) assert.equal(calcReady('spb', area).price, 42990)
  assert.equal(calcReady('spb', '120,5').steps, 1)
})

test('незнакомый регион считается как Москва', () => {
  assert.equal(calcReady('nowhere', 50).price, 45990)
})

test('цены и шаги берутся из настроек сайта, мусор заменяется значениями по умолчанию', () => {
  const settings = { ready_price_msk: '50 000', ready_area_base: '100', ready_area_step: '', ready_days_step: 'x', ready_area_step_price: '-1' }
  const config = readyConfig(settings)
  assert.equal(config.ready_price_msk, 50000)
  assert.equal(config.ready_area_step, 50)
  assert.equal(config.ready_area_step_price, 23990)
  assert.equal(calcReady('msk', 100, settings).price, 50000)
  assert.deepEqual(calcReady('msk', 101, settings), { base: 50000, extra: 23990, steps: 1, price: 73990, days: 30 })
  assert.equal(extraSteps(151, config), 2)
})

test('цена «от» — самая низкая из трёх', () => {
  assert.equal(minReadyPrice({}), 40990)
  assert.equal(minReadyPrice({ ready_price_spb: '30000' }), 30000)
})

test('список городов: свой из настроек или по умолчанию', () => {
  assert.equal(regionCities({}), DEFAULT_REGION_CITIES)
  assert.deepEqual(regionCities({ ready_region_cities: ' Казань \n\nУфа\r\nКазань\n' }), ['Казань', 'Уфа'])
  assert.ok(!DEFAULT_REGION_CITIES.includes('Москва') && !DEFAULT_REGION_CITIES.includes('Санкт-Петербург'))
})

test('формат цены и срока', () => {
  assert.equal(formatPrice(45990), '45 990 ₽')
  assert.equal(formatPrice(137950), '137 950 ₽')
  assert.equal(formatDays(20), '20 рабочих дней')
  assert.equal(formatDays(21), '21 рабочий день')
  assert.equal(formatDays(32), '32 рабочих дня')
  assert.equal(formatDays(111), '111 рабочих дней')
})
