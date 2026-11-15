<template>
  <q-card class="is-card q-mb-md">
    <q-card-section class="q-pb-xs">
      <div class="row items-center no-wrap">
        <div class="text-subtitle2 text-weight-bold col" style="color: var(--fc-text)">
          Оплаты клиента
        </div>
        <q-btn
          v-if="canManage"
          flat
          round
          dense
          icon="more_vert"
          size="sm"
        >
          <q-menu auto-close>
            <q-list dense style="min-width: 240px">
              <q-item clickable @click="openExtra">
                <q-item-section avatar>
                  <q-icon name="add_card" size="20px" />
                </q-item-section>
                <q-item-section>Дополнительный платёж</q-item-section>
              </q-item>
              <q-item clickable @click="openDecrease">
                <q-item-section avatar>
                  <q-icon name="trending_down" size="20px" />
                </q-item-section>
                <q-item-section>Уменьшение стоимости</q-item-section>
              </q-item>
              <q-item clickable @click="openTerminate">
                <q-item-section avatar>
                  <q-icon name="gavel" size="20px" />
                </q-item-section>
                <q-item-section>Расчёт при расторжении</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </div>

      <!-- Итоги -->
      <div class="cp-summary q-mt-xs">
        <div><span>Стоимость</span><b>{{ money(state.summary.total) }}</b></div>
        <div><span>Оплачено</span><b style="color: #27AE60">{{ money(state.summary.net_paid) }}</b></div>
        <div><span>Остаток</span><b :style="{ color: state.summary.due > 0 ? '#E67E22' : 'var(--fc-text)' }">{{ money(state.summary.due) }}</b></div>
        <div v-if="state.summary.to_refund > 0">
          <span>К возврату</span><b style="color: #C62828">{{ money(state.summary.to_refund) }}</b>
        </div>
        <div v-if="state.summary.refunded > 0">
          <span>Возвращено</span><b>{{ money(state.summary.refunded) }}</b>
        </div>
      </div>
      <div v-if="canManage && state.requisites_missing.length" class="cp-warn q-mt-sm">
        Для документов об оплате заполните реквизиты в Админке → «Оплаты (СБП)»: {{ state.requisites_missing.join(', ') }}
      </div>
    </q-card-section>

    <div v-if="loading && !state.payments.length" class="q-pa-md text-center">
      <q-spinner size="24px" />
    </div>
    <q-list v-else dense separator>
      <q-item
        v-for="p in state.payments"
        :key="p.id"
        class="cp-item"
        :class="{ 'cp-cancelled': p.status === 'cancelled' }"
        :style="p.status === 'paid' ? { background: 'var(--fc-state-success-bg)' } : {}"
      >
        <q-item-section>
          <q-item-label class="text-weight-medium" style="font-size: 13px">
            <q-icon
              v-if="p.direction === 'out'"
              name="undo"
              size="14px"
              color="negative"
              class="q-mr-xs"
            />{{ p.title }}
          </q-item-label>
          <q-item-label class="text-weight-bold" style="color: var(--fc-text)">
            {{ money(p.status === 'paid' ? p.paid_amount : p.amount) }}
            <span v-if="p.status === 'paid' && p.paid_amount !== p.amount && p.kind !== 'refund' && p.amount" class="text-caption text-grey-6"> из {{ money(p.amount) }}</span>
          </q-item-label>
          <q-item-label caption :style="{ color: statusColor(p) }">
            {{ statusText(p) }}
          </q-item-label>
          <q-item-label v-if="p.basis" caption style="white-space: pre-line">
            {{ p.basis }}
          </q-item-label>
          <q-item-label v-if="p.annulled_docs.length" caption class="text-grey-6">
            Аннулированы: {{ p.annulled_docs.map(d => '№ ' + d.number).join(', ') }}
          </q-item-label>
        </q-item-section>
        <q-item-section side top style="min-width: 118px">
          <div class="column q-gutter-xs items-stretch">
            <template v-if="isOpen(p) && p.direction === 'in' && canManage">
              <button v-if="state.sbp_configured" type="button" class="cp-btn" @click="openLink(p)">
                <q-icon name="qr_code_2" size="16px" />Сформировать оплату
              </button>
              <button type="button" class="cp-btn cp-btn--ok" @click="openPay(p)">
                <q-icon name="check_circle" size="16px" />Провести оплату
              </button>
            </template>
            <button v-if="isOpen(p) && p.direction === 'out' && canRefund" type="button" class="cp-btn cp-btn--ok" @click="openPay(p)">
              <q-icon name="undo" size="16px" />Провести возврат
            </button>
            <button v-if="p.status === 'paid' && p.doc" type="button" class="cp-btn" @click="openDoc(p.doc)">
              <q-icon name="receipt_long" size="16px" />Документ № {{ p.doc.number }}
            </button>
            <button v-if="p.status === 'paid' && !p.doc && canManage && (p.direction === 'in' || canRefund)" type="button" class="cp-btn" @click="openIssue(p)">
              <q-icon name="receipt_long" size="16px" />Выписать документ
            </button>
            <div class="row justify-end q-gutter-xs">
              <q-btn
                v-if="p.status === 'paid' && canCancel"
                flat
                dense
                round
                size="sm"
                icon="remove_done"
                color="negative"
                @click="cancelPaid(p)"
              >
                <q-tooltip>Снять оплату (документ аннулируется)</q-tooltip>
              </q-btn>
              <q-btn
                v-if="isOpen(p) && !BASE_KINDS.includes(p.kind) && canCancel"
                flat
                dense
                round
                size="sm"
                icon="delete_outline"
                color="negative"
                @click="removeRow(p)"
              >
                <q-tooltip>Удалить строку</q-tooltip>
              </q-btn>
            </div>
          </div>
        </q-item-section>
      </q-item>
    </q-list>

    <!-- ── Сформировать оплату (СБП) ── -->
    <q-dialog v-model="link.show">
      <q-card class="cp-dialog">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold col">
            Оплата по СБП
          </div>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section class="text-center">
          <div class="text-caption text-grey-7">
            Сумма, которую нужно назвать клиенту
          </div>
          <div class="cp-big">
            {{ money(link.data.amount) }}
          </div>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div class="cp-qr" v-html="link.data.qr_svg" />
          <a :href="link.data.sbp_link" target="_blank" rel="noopener" class="cp-link">{{ link.data.sbp_link }}</a>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-input
            v-model="link.data.message"
            type="textarea"
            outlined
            dense
            autogrow
            label="Сообщение клиенту"
          />
          <div class="text-caption text-grey-7 q-mt-xs">
            По статической ссылке клиент вводит сумму сам — поэтому сумма есть в сообщении.
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn
            outline
            no-caps
            icon="content_copy"
            label="Скопировать"
            @click="copy(link.data.message, 'Сообщение скопировано')"
          />
          <q-btn
            v-if="canShare"
            unelevated
            no-caps
            icon="share"
            label="Отправить"
            color="positive"
            @click="shareText(link.data.message)"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── Провести оплату / возврат / выписать документ ── -->
    <q-dialog v-model="pay.show" persistent>
      <q-card class="cp-dialog">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold col">
            {{ payTitle }}
          </div>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <div class="text-caption text-grey-7">
            {{ pay.row?.title }} · {{ pay.row?.direction === 'out' ? 'к возврату' : 'по плану' }} {{ money(pay.row?.amount) }}
          </div>
          <div class="text-caption text-weight-medium">
            Способ
          </div>
          <q-btn-toggle
            v-model="pay.method"
            spread
            no-caps
            unelevated
            toggle-color="grey-4"
            toggle-text-color="dark"
            text-color="grey-8"
            class="cp-toggle"
            :options="methodOptions"
          />
          <q-input
            v-model.number="pay.amount"
            type="number"
            outlined
            dense
            label="Сумма, ₽"
          />
          <div v-if="amountHint" class="cp-warn">
            {{ amountHint }}
          </div>
          <!-- Без q-col-gutter: родитель q-gutter-sm уже даёт отступы, вместе они сдвигают поля за край окна -->
          <div class="cp-row">
            <div style="flex: 7">
              <q-input
                v-model="pay.date"
                type="date"
                outlined
                dense
                label="Дата"
                stack-label
              />
            </div>
            <div style="flex: 5">
              <q-input
                v-model="pay.time"
                type="time"
                outlined
                dense
                label="Время (МСК)"
                stack-label
              />
            </div>
          </div>
          <div class="text-caption text-grey-7">
            Будет сформирован документ, подтверждающий расчёт ({{ pay.row?.direction === 'out' ? 'возврат прихода' : 'приход' }}), с порядковым номером.
            <template v-if="pay.method === 'cash'">
              Место расчёта — адрес офиса из настроек.
            </template>
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn v-close-popup flat no-caps label="Отмена" />
          <q-btn
            unelevated
            no-caps
            color="positive"
            :loading="saving"
            :label="pay.mode === 'issue' ? 'Выписать документ' : (pay.row?.direction === 'out' ? 'Провести возврат' : 'Провести оплату')"
            @click="submitPay"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── Документ об оплате ── -->
    <q-dialog v-model="docDlg.show">
      <q-card class="cp-dialog">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold col">
            Документ № {{ docDlg.doc?.number }}
          </div>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section>
          <div class="text-body2">
            {{ docDlg.doc?.calc_sign === 'Возврат прихода' ? 'Возврат' : 'Оплата' }}: <b>{{ money(docDlg.doc?.amount) }}</b>
          </div>
          <div v-if="docDlg.doc?.annulled" class="cp-warn q-mt-sm">
            Документ аннулирован
          </div>
          <div class="text-caption text-grey-7 q-mt-sm">
            Отправьте клиенту ссылку на документ и/или PDF-файл.
          </div>
          <div class="cp-link q-mt-xs">
            {{ docDlg.doc?.public_url }}
          </div>
        </q-card-section>
        <q-card-actions class="q-px-md q-pb-md column items-stretch q-gutter-xs">
          <q-btn
            outline
            no-caps
            icon="content_copy"
            label="Скопировать ссылку"
            @click="copy(docMessage, 'Ссылка скопирована')"
          />
          <q-btn
            outline
            no-caps
            icon="open_in_new"
            label="Открыть документ"
            :href="docDlg.doc?.public_url"
            target="_blank"
          />
          <q-btn
            outline
            no-caps
            icon="download"
            label="Скачать PDF"
            :loading="pdfBusy"
            @click="downloadPdf"
          />
          <q-btn
            v-if="canShare"
            unelevated
            no-caps
            icon="share"
            color="positive"
            label="Отправить PDF и ссылку"
            :loading="pdfBusy"
            @click="sharePdf"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── Дополнительный платёж (доп. соглашение) ── -->
    <q-dialog v-model="extra.show" persistent>
      <q-card class="cp-dialog">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold col">
            Дополнительный платёж
          </div>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-btn-toggle
            v-model="extra.reason"
            spread
            no-caps
            unelevated
            toggle-color="grey-4"
            toggle-text-color="dark"
            text-color="grey-8"
            class="cp-toggle"
            :options="[{ label: 'Увеличение площади', value: 'area' }, { label: 'Доп. услуги', value: 'services' }]"
          />
          <q-input
            v-if="extra.reason === 'area'"
            v-model.number="extra.new_area"
            type="number"
            outlined
            dense
            :label="`Площадь по доп. соглашению, м² (сейчас ${contract.area || 0})`"
          />
          <q-input
            v-model.number="extra.amount"
            type="number"
            outlined
            dense
            label="Доплата клиента, ₽"
          />
          <q-input v-model="extra.basis" outlined dense label="Основание (№ и дата доп. соглашения)" />
          <div class="text-caption text-grey-7">
            Стоимость договора станет {{ money((state.summary.total || 0) + (Number(extra.amount) || 0)) }}.
            <template v-if="extra.reason === 'area' && extra.new_area && Number(extra.new_area) !== Number(contract.area)">
              Площадь договора изменится на {{ extra.new_area }} м², оплаты исполнителям будут пересчитаны.
            </template>
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn v-close-popup flat no-caps label="Отмена" />
          <q-btn
            unelevated
            no-caps
            color="positive"
            :loading="saving"
            label="Добавить платёж"
            @click="submitExtra"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── Уменьшение стоимости ── -->
    <q-dialog v-model="dec.show" persistent>
      <q-card class="cp-dialog">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold col">
            Уменьшение стоимости
          </div>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model.number="dec.amount"
            type="number"
            outlined
            dense
            label="На сколько уменьшается стоимость, ₽"
          />
          <q-input
            v-model.number="dec.new_area"
            type="number"
            outlined
            dense
            :label="`Новая площадь, м² (если меняется; сейчас ${contract.area || 0})`"
          />
          <q-input v-model="dec.basis" outlined dense label="Основание (№ и дата доп. соглашения)" />
          <div class="text-caption text-grey-7">
            Сначала уменьшаются неоплаченные платежи (с последнего).
            <template v-if="decRefund > 0">
              <br><b style="color: #C62828">К возврату клиенту: {{ money(decRefund) }}</b> — возврат проводит руководитель.
            </template>
            <template v-else-if="Number(dec.amount) > 0">
              <br>Возврат не потребуется.
            </template>
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn v-close-popup flat no-caps label="Отмена" />
          <q-btn
            unelevated
            no-caps
            color="positive"
            :loading="saving"
            label="Применить"
            @click="submitDecrease"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- ── Расчёт при расторжении ── -->
    <q-dialog v-model="term.show" persistent>
      <q-card class="cp-dialog">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-subtitle1 text-weight-bold col">
            Расчёт при расторжении
          </div>
          <q-btn
            v-close-popup
            flat
            round
            dense
            icon="close"
          />
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <div class="text-body2">
            Оплачено клиентом: <b>{{ money(state.summary.net_paid - state.summary.to_refund) }}</b>
          </div>
          <q-input
            v-model.number="term.retained"
            type="number"
            outlined
            dense
            label="Стоимость фактически выполненных работ, ₽"
          />
          <q-input
            v-model="term.reason"
            outlined
            dense
            type="textarea"
            autogrow
            label="Основание расторжения"
          />
          <div class="text-caption">
            <template v-if="termBalance > 0.01">
              <b style="color: #C62828">К возврату клиенту: {{ money(termBalance) }}</b>
            </template>
            <template v-else-if="termBalance < -0.01">
              <b style="color: #E67E22">Клиент доплачивает: {{ money(-termBalance) }}</b>
            </template>
            <template v-else>
              Взаиморасчётов нет
            </template>
          </div>
          <div class="text-caption text-grey-7">
            Неоплаченные платежи будут аннулированы. Статус договора «РАСТОРГНУТ» ставится на доске CRM. Оплаты исполнителям не меняются — решите их вручную.
          </div>
        </q-card-section>
        <q-card-actions align="right" class="q-px-md q-pb-md">
          <q-btn v-close-popup flat no-caps label="Отмена" />
          <q-btn
            unelevated
            no-caps
            color="negative"
            :loading="saving"
            label="Рассчитать"
            @click="submitTerminate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-card>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useQuasar, copyToClipboard } from 'quasar'
