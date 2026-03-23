<template>
  <q-page padding>
    <q-pull-to-refresh @refresh="onRefresh">
      <!-- Фильтр -->
      <div class="row items-center justify-between q-mb-md">
        <q-btn-toggle
          v-model="filter"
          no-caps
          dense
          unelevated
          toggle-color="primary"
          :options="[
            { label: 'Все', value: 'all' },
            { label: 'Непрочитанные', value: 'unread' }
          ]"
        />
        <q-btn
          v-if="store.unreadCount > 0"
          flat
          dense
          label="Прочитать все"
          no-caps
          color="primary"
          @click="markAllRead"
        />
      </div>

      <!-- Загрузка -->
      <div v-if="store.loading && store.items.length === 0">
        <q-card class="is-card q-mb-sm" v-for="n in 5" :key="n">
          <q-item>
            <q-item-section avatar><q-skeleton type="circle" size="36px" /></q-item-section>
            <q-item-section>
              <q-skeleton type="text" width="70%" />
              <q-skeleton type="text" width="50%" />
            </q-item-section>
          </q-item>
        </q-card>
      </div>

      <!-- Список -->
      <q-card class="is-card" v-else-if="filteredItems.length > 0">
        <q-list separator>
          <q-item
            v-for="n in filteredItems"
            :key="n.id"
            clickable
            v-ripple
            :class="{ 'bg-blue-1': !n.is_read }"
            @click="handleClick(n)"
          >
            <q-item-section avatar>
              <q-icon :name="iconFor(n.notification_type)" :color="n.is_read ? 'grey-5' : 'primary'" size="24px" />
            </q-item-section>
            <q-item-section>
              <q-item-label :class="{ 'text-weight-bold': !n.is_read }">{{ n.title }}</q-item-label>
              <q-item-label caption lines="2">{{ n.message }}</q-item-label>
              <q-item-label caption class="text-grey-5">{{ formatTime(n.created_at) }}</q-item-label>
            </q-item-section>
            <q-item-section side v-if="!n.is_read">
              <q-badge color="primary" rounded />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>

      <div v-else class="text-center q-pa-xl text-grey-5">
        <q-icon name="notifications_none" size="48px" class="q-mb-sm" />
        <div>{{ filter === 'unread' ? 'Нет непрочитанных' : 'Нет уведомлений' }}</div>
      </div>
    </q-pull-to-refresh>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from 'src/stores/notifications'

const router = useRouter()
const store = useNotificationsStore()
const filter = ref('all')

const filteredItems = computed(() => {
  if (filter.value === 'unread') return store.items.filter(n => !n.is_read)
  return store.items
})

function iconFor(type) {
  const icons = {
    assigned: 'assignment_ind',
    deadline: 'schedule',
    payment: 'payments',
    crm_stage: 'swap_horiz',
    supervision: 'engineering'
  }
  return icons[type] || 'notifications'
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const now = new Date()
  const mins = Math.floor((now - d) / 60000)
  if (mins < 1) return 'только что'
  if (mins < 60) return `${mins} мин. назад`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs} ч. назад`
  const days = Math.floor(hrs / 24)
  if (days < 7) return `${days} дн. назад`
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

function handleClick(n) {
  if (!n.is_read) store.markRead(n.id)
  if (n.related_entity_type === 'crm_card' && n.related_entity_id) {
    router.push(`/crm/${n.related_entity_id}`)
  } else if (n.related_entity_type === 'supervision_card' && n.related_entity_id) {
    router.push(`/supervision/${n.related_entity_id}`)
  }
}

function markAllRead() {
  store.items.filter(n => !n.is_read).forEach(n => store.markRead(n.id))
}

function onRefresh(done) {
  store.load().finally(done)
}

onMounted(() => store.load())
</script>
