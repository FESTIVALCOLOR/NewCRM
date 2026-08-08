<template>
  <!-- Действия с CRM карточкой -->
  <q-dialog v-model="show" position="bottom">
    <q-card style="width: 100%; max-width: 500px">
      <q-card-section class="q-pb-none">
        <div class="text-subtitle1 text-weight-bold">
          Действия
        </div>
      </q-card-section>

      <q-list>
        <!-- Переместить в колонку -->
        <q-expansion-item v-if="can('crm_cards.move')" icon="swap_horiz" label="Переместить" dense>
          <q-list dense class="q-pl-md">
            <q-item
              v-for="col in availableColumns"
              :key="col"
              v-ripple
              clickable
              :disable="col === card?.column_name"
              @click="moveToColumn(col)"
            >
              <q-item-section>
                <q-item-label :class="{ 'text-grey-5': col === card?.column_name }">
                  {{ col }}
                </q-item-label>
              </q-item-section>
              <q-item-section v-if="col === card?.column_name" side>
                <q-icon name="check" color="primary" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-expansion-item>

        <!-- Назначить исполнителя -->
        <q-expansion-item v-if="can('crm_cards.assign_executor')" icon="person_add" label="Назначить исполнителя" dense>
          <div class="q-pa-md">
            <q-select
              v-model="assignForm.stage_name"
              :options="stageOptions"
              label="Стадия"
              outlined
              dense
              class="q-mb-sm"
            />
            <q-select
              v-model="assignForm.executor_id"
              :options="employeeOptions"
              option-value="id"
              option-label="label"
              label="Исполнитель"
              outlined
              dense
              emit-value
              map-options
              class="q-mb-sm"
            />
            <q-input
              v-model="assignForm.deadline"
              label="Дедлайн"
              outlined
              dense
              type="date"
              class="q-mb-sm"
            />
            <q-btn
              color="primary"
              label="Назначить"
              no-caps
              unelevated
              class="full-width"
              :loading="actionLoading"
              @click="assignExecutor"
            />
          </div>
        </q-expansion-item>

        <!-- Изменить дедлайн -->
        <q-expansion-item v-if="can('crm_cards.deadlines')" icon="event" label="Изменить дедлайн" dense>
          <div class="q-pa-md">
            <q-input
              v-model="newDeadline"
              label="Новый дедлайн"
              outlined
              dense
              type="date"
              class="q-mb-sm"
            />
            <q-btn
              color="primary"
              label="Сохранить"
              no-caps
              unelevated
              class="full-width"
              :loading="actionLoading"
              @click="updateCardDeadline"
            />
          </div>
        </q-expansion-item>
      </q-list>

      <q-card-actions align="center" class="q-pt-none">
        <q-btn
          v-close-popup
          flat
          label="Закрыть"
          no-caps
          color="grey-7"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { crmApi, employeesApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'

const { can } = usePermission()

const props = defineProps({
  modelValue: Boolean,
  card: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'updated'])

const $q = useQuasar()
const show = ref(false)
const actionLoading = ref(false)
const newDeadline = ref('')
const employeeOptions = ref([])

const assignForm = ref({
  stage_name: '',
  executor_id: null,
  deadline: '',
})

const COLUMNS_INDIVIDUAL = [
  'Новый заказ', 'В ожидании',
  'Стадия 1: планировочные решения',
  'Стадия 2: концепция дизайна',
  'Стадия 3: рабочие чертежи',
  'Выполненный проект',
]

const STAGES_INDIVIDUAL = [
  'Стадия 1: планировочные решения',
  'Стадия 2: концепция дизайна',
  'Стадия 3: рабочие чертежи',
]

const availableColumns = ref(COLUMNS_INDIVIDUAL)
const stageOptions = ref(STAGES_INDIVIDUAL)

watch(() => props.modelValue, (val) => {
  show.value = val
  if (val && props.card) {
    newDeadline.value = props.card.deadline || ''
  }
})

watch(show, (val) => emit('update:modelValue', val))

onMounted(async () => {
  try {
    const { data } = await employeesApi.getList()
    employeeOptions.value = data
      .filter(e => e.status === 'активный')
      .map(e => ({ id: e.id, label: `${e.full_name} (${e.position})` }))
  } catch { /* ignore */ }
})

async function moveToColumn(col) {
  if (!props.card) return
  actionLoading.value = true
  try {
    await crmApi.moveCard(props.card.id, col)
    $q.notify({ type: 'positive', message: `Перемещено в "${col}"` })
    emit('updated')
    show.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка перемещения' })
  } finally {
    actionLoading.value = false
  }
}

async function assignExecutor() {
  if (!assignForm.value.stage_name || !assignForm.value.executor_id) {
    $q.notify({ type: 'warning', message: 'Выберите стадию и исполнителя' })
    return
  }
  actionLoading.value = true
  try {
    await crmApi.assignExecutor(props.card.id, assignForm.value)
    $q.notify({ type: 'positive', message: 'Исполнитель назначен' })
    emit('updated')
    show.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка назначения' })
  } finally {
    actionLoading.value = false
  }
}

async function updateCardDeadline() {
  if (!newDeadline.value) return
  actionLoading.value = true
  try {
    await crmApi.updateCard(props.card.id, { deadline: newDeadline.value })
    $q.notify({ type: 'positive', message: 'Дедлайн обновлён' })
    emit('updated')
    show.value = false
  } catch (err) {
    $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка' })
  } finally {
    actionLoading.value = false
  }
}
</script>