import { clientPaymentsApi } from 'src/services/api'
import { usePermission } from 'src/composables/usePermission'

const props = defineProps({ contract: { type: Object, required: true } })
const emit = defineEmits(['changed'])

const $q = useQuasar()
const { can } = usePermission()
const canManage = computed(() => can('client_payments.manage'))
const canRefund = computed(() => can('client_payments.refund'))
const canCancel = computed(() => can('client_payments.cancel'))
const canShare = typeof navigator !== 'undefined' && !!navigator.share

const BASE_KINDS = ['advance', 'additional', 'third']
const METHOD_LABELS = { sbp: 'СБП', cash: 'наличные', transfer: 'перевод', card: 'карта' }

const loading = ref(false)
const saving = ref(false)
const pdfBusy = ref(false)
const state = reactive({ summary: { total: 0, paid: 0, due: 0, to_refund: 0, refunded: 0, net_paid: 0 }, payments: [], sbp_configured: false, requisites_missing: [] })

const link = reactive({ show: false, data: {} })
const pay = reactive({ show: false, mode: 'pay', row: null, method: 'sbp', amount: null, date: '', time: '' })
const docDlg = reactive({ show: false, doc: null })
const extra = reactive({ show: false, reason: 'area', amount: null, basis: '', new_area: null })
const dec = reactive({ show: false, amount: null, basis: '', new_area: null })
const term = reactive({ show: false, retained: null, reason: '' })

