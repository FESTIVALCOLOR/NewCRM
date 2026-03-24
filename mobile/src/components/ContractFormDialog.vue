<template>
  <q-dialog v-model="show" persistent maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card>
      <q-toolbar style="background: #ffd93c; color: #333">
        <q-btn flat round dense icon="close" @click="close" />
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
          {{ isEdit ? 'Редактировать договор' : 'Новый договор' }}
        </q-toolbar-title>
        <q-btn label="Сохранить" no-caps @click="save" :loading="saving" outline style="border: 1px solid #333; border-radius: 8px; color: #333" />
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
            @filter="filterClients"
            :rules="[val => !!val || 'Выберите клиента']"
          >
            <template v-slot:no-option>
              <q-item><q-item-section class="text-grey">Не найдено</q-item-section></q-item>
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
          />

          <!-- Адрес -->
          <q-input v-model="form.address" label="Адрес объекта" outlined dense />

          <!-- Город -->
          <q-select v-model="form.city" :options="cityOptions" label="Город" outlined dense use-input new-value-mode="add" />

          <!-- Тип агента -->
          <q-select v-model="form.agent_type" :options="agentOptions" label="Тип агента" outlined dense use-input new-value-mode="add" />

          <!-- Статус -->
          <q-select v-if="isEdit" v-model="form.status" :options="statusOptions" label="Статус" outlined dense />

          <!-- Площадь -->
          <q-input
            v-model.number="form.area"
            label="Площадь (м²) *"
            outlined
            dense
            type="number"
            :rules="[val => val > 0 || 'Укажите площадь']"
          />

          <!-- Этажность -->
          <q-input v-model.number="form.floors" label="Этажей" outlined dense type="number" />

          <!-- Дата договора -->
          <q-input v-model="form.contract_date" label="Дата договора" outlined dense type="date" />

          <!-- Срок выполнения -->
          <q-input v-model.number="form.contract_period" label="Срок выполнения (дней)" outlined dense type="number" />

          <div class="text-subtitle2 text-weight-bold q-mt-md">Финансы</div>

          <q-input v-model.number="form.total_amount" label="Общая сумма" outlined dense type="number" prefix="₽" />
          <q-input v-model.number="form.advance_payment" label="Аванс" outlined dense type="number" prefix="₽" />
          <q-input v-model.number="form.additional_payment" label="Доп. оплата" outlined dense type="number" prefix="₽" />
          <q-input v-model.number="form.third_payment" label="Третий платёж" outlined dense type="number" prefix="₽" />

          <q-input v-model="form.comments" label="Комментарий" outlined dense type="textarea" autogrow />
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { contractsApi, clientsApi } from 'src/services/api'
import { useReferencesStore } from 'src/stores/references'

const props = defineProps({
  modelValue: Boolean,
  contract: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const refs = useReferencesStore()
const show = ref(false)
const saving = ref(false)
const formRef = ref(null)
const isEdit = ref(false)
const clientOptions = ref([])

const today = new Date().toISOString().split('T')[0]

const emptyForm = () => ({
  client_id: null,
  contract_number: '',
  project_type: 'Индивидуальный',
  address: '',
  city: 'Москва',
  area: null,
  floors: 1,
  agent_type: '',
  contract_date: today,
  contract_period: 45,
  total_amount: null,
  advance_payment: null,
  additional_payment: null,
  third_payment: null,
  status: 'Новый заказ',
  comments: ''
})

const form = ref(emptyForm())

const statusOptions = refs.contractStatuses
const cityOptions = refs.cities
const agentOptions = refs.agentNames()

watch(() => props.modelValue, (val) => {
  show.value = val
  if (val && props.contract) {
    isEdit.value = true
    form.value = { ...emptyForm(), ...props.contract }
  } else if (val) {
    isEdit.value = false
    form.value = emptyForm()
  }
})

watch(show, (val) => emit('update:modelValue', val))

function close() {
  show.value = false
}

async function filterClients(val, update) {
  try {
    const params = val ? { search: val, search_type: 'all', limit: 20 } : { limit: 20 }
    const { data } = await clientsApi.getList(params)
    update(() => {
      clientOptions.value = data.map(c => ({
        id: c.id,
        label: `${c.full_name}${c.organization_name ? ' (' + c.organization_name + ')' : ''}`
      }))
    })
  } catch {
    update(() => { clientOptions.value = [] })
  }
}

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  saving.value = true
  try {
    if (isEdit.value) {
      await contractsApi.update(props.contract.id, form.value)
      $q.notify({ type: 'positive', message: 'Договор обновлён' })
    } else {
      await contractsApi.create(form.value)
      $q.notify({ type: 'positive', message: 'Договор создан' })
    }
    emit('saved')
    close()
  } catch (err) {
    const msg = err.response?.data?.detail || 'Ошибка сохранения'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    saving.value = false
  }
}
</script>
