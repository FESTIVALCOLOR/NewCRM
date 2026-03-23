<template>
  <q-page padding>
    <!-- Профиль -->
    <q-card class="is-card q-mb-md">
      <q-card-section class="text-center">
        <q-avatar size="80px" color="primary" text-color="white" class="q-mb-md">
          <span class="text-h4">{{ authStore.initials }}</span>
        </q-avatar>
        <div class="text-h6 text-weight-bold">{{ authStore.fullName }}</div>
        <div class="text-body2 text-grey-7">{{ authStore.userPosition }}</div>
        <div class="text-caption text-grey-5">{{ authStore.userRole }}</div>
      </q-card-section>
    </q-card>

    <!-- Информация -->
    <q-card class="is-card q-mb-md">
      <q-list>
        <q-item v-if="authStore.user?.email">
          <q-item-section avatar>
            <q-icon name="email" color="grey-7" />
          </q-item-section>
          <q-item-section>
            <q-item-label caption>Email</q-item-label>
            <q-item-label>{{ authStore.user.email }}</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-if="authStore.user?.phone">
          <q-item-section avatar>
            <q-icon name="phone" color="grey-7" />
          </q-item-section>
          <q-item-section>
            <q-item-label caption>Телефон</q-item-label>
            <q-item-label>{{ authStore.user.phone }}</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-if="authStore.user?.department">
          <q-item-section avatar>
            <q-icon name="business" color="grey-7" />
          </q-item-section>
          <q-item-section>
            <q-item-label caption>Отдел</q-item-label>
            <q-item-label>{{ authStore.user.department }}</q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>

    <!-- Действия -->
    <q-card class="is-card">
      <q-list>
        <q-item clickable v-ripple @click="checkUpdate">
          <q-item-section avatar>
            <q-icon name="system_update" color="grey-7" />
          </q-item-section>
          <q-item-section>Проверить обновление</q-item-section>
        </q-item>

        <q-item>
          <q-item-section avatar>
            <q-icon name="info" color="grey-7" />
          </q-item-section>
          <q-item-section>О приложении</q-item-section>
          <q-item-section side>
            <span class="text-caption text-grey-5">v1.0.0 PWA</span>
          </q-item-section>
        </q-item>

        <q-item clickable v-ripple @click="handleLogout" class="text-negative">
          <q-item-section avatar>
            <q-icon name="logout" color="negative" />
          </q-item-section>
          <q-item-section>Выйти</q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-page>
</template>

<script setup>
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'

const $q = useQuasar()
const authStore = useAuthStore()

function checkUpdate() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistration().then(reg => {
      if (reg) {
        reg.update().then(() => {
          $q.notify({ type: 'info', message: 'Проверка обновлений...' })
        })
      }
    })
  }
}

async function handleLogout() {
  await authStore.logout()
}
</script>