function money(v) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(v) || 0) + ' ₽'
}
function fmtDate(d) {
  if (!d) return ''
  const [y, m, day] = d.split('-')
  return `${day}.${m}.${y}`
}
function isOpen(p) { return p.status === 'planned' || p.status === 'link_sent' }

function statusText(p) {
  if (p.status === 'cancelled') return 'Аннулирован'
  if (p.status === 'paid') {
    const verb = p.direction === 'out' ? 'Возвращено' : 'Оплачено'
    const how = p.method ? `, ${METHOD_LABELS[p.method]}` : ''
    const who = p.paid_by_name ? ` · провёл(а) ${p.paid_by_name}` : ''
    return `${verb} ${fmtDate(p.paid_date)}${how}${p.legacy ? ' · без документа' : ''}${who}`
  }
  if (p.direction === 'out') return 'Ожидает возврата'
  if (p.status === 'link_sent') return `Ссылка отправлена ${new Date(p.link_sent_at).toLocaleDateString('ru-RU')}`
  return 'Не оплачено'
}
function statusColor(p) {
  if (p.status === 'paid') return '#27AE60'
  if (p.status === 'cancelled') return 'var(--fc-text-muted)'
  if (p.direction === 'out') return '#C62828'
  return 'var(--fc-text-light)'
}

