<template>
  <div class="calc">
    <div class="calc__field">
      <span class="calc__label">Город</span>
      <div class="calc__regions">
        <button v-for="region in REGIONS" :key="region.key" type="button" :class="{ active: choice.region === region.key }" @click="choice.region = region.key">
          {{ region.label }}
        </button>
      </div>
      <select v-if="choice.region === 'region'" v-model="choice.city" class="calc__input" aria-label="Город">
        <option value="">Выберите город</option>
        <option v-for="city in cities" :key="city" :value="city">{{ city }}</option>
      </select>
    </div>
    <label class="calc__field">
      <span class="calc__label">Площадь объекта, м²</span>
      <input v-model="choice.area" class="calc__input" type="number" inputmode="decimal" min="1" max="2000" step="1" :placeholder="`до ${config.ready_area_base} — базовая цена`" />
    </label>

    <div class="calc__result">
      <div>
        <span class="calc__caption">Стоимость</span>
        <strong class="calc__price">{{ formatPrice(result.price) }}</strong>
      </div>
      <div>
        <span class="calc__caption">Срок</span>
        <strong class="calc__days">{{ formatDays(result.days) }}</strong>
      </div>
    </div>
    <p class="calc__note">
      <template v-if="result.steps">
        {{ formatPrice(result.base) }} за площадь до {{ config.ready_area_base }} м² + {{ formatPrice(result.extra) }} за {{ overArea }} м² сверх неё.
      </template>
      <template v-else-if="hasArea">Площадь до {{ config.ready_area_base }} м² входит в базовую цену.</template>
      <template v-else>Цена для объекта до {{ config.ready_area_base }} м². Укажите площадь, чтобы увидеть точную стоимость и срок.</template>
    </p>
    <a :href="orderUrl" target="_blank" rel="noopener" class="btn btn--accent calc__order">{{ design ? 'Заказать этот дизайн' : 'Заказать готовый дизайн' }}</a>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ctaUrl } from '../contact.js'
import { choice } from '../store.js'
import { REGIONS, calcReady, readyConfig, regionCities, formatPrice, formatDays } from '../readyPricing.js'

const props = defineProps({ settings: Object, design: { type: Object, default: null } })

const config = computed(() => readyConfig(props.settings))
const cities = computed(() => regionCities(props.settings))
const result = computed(() => calcReady(choice.region, choice.area, props.settings))
const hasArea = computed(() => Number(choice.area) > 0)
const overArea = computed(() => Math.round((Number(choice.area) - config.value.ready_area_base) * 10) / 10)

const cityName = computed(() => {
  if (choice.region === 'region') return choice.city || 'другой город'
  return REGIONS.find(region => region.key === choice.region)?.label || ''
})

// В заявку попадает всё, что посетитель выбрал: менеджеру не придётся переспрашивать
const orderUrl = computed(() => {
  const what = props.design ? `готовый дизайн «${props.design.title}»` : 'готовый дизайн'
  const area = hasArea.value ? ` Площадь: ${choice.area} м².` : ''
  const text = `Здравствуйте! Хочу заказать ${what}. Город: ${cityName.value}.${area} Стоимость по калькулятору на сайте: ${formatPrice(result.value.price)}, срок: ${formatDays(result.value.days)}.`
  return ctaUrl(props.settings, text)
})
</script>

<style scoped>
.calc { background: #fff; border: 1px solid var(--border); border-radius: 14px; padding: 28px; display: flex; flex-direction: column; gap: 18px; color: var(--text); }
.calc__field { display: flex; flex-direction: column; gap: 8px; }
.calc__label { font-size: calc(0.78rem * var(--ts, 1)); text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-light); }
.calc__regions { display: flex; flex-wrap: wrap; gap: 8px; }
.calc__regions button {
  flex: 1 1 auto; border: 1px solid var(--border); background: #fff; color: var(--text); border-radius: 8px; padding: 10px 14px; cursor: pointer;
  font-family: inherit; font-size: calc(0.9rem * var(--ts, 1)); transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.calc__regions button:hover { border-color: var(--accent); color: var(--accent); }
.calc__regions button.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.calc__input {
  width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 11px 14px; background: #fff; color: var(--text);
  font-family: inherit; font-size: calc(0.95rem * var(--ts, 1)); outline: none;
}
.calc__input:focus { border-color: var(--accent); }
.calc__result { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 18px 20px; border-radius: 10px; background: color-mix(in srgb, var(--accent) 7%, #fff); }
.calc__result > div { display: flex; flex-direction: column; gap: 2px; }
.calc__caption { font-size: calc(0.78rem * var(--ts, 1)); color: var(--text-light); }
.calc__price { font-family: var(--font-head); font-size: calc(1.7rem * var(--ts, 1)); color: var(--accent); line-height: 1.2; white-space: nowrap; }
.calc__days { font-family: var(--font-head); font-size: calc(1.1rem * var(--ts, 1)); color: var(--dark); line-height: 1.7; }
.calc__note { font-size: calc(0.85rem * var(--ts, 1)); color: var(--text-light); }
.calc__order { text-align: center; }
@media (max-width: 480px) {
  .calc { padding: 20px; }
  .calc__result { grid-template-columns: 1fr; }
}
</style>
