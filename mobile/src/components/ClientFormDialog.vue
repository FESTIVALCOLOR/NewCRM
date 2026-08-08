<template>
  <q-dialog
    v-model="show"
    persistent
    maximized
    transition-show="slide-up"
    transition-hide="slide-down"
  >
    <q-card>
      <!-- Жёлтый заголовок, чёрный текст -->
      <q-toolbar style="background: #ffd93c; color: #333">
        <q-btn
          flat
          round
          dense
          icon="close"
          @click="close"
        />
        <q-toolbar-title class="text-weight-bold" style="font-size: 14px">
          {{ isEdit ? 'Редактировать клиента' : 'Новый клиент' }}
        </q-toolbar-title>
        <button type="button" class="save-btn" :disabled="saving" @click="save">
          <q-spinner v-if="saving" size="16px" />
          <span v-else>Сохранить</span>
        </button>
      </q-toolbar>

      <q-card-section class="q-pa-md" style="max-height: calc(100vh - 50px); overflow-y: auto">
        <q-form ref="formRef" class="q-gutter-md">
          <!-- Тип клиента -->
          <q-select
            v-model="form.client_type"
            :options="['Физическое лицо', 'Юридическое лицо']"
            label="Тип клиента"
            outlined
            dense
          />

          <!-- ФИО -->
          <q-input
            v-model="form.full_name"
            label="ФИО *"
            outlined
            dense
            :rules="[val => !!val || 'Обязательное поле']"
          />

          <!-- Телефон -->
          <q-input
            v-model="form.phone"
            label="Телефон *"
            outlined
            dense
            type="tel"
            :rules="[val => !!val || 'Обязательное поле']"
          />

          <!-- Email (обязательный) -->
          <q-input
            v-model="form.email"
            label="Email *"
            outlined
            dense
            type="email"
            :rules="[val => !!val || 'Введите email']"
          />

          <!-- Telegram -->
          <q-input
            v-model="form.telegram_account"
            label="Telegram (имя или телефон)"
            outlined
            dense
            placeholder="@username или +79001234567"
          >
            <template #prepend>
              <q-icon name="send" />
            </template>
            <template #append>
              <q-btn
                v-if="telegramSearchLink"
                flat
                round
                dense
                size="sm"
                icon="open_in_new"
                @click="openTelegram"
              >
                <q-tooltip>Открыть в Telegram</q-tooltip>
              </q-btn>
            </template>
          </q-input>
          <div v-if="telegramSearchLink" class="text-caption q-mt-xs" style="color: #3498DB; cursor: pointer" @click="openTelegram">
            Найти в Telegram →
          </div>

          <!-- Адрес регистрации -->
          <q-input v-model="form.registration_address" label="Адрес регистрации" outlined dense />

          <!-- Юр. лицо — дополнительные поля -->
          <template v-if="form.client_type === 'Юридическое лицо'">
            <div class="text-subtitle2 text-weight-bold q-mt-md">
              Организация
            </div>

            <q-select
              v-model="form.organization_type"
              :options="['ООО', 'ИП', 'АО', 'ПАО', 'ЗАО']"
              label="Тип организации"
              outlined
              dense
            />

            <q-input v-model="form.organization_name" label="Название организации" outlined dense />
            <q-input v-model="form.inn" label="ИНН" outlined dense />
            <q-input v-model="form.ogrn" label="ОГРН" outlined dense />
            <q-input
              v-model="form.account_details"
              label="Банковские реквизиты"
              outlined
              dense
              type="textarea"
              autogrow
            />
            <q-input v-model="form.responsible_person" label="Ответственное лицо" outlined dense />
          </template>

          <!-- Физ. лицо — паспорт -->
          <template v-if="form.client_type === 'Физическое лицо'">
            <div class="text-subtitle2 text-weight-bold q-mt-md">
              Паспортные данные
            </div>

            <div class="row q-gutter-sm">
              <q-input
                v-model="form.passport_series"
                label="Серия паспорта"
                outlined
                dense
                style="flex: 1; min-width: 120px"
              />
              <q-input
                v-model="form.passport_number"
                label="Номер паспорта"
                outlined
                dense
                style="flex: 1; min-width: 120px"
              />
            </div>

            <q-input v-model="form.passport_issued_by" label="Кем выдан" outlined dense />
            <q-input
              v-model="form.passport_issued_date"
              label="Дата выдачи"
              outlined
              dense
              type="date"
            />
          </template>

          <!-- Кнопка удаления (только при редактировании) -->
          <q-btn
            v-if="isEdit"
            label="Удалить клиента"
            icon="delete"
            color="negative"
            flat
            no-caps
            class="full-width q-mt-lg"
            @click="deleteClient"
          />
        </q-form>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useQuasar } from 'quasar'