function errorText(e, fallback) { return e?.response?.data?.detail || fallback }

async function load() {
  loading.value = true
  try {
    const { data } = await clientPaymentsApi.getByContract(props.contract.id)
    Object.assign(state, data)
  } catch (e) {
    $q.notify({ type: 'negative', message: errorText(e, 'Не удалось загрузить оплаты') })
  } finally { loading.value = false }
}

function applyResult(data) {
  Object.assign(state, data)
  emit('changed')
}

// ── Сформировать оплату ──
async function openLink(p) {
  try {
    const { data } = await clientPaymentsApi.link(p.id)
    link.data = data
    link.show = true
    p.status = 'link_sent'
    p.link_sent_at = new Date().toISOString()
  } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось сформировать оплату') }) }
}

// ── Провести оплату / возврат / выписать документ ──
const methodOptions = [
  { label: 'СБП', value: 'sbp' },
  { label: 'Наличные', value: 'cash' },
  { label: 'Перевод', value: 'transfer' },
  { label: 'Карта', value: 'card' },
]
const payTitle = computed(() => {
  if (pay.mode === 'issue') return 'Выписать документ'
  return pay.row?.direction === 'out' ? 'Провести возврат' : 'Провести оплату'
})
const amountHint = computed(() => {
  if (!pay.row || pay.mode === 'issue') return ''
  const planned = Number(pay.row.amount) || 0
  const value = Number(pay.amount) || 0
  if (pay.row.direction === 'out' && value > planned) return 'Сумма больше суммы к возврату'
  if (value && value < planned) return `Внесено меньше плана — остаток ${money(planned - value)} появится отдельной строкой`
  if (value > planned) return `Внесено больше плана на ${money(value - planned)}`
  return ''
})

