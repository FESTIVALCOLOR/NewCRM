<template>
  <q-page class="flex flex-center" style="background: #F5F5F5; min-height: 100vh">
    <q-card style="width: 100%; max-width: 400px; margin: 16px">
      <q-card-section class="text-center q-pt-xl q-pb-sm">
        <q-icon name="chat" size="56px" color="green-7" />
        <div class="text-h5 q-mt-md" style="font-weight: 600">
          Добро пожаловать
        </div>
        <div class="text-body2 text-grey q-mt-xs">
          Представьтесь, чтобы начать общение с нашей командой
        </div>
      </q-card-section>

      <q-card-section>
        <q-form class="q-gutter-md" @submit="register">
          <q-input
            v-model="name"
            label="Ваше имя *"
            outlined
            :rules="[v => !!v.trim() || 'Введите имя']"
            lazy-rules
          />
          <q-input
            v-model="phone"
            label="Телефон *"
            outlined
            type="tel"
            hint="+7XXXXXXXXXX"
            :rules="[
              v => !!v.trim() || 'Введите телефон',
              v => /^\+7\d{10}$/.test(v.trim()) || 'Формат: +7XXXXXXXXXX'
            ]"
            lazy-rules
          />
          <q-btn
            type="submit"
            color="green-7"
            label="Войти в чат"
            class="full-width"
            size="lg"
            :loading="loading"
          />
        </q-form>
      </q-card-section>

      <q-card-section class="text-center text-caption text-grey q-pt-none">
        Данные используются только для идентификации в переписке
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const accessToken = route.params.token  // UUID из URL /c/{token}
const name = ref('')
const phone = ref('+7')
const loading = ref(false)

async function register() {
  loading.value = true
  try {
    const baseURL = window.location.origin
    await axios.post(`${baseURL}/api/v1/client-chat/${accessToken}/register`, {
      name: name.value.trim(),
      phone: phone.value.trim(),
    })
    // Сохраняем данные в sessionStorage для идентификации в чате
    sessionStorage.setItem('client_name', name.value.trim())
    sessionStorage.setItem('client_phone', phone.value.trim())
    sessionStorage.setItem('client_token', accessToken)
    // Переходим в чат
    router.replace({ name: 'client-chat', params: { token: accessToken } })
  } catch (e) {
    const msg = e.response?.data?.detail || 'Ошибка регистрации'
    $q.notify({ type: 'negative', message: msg })
  } finally {
    loading.value = false
  }
}
</script>
