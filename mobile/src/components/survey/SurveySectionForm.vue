<template>
  <div class="survey-section-form">
    <div
      v-for="q in section.questions"
      :key="q.id"
      :class="['survey-question-row', { 'field-error': q.required && invalidFields.has(q.id) }]"
    >
      <!-- Заметка (note) -->
      <template v-if="q.type === 'note'">
        <div class="survey-note">
          {{ q.text }}
        </div>
      </template>

      <!-- Текстовое поле -->
      <template v-else-if="q.type === 'text'">
        <div class="q-label">
          {{ q.label }}<span v-if="q.required" class="req-star">*</span>
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
          {{ q.label }}<span v-if="q.required" class="req-star">*</span>
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
          {{ q.label }}<span v-if="q.required" class="req-star">*</span>
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
            <!-- Разделитель секции -->
            <template v-if="opt.type === 'separator'">
              <div class="opt-separator">
                <span class="opt-separator-label">{{ opt.label }}</span>
              </div>
            </template>

            <!-- Поле-только-текст (например "Желаемые габариты ванны:") -->
            <template v-else-if="opt.type === 'text_field'">
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
                <span class="yn-line" />
                <div class="yes-no-btns">
                  <q-btn
                    unelevated
                    size="sm"
                    :color="getCheckboxTextValue(q.id, opt.value) === 'Да' ? 'purple' : 'grey-3'"
                    :text-color="getCheckboxTextValue(q.id, opt.value) === 'Да' ? 'white' : 'grey-8'"
                    label="Да"
                    class="yn-btn"
                    @click="setCheckboxText(q.id, opt.value, 'Да')"
                  />
                  <q-btn
                    unelevated
                    size="sm"
                    :color="getCheckboxTextValue(q.id, opt.value) === 'Нет' ? 'negative' : 'grey-3'"
                    :text-color="getCheckboxTextValue(q.id, opt.value) === 'Нет' ? 'white' : 'grey-8'"
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

              <!-- Описание под чекбоксом (description) — скрыть только если есть children И выбрано -->
              <div v-if="opt.description && !(opt.children && isChecked(q.id, opt.value))" class="opt-description">
                {{ opt.description }}
              </div>

              <!-- Дочерние опции -->
              <div v-if="opt.children && isChecked(q.id, opt.value)" class="children-block">
                <q-checkbox
                  v-for="child in opt.children"
                  :key="child.value"
                  :model-value="isChecked(q.id + '_sub_' + opt.value, child.value)"
                  :label="child.label"
                  :class="child.italic ? 'italic-opt' : ''"
                  color="purple"
                  dense
                  class="q-ml-md"
                  @update:model-value="val => toggleCheckbox(q.id + '_sub_' + opt.value, child.value, val, true)"
                />
              </div>

              <!-- Выпадающий список при выборе (has_select) -->
              <div v-if="opt.has_select && isChecked(q.id, opt.value)" class="checkbox-text-field">
                <q-select
                  :label="opt.select_label || 'Выбрать'"
                  :model-value="getCheckboxTextValue(q.id, opt.value + '_sel')"
                  :options="opt.select_options || []"
                  outlined
                  dense
                  emit-value
                  map-options
                  class="q-ml-lg q-mt-xs"
                  style="min-width: 200px"
                  @update:model-value="val => setCheckboxText(q.id, opt.value + '_sel', val)"
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
          <div
            v-for="sf in q.subfields"
            :key="sf.key"
            class="q-mb-sm"
          >
            <!-- Да/Нет вопрос -->
            <template v-if="sf.type === 'yes_no'">
              <div class="yes-no-subfield">
                <span class="sf-label">{{ sf.label }}</span>
                <span class="yn-line" />
                <div class="yes-no-btns">
                  <q-btn
                    unelevated
                    size="sm"
                    :color="getElectroValue(q.id, sf.key) === 'Да' ? 'purple' : 'grey-3'"
                    :text-color="getElectroValue(q.id, sf.key) === 'Да' ? 'white' : 'grey-8'"
                    label="Да"
                    class="yn-btn"
                    @click="setElectroValue(q.id, sf.key, 'Да')"
                  />
                  <q-btn
                    unelevated
                    size="sm"
                    :color="getElectroValue(q.id, sf.key) === 'Нет' ? 'negative' : 'grey-3'"
                    :text-color="getElectroValue(q.id, sf.key) === 'Нет' ? 'white' : 'grey-8'"
                    label="Нет"
                    class="yn-btn"
                    @click="setElectroValue(q.id, sf.key, 'Нет')"
                  />
                </div>
              </div>
            </template>
            <!-- Текст / textarea -->
            <template v-else>
              <q-input
                :label="sf.label"
                :model-value="getElectroValue(q.id, sf.key)"
                outlined
                dense
                :type="sf.type === 'textarea' ? 'textarea' : 'text'"
                :rows="sf.type === 'textarea' ? 2 : undefined"
                @update:model-value="val => setElectroValue(q.id, sf.key, val)"
              />
            </template>
          </div>

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
              <!-- Выпадающий список при выборе (has_select) -->
              <div v-if="opt.has_select && isElectroChecked(q.id, opt.value)" class="checkbox-text-field">
                <q-select
                  :label="opt.select_label || 'Выбрать'"
                  :model-value="getElectroValue(q.id, opt.value + '_select')"
                  :options="opt.select_options || []"
                  outlined
                  dense
                  emit-value
                  map-options
                  class="q-ml-lg q-mt-xs"
                  style="min-width: 200px"
                  @update:model-value="val => setElectroValue(q.id, opt.value + '_select', val)"
                />
              </div>
              <!-- Текстовое поле при выборе (has_text_input) -->
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
  invalidFields: { type: Object, default: () => new Set() },
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