function nowParts() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return { date: `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`, time: `${pad(d.getHours())}:${pad(d.getMinutes())}` }
}
function openPay(p) {
  const now = nowParts()
  Object.assign(pay, { show: true, mode: 'pay', row: p, method: p.direction === 'out' ? 'transfer' : 'sbp', amount: p.amount, date: now.date, time: now.time })
}
function openIssue(p) {
  const now = nowParts()
  Object.assign(pay, { show: true, mode: 'issue', row: p, method: p.method || 'sbp', amount: p.paid_amount || p.amount, date: p.paid_date || now.date, time: p.paid_time || '12:00' })
}
async function submitPay() {
  if (!(Number(pay.amount) > 0)) { $q.notify({ type: 'warning', message: 'Укажите сумму' }); return }
  saving.value = true
  try {
    const body = { amount: Number(pay.amount), date: pay.date, time: pay.time, method: pay.method }
    const { data } = pay.mode === 'issue' ? await clientPaymentsApi.issueDoc(pay.row.id, body) : await clientPaymentsApi.pay(pay.row.id, body)
    applyResult(data)
    pay.show = false
    $q.notify({ type: 'positive', message: `Документ № ${data.doc?.number} сформирован` })
    if (data.doc) openDoc(data.doc)
  } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось провести') }) } finally { saving.value = false }
}

