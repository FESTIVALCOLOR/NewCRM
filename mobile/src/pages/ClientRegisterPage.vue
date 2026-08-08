<template>
  <q-page class="register-page">
    <div class="register-wrapper">
      <q-card class="register-card">
        <!-- Шапка с логотипом -->
        <q-card-section class="text-center q-pb-none q-pt-xl">
          <img
            src="/festival_logo.png"
            alt="Festival Color"
            style="height: 64px; width: auto"
            class="q-mb-sm"
            @error="logoFailed = true"
          >
          <div class="text-h6 text-weight-bold q-mb-xs" style="color: #333">
            Добро пожаловать
          </div>
          <div class="text-caption" style="color: #999">
            Представьтесь, чтобы начать общение с нашей командой
          </div>
        </q-card-section>

        <!-- Форма -->
        <q-card-section class="q-pt-lg">
          <q-form class="q-gutter-md" @submit.prevent="register">
            <q-input
              v-model="name"
              label="Ваше имя *"
              outlined
              dense
              :rules="[v => !!v.trim() || 'Введите имя']"
              lazy-rules
            />

            <div>
              <q-input
                v-model="phone"
                label="Телефон *"
                outlined
                dense
                type="tel"
                :rules="[
                  v => !!v.trim() || 'Введите телефон',
                  v => /^\+?[78]\d{10}$/.test(v.trim().replace(/[\s\-\(\)]/g, '')) || 'Формат: +7XXXXXXXXXX'
                ]"
                lazy-rules
              />
              <div class="text-caption text-grey q-mt-xs q-ml-xs">
                +7XXXXXXXXXX
              </div>
            </div>

            <q-banner v-if="errorMsg" class="bg-negative text-white" dense style="border-radius: 4px">
              {{ errorMsg }}
            </q-banner>

            <div class="register-btn-wrap">
              <q-btn
                type="submit"
                color="green-7"
                label="ВОЙТИ В ЧАТ"
                class="full-width"
                unelevated
                :loading="loading"
                style="border-radius: 4px; font-weight: 600; font-size: 14px"
              />
            </div>
          </q-form>
        </q-card-section>

        <q-card-section class="text-center q-pt-none">
          <div class="text-caption" style="color: #ccc">
            Данные используются только для идентификации в переписке
          </div>
        </q-card-section>
      </q-card>
    </div>

    <!-- Баннер установки PWA -->
    <PwaInstallBanner />
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import axios from 'axios'
import PwaInstallBanner from 'src/components/PwaInstallBanner.vue'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const accessToken = route.params.token
const name = ref('')
const phone = ref('+7')
const loading = ref(false)
const errorMsg = ref('')
const logoFailed = ref(false)

async function register() {
  errorMsg.value = ''
  loading.value = true
  try {
    const baseURL = window.location.origin
    const resp = await axios.post(`${baseURL}/api/v1/client-chat/${accessToken}/register`, {
      guest_name: name.value.trim(),
      guest_phone: phone.value.trim(),
    })
    // Сохраняем персональный токен гостя для повторных входов по той же ссылке
    if (resp.data.access_token) {
      localStorage.setItem(`chat_member_token_${accessToken}`, resp.data.access_token)
    }
    localStorage.setItem('client_name', name.value.trim())
    router.replace({ name: 'client-chat', params: { token: accessToken } })
  } catch (e) {
    const detail = e.response?.data?.detail
    if (Array.isArray(detail)) {
      errorMsg.value = detail.map(d => d.msg || String(d)).join('; ')
    } else {
      errorMsg.value = detail || 'Ошибка регистрации'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
}

.register-wrapper {
  width: 100%;
  padding: 24px;
  max-width: 440px;
}

.register-card {
  border-radius: 10px;
  border: 1px solid #E0E0E0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.register-btn-wrap :deep(.q-btn) {
  min-height: 40px !important;
  height: 40px !important;
}
</style>
