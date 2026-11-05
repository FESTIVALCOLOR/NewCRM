<template>
  <div class="survey-section-form">
    <div
      v-for="q in section.questions"
      :key="q.id"
      class="survey-question-row"
    >
      <!-- Текстовое поле -->
      <template v-if="q.type === 'text'">
        <div class="q-label">
          {{ q.label }}
        </div>
        <q-input
          :model-value="answers[q.id] || ''"
          outlined
          dense
          class="q-mt-xs"
          @update:model-value="val => emit('update', q.id, val)"
        />
      </template>

      <!-- Многострочное поле -->
      <template v-else-if="q.type === 'textarea'">
        <div class="q-label">
          {{ q.label }}
        </div>
        <q-input
          :model-value="answers[q.id] || ''"
          outlined
          dense
          type="textarea"
          rows="3"
          class="q-mt-xs"
          @update:model-value="val => emit('update', q.id, val)"
        />
      </template>

      <!-- Контакты (тел + email) -->
      <template v-else-if="q.type === 'contacts'">
        <div class="q-label">
          {{ q.label }}
        </div>
        <div class="contacts-row">
          <q-input
            v-for="sf in q.subfields"
            :key="sf.key"
            :label="sf.label"
            :model-value="(answers[q.id] || {})[sf.key] || ''"
            outlined
            dense
            class="contact-field q-mt-xs"
            @update:model-value="val => emit('update', q.id, { ...(answers[q.id] || {}), [sf.key]: val })"
          />
        </div>
      </template>

      <!-- Группа чекбоксов -->
      <template v-else-if="q.type === 'checkbox_group'">
        <div class="q-label">
          {{ q.label }}
        </div>
        <div class="checkboxes-block q-mt-xs">
          <div
            v-for="opt in q.options"
            :key="opt.value"
            class="checkbox-option"
          >
            <!-- Поле-только-текст (например "Желаемые габариты ванны:") -->
            <template v-if="opt.type === 'text_field'">
              <div class="text-field-inline">
                <span class="opt-label-text">{{ opt.label }}</span>
                <q-input
                  :model-value="getCheckboxTextValue(q.id, opt.value)"
                  outlined
                  dense
                  class="inline-text-input"
                  @update:model-value="val => setCheckboxText(q.id, opt.value, val)"
                />
              </div>
            </template>

            <!-- Да/Нет inline -->
            <template v-else-if="opt.type === 'yes_no_inline'">
              <div class="yes-no-row">
                <span class="opt-label-text">{{ opt.label }}</span>
                <div class="yes-no-btns">
                  <q-btn
                    flat
                    size="sm"
                    :color="getCheckboxTextValue(q.id, opt.value) === 'Да' ? 'purple' : 'grey'"
                    label="Да"
                    class="yn-btn"
                    @click="setCheckboxText(q.id, opt.value, 'Да')"
                  />
                  <q-btn
                    flat
                    size="sm"
                    :color="getCheckboxTextValue(q.id, opt.value) === 'Нет' ? 'purple' : 'grey'"
                    label="Нет"
                    class="yn-btn"
                    @click="setCheckboxText(q.id, opt.value, 'Нет')"
                  />
                </div>
              </div>
            </template>

            <!-- Обычный чекбокс -->
            <template v-else>
              <q-checkbox
                :model-value="isChecked(q.id, opt.value)"
                :label="opt.label"
                :class="opt.italic ? 'italic-opt' : ''"
                color="purple"
                dense
                @update:model-value="val => toggleCheckbox(q.id, opt.value, val, q.multiple)"
              />

              <!-- Дочерние опции -->
              <div v-if="opt.children && isChecked(q.id, opt.value)" class="children-block">
                <q-checkbox
                  v-for="child in opt.children"
                  :key="child.value"
                  :model-value="isChecked(q.id + '_children', child.value)"
                  :label="child.label"
                  :class="child.italic ? 'italic-opt' : ''"
                  color="purple"
                  dense
                  class="q-ml-md"
                  @update:model-value="val => toggleCheckbox(q.id + '_children', child.value, val, true)"
                />
              </div>

              <!-- Текстовое поле под чекбоксом -->
              <div v-if="opt.has_text_input && isChecked(q.id, opt.value)" class="checkbox-text-field">
                <q-input
                  :label="opt.text_input_label || ''"
                  :model-value="getCheckboxTextValue(q.id, opt.value)"
                  outlined
                  dense
                  class="q-ml-lg q-mt-xs"
                  @update:model-value="val => setCheckboxText(q.id, opt.value, val)"
                />
              </div>
            </template>
          </div>
        </div>
      </template>

      <!-- Блок электрики -->
      <template v-else-if="q.type === 'electro_block'">
        <div class="q-label">
          {{ q.label }}
        </div>
        <div class="electro-block q-mt-xs">
          <q-input
            v-for="sf in q.subfields"
            :key="sf.key"
            :label="sf.label"
            :model-value="getElectroValue(q.id, sf.key)"
            outlined
            dense
            :type="sf.type === 'textarea' ? 'textarea' : 'text'"
            :rows="sf.type === 'textarea' ? 2 : undefined"
            class="q-mb-sm"
            @update:model-value="val => setElectroValue(q.id, sf.key, val)"
          />

          <div v-if="q.checkboxes?.length" class="checkboxes-block q-mt-xs">
            <div
              v-for="opt in q.checkboxes"
              :key="opt.value"
              class="checkbox-option"
            >
              <q-checkbox
                :model-value="isElectroChecked(q.id, opt.value)"
                :label="opt.label"
                color="purple"
                dense
                @update:model-value="val => toggleElectro(q.id, opt.value, val)"
              />
              <div v-if="opt.has_text_input && isElectroChecked(q.id, opt.value)" class="checkbox-text-field">
                <q-input
                  :label="opt.text_input_label || ''"
                  :model-value="getElectroValue(q.id, opt.value + '_text')"
                  outlined
                  dense
                  class="q-ml-lg q-mt-xs"
                  @update:model-value="val => setElectroValue(q.id, opt.value + '_text', val)"
                />
              </div>
            </div>
          </div>

          <q-input
            v-if="q.has_comment"
            :label="q.comment_label || 'Пожелания:'"
            :model-value="getElectroValue(q.id, '_comment')"
            outlined
            dense
            type="textarea"
            rows="2"
            class="q-mt-sm"
            @update:model-value="val => setElectroValue(q.id, '_comment', val)"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  section: { type: Object, required: true },
  answers: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update'])

