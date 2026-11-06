<template>
  <div class="survey-readonly-view">
    <!-- Секции до комнат -->
    <div
      v-for="section in templateData.sections_before_rooms"
      :key="section.id"
      class="survey-section q-mb-lg"
    >
      <div class="section-header">
        {{ section.title }}
      </div>
      <ReadonlySection :section="section" :answers="answers.general_answers || {}" :hide-personal-data="hidePersonalData" />
    </div>

    <!-- Комнаты -->
    <div v-if="answers.rooms?.length" class="survey-section q-mb-lg">
      <div class="section-header rooms-header">
        Информация по помещениям
      </div>
      <div
        v-for="(room, idx) in answers.rooms"
        :key="idx"
        class="room-block q-pa-md"
      >
        <div class="room-title">
          {{ idx + 1 }}. {{ room.room_name }}
        </div>
        <ReadonlySection
          v-if="getRoomTemplate(room.room_template_id)"
          :section="{ id: 'room_' + idx, title: '', questions: getRoomTemplate(room.room_template_id).questions }"
          :answers="room.answers || {}"
        />
      </div>
    </div>

    <!-- Секции после комнат -->
    <div
      v-for="section in templateData.sections_after_rooms"
      :key="section.id"
      class="survey-section q-mb-lg"
    >
      <div class="section-header">
        {{ section.title }}
      </div>
      <ReadonlySection :section="section" :answers="answers.general_answers || {}" :hide-personal-data="hidePersonalData" />
    </div>
  </div>
</template>

<script setup>
import ReadonlySection from './ReadonlySection.vue'

const props = defineProps({
  templateData: { type: Object, required: true },
  answers: { type: Object, required: true },
  hidePersonalData: { type: Boolean, default: false },
})

function getRoomTemplate(id) {
  return props.templateData?.room_templates?.find(rt => rt.id === id)
}
</script>

<style scoped>
.survey-readonly-view {}

.survey-section {
  background: white;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.07);
  overflow: hidden;
}

.section-header {
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

.room-block {
  border-bottom: 1px solid #f0f0f0;
}

.room-block:last-child {
  border-bottom: none;
}

.room-title {
  font-weight: 600;
  color: #333;
  font-size: 14px;
  margin-bottom: 8px;
}

/* ─── Тёмная тема ─────────────────────────────────────────────── */
:global(.body--dark .survey-readonly-view .survey-section) {
  background: #1e1e3a;
  box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

:global(.body--dark .survey-readonly-view .section-header) {
  background: #2a2a2a;
  color: #e0e0e0;
  border-bottom-color: #444;
}

:global(.body--dark .survey-readonly-view .rooms-header) {
  background: #3a3a3a;
  border-bottom-color: #4a4a4a;
}

:global(.body--dark .survey-readonly-view .room-block) {
  border-bottom-color: #3a3a3a;
}

:global(.body--dark .survey-readonly-view .room-title) {
  color: #d0cce8;
}
</style>
