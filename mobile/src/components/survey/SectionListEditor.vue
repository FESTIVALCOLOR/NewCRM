<template>
  <div class="section-list-editor">
    <!-- Список секций -->
    <div
      v-for="(sec, si) in localSections"
      :key="sec.id || si"
      class="section-card q-mb-md"
    >
      <!-- Заголовок секции -->
      <div class="section-card-header">
        <q-icon name="drag_indicator" color="grey-4" size="18px" class="drag-icon" />
        <q-input
          v-model="sec.title"
          dense
          borderless
          placeholder="Название секции"
          class="section-title-input"
          @update:model-value="emitUpdate"
        />
        <div class="section-actions">
          <q-btn
            flat
            round
            icon="keyboard_arrow_up"
            size="xs"
            color="grey-7"
            :disable="si === 0"
            @click="moveSection(si, -1)"
          />
          <q-btn
            flat
            round
            icon="keyboard_arrow_down"
            size="xs"
            color="grey-7"
            :disable="si === localSections.length - 1"
            @click="moveSection(si, 1)"
          />
          <q-btn
            flat
            round
            icon="expand_more"
            size="xs"
            color="grey-7"
            @click="toggleSection(si)"
          />
          <q-btn
            flat
            round
            icon="delete"
            size="xs"
            color="negative"
            @click="removeSection(si)"
          />
        </div>
      </div>

      <!-- Тело секции (вопросы) -->
      <div v-if="expandedSections[si]" class="section-card-body">
        <div
          v-for="(q, qi) in sec.questions"
          :key="q.id || qi"
          class="question-row"
        >
          <div class="question-header">
            <q-chip
              size="sm"
              :color="typeColor(q.type)"
              text-color="white"
              class="type-chip"
            >
              {{ typeLabel(q.type) }}
            </q-chip>
            <q-input
              v-model="q.label"
              dense
              borderless
              placeholder="Текст вопроса"
              class="question-label-input"
              @update:model-value="emitUpdate"
            />
            <div class="q-row-actions">
              <q-btn
                flat
                round
                icon="keyboard_arrow_up"
                size="xs"
                color="grey-6"
                :disable="qi === 0"
                @click="moveQuestion(si, qi, -1)"
              />
              <q-btn
                flat
                round
                icon="keyboard_arrow_down"
                size="xs"
                color="grey-6"
                :disable="qi === sec.questions.length - 1"
                @click="moveQuestion(si, qi, 1)"
              />
              <q-btn
                flat
                round
                icon="delete"
                size="xs"
                color="negative"
                @click="removeQuestion(si, qi)"
              />
            </div>
          </div>

          <!-- Опции для checkbox_group -->
          <div v-if="q.type === 'checkbox_group' && q.options?.length" class="options-block q-ml-md q-mt-xs">
            <div class="text-caption text-grey-7 q-mb-xs">
              Опции ({{ q.options.length }}):
            </div>
            <div
              v-for="(opt, oi) in q.options"
              :key="opt.value || oi"
              class="option-row"
            >
              <q-input
                v-model="opt.label"
                dense
                borderless
                placeholder="Текст опции"
                class="option-label-input"
                @update:model-value="emitUpdate"
              />
              <q-btn
                flat
                round
                icon="delete"
                size="xs"
                color="negative"
                @click="removeOption(si, qi, oi)"
              />
            </div>
            <q-btn
              flat
              dense
              size="xs"
              icon="add"
              color="grey-7"
              label="+ опция"
              class="q-mt-xs"
              @click="addOption(si, qi)"
            />
          </div>
        </div>

        <!-- Добавить вопрос -->
        <div class="add-question-row q-mt-sm">
          <div class="text-caption text-grey-7 q-mr-sm">
            Добавить вопрос:
          </div>
          <q-btn
            v-for="qt in questionTypes"
            :key="qt.value"
            outline
            size="xs"
            :color="typeColor(qt.value)"
            :label="qt.label"
            class="q-mr-xs q-mb-xs"
            @click="addQuestion(si, qt.value)"
          />
        </div>
      </div>
    </div>

    <!-- Добавить секцию -->
    <q-btn
      outline
      color="grey-7"
      icon="add"
      label="Добавить секцию"
      size="sm"
      class="full-width q-mt-sm"
      @click="addSection"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  sections: { type: Array, default: () => [] },
})
const emit = defineEmits(['update'])

