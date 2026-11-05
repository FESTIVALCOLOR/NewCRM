<template>
  <q-page class="survey-fill-page">
    <!-- Загрузка -->
    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner-oval color="purple" size="48px" />
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="flex flex-center q-pa-xl">
      <div class="text-center">
        <q-icon name="error_outline" color="negative" size="64px" />
        <div class="text-h6 q-mt-md">
          {{ error }}
        </div>
      </div>
    </div>

    <!-- Анкета заполнена (режим просмотра) -->
    <template v-else-if="readonly && answers">
      <div class="survey-header">
        <div class="survey-logo-wrap">
          <img v-if="agentLogo" :src="agentLogo" class="survey-logo" alt="logo">
        </div>
        <div class="survey-title-block">
          <div class="survey-title">
            АНКЕТА
          </div>
          <div class="survey-subtitle">
            технического задания
          </div>
          <div v-if="contractNumber" class="survey-contract-ref">
            Приложение к Договору № {{ contractNumber }}
          </div>
        </div>
      </div>

      <div class="survey-readonly-notice q-ma-md">
        <q-banner rounded class="bg-positive text-white">
          <template #avatar>
            <q-icon name="check_circle" color="white" />
          </template>
          Анкета успешно заполнена. Ниже отображены ваши ответы.
          Для внесения изменений обратитесь к вашему менеджеру.
        </q-banner>
      </div>

      <SurveyReadonlyView
        :template-data="templateData"
        :answers="answers"
        class="q-pa-md"
      />
    </template>

    <!-- Форма заполнения -->
    <template v-else-if="templateData">
      <div class="survey-header">
        <div class="survey-logo-wrap">
          <img v-if="agentLogo" :src="agentLogo" class="survey-logo" alt="logo">
        </div>
        <div class="survey-title-block">
          <div class="survey-title">
            АНКЕТА
          </div>
          <div class="survey-subtitle">
            технического задания на разработку
            {{ projectType === 'Шаблонный' ? 'шаблонного ' : '' }}дизайн-проекта интерьера
          </div>
          <div v-if="contractNumber" class="survey-contract-ref">
            Приложение к Договору № {{ contractNumber }}
          </div>
        </div>
      </div>

      <div class="q-pa-md">
        <!-- Секции до комнат -->
        <div
          v-for="section in templateData.sections_before_rooms"
          :key="section.id"
          class="survey-section q-mb-lg"
        >
          <div class="survey-section-header">
            {{ section.title }}
          </div>
          <SurveySectionForm
            :section="section"
            :answers="formAnswers.general_answers"
            @update="(id, val) => updateGeneralAnswer(id, val)"
          />
        </div>

        <!-- Комнаты -->
        <div class="survey-section q-mb-md">
          <div class="survey-section-header rooms-header">
            Информация по помещениям
          </div>

          <!-- Добавленные комнаты -->
          <div
            v-for="(room, idx) in formAnswers.rooms"
            :key="room._key"
            class="survey-room q-mb-md"
          >
            <div class="survey-room-header">
              <div class="room-title-row">
                <span class="room-idx">{{ idx + 1 }}.</span>
                <q-input
                  v-model="room.room_name"
                  dense
                  outlined
                  placeholder="Название помещения (напр. Гостиная, Санузел 1)"
                  class="room-name-input"
                />
              </div>
              <q-btn
                flat
                round
                icon="close"
                color="negative"
                size="sm"
                @click="removeRoom(idx)"
              />
            </div>

            <SurveySectionForm
              v-if="getRoomTemplate(room.room_template_id)"
              :section="{ id: room._key, title: '', questions: getRoomTemplate(room.room_template_id).questions }"
              :answers="room.answers"
              @update="(id, val) => updateRoomAnswer(idx, id, val)"
            />
          </div>

          <!-- Кнопка добавить комнату -->
          <div class="q-mt-md">
            <div class="text-subtitle2 text-grey-7 q-mb-sm">
              Добавить помещение:
            </div>
            <div class="room-templates-row">
              <q-btn
                v-for="rt in templateData.room_templates"
                :key="rt.id"
                outline
                color="purple"
                :label="rt.name"
                size="sm"
                class="q-mr-sm q-mb-sm"
                @click="addRoom(rt)"
              />
            </div>
          </div>
        </div>

        <!-- Секции после комнат -->
        <div
          v-for="section in templateData.sections_after_rooms"
          :key="section.id"
          class="survey-section q-mb-lg"
        >
          <div class="survey-section-header">
            {{ section.title }}
          </div>
          <SurveySectionForm
            :section="section"
            :answers="formAnswers.general_answers"
            @update="(id, val) => updateGeneralAnswer(id, val)"
          />
        </div>

        <!-- Согласие перед отправкой -->
        <div class="survey-consent-block q-mt-lg">
          <q-checkbox
            v-model="consentChecked"
            color="purple"
            class="consent-checkbox"
          >
            <span class="consent-label">
              Я подтверждаю достоверность указанных данных и несу ответственность за их актуальность.
              Понимаю, что дизайн-проект будет разрабатываться на основании предоставленной мной информации.
            </span>
          </q-checkbox>
        </div>

        <!-- Кнопка отправки -->
        <div class="q-mt-md q-mb-xl text-center">
          <q-btn
            color="purple"
            size="lg"
            label="Отправить анкету"
            :loading="submitting"
            :disable="submitting || !consentChecked"
            class="survey-submit-btn"
            @click="submitSurvey"
          />
          <div v-if="!consentChecked" class="text-caption text-orange q-mt-sm">
            Необходимо подтвердить достоверность данных
          </div>
          <div v-else class="text-caption text-grey q-mt-sm">
            После отправки редактирование будет недоступно
          </div>
        </div>
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useQuasar } from 'quasar'
import { tzApi } from 'src/services/api'
import SurveySectionForm from 'src/components/survey/SurveySectionForm.vue'
import SurveyReadonlyView from 'src/components/survey/SurveyReadonlyView.vue'