function isChecked(questionId, value) {
  const ans = props.answers[questionId]
  if (Array.isArray(ans)) return ans.includes(value)
  return ans === value
}

function toggleCheckbox(questionId, value, checked, multiple) {
  const current = props.answers[questionId]
  if (multiple) {
    const arr = Array.isArray(current) ? [...current] : []
    if (checked) {
      if (!arr.includes(value)) arr.push(value)
    } else {
      const idx = arr.indexOf(value)
      if (idx >= 0) arr.splice(idx, 1)
    }
    emit('update', questionId, arr)
  } else {
    emit('update', questionId, checked ? value : null)
  }
}

function getCheckboxTextValue(questionId, optValue) {
  const textKey = questionId + '_text_' + optValue
  return props.answers[textKey] || ''
}

function setCheckboxText(questionId, optValue, val) {
  const textKey = questionId + '_text_' + optValue
  emit('update', textKey, val)
}

function getElectroValue(questionId, key) {
  const ans = props.answers[questionId]
  if (ans && typeof ans === 'object') return ans[key] || ''
  return ''
}

function setElectroValue(questionId, key, val) {
  const current = props.answers[questionId] || {}
  emit('update', questionId, { ...current, [key]: val })
}

function isElectroChecked(questionId, value) {
  const ans = props.answers[questionId] || {}
  const checked = ans._checked || []
  return Array.isArray(checked) && checked.includes(value)
}

function toggleElectro(questionId, value, checked) {
  const current = props.answers[questionId] || {}
  const arr = Array.isArray(current._checked) ? [...current._checked] : []
  if (checked) {
    if (!arr.includes(value)) arr.push(value)
  } else {
    const idx = arr.indexOf(value)
    if (idx >= 0) arr.splice(idx, 1)
  }
  emit('update', questionId, { ...current, _checked: arr })
}
</script>

<style scoped>
.survey-section-form {
  padding: 12px 16px;
}

.survey-question-row {
  margin-bottom: 16px;
}

.q-label {
  font-size: 13px;
  color: #555;
  font-style: italic;
  margin-bottom: 4px;
  line-height: 1.4;
}

.contacts-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.contact-field {
  flex: 1;
  min-width: 160px;
}

.checkboxes-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.checkbox-option {
  margin-bottom: 2px;
}

.italic-opt :deep(.q-checkbox__label) {
  font-style: italic;
  color: #666;
}

.children-block {
  margin-left: 24px;
  margin-top: 2px;
  border-left: 2px solid #e0d9f0;
  padding-left: 8px;
}

.checkbox-text-field {
  margin-top: 4px;
}

.text-field-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

.opt-label-text {
  font-size: 13px;
  color: #333;
  white-space: nowrap;
}

.inline-text-input {
  flex: 1;
  max-width: 300px;
}

.yes-no-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.yes-no-btns {
  display: flex;
  gap: 4px;
}

.yn-btn {
  min-width: 48px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.electro-block {
  border: 1px solid #e0d9f0;
  border-radius: 8px;
  padding: 12px;
  background: #faf9ff;
}
</style>