import { clientsApi } from 'src/services/api'

const props = defineProps({
  modelValue: Boolean,
  client: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const $q = useQuasar()
const show = ref(false)
const saving = ref(false)
const formRef = ref(null)
const isEdit = ref(false)

const emptyForm = () => ({
  client_type: 'Физическое лицо',
  full_name: '',
  phone: '',
  email: '',
  telegram_account: '',
  registration_address: '',
  organization_type: '',
  organization_name: '',
  inn: '',
  ogrn: '',
  account_details: '',
  responsible_person: '',
  passport_series: '',
  passport_number: '',
  passport_issued_by: '',
  passport_issued_date: '',
})

const form = ref(emptyForm())

const telegramSearchLink = computed(() => {
  const tg = form.value.telegram_account
  if (!tg) return null
  const clean = tg.replace('@', '').trim()
  if (!clean) return null
  // Для номера: tg://msg?to=+номер (открывает чат)
  if (/^\+?\d{7,}$/.test(clean.replace(/\s/g, ''))) {
    const phone = clean.replace(/[^\d+]/g, '')
    return `tg://msg?to=${phone.startsWith('+') ? phone : '+' + phone}`
  }
  // Для username: tg://resolve?domain=username
  return `tg://resolve?domain=${clean}`
})

watch(() => props.modelValue, (val) => {
  show.value = val
  if (val && props.client) {
    isEdit.value = true
    form.value = { ...emptyForm(), ...props.client }
  } else if (val) {
    isEdit.value = false
    form.value = emptyForm()
  }
})

watch(show, (val) => emit('update:modelValue', val))

function close() { show.value = false }

function openTelegram() {
  if (telegramSearchLink.value) window.open(telegramSearchLink.value, '_blank')
}

async function deleteClient() {
  $q.dialog({
    title: 'Удалить клиента?',
    message: form.value.full_name,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await clientsApi.delete(props.client.id)
      $q.notify({ type: 'positive', message: 'Клиент удалён' })
      emit('saved')
      close()
    } catch (err) {
      $q.notify({ type: 'negative', message: err.response?.data?.detail || 'Ошибка удаления' })
    }
  })
}

async function save() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  // Проверка дубликатов только при создании нового клиента
  if (!isEdit.value) {
    try {
      const duplicates = []
      if (form.value.phone) {
        const { data: byPhone } = await clientsApi.getList({ search: form.value.phone, limit: 10 })
        byPhone.forEach(c => { if (c.phone === form.value.phone) duplicates.push(c) })
      }
      if (form.value.full_name) {
        const { data: byName } = await clientsApi.getList({ search: form.value.full_name, limit: 10 })
        byName.forEach(c => {
          if (c.full_name?.toLowerCase() === form.value.full_name.toLowerCase() && !duplicates.find(d => d.id === c.id)) {
            duplicates.push(c)
          }
        })
      }
      if (duplicates.length > 0) {
        const dupList = duplicates.map(c => `${c.full_name} (${c.phone || 'без тел.'})`).join('; ')
        const confirmed = await new Promise(resolve => {
          $q.dialog({
            title: 'Похожий клиент уже существует',
            message: `Найдено: ${dupList}.\n\nВсё равно создать нового клиента?`,
            cancel: { label: 'Отмена', flat: true },
            ok: { label: 'Создать всё равно', color: 'warning' },
            persistent: true,
          }).onOk(() => resolve(true)).onCancel(() => resolve(false))
        })
        if (!confirmed) return
      }
    } catch {}
  }

  saving.value = true
  try {
    if (isEdit.value) {
      await clientsApi.update(props.client.id, form.value)
      $q.notify({ type: 'positive', message: 'Клиент обновлён' })
      emit('saved')
    } else {
      const { data: newClient } = await clientsApi.create(form.value)
      $q.notify({ type: 'positive', message: 'Клиент создан' })
      emit('saved', newClient)
    }
    close()
  } catch (err) {
    const msg = err.response?.data?.detail || 'Ошибка сохранения'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.save-btn {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #333;
  border-radius: 8px;
  background: transparent;
  color: #333;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  outline: none;
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