// ── Документ ──
const docMessage = computed(() => docDlg.doc ? `Документ, подтверждающий оплату № ${docDlg.doc.number}: ${docDlg.doc.public_url}` : '')
function openDoc(doc) { docDlg.doc = doc; docDlg.show = true }
async function fetchPdf() {
  const response = await fetch(clientPaymentsApi.publicPdfUrl(docDlg.doc.token, true))
  if (!response.ok) throw new Error('PDF недоступен')
  const kind = docDlg.doc.calc_sign === 'Возврат прихода' ? 'Возврат' : 'Оплата'
  return new File([await response.blob()], `${kind}_№${docDlg.doc.number}.pdf`, { type: 'application/pdf' })
}
async function downloadPdf() {
  pdfBusy.value = true
  try {
    const file = await fetchPdf()
    const url = URL.createObjectURL(file)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 5000)
  } catch { $q.notify({ type: 'negative', message: 'Не удалось скачать PDF' }) } finally { pdfBusy.value = false }
}
async function sharePdf() {
  pdfBusy.value = true
  try {
    const file = await fetchPdf()
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], text: docMessage.value })
    } else {
      await navigator.share({ text: docMessage.value })
    }
  } catch (e) {
    if (e?.name !== 'AbortError') $q.notify({ type: 'negative', message: 'Не удалось отправить' })
  } finally { pdfBusy.value = false }
}

// ── Отмена / удаление ──
function cancelPaid(p) {
  const what = p.direction === 'out' ? 'возврат' : 'оплату'
  $q.dialog({
    title: `Снять ${what}?`,
    message: p.doc ? `Документ № ${p.doc.number} будет аннулирован (номер не используется повторно). Клиенту стоит сообщить об этом.` : 'Отметка об оплате будет снята.',
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Да, снять', color: 'negative', noCaps: true },
  }).onOk(async () => {
    try { applyResult((await clientPaymentsApi.cancel(p.id)).data) } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось снять') }) }
  })
}
function removeRow(p) {
  $q.dialog({
    title: 'Удалить строку?',
    message: p.kind === 'extra' ? `Стоимость договора уменьшится на ${money(p.amount)}. Площадь, если менялась, верните вручную.` : `«${p.title}» будет удалена.`,
    cancel: { label: 'Нет', flat: true, noCaps: true },
    ok: { label: 'Удалить', color: 'negative', noCaps: true },
  }).onOk(async () => {
    try { applyResult((await clientPaymentsApi.remove(p.id)).data) } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось удалить') }) }
  })
}

// ── Доп. соглашение: увеличение ──
function openExtra() { Object.assign(extra, { show: true, reason: 'area', amount: null, basis: '', new_area: props.contract.area || null }) }
async function submitExtra() {
  saving.value = true
  try {
    const body = { reason: extra.reason, amount: Number(extra.amount) || 0, basis: extra.basis, new_area: extra.reason === 'area' ? (Number(extra.new_area) || null) : null }
    const { data } = await clientPaymentsApi.extra(props.contract.id, body)
    applyResult(data)
    extra.show = false
    const area = data.area_change ? ` Площадь ${data.area_change.new} м², пересчитано оплат исполнителям: ${data.area_change.recalculated}.` : ''
    $q.notify({ type: 'positive', message: `Дополнительный платёж добавлен.${area}` })
  } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось добавить') }) } finally { saving.value = false }
}