const localSections = ref(JSON.parse(JSON.stringify(props.sections)))
const expandedSections = ref({})

watch(() => props.sections, (val) => {
  localSections.value = JSON.parse(JSON.stringify(val))
}, { deep: true })

const questionTypes = [
  { value: 'text', label: 'Текст' },
  { value: 'textarea', label: 'Многостроч.' },
  { value: 'checkbox_group', label: 'Чекбоксы' },
  { value: 'contacts', label: 'Контакты' },
]

function typeLabel(type) {
  const map = {
    text: 'Текст',
    textarea: 'Многостр.',
    checkbox_group: 'Выбор',
    contacts: 'Контакты',
    electro_block: 'Электрика',
  }
  return map[type] || type
}

function typeColor(type) {
  const map = {
    text: 'teal',
    textarea: 'blue',
    checkbox_group: 'grey-7',
    contacts: 'orange',
    electro_block: 'amber',
  }
  return map[type] || 'grey'
}

function toggleSection(si) {
  expandedSections.value[si] = !expandedSections.value[si]
}

function emitUpdate() {
  emit('update', JSON.parse(JSON.stringify(localSections.value)))
}

function addSection() {
  const newId = 'section_' + Date.now()
  localSections.value.push({ id: newId, title: 'Новая секция', questions: [] })
  expandedSections.value[localSections.value.length - 1] = true
  emitUpdate()
}

function removeSection(si) {
  localSections.value.splice(si, 1)
  emitUpdate()
}

function moveSection(si, dir) {
  const arr = localSections.value
  const target = si + dir
  if (target < 0 || target >= arr.length) return
  const tmp = arr[si]
  arr[si] = arr[target]
  arr[target] = tmp
  emitUpdate()
}

function addQuestion(si, type) {
  const qId = 'q_' + Date.now()
  const q = { id: qId, type, label: '' }
  if (type === 'checkbox_group') {
    q.options = []
    q.multiple = true
  }
  if (type === 'contacts') {
    q.subfields = [
      { key: 'phone', label: 'Телефон' },
      { key: 'email', label: 'Email' },
    ]
  }
  localSections.value[si].questions.push(q)
  emitUpdate()
}

function removeQuestion(si, qi) {
  localSections.value[si].questions.splice(qi, 1)
  emitUpdate()
}

function moveQuestion(si, qi, dir) {
  const arr = localSections.value[si].questions
  const target = qi + dir
  if (target < 0 || target >= arr.length) return
  const tmp = arr[qi]
  arr[qi] = arr[target]
  arr[target] = tmp
  emitUpdate()
}

function addOption(si, qi) {
  const q = localSections.value[si].questions[qi]
  if (!q.options) q.options = []
  q.options.push({ value: 'opt_' + Date.now(), label: 'Новая опция' })
  emitUpdate()
}

function removeOption(si, qi, oi) {
  localSections.value[si].questions[qi].options.splice(oi, 1)
  emitUpdate()
}
</script>

<style scoped>
.section-list-editor {
  padding: 4px 0;
}

.section-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.section-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: #f0f0f0;
  cursor: pointer;
}

.drag-icon {
  flex-shrink: 0;
}

.section-title-input {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #2a1a4e;
}

.section-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.section-card-body {
  padding: 10px 12px;
  background: white;
}

.question-row {
  border: 1px solid #ede8f5;
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  background: #faf9ff;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.type-chip {
  flex-shrink: 0;
  font-size: 10px !important;
}

.question-label-input {
  flex: 1;
  min-width: 120px;
  font-size: 13px;
}

.q-row-actions {
  display: flex;
  gap: 1px;
  flex-shrink: 0;
}

.options-block {
  border-left: 2px solid #e0d9f0;
  padding-left: 8px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
}

.option-label-input {
  flex: 1;
  font-size: 12px;
  border-bottom: 1px dashed #bbb;
}

.add-question-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px 0 2px;
  border-top: 1px dashed #e0d9f0;
  margin-top: 8px;
}
</style>
