<template>
  <div class="ps-wrap">
    <div v-if="!canEdit" class="text-grey-7 q-pa-md">
      Настройки оплат доступны руководителю студии.
    </div>
    <template v-else>
      <div v-if="loading" class="text-center q-pa-lg">
        <q-spinner size="28px" />
      </div>
      <q-form v-else class="q-gutter-md" @submit.prevent="save">
        <div class="ps-section">
          СБП-ссылка
        </div>
        <q-input
          v-model="form.sbp_link"
          outlined
          dense
          label="Ссылка на оплату по СБП (Точка → QR-платежи)"
          hint="Статическая ссылка: клиент сам вводит сумму, поэтому сумма есть в сообщении"
        />
        <div v-if="form.sbp_link" class="row items-center q-gutter-md">
          <img :src="qrUrl" alt="QR" class="ps-qr">
          <div class="text-caption text-grey-7">
            Этот QR-код увидит менеджер в окне «Сформировать оплату».
          </div>
        </div>
        <q-input
          v-model="form.message_template"
          outlined
          dense
          type="textarea"
          autogrow
          label="Сообщение клиенту"
          hint="Подстановки: {клиент}, {договор}, {платёж}, {сумма}, {ссылка}"
        />

        <div class="ps-section">
          Реквизиты для документа об оплате
        </div>
        <div class="text-caption text-grey-7" style="margin-top: 4px">
          Документ, подтверждающий расчёт, выдаётся без ККТ (ИП на ПСН, п. 2.1 ст. 2 54-ФЗ). Реквизиты фиксируются в документе в момент выдачи.
        </div>
        <q-input v-model="form.seller_name" outlined dense label="ФИО индивидуального предпринимателя *" />
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-sm-6">
            <q-input v-model="form.seller_inn" outlined dense label="ИНН *" />
          </div>
          <div class="col-12 col-sm-6">
            <q-input v-model="form.seller_ogrnip" outlined dense label="ОГРНИП" />
          </div>
        </div>
        <q-input v-model="form.tax_system" outlined dense label="Система налогообложения *" />
        <q-input
          v-model="form.service_name"
          outlined
          dense
          label="Наименование услуги *"
          hint="В документе дополняется словами «по договору № …»"
        />
        <q-input
          v-model="form.cashier"
          outlined
          dense
          label="Расчёт осуществил (должность и ФИО)"
          :placeholder="cashierDefault"
          :hint="cashierDefault ? `Если пусто — ${cashierDefault}` : 'Укажите руководителя: в CRM нет активного «Руководителя студии»'"
        />
        <q-input
          v-model="form.place_remote"
          outlined
          dense
          label="Место расчёта при оплате онлайн (СБП, перевод, карта)"
          hint="Адрес сайта студии"
        />
        <q-input
          v-model="form.place_office"
          outlined
          dense
          label="Место расчёта при оплате наличными"
          hint="Адрес офиса, где принимаются наличные"
        />

        <div v-if="missing.length" class="ps-warn">
          Не заполнено: {{ missing.join(', ') }} — без этого документ не сформируется.
        </div>
        <div class="row justify-end">
          <q-btn
            type="submit"
            unelevated
            no-caps
            color="primary"
            label="Сохранить"
            :loading="saving"
          />
        </div>
      </q-form>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'src/boot/axios'
import { clientPaymentsApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'

const $q = useQuasar()
const { can } = usePermission()
const canEdit = computed(() => can('client_payments.settings'))

const FIELDS = ['sbp_link', 'message_template', 'seller_name', 'seller_inn', 'seller_ogrnip', 'tax_system', 'service_name', 'cashier', 'place_remote', 'place_office']
const form = ref(Object.fromEntries(FIELDS.map(f => [f, ''])))
const missing = ref([])
const cashierDefault = ref('')
const loading = ref(false)
const saving = ref(false)
const qrBlobUrl = ref('')

const qrUrl = computed(() => qrBlobUrl.value)

async function loadQr() {
  if (!form.value.sbp_link) { qrBlobUrl.value = ''; return }
  try {
    const { data } = await api.get('/api/v1/client-payments/qr.svg', { params: { data: form.value.sbp_link }, responseType: 'blob' })
    if (qrBlobUrl.value) URL.revokeObjectURL(qrBlobUrl.value)
    qrBlobUrl.value = URL.createObjectURL(data)
  } catch { qrBlobUrl.value = '' }
}

function apply(data) {
  for (const f of FIELDS) form.value[f] = data[f] || ''
  missing.value = data.requisites_missing || []
  cashierDefault.value = data.cashier_default || ''
  loadQr()
}

async function load() {
  if (!canEdit.value) return
  loading.value = true
  try { apply((await clientPaymentsApi.getSettings()).data) } catch { $q.notify({ type: 'negative', message: 'Не удалось загрузить настройки оплат' }) } finally { loading.value = false }
}

async function save() {
  saving.value = true
  try {
    const { data } = await clientPaymentsApi.saveSettings(form.value)
    apply({ ...data, cashier_default: cashierDefault.value })
    $q.notify({ type: 'positive', message: 'Настройки оплат сохранены' })
  } catch (e) {
    $q.notify({ type: 'negative', message: e?.response?.data?.detail || 'Не удалось сохранить' })
  } finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.ps-wrap { max-width: 720px; }
.ps-section { font-weight: 700; font-size: 14px; color: var(--fc-text); margin-top: 18px; }
.ps-qr { width: 120px; height: 120px; background: #fff; padding: 4px; border-radius: 6px; border: 1px solid #E0E0E0; }
.ps-warn { background: #FFF4E5; color: #8A4B00; border: 1px solid #F5C77E; border-radius: 6px; padding: 8px 12px; font-size: 13px; }
</style>