// ── Доп. соглашение: уменьшение ──
const openDue = computed(() => state.payments.filter(p => p.direction === 'in' && isOpen(p) && p.kind !== 'termination_debt').reduce((s, p) => s + (Number(p.amount) || 0), 0))
const decRefund = computed(() => Math.max(0, (Number(dec.amount) || 0) - openDue.value))
function openDecrease() { Object.assign(dec, { show: true, amount: null, basis: '', new_area: null }) }
async function submitDecrease() {
  saving.value = true
  try {
    const body = { amount: Number(dec.amount) || 0, basis: dec.basis, new_area: Number(dec.new_area) || null }
    const { data } = await clientPaymentsApi.decrease(props.contract.id, body)
    applyResult(data)
    dec.show = false
    $q.notify({ type: 'positive', message: data.refund > 0 ? `Стоимость уменьшена, к возврату ${money(data.refund)}` : 'Стоимость уменьшена' })
  } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось применить') }) } finally { saving.value = false }
}

// ── Расторжение ──
const termBalance = computed(() => (state.summary.net_paid - state.summary.to_refund) - (Number(term.retained) || 0))
function openTerminate() { Object.assign(term, { show: true, retained: null, reason: props.contract.termination_reason || '' }) }
async function submitTerminate() {
  if (term.retained === null || term.retained === '') { $q.notify({ type: 'warning', message: 'Укажите стоимость выполненных работ' }); return }
  saving.value = true
  try {
    const { data } = await clientPaymentsApi.terminate(props.contract.id, { retained: Number(term.retained) || 0, reason: term.reason })
    applyResult(data)
    term.show = false
    $q.notify({ type: 'positive', message: data.refund > 0 ? `К возврату клиенту ${money(data.refund)}` : (data.debt > 0 ? `Клиент доплачивает ${money(data.debt)}` : 'Расчёт сохранён') })
  } catch (e) { $q.notify({ type: 'negative', message: errorText(e, 'Не удалось рассчитать') }) } finally { saving.value = false }
}

// ── Общее ──
function copy(textValue, message) {
  copyToClipboard(textValue).then(() => $q.notify({ type: 'positive', message, timeout: 1500 })).catch(() => $q.notify({ type: 'negative', message: 'Не удалось скопировать' }))
}
async function shareText(textValue) {
  try { await navigator.share({ text: textValue }) } catch (e) { if (e?.name !== 'AbortError') copy(textValue, 'Сообщение скопировано') }
}

watch(() => props.contract.id, load)
onMounted(load)
defineExpose({ reload: load })
</script>

<style scoped>
.cp-summary { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12px; }
.cp-summary div { display: flex; flex-direction: column; }
.cp-summary span { color: var(--fc-text-muted); font-size: 11px; }
.cp-summary b { color: var(--fc-text); font-size: 13px; }
.cp-warn { background: #FFF4E5; color: #8A4B00; border: 1px solid #F5C77E; border-radius: 6px; padding: 6px 10px; font-size: 12px; }
.cp-cancelled { opacity: 0.55; }
/* Одинаковые поля сверху и снизу строки: кнопки не прилипают к верхнему краю зелёной подложки */
.cp-item { padding-top: 10px; padding-bottom: 10px; }
.cp-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  min-height: 30px; padding: 0 8px; border-radius: 4px; cursor: pointer;
  border: 1px solid var(--fc-accent); background: transparent; color: var(--fc-text);
  font-size: 12px; line-height: 1.1; text-align: center;
}
.cp-btn--ok { border-color: #27AE60; color: #1E8449; }
.cp-dialog { width: 440px; max-width: 94vw; }
.cp-big { font-size: 30px; font-weight: 700; color: var(--fc-text); margin: 2px 0 10px; }
.cp-qr { width: 200px; height: 200px; margin: 0 auto 8px; background: #fff; padding: 6px; border-radius: 8px; }
.cp-qr :deep(svg) { width: 100%; height: 100%; }
.cp-link { font-size: 12px; word-break: break-all; color: var(--fc-text-light); }
.cp-toggle { border: 1px solid #d9d9d9; border-radius: 6px; }
.cp-row { display: flex; gap: 8px; }
</style>
