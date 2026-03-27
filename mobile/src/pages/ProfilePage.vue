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

    <!-- Редактировать профиль -->
    <q-card class="is-card q-mb-md">
      <q-list>
        <q-item clickable v-ripple @click="openEditProfile">
          <q-item-section avatar>
            <q-icon name="edit" color="grey-7" />
          </q-item-section>
          <q-item-section>Редактировать профиль</q-item-section>
          <q-item-section side>
            <q-icon name="chevron_right" color="grey-5" />
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

    <!-- Диалог редактирования профиля -->
    <q-dialog v-model="showEditProfile">
      <q-card style="min-width: 320px; border-radius: 10px">
        <q-toolbar style="background: #ffd93c; color: #333">
          <q-toolbar-title class="text-weight-bold" style="font-size: 14px">Редактировать профиль</q-toolbar-title>
          <q-btn flat round dense icon="close" @click="showEditProfile = false" />
        </q-toolbar>
        <q-card-section>
          <q-input v-model="profileForm.phone" label="Телефон" outlined dense type="tel" class="q-mb-sm" />
          <q-input v-model="profileForm.email" label="Email" outlined dense type="email" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup no-caps />
          <q-btn unelevated label="Сохранить" style="background: #ffd93c; color: #333; border-radius: 4px" no-caps :loading="profileSaving" @click="saveProfile" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { useAuthStore } from 'src/stores/auth'
import { employeesApi } from 'src/services/api'

const $q = useQuasar()
const authStore = useAuthStore()

const showEditProfile = ref(false)
const profileSaving = ref(false)
const profileForm = ref({ phone: '', email: '' })

function openEditProfile() {
  profileForm.value = {
    phone: authStore.user?.phone || '',
    email: authStore.user?.email || ''
  }
  showEditProfile.value = true
}

async function saveProfile() {
  profileSaving.value = true
  try {
    const userId = authStore.user?.id
    if (!userId) { $q.notify({ type: 'negative', message: 'Не удалось определить пользователя' }); return }
    await employeesApi.update(userId, {
      phone: profileForm.value.phone || null,
      email: profileForm.value.email || null
    })
    // Обновляем локальные данные
    if (authStore.user) {
      authStore.user.phone = profileForm.value.phone
      authStore.user.email = profileForm.value.email
    }
    $q.notify({ type: 'positive', message: 'Профиль обновлён' })
    showEditProfile.value = false
  } catch (err) {
    const d = err.response?.data?.detail
    $q.notify({ type: 'negative', message: typeof d === 'string' ? d : 'Ошибка сохранения' })
  } finally { profileSaving.value = false }
}

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
