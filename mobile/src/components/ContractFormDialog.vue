<template>
  <q-dialog
    v-model="show"
    persistent
    maximized
    transition-show="slide-up"
    transition-hide="slide-down"
  >
    <q-card>
      <q-toolbar style="background: #ffd93c; color: #333">
        <q-btn
          flat
          round
          dense
          icon="close"
          @click="close"
        />
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
          {{ isEdit ? 'Редактировать договор' : 'Новый договор' }}
        </q-toolbar-title>
        <q-btn
          label="Сохранить"
          no-caps
          :loading="saving"
          outline
          style="border: 1px solid #333; border-radius: 8px; color: #333"
          @click="save"
        />
      </q-toolbar>

      <q-card-section class="q-pa-md" style="max-height: calc(100vh - 50px); overflow-y: auto">
        <q-form ref="formRef" class="q-gutter-md">
          <!-- Клиент -->
          <q-select
            v-if="!isEdit"
            v-model="form.client_id"
            :options="clientOptions"
            option-value="id"
            option-label="label"
            label="Клиент *"
            outlined
            dense
            emit-value
            map-options
            use-input
            input-debounce="200"
            :rules="[val => !!val || 'Выберите клиента']"
            @filter="filterClients"
          >
            <template #no-option>
              <q-item>
                <q-item-section class="text-grey">
                  Не найдено
                </q-item-section>
              </q-item>
            </template>
          </q-select>

          <!-- Номер договора -->
          <q-input
            v-model="form.contract_number"
            label="Номер договора *"
            outlined
            dense
            :rules="[val => !!val || 'Обязательное поле']"
          />

          <!-- Тип проекта -->
          <q-select
            v-model="form.project_type"
            :options="['Индивидуальный', 'Шаблонный', 'Авторский надзор']"
            label="Тип проекта *"
            outlined
            dense
            :rules="[val => !!val || 'Выберите тип']"
            @update:model-value="onProjectTypeChange"
          />

          <!-- Подтип проекта -->
          <q-select
            v-model="form.project_subtype"
            :options="subtypeOptions"
            label="Подтип проекта"
            outlined
            dense
          />

          <!-- Адрес -->
          <q-input v-model="form.address" label="Адрес объекта" outlined dense />

          <!-- Город -->
          <q-select
            v-model="form.city"
            :options="cityOptions"
            label="Город *"
            outlined
            dense
          />

          <!-- Тип агента -->
          <q-select
            v-model="form.agent_type"
            :options="agentOptions"
            label="Тип агента"
            outlined
            dense
            use-input
            new-value-mode="add"
          />

          <!-- Статус -->
          <q-select
            v-if="isEdit"
            v-model="form.status"
            :options="statusOptions"
            label="Статус"
            outlined
            dense
          />

          <!-- Площадь -->
          <q-input
            v-model.number="form.area"
            label="Площадь (м²) *"
            outlined
            dense
            type="number"
            :rules="[val => val > 0 || 'Укажите площадь']"
            @update:model-value="recalcPeriod"
          />

          <!-- Этажность (только для шаблонных) -->
          <q-input
            v-if="form.project_type === 'Шаблонный'"
            v-model.number="form.floors"
            label="Этажей"
            outlined
            dense
            type="number"
            @update:model-value="recalcPeriod"
          />

          <!-- Дата договора -->
          <q-input
            v-model="form.contract_date"
            label="Дата договора"
            outlined
            dense
            type="date"
          />

          <!-- Срок выполнения (авторасчёт / ручной) -->
          <div>
            <div class="row items-center q-gutter-xs q-mb-xs">
              <div class="text-caption text-weight-bold" style="color: #333">
                Срок выполнения (раб. дней)
              </div>
              <q-badge :color="manualPeriod ? 'orange' : 'positive'" :label="manualPeriod ? 'Ручной' : 'Авто'" dense style="font-size: 9px" />
              <q-btn
                flat
                dense
                size="xs"
                :label="manualPeriod ? 'Авто' : 'Вручную'"
                no-caps
                style="font-size: 10px; color: #666"
                @click="toggleManualPeriod"
              />
            </div>
            <q-input
              v-model.number="form.contract_period"
              outlined
              dense
              type="number"
              :disable="!manualPeriod"
            />
          </div>

          <div class="text-subtitle2 text-weight-bold q-mt-md" style="color: #333">
            Финансы
          </div>

          <q-input
            v-model.number="form.total_amount"
            label="Общая сумма"
            outlined
            dense
            type="number"
            prefix="₽"
          />
          <q-input
            v-model.number="form.advance_payment"
            label="Аванс"
            outlined
            dense
            type="number"
            prefix="₽"
          />
          <q-input
            v-model.number="form.additional_payment"
            label="Доп. оплата"
            outlined
            dense
            type="number"
            prefix="₽"
          />
          <q-input
            v-model.number="form.third_payment"
            label="Третий платёж"
            outlined
            dense
            type="number"
            prefix="₽"
          />

          <q-input
            v-model="form.comments"
            label="Комментарий"
            outlined
            dense
            type="textarea"
            autogrow
          />
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { contractsApi, clientsApi } from 'src/services/api'
import { api } from 'src/boot/axios'
import { useReferencesStore } from 'src/stores/references'