const route = useRoute()
const $q = useQuasar()

const loading = ref(true)
const error = ref(null)
const submitting = ref(false)
const consentChecked = ref(false)

const surveyId = ref(null)
const readonly = ref(false)
const templateData = ref(null)
const answers = ref(null)
const projectType = ref('')
const contractNumber = ref('')
const agentType = ref(null)
const agentLogo = ref(null)

const formAnswers = ref({
  general_answers: {},
  rooms: [],
})

let _roomKey = 0

const token = computed(() => route.params.token)

function getRoomTemplate(id) {
  return templateData.value?.room_templates?.find(rt => rt.id === id)
}

function addRoom(rt) {
  formAnswers.value.rooms.push({
    _key: `room_${++_roomKey}`,
    room_template_id: rt.id,
    room_name: rt.name,
    answers: {},
  })
}

function removeRoom(idx) {
  formAnswers.value.rooms.splice(idx, 1)
}

function updateGeneralAnswer(questionId, val) {
  formAnswers.value.general_answers[questionId] = val
}

function updateRoomAnswer(roomIdx, questionId, val) {
  if (!formAnswers.value.rooms[roomIdx]) return
  formAnswers.value.rooms[roomIdx].answers[questionId] = val
}

async function loadSurvey() {
  try {
    loading.value = true
    error.value = null
    const res = await tzApi.getForClient(token.value)
    const data = res.data
    surveyId.value = data.survey_id
    readonly.value = data.readonly
    templateData.value = data.template_data
    projectType.value = data.project_type || ''
    contractNumber.value = data.contract_number || ''
    agentType.value = data.agent_type || null
    if (data.readonly && data.answers) {
      answers.value = data.answers
    }
  } catch (e) {
    if (e.response?.status === 404) {
      error.value = 'Анкета не найдена или ссылка недействительна'
    } else {
      error.value = 'Ошибка загрузки анкеты'
    }
  } finally {
    loading.value = false
  }
}

async function submitSurvey() {
  if (submitting.value) return
  // Собираем ответы — убираем служебные ключи _key из rooms
  const cleanRooms = formAnswers.value.rooms.map(r => ({
    room_template_id: r.room_template_id,
    room_name: r.room_name,
    answers: r.answers,
  }))
  const payload = {
    general_answers: formAnswers.value.general_answers,
    rooms: cleanRooms,
  }

  try {
    submitting.value = true
    await tzApi.submitByClient(token.value, payload)
    // После успешной отправки переключаем в режим просмотра
    answers.value = payload
    readonly.value = true
    $q.notify({ type: 'positive', message: 'Анкета успешно отправлена!' })
  } catch (e) {
    if (e.response?.status === 409) {
      $q.notify({ type: 'warning', message: 'Анкета уже была заполнена ранее' })
      readonly.value = true
    } else {
      $q.notify({ type: 'negative', message: 'Ошибка отправки анкеты. Попробуйте ещё раз.' })
    }
  } finally {
    submitting.value = false
  }
}

onMounted(loadSurvey)
</script>

<style scoped>
.survey-fill-page {
  min-height: 100vh;
  background: #fafafa;
  max-width: 820px;
  margin: 0 auto;
}

.survey-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px 20px 12px;
  border-bottom: 2px solid #6B4FA0;
  background: white;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.survey-logo-wrap {
  flex-shrink: 0;
}

.survey-logo {
  max-height: 52px;
  max-width: 140px;
  object-fit: contain;
}

.survey-title-block {
  flex: 1;
}

.survey-title {
  font-size: 20px;
  font-weight: 700;
  color: #222;
  letter-spacing: 0.05em;
}

.survey-subtitle {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.survey-contract-ref {
  font-size: 11px;
  color: #6B4FA0;
  margin-top: 2px;
  font-style: italic;
}

.survey-section {
  background: white;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07);
  overflow: hidden;
}

.survey-section-header {
  background: #EDE8F5;
  color: #2a1a4e;
  font-weight: 700;
  font-size: 16px;
  padding: 12px 16px 10px;
  border-bottom: 2px solid #6B4FA0;
  letter-spacing: 0.01em;
  position: relative;
}

.rooms-header {
  background: #6B4FA0;
  color: white;
  border-bottom-color: #5a3f8a;
}

.survey-room {
  background: white;
  border: 1px solid #e0d9f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 12px;
}

.survey-room-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.room-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.room-idx {
  font-weight: 700;
  color: #6B4FA0;
  font-size: 15px;
  min-width: 20px;
}

.room-name-input {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #333;
  border-bottom: 1px dashed #bbb;
}

.room-templates-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.survey-submit-btn {
  min-width: 240px;
  border-radius: 8px;
}

.survey-readonly-notice {
  margin-top: 12px;
}

.survey-consent-block {
  background: #fff9f0;
  border: 1px solid #f0a040;
  border-radius: 10px;
  padding: 14px 16px;
}

.consent-label {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}
</style>
