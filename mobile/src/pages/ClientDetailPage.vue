<template>
  <q-page padding>
    <template v-if="client">
      <!-- Шапка -->
      <q-card class="is-card q-mb-md" style="position: relative">
        <q-btn
          round
          flat
          dense
          icon="arrow_back"
          style="position: absolute; top: -14px; left: -14px; z-index: 10; width: 27px; height: 32px; min-height: 32px; min-width: 27px; max-width: 27px; max-height: 32px; padding: 0; overflow: hidden; background: white; border: 1.5px solid #E0E0E0; box-shadow: 0 2px 8px rgba(0,0,0,0.13); color: #555"
          @click="$router.back()"
        >
          <q-tooltip>Назад</q-tooltip>
        </q-btn>
        <q-card-section class="text-center">
          <!-- Аватар с загрузкой фото при клике -->
          <div class="avatar-upload-wrap q-mb-sm" style="display: inline-block; position: relative; cursor: pointer" @click="$refs.clientPhotoInput.click()">
            <q-avatar size="64px" :color="clientPhotoUrl ? 'grey-2' : (client.organization_name ? 'blue-2' : 'green-2')" :text-color="client.organization_name ? 'blue-8' : 'green-8'">
              <img v-if="clientPhotoUrl" :src="clientPhotoUrl" style="width:100%;height:100%;object-fit:cover;border-radius:50%">
              <q-icon v-else :name="client.organization_name ? 'business' : 'person'" size="28px" />
            </q-avatar>
            <div class="avatar-cam-overlay">
              <q-spinner v-if="photoUploading" size="20px" color="white" />
              <q-icon v-else name="photo_camera" size="20px" color="white" />
            </div>
          </div>
          <input
            ref="clientPhotoInput"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            style="display:none"
            @change="handlePhotoUpload"
          >
          <div class="text-h6 text-weight-bold" style="color: #333">
            <template v-if="client.organization_type === 'ИП'">
              ИП {{ client.full_name }}
            </template>
            <template v-else-if="client.organization_type && client.organization_name">
              {{ client.organization_type }} «{{ client.organization_name }}»
            </template>
            <template v-else>
              {{ client.organization_name || client.full_name }}
            </template>
          </div>
          <div v-if="client.organization_name && client.organization_type !== 'ИП'" class="text-body2" style="color: #888">
            {{ client.full_name }}
          </div>
          <div v-if="client.responsible_person" class="text-body2" style="color: #888">
            Ответственное лицо: {{ client.responsible_person }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Ландшафт: 2 колонки (контакты слева, паспорт/реквизиты справа) -->
      <div class="client-detail-2col q-mb-md">
        <!-- Контакты: кнопки СЛЕВА вертикально, данные справа -->
        <q-card class="is-card client-contacts-card">
          <q-card-section class="q-pb-none">
            <div class="text-subtitle2 text-weight-bold" style="color: #333">
              Контакты
            </div>
          </q-card-section>
          <q-list>
            <!-- Телефон -->
            <q-item>
              <q-item-section avatar>
                <q-btn
                  flat
                  round
                  dense
                  :icon="client.phone ? 'phone' : 'phone_disabled'"
                  :style="{ color: client.phone ? '#333' : '#ccc' }"
                  @click="client.phone && callPhone(client.phone)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>
                  Телефон
                </q-item-label>
                <q-item-label :style="{ color: client.phone ? '#333' : '#bbb' }">
                  {{ client.phone || 'Не указан' }}
                </q-item-label>
              </q-item-section>
            </q-item>
            <!-- Email -->
            <q-item>
              <q-item-section avatar>
                <q-btn
                  flat
                  round
                  dense
                  :icon="client.email ? 'email' : 'mail_outline'"
                  :style="{ color: client.email ? '#333' : '#ccc' }"
                  @click="client.email && sendEmail(client.email)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>
                  Email
                </q-item-label>
                <q-item-label :style="{ color: client.email ? '#333' : '#bbb' }">
                  {{ client.email || 'Не указан' }}
                </q-item-label>
              </q-item-section>
            </q-item>
            <!-- Telegram -->
            <q-item>
              <q-item-section avatar>
                <q-btn
                  flat
                  round
                  dense
                  icon="send"
                  :style="{ color: telegramLink ? '#333' : '#ccc' }"
                  @click="telegramLink && openLink(telegramLink)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>
                  Telegram
                </q-item-label>
                <q-item-label :style="{ color: client.telegram_account ? '#333' : '#bbb' }">
                  {{ client.telegram_account || 'Не указан' }}
                </q-item-label>
              </q-item-section>
            </q-item>
            <!-- Адрес / Геоточка -->
            <q-item>
              <q-item-section avatar>
                <q-btn
                  flat
                  round
                  dense
                  :icon="client.registration_address ? 'location_on' : 'location_off'"
                  :style="{ color: client.registration_address ? '#333' : '#ccc' }"
                  @click="client.registration_address && openMap(client.registration_address)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label caption>
                  Адрес
                </q-item-label>
                <q-item-label :style="{ color: client.registration_address ? '#333' : '#bbb' }">
                  {{ client.registration_address || 'Не указан' }}
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card>

        <!-- Правая колонка: паспорт + реквизиты -->
        <div class="client-right-col">
          <!-- Паспорт (физ. лицо) -->
          <q-card v-if="client.passport_series || client.passport_number" class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Паспорт
              </div>
            </q-card-section>
            <q-list dense>
              <q-item>
                <q-item-section>
                  <q-item-label caption>
                    Серия и номер
                  </q-item-label><q-item-label>{{ client.passport_series }} {{ client.passport_number }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>

          <!-- Реквизиты (юр. лицо) -->
          <q-card v-if="client.inn || client.ogrn" class="is-card q-mb-md">
            <q-card-section class="q-pb-none">
              <div class="text-subtitle2 text-weight-bold" style="color: #333">
                Реквизиты
              </div>
            </q-card-section>
            <q-list dense>
              <q-item v-if="client.inn">
                <q-item-section>
                  <q-item-label caption>
                    ИНН
                  </q-item-label><q-item-label>{{ client.inn }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="client.ogrn">
                <q-item-section>
                  <q-item-label caption>
                    ОГРН
                  </q-item-label><q-item-label>{{ client.ogrn }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-item v-if="client.account_details">
                <q-item-section>
                  <q-item-label caption>
                    Банковские реквизиты
                  </q-item-label><q-item-label>{{ client.account_details }}</q-item-label>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div><!-- /client-right-col -->
      </div><!-- /client-detail-2col -->

      <!-- Договоры клиента (всегда на всю ширину) -->
      <q-card class="is-card">
        <q-card-section class="q-pb-none">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Договоры <q-badge v-if="clientsStore.clientContracts.length" :label="clientsStore.clientContracts.length" class="q-ml-xs" />
          </div>
        </q-card-section>
        <q-list v-if="clientsStore.clientContracts.length > 0" separator>
          <q-item
            v-for="c in clientsStore.clientContracts"
            :key="c.id"
            v-ripple
            clickable
            @click="$router.push(`/contracts/${c.id}`)"
          >
            <q-item-section>
              <q-item-label class="text-weight-medium">
                {{ c.contract_number }}
              </q-item-label>
              <q-item-label caption>
                {{ c.address }}
              </q-item-label>
              <q-item-label caption>
                {{ c.project_type }} — {{ c.area }} м²
              </q-item-label>
            </q-item-section>
            <q-item-section side style="min-width: 100px">
              <div class="column items-end q-gutter-xs">
                <q-badge :color="contractStatusColor(c.status)" :label="c.status" style="min-width: 90px; justify-content: center; padding: 4px 8px; font-size: 11px" />
                <q-badge v-if="c.agent_type" text-color="white" :style="{ background: agentColor(c.agent_type), minWidth: '90px', justifyContent: 'center', padding: '4px 8px', fontSize: '11px' }" :label="c.agent_type" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
        <q-card-section v-else class="text-center" style="color: #999">
          Нет договоров
        </q-card-section>
      </q-card>

      <!-- FAB редактирования -->
      <q-page-sticky v-if="can('clients.update')" position="bottom-right" :offset="[18, 80]">
        <q-btn fab icon="edit" style="background: #ffd93c; color: #333" @click="showEdit = true" />
      </q-page-sticky>

      <client-form-dialog v-model="showEdit" :client="client" @saved="reloadClient" />
      <avatar-crop-dialog v-model="showCrop" :src="cropSrc" @cropped="onCropped" />
    </template>

    <div v-else class="text-center q-pa-xl" style="color: #999">
      <q-spinner v-if="!loaded" size="40px" color="accent" />
      <template v-else>
        <q-icon name="person_off" size="48px" class="q-mb-sm" /><div>Клиент не найден</div>
      </template>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useClientsStore } from 'src/stores/clients'
import { useReferencesStore } from 'src/stores/references'
import { usePermission } from 'src/composables/usePermission'
import { useQuasar } from 'quasar'
import ClientFormDialog from 'src/components/ClientFormDialog.vue'
import AvatarCropDialog from 'src/components/AvatarCropDialog.vue'
import { clientsApi } from 'src/services/api'

const { can } = usePermission()
const $q = useQuasar()

const route = useRoute()
const clientsStore = useClientsStore()
const refs = useReferencesStore()
const loaded = ref(false)
const showEdit = ref(false)
const photoUploading = ref(false)
const clientPhotoUrl = ref(null)
const showCrop = ref(false)
const cropSrc = ref(null)

const client = computed(() => clientsStore.selectedClient)

const telegramLink = computed(() => {
  const tg = client.value?.telegram_account
  if (!tg) return null
  const clean = tg.replace('@', '').trim()
  if (!clean) return null
  if (/^\+?\d+$/.test(clean.replace(/\s/g, ''))) {
    const phone = clean.replace(/[^\d+]/g, '')
    return `tg://msg?to=${phone.startsWith('+') ? phone : '+' + phone}`
  }
  return `tg://resolve?domain=${clean}`
})

function callPhone(phone) { window.location.href = `tel:${phone.replace(/[^\d+]/g, '')}` }
function sendEmail(email) { window.location.href = `mailto:${email}` }
function openLink(url) { if (url) window.open(url, '_blank') }
function openMap(address) { window.open(`https://yandex.ru/maps/?text=${encodeURIComponent(address)}`, '_blank') }
function agentColor(name) { return refs.agentByName(name)?.color || '#95A5A6' }
function contractStatusColor(status) {
  if (!status) return 'grey'
  if (status === 'В работе') return 'orange'
  if (status.includes('СДАН') || status.includes('Сдан')) return 'positive'
  if (status.includes('РАСТОРГНУТ')) return 'negative'
  if (status.includes('НАДЗОР')) return 'purple'
  return 'blue'
}

async function reloadClient() {
  const clientId = route.params.id
  if (clientId) {
    await clientsStore.loadClient(clientId)
    await clientsStore.loadClientContracts(clientId)
  }
}

function handlePhotoUpload(e) {
  const file = e.target?.files?.[0]
  if (!file) return
  // Открываем диалог обрезки
  const reader = new FileReader()
  reader.onload = (ev) => {
    cropSrc.value = ev.target.result
    showCrop.value = true
  }
  reader.readAsDataURL(file)
  // Сбрасываем input чтобы повторный выбор того же файла работал
  e.target.value = ''
}

async function onCropped(blob) {
  photoUploading.value = true
  try {
    const { data } = await clientsApi.uploadPhoto(client.value.id, blob)
    clientPhotoUrl.value = data.photo_url
    $q.notify({ type: 'positive', message: 'Фото загружено' })
  } catch {
    $q.notify({ type: 'negative', message: 'Ошибка загрузки фото' })
  } finally {
    photoUploading.value = false
  }
}

onMounted(async () => {
  const clientId = route.params.id
  if (clientId) {
    await Promise.all([clientsStore.loadClient(clientId), clientsStore.loadClientContracts(clientId)])
    clientPhotoUrl.value = client.value?.photo_url || null
  }
  loaded.value = true
})
</script>

<style scoped>
@media (orientation: landscape) {
  .client-detail-2col {
    display: flex;
    flex-direction: row;
    gap: 12px;
    align-items: stretch;
  }
  .client-detail-2col > .client-contacts-card {
    flex: 1;
    min-width: 0;
  }
  .client-right-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .client-right-col > * {
    margin-bottom: 0 !important;
  }
}
</style>
