<template>
  <q-page class="login-page flex flex-center">
    <q-card class="login-card shadow-10">
      <!-- Логотип и заголовок -->
      <q-card-section class="text-center q-pb-none">
        <q-avatar size="72px" color="accent" text-color="dark" class="q-mb-md">
          <span class="text-h5 text-weight-bold">FC</span>
        </q-avatar>
        <div class="text-h5 text-weight-bold q-mb-xs" style="color: #333">FESTIVAL COLOR</div>
        <div class="text-caption text-grey-7">CRM для интерьерного бюро</div>
      </q-card-section>

      <!-- Форма входа -->
      <q-card-section>
        <q-form @submit.prevent="handleLogin" class="q-gutter-md">
          <q-input
            v-model="username"
            label="Логин"
            outlined
            dense
            :rules="[val => !!val || 'Введите логин']"
            autocomplete="username"
          >
            <template v-slot:prepend>
              <q-icon name="person" />
            </template>
          </q-input>

          <q-input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            label="Пароль"
            outlined
            dense
            :rules="[val => !!val || 'Введите пароль']"
            autocomplete="current-password"
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
            <template v-slot:append>
              <q-icon
                :name="showPassword ? 'visibility_off' : 'visibility'"
                class="cursor-pointer"
                @click="showPassword = !showPassword"
              />
            </template>
          </q-input>

          <!-- Ошибка -->
          <q-banner v-if="authStore.error" class="bg-negative text-white rounded-borders" dense>
            <template v-slot:avatar>
              <q-icon name="error" />
            </template>
            {{ authStore.error }}
          </q-banner>

          <!-- Кнопка входа -->
          <q-btn
            type="submit"
            color="primary"
            label="Войти"
            :loading="authStore.loading"
            class="full-width"
            size="lg"
            no-caps
            unelevated
          />
        </q-form>
      </q-card-section>

      <!-- Версия -->
      <q-card-section class="text-center q-pt-none">
        <div class="text-caption text-grey-5">v1.0.0</div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from 'src/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)

async function handleLogin() {
  const success = await authStore.login(username.value, password.value)
  if (success) {
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  }
}
</script>
