<template>
  <q-page class="survey-edit-page">
    <div class="survey-edit-topbar">
      <q-btn
        flat
        round
        icon="arrow_back"
        color="white"
        @click="router.back()"
      />
      <span class="topbar-title">Редактирование анкеты ТЗ</span>
      <q-btn
        flat
        round
        icon="save"
        color="white"
        :loading="saving"
        @click="saveSurvey"
      />
    </div>

    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner-oval color="purple" size="48px" />
    </div>

    <div v-else-if="error" class="flex flex-center q-pa-xl">
      <div class="text-center">
        <q-icon name="error_outline" color="negative" size="64px" />
        <div class="text-h6 q-mt-md">
          {{ error }}
        </div>
      </div>
    </div>

    <template v-else-if="templateData">
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

          <div
            v-for="(room, idx) in formAnswers.rooms"
            :key="room._key || idx"
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
              :section="{ id: 'room_' + idx, title: '', questions: getRoomTemplate(room.room_template_id).questions }"
              :answers="room.answers"
              @update="(id, val) => updateRoomAnswer(idx, id, val)"
            />
          </div>

          <div class="q-pa-md">
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

        <div class="q-mt-xl q-mb-xl text-center">
          <q-btn
            color="purple"
            size="lg"
            label="Сохранить изменения"
            :loading="saving"
            @click="saveSurvey"
          />
        </div>
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { tzApi } from 'src/services/api'
import SurveySectionForm from 'src/components/survey/SurveySectionForm.vue'

const route = useRoute()
const router = useRouter()
const $q = useQuasar()

const loading = ref(true)
const saving = ref(false)
const error = ref(null)

const survey = ref(null)
const templateData = ref(null)
const formAnswers = ref({ general_answers: {}, rooms: [] })

function getRoomTemplate(id) {
  return templateData.value?.room_templates?.find(rt => rt.id === id)
}

function addRoom(rt) {
  formAnswers.value.rooms.push({
    _key: `room_${Date.now()}`,
    room_template_id: rt.id,
    room_name: rt.name,
    answers: {},
  })
}

function removeRoom(idx) {
  formAnswers.value.rooms.splice(idx, 1)
}

function updateGeneralAnswer(id, val) {
  formAnswers.value.general_answers[id] = val
}

function updateRoomAnswer(roomIdx, id, val) {
  if (formAnswers.value.rooms[roomIdx]) {
    formAnswers.value.rooms[roomIdx].answers[id] = val
  }
}

async function loadSurvey() {
  try {
    loading.value = true
    const { data } = await tzApi.getSurvey(route.params.id)
    survey.value = data
    templateData.value = data.template_data
    if (data.answers) {
      formAnswers.value = {
        general_answers: data.answers.general_answers || {},
        rooms: (data.answers.rooms || []).map((r, i) => ({
          ...r,
          _key: `room_${i}`,
        })),
      }
    }
  } catch (e) {
    error.value = 'Ошибка загрузки анкеты'
  } finally {
    loading.value = false
  }
}

async function saveSurvey() {
  if (saving.value || !survey.value) return
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
    saving.value = true
    await tzApi.editAnswers(survey.value.id, payload)
    $q.notify({ type: 'positive', message: 'Анкета сохранена' })
    router.back()
  } catch (e) {
    $q.notify({ type: 'negative', message: 'Ошибка сохранения' })
  } finally {
    saving.value = false
  }
}

onMounted(loadSurvey)
</script>

<style scoped>
.survey-edit-page {
  max-width: 820px;
  margin: 0 auto;
}

.survey-edit-topbar {
  display: flex;
  align-items: center;
  background: #6B4FA0;
  padding: 4px 8px;
  color: white;
  position: sticky;
  top: 0;
  z-index: 100;
}

.topbar-title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  text-align: center;
  color: white;
}

.survey-section {
  background: white;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07);
  overflow: hidden;
}

.survey-section-header {
  background: #f0f0f0;
  color: #2a2a2a;
  font-weight: 600;
  font-size: 14px;
  padding: 10px 16px;
  border-bottom: 1px solid #ccc;
}

.rooms-header {
  background: #555;
  color: white;
  border-bottom-color: #444;
}

.survey-room {
  background: white;
  border: 1px solid #e0d9f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 12px 16px 0;
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
  border-bottom: 1px dashed #bbb;
}

.room-templates-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* ─── Тёмная тема ─────────────────────────────────────────────── */
:global(.body--dark .survey-edit-page) {
  background: #1a1a2e;
}

:global(.body--dark .survey-section) {
  background: #1e1e3a !important;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

:global(.body--dark .survey-section-header) {
  background: #2a2a2a !important;
  color: #e0e0e0 !important;
  border-bottom-color: #444 !important;
}

:global(.body--dark .rooms-header) {
  background: #3a3a3a !important;
  border-bottom-color: #4a4a4a !important;
}

:global(.body--dark .survey-room) {
  background: #22203a !important;
  border-color: #3d3060 !important;
}
</style>
