import test from 'node:test'
import assert from 'node:assert/strict'

import { parseDescription, roomTitle } from '../src/designDescription.js'

test('строки «Помещение: описание» — карточки, «Гамма» — вводный абзац', () => {
  const result = parseDescription('Гамма: Теплый светлый интерьер.\nПрихожая: Белая мебель. \nВанная комната и санузел: : Плитка под мрамор.\nДетская: Голубые стены.')
  assert.equal(result.mode, 'labeled')
  assert.deepEqual(result.lead, { title: 'Гамма', text: 'Теплый светлый интерьер.' })
  assert.deepEqual(result.cards.map(c => c.title), ['Прихожая', 'Ванная комната и санузел', 'Детская'])
  // Лишнее двоеточие («санузел: : Плитка») не попадает в текст
  assert.equal(result.cards[1].text, 'Плитка под мрамор.')
})

test('абзацы через пустую строку — карточки с заголовком по комнате из первой фразы', () => {
  const text = [
    'Прихожая вмещает только необходимое.',
    'Пространство кухни-гостиной открытое, без дверей. Духовой шкаф на уровне плеч.',
    'Еще одна комната решена удобно и минималистично.',
    'В отдельных помещениях санузел и душевая.',
  ].join('\n\n')
  const result = parseDescription(text)
  assert.equal(result.mode, 'paragraphs')
  assert.deepEqual(result.cards.map(c => c.title), ['Прихожая', 'Кухня-гостиная', '', 'Санузел'])
})

test('предложение с двоеточием внутри абзаца не считается заголовком', () => {
  const result = parseDescription('Освещение: трековые светильники и бра.\n\nВ зоне гостиной мягкий диван. Цвета: песочный и молочный.')
  assert.equal(result.mode, 'paragraphs')
})

test('комната определяется по первому упоминанию в первой фразе', () => {
  assert.equal(roomTitle('За панорамной стеклянной стеной находится пространство гостиной. Кухня рядом.'), 'Гостиная')
  assert.equal(roomTitle('Кухня-столовая отделена стеклянной перегородкой.'), 'Кухня-столовая')
  assert.equal(roomTitle('Гостевая комната своими решениями напоминает итальянский дизайн.'), 'Гостевая комната')
  assert.equal(roomTitle('Современное пространство при входе с темно-серой поверхностью.'), '')
})

test('пустое описание', () => {
  assert.deepEqual(parseDescription('  ').cards, [])
})
