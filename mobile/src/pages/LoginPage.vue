<template>
  <q-page class="login-page">
    <div class="login-wrapper">
      <q-card class="login-card">
        <!-- Логотип -->
        <q-card-section class="text-center q-pb-none">
          <img src="/festival_logo.png" alt="Festival Color" style="height: 64px; width: auto" class="q-mb-sm" />
          <div class="text-h6 text-weight-bold q-mb-xs" style="color: #333">FESTIVAL COLOR</div>
          <div class="text-caption" style="color: #999">Система управления заказами</div>
        </q-card-section>

        <!-- Форма -->
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
              <template v-slot:prepend><q-icon name="person" /></template>
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
              <template v-slot:prepend><q-icon name="lock" /></template>
              <template v-slot:append>
                <q-icon :name="showPassword ? 'visibility_off' : 'visibility'" class="cursor-pointer" @click="showPassword = !showPassword" />
              </template>
            </q-input>

            <!-- Запомнить меня -->
            <q-checkbox v-model="rememberMe" label="Запомнить меня" dense style="color: #666" />

            <!-- Ошибка -->
            <q-banner v-if="authStore.error" class="bg-negative text-white" dense style="border-radius: 4px">
              <template v-slot:avatar><q-icon name="error" /></template>
              {{ authStore.error }}
            </q-banner>

            <!-- Кнопка — белая с чёрной рамкой, по ширине полей -->
            <div>
              <q-btn
                type="submit"
                label="Войти"
                :loading="authStore.loading"
                class="full-width"
                size="lg"
                no-caps
                outline
                color="dark"
                style="border-radius: 8px; font-weight: 600"
              />
            </div>
          </q-form>
        </q-card-section>

        <q-card-section class="text-center q-pt-none">
          <div class="text-caption" style="color: #ccc">v1.2.0</div>
        </q-card-section>
      </q-card>
    </div>
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
const rememberMe = ref(true)

async function handleLogin() {
  const success = await authStore.login(username.value, password.value)
  if (success) {
    if (rememberMe.value) {
      localStorage.setItem('remember_me', 'true')
    }
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-wrapper {
  width: 100%;
  padding: 24px;
  max-width: 440px;
}

.login-card {
  border-radius: 10px;
  border: 1px solid #E0E0E0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
</style>
