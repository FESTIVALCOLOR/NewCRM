<template>
  <q-page padding>
    <q-card class="q-mb-md" style="border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08)">
      <q-card-section>
        <div class="text-subtitle1 text-weight-bold" style="color: #333">
          Настройки уведомлений
        </div>
        <div class="text-caption text-grey-7">
          Управление типами и каналами уведомлений
        </div>
      </q-card-section>
    </q-card>

    <q-card v-if="loading" class="q-pa-lg text-center">
      <q-spinner size="32px" color="primary" />
    </q-card>

    <template v-else>
      <!-- Каналы -->
      <q-card class="q-mb-md" style="border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08)">
        <q-card-section class="q-pb-xs">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Каналы
          </div>
        </q-card-section>
        <q-list>
          <q-item>
            <q-item-section>
              <q-item-label>Telegram</q-item-label>
              <q-item-label caption>
                Уведомления в Telegram бот
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.telegram_enabled" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Push-уведомления</q-item-label>
              <q-item-label caption>
                В браузере / PWA приложении
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.push_enabled" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Типы событий -->
      <q-card class="q-mb-md" style="border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08)">
        <q-card-section class="q-pb-xs">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Типы событий
          </div>
        </q-card-section>
        <q-list>
          <q-item>
            <q-item-section>
              <q-item-label>Назначения</q-item-label>
              <q-item-label caption>
                Назначение на проект
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_assigned" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Смена стадий</q-item-label>
              <q-item-label caption>
                Сдача, проверка, согласование
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_crm_stage" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Дедлайны</q-item-label>
              <q-item-label caption>
                Предупреждения о сроках
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_deadline" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Оплаты</q-item-label>
              <q-item-label caption>
                Создание и изменение платежей
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_payment" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Авторский надзор</q-item-label>
              <q-item-label caption>
                События по надзору
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_supervision" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Типы проектов -->
      <q-card class="q-mb-md" style="border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08)">
        <q-card-section class="q-pb-xs">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Типы проектов
          </div>
        </q-card-section>
        <q-list>
          <q-item>
            <q-item-section>
              <q-item-label>Индивидуальные</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_individual" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Шаблонные</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_template" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <!-- Дополнительно -->
      <q-card class="q-mb-md" style="border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08)">
        <q-card-section class="q-pb-xs">
          <div class="text-subtitle2 text-weight-bold" style="color: #333">
            Дополнительно
          </div>
        </q-card-section>
        <q-list>
          <q-item>
            <q-item-section>
              <q-item-label>Информационные дубли</q-item-label>
              <q-item-label caption>
                Получать копии уведомлений подчинённых
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_duplicate_info" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label>Уведомления об исправлениях</q-item-label>
              <q-item-label caption>
                Когда работа отправлена на исправление
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle v-model="settings.notify_revision_info" color="positive" @update:model-value="save" />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </template>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useQuasar } from 'quasar'
import { notificationsApi } from '../services/api.js'
import { useAuthStore } from '../stores/auth.js'

const $q = useQuasar()
const auth = useAuthStore()
const loading = ref(true)

const settings = ref({
  telegram_enabled: true,
  push_enabled: false,
  notify_assigned: true,
  notify_crm_stage: true,
  notify_deadline: true,
  notify_payment: false,
  notify_supervision: false,
  notify_individual: true,
  notify_template: true,
  notify_duplicate_info: false,
  notify_revision_info: false,
})

onMounted(async () => {
  try {
    const { data } = await notificationsApi.getSettings(auth.user.id)
    Object.assign(settings.value, data)
  } catch (err) {
    console.warn('Не удалось загрузить настройки уведомлений', err)
  } finally {
    loading.value = false
  }
})

let saveTimeout = null
function save() {
  clearTimeout(saveTimeout)
  saveTimeout = setTimeout(async () => {
    try {
      await notificationsApi.updateSettings(auth.user.id, settings.value)
    } catch (err) {
      $q.notify({ type: 'negative', message: 'Ошибка сохранения настроек' })
    }
  }, 500)
}
</script>