.req-star {
  color: #e53935;
  font-style: normal;
  font-weight: 700;
  margin-left: 2px;
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
  flex: 1;
  min-width: 0;
}

.inline-text-input {
  flex: 1;
  max-width: 300px;
}

.yes-no-row {
  display: flex;
  align-items: center;
  gap: 0;
}

.yes-no-btns {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.yn-btn {
  min-width: 48px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.field-error {
  border-left: 3px solid #e53935;
  padding-left: 8px;
  margin-left: -8px;
  border-radius: 2px;
  background: #fff8f8;
}

.electro-block {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 12px;
  background: #f7f7f7;
}

.yes-no-subfield {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 6px 8px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
}

.sf-label {
  font-size: 13px;
  color: #333;
  line-height: 1.4;
}

.yn-line {
  flex: 1;
  border-bottom: 1px dashed #c8c0d8;
  align-self: flex-end;
  margin: 0 8px 3px;
  min-width: 8px;
}

.opt-description {
  font-size: 11px;
  color: #888;
  font-style: italic;
  margin-left: 28px;
  margin-top: -2px;
  line-height: 1.3;
}

.survey-note {
  font-size: 12px;
  color: #666;
  font-style: italic;
  background: #f5f5f5;
  border-left: 3px solid #9c89b8;
  padding: 8px 12px;
  border-radius: 4px;
  line-height: 1.5;
  white-space: pre-line;
}

.opt-separator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 4px;
}

.opt-separator::before,
.opt-separator::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #d0c8e8;
}

.opt-separator-label {
  font-size: 11px;
  color: #7c6fa8;
  font-weight: 600;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ─── Тёмная тема ─────────────────────────────────────────────── */
/* Используем .survey-section-form для специфичности 0,3,0 > scoped 0,2,0 */
:global(.body--dark .survey-section-form .q-label) { color: #9d94c0; }
:global(.body--dark .survey-section-form .opt-label-text) { color: #d0cce8; }
:global(.body--dark .survey-section-form .sf-label) { color: #d0cce8; }
:global(.body--dark .survey-section-form .opt-description) { color: #7a7599; }
:global(.body--dark .survey-section-form .field-error) {
  background: #2a1a1a !important;
}

:global(.body--dark .survey-section-form .electro-block) {
  background: #252525 !important;
  border-color: #3a3a3a !important;
}
:global(.body--dark .survey-section-form .yes-no-subfield) {
  background: #2a2a2a !important;
  border-color: #3a3a3a !important;
}
:global(.body--dark .survey-section-form .survey-note) {
  background: #242424 !important;
  color: #c8c8c8;
  border-left-color: #555;
}
:global(.body--dark .survey-section-form .yn-btn) { border-color: #555; }
:global(.body--dark .survey-section-form .yn-line) { border-bottom-color: #555; }
:global(.body--dark .survey-section-form .children-block) { border-left-color: #444; }
:global(.body--dark .survey-section-form .opt-separator::before),
:global(.body--dark .survey-section-form .opt-separator::after) { background: #444; }
:global(.body--dark .survey-section-form .opt-separator-label) { color: #aaa; }
</style>