const PROJECT_SUBTYPES = ['Полный (с 3д визуализацией)', 'Эскизный (с коллажами)', 'Планировочный']
const TEMPLATE_SUBTYPES = ['Стандарт', 'Стандарт с визуализацией', 'Проект ванной комнаты', 'Проект ванной комнаты с визуализацией']

const props = defineProps({ modelValue: Boolean, contract: { type: Object, default: null } })
const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const refs = useReferencesStore()
const show = ref(false)
const saving = ref(false)
const formRef = ref(null)
const isEdit = ref(false)
const clientOptions = ref([])
const manualPeriod = ref(false)

const today = new Date().toISOString().split('T')[0]

const emptyForm = () => ({
  client_id: null, contract_number: '', project_type: 'Индивидуальный', project_subtype: '',
  address: '', city: 'МСК', area: null, floors: 1, agent_type: '',
  contract_date: today, contract_period: 45,
  total_amount: null, advance_payment: null, additional_payment: null, third_payment: null,
  status: 'Новый заказ', comments: '',
})

const form = ref(emptyForm())

const statusOptions = refs.contractStatuses
const cityOptions = refs.cities
const agentOptions = refs.agentNames()

// Подтипы зависят от типа проекта
const subtypeOptions = computed(() => {
  if (form.value.project_type === 'Шаблонный') return TEMPLATE_SUBTYPES
  return PROJECT_SUBTYPES
})

watch(() => props.modelValue, (val) => {
  show.value = val
  if (val && props.contract) {
    isEdit.value = true
    form.value = { ...emptyForm(), ...props.contract }
    manualPeriod.value = false
  } else if (val) {
    isEdit.value = false
    form.value = emptyForm()
    manualPeriod.value = false
  }
})
watch(show, (val) => emit('update:modelValue', val))

function close() { show.value = false }

function onProjectTypeChange() {
  // Сброс подтипа при смене типа
  form.value.project_subtype = subtypeOptions.value[0] || ''
  recalcPeriod()
}

function toggleManualPeriod() {
  manualPeriod.value = !manualPeriod.value
  if (!manualPeriod.value) recalcPeriod()
}

function recalcPeriod() {
  if (manualPeriod.value) return
  const area = form.value.area
  if (!area || area <= 0) return

  let term = 0
  if (form.value.project_type === 'Шаблонный') {
    term = calcTemplateTerm(form.value.project_subtype || '', area, form.value.floors || 1)
  } else {
    const ptCode = getPtCode(form.value.project_subtype || '')
    term = calcIndividualTerm(ptCode, area)
  }
  if (term > 0) form.value.contract_period = term
}

function getPtCode(subtype) {
  if (subtype.includes('Полный')) return 1
  if (subtype.includes('Планировочный')) return 3
  return 2
}

function calcIndividualTerm(ptCode, area) {
  const tables = {
    1: [[70,50],[100,60],[130,70],[160,80],[190,90],[220,100],[250,110],[300,120],[350,130],[400,140],[450,150],[500,160]],
    3: [[70,10],[100,15],[130,20],[160,25],[190,30],[220,35],[250,40],[300,45],[350,50],[400,55],[450,60],[500,65]],
    2: [[70,30],[100,35],[130,40],[160,45],[190,50],[220,55],[250,60],[300,65],[350,70],[400,75],[450,80],[500,85]],
  }
  const thresholds = tables[ptCode] || tables[2]
  for (const [maxArea, days] of thresholds) {
    if (area <= maxArea) return days
  }
  return thresholds[thresholds.length - 1][1]
}

