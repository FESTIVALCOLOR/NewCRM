<template>
  <section class="tab-body">
    <div class="card-info">
      Страница «Индивидуальный дизайн» состоит из трёх блоков: преимущества (редактируются здесь), портфолио и цены.
      Фотографии портфолио — во вкладке «Портфолио», тарифы — во вкладке «Цены». Скрыть портфолио или цены на странице можно во вкладке «Секции меню».
    </div>

    <div class="card">
      <h3>Тексты страницы и карточки на главной</h3>
      <div class="form-grid">
        <label>Заголовок страницы<input v-model="form.individual_title" placeholder="ИНДИВИДУАЛЬНЫЙ ДИЗАЙН" /></label>
        <label>Текст карточки «Индивидуальный дизайн» на главной<input v-model="form.individual_card_text" placeholder="Проект с нуля под ваш образ жизни, планировку и бюджет." /></label>
      </div>
      <label>Подзаголовок страницы<input v-model="form.individual_subtitle" placeholder="Проект, который создаётся с нуля под вашу квартиру, привычки и бюджет." /></label>
      <label style="margin-top:12px">Фото карточки на главной (пусто — первое фото портфолио)
        <div class="upload-row">
          <input v-model="form.individual_cover_url" placeholder="https://... или загрузите" />
          <button class="btn-sm" @click.prevent="$refs.coverInput.click()">Загрузить</button>
          <input ref="coverInput" type="file" accept="image/jpeg,image/png,image/webp" style="display:none" @change="uploadCover" />
        </div>
      </label>
    </div>

    <div class="card">
      <h3>Краткие преимущества</h3>
      <p class="hint">Короткий заголовок и одна-две строки пояснения. Лучше всего смотрятся 3 или 6 пунктов; максимум — {{ MAX_ADVANTAGES }}. Если удалить все пункты, блок на странице не показывается.</p>
      <div class="adv-list">
        <div v-for="(item, index) in advantages" :key="index" class="adv-row">
          <span class="adv-row__num">{{ index + 1 }}</span>
          <div class="adv-row__fields">
            <input v-model="item.title" maxlength="80" placeholder="Заголовок" />
            <textarea v-model="item.text" rows="2" maxlength="240" placeholder="Пояснение (необязательно)"></textarea>
          </div>
          <div class="adv-row__actions">
            <button class="btn-sm" :disabled="index === 0" title="Выше" @click="move(index, -1)">↑</button>
            <button class="btn-sm" :disabled="index === advantages.length - 1" title="Ниже" @click="move(index, 1)">↓</button>
            <button class="btn-sm btn-danger" title="Удалить" @click="advantages.splice(index, 1)">✕</button>
          </div>
        </div>
      </div>
      <div class="list-toolbar" style="margin:12px 0 16px">
        <button class="btn-sm" :disabled="advantages.length >= MAX_ADVANTAGES" @click="advantages.push({ title: '', text: '' })">+ Добавить пункт</button>
        <button class="btn-sm" @click="resetAdvantages">Вернуть стандартные</button>
      </div>
      <button class="btn-primary" @click="save">Сохранить страницу</button>
    </div>
  </section>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import * as api from './api.js'
import { ADVANTAGES_KEY, DEFAULT_ADVANTAGES, MAX_ADVANTAGES, parseAdvantages } from '../advantages.js'

const props = defineProps({ toast: { type: Function, required: true } })

const form = reactive({ individual_title: '', individual_subtitle: '', individual_card_text: '', individual_cover_url: '' })
const advantages = ref([])

async function load() {
  try {
    const rows = await api.settings.list()
    rows.forEach(row => { if (row.key in form) form[row.key] = row.value || '' })
    const settings = Object.fromEntries(rows.map(row => [row.key, row.value]))
    advantages.value = parseAdvantages(settings).map(item => ({ ...item }))
  } catch (e) { if (e.message !== '401') props.toast('Не удалось загрузить данные: ' + e.message, 'error') }
}

function move(index, delta) {
  const [item] = advantages.value.splice(index, 1)
  advantages.value.splice(index + delta, 0, item)
}
function resetAdvantages() {
  advantages.value = DEFAULT_ADVANTAGES.map(item => ({ ...item }))
  props.toast('Стандартные пункты подставлены в форму — нажмите «Сохранить страницу», чтобы применить их на сайте')
}
async function uploadCover(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file) return
  try { form.individual_cover_url = (await api.portfolio.upload(file)).url } catch (err) { props.toast('Ошибка загрузки: ' + err.message, 'error') }
}
async function save() {
  const list = advantages.value.map(item => ({ title: item.title.trim(), text: (item.text || '').trim() }))
  const untitled = list.findIndex(item => !item.title)
  if (untitled >= 0) { props.toast(`У пункта ${untitled + 1} нет заголовка — заполните его или удалите пункт`, 'error'); return }
  try {
    for (const key of Object.keys(form)) await api.settings.update(key, form[key].trim())
    await api.settings.update(ADVANTAGES_KEY, JSON.stringify(list))
    props.toast('Сохранено — обновите страницу сайта, чтобы увидеть изменения')
  } catch (e) { props.toast(e.message, 'error') }
}

onMounted(load)
</script>

<style scoped>
.adv-list { display: flex; flex-direction: column; gap: 10px; }
.adv-row { display: flex; gap: 12px; align-items: flex-start; }
.adv-row__num { flex: 0 0 26px; height: 26px; margin-top: 4px; border-radius: 50%; background: #f3f4f6; color: #6b7280; font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.adv-row__fields { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.adv-row__fields input, .adv-row__fields textarea { border: 1px solid #d9d9d9; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; font-family: inherit; outline: none; }
.adv-row__fields input:focus, .adv-row__fields textarea:focus { border-color: #c0392b; }
.adv-row__actions { display: flex; gap: 4px; margin-top: 4px; }
</style>