function calcTemplateTerm(subtype, area, floors) {
  const sub = subtype.toLowerCase()
  const hasViz = sub.includes('визуализац')
  if (sub.includes('ванн')) return hasViz ? 20 : 10

  let baseDays = 20
  if (area > 90) {
    const extra = Math.floor((area - 91) / 50) + 1
    baseDays = 20 + extra * 10
  }
  if (floors > 1) {
    baseDays += (floors - 1) * (hasViz ? 20 : 10)
  }
  if (hasViz) {
    if (area <= 90) baseDays += 25
    else baseDays += 25 + (Math.floor((area - 91) / 50) + 1) * 15
  }
  return Math.round(baseDays)
}

async function filterClients(val, update) {
  try {
    const params = val ? { search: val, search_type: 'all', limit: 20 } : { limit: 20 }
    const { data } = await clientsApi.getList(params)
    update(() => {
      clientOptions.value = data.map(c => ({
        id: c.id, label: `${c.full_name}${c.organization_name ? ' (' + c.organization_name + ')' : ''}`,
      }))
    })
  } catch { update(() => { clientOptions.value = [] }) }
}

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      await contractsApi.update(props.contract.id, form.value)

      // Всегда пересчитываем yandex_folder_path из текущих данных формы
      // (как десктоп contract_dialogs.py:4460-4474)
      const c = form.value
      const agent = c.agent_type || 'ФЕСТИВАЛЬ'
      const ptype = c.project_type || 'Индивидуальный'
      const city = c.city || 'МСК'
      const addr = (c.address || '').replace(/[/\\<>:"|?*]/g, '-')
      const rawArea = c.area || 0
      const area = Number.isInteger(Number(rawArea)) ? Number(rawArea).toFixed(1) : rawArea
      const typeFolder = ptype.includes('ндивид') ? 'Индивидуальные' : 'Шаблонные'
      const newPath = `disk:/CRM/Проекты/${agent}/${typeFolder}/${city}/${city}-${addr}-${area}м2`

      // Загружаем свежие данные из БД (yandex_folder_path мог измениться)
      let oldPath = ''
      try {
        const { data: fresh } = await contractsApi.getById(props.contract.id)
        oldPath = fresh.yandex_folder_path || ''
      } catch {}

      if (oldPath !== newPath) {
        try {
          if (oldPath) {
            // Пробуем переименовать
            await api.post('/api/v1/files/move-folder', null, { params: { from_path: oldPath, to_path: newPath } })
          } else {
            // Папки не было — создаём
            await api.post('/api/v1/files/folder', null, { params: { folder_path: newPath } })
          }
        } catch {
          // move не удался — создаём новую
          try { await api.post('/api/v1/files/folder', null, { params: { folder_path: newPath } }) } catch {}
        }
        // Обновляем путь в БД
        try { await contractsApi.update(props.contract.id, { yandex_folder_path: newPath }) } catch {}
        // Создаём подпапки (как десктоп create_document_subfolders + create_stage_folders)
        const subs = ['Документы', 'Документы/Акты', 'Документы/Информационные письма', 'Документы/Доп. соглашения',
          'Анкета', 'Замер', 'Референсы', 'Фотофиксация',
          '1 стадия - Планировочное решение', '2 стадия - Концепция дизайна',
          '2 стадия - Концепция дизайна/Концепция-коллажи', '2 стадия - Концепция дизайна/3D визуализация',
          '3 стадия - Чертежный проект']
        for (const s of subs) { try { await api.post('/api/v1/files/folder', null, { params: { folder_path: `${newPath}/${s}` } }) } catch {} }
      }
      $q.notify({ type: 'positive', message: 'Договор обновлён' })
    } else {
      const { data: newContract } = await contractsApi.create(form.value)
      // Создаём папку на ЯД сразу (как десктоп)
      if (newContract?.id) {
        try { await api.post(`/api/v1/contracts/${newContract.id}/fix-folder`) } catch {}
      }
      $q.notify({ type: 'positive', message: 'Договор создан' })
    }
    emit('saved')
    close()
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка сохранения' })
  } finally { saving.value = false }
}
</script>
