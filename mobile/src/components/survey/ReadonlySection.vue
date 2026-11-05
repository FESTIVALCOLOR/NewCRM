<template>
  <div class="readonly-section q-pa-md">
    <div
      v-for="q in section.questions"
      :key="q.id"
      class="readonly-row"
    >
      <div class="ro-label">
        {{ q.label }}
      </div>

      <!-- text / textarea -->
      <template v-if="q.type === 'text' || q.type === 'textarea'">
        <div class="ro-value">
          {{ answers[q.id] || '—' }}
        </div>
      </template>

      <!-- contacts -->
      <template v-else-if="q.type === 'contacts'">
        <div class="ro-value">
          <div v-for="sf in q.subfields" :key="sf.key">
            <span class="ro-sub-label">{{ sf.label }}: </span>
            {{ (answers[q.id] || {})[sf.key] || '—' }}
          </div>
        </div>
      </template>

      <!-- checkbox_group -->
      <template v-else-if="q.type === 'checkbox_group'">
        <div class="ro-value">
          <div
            v-for="opt in q.options"
            :key="opt.value"
          >
            <!-- Разделитель секции -->
            <template v-if="opt.type === 'separator'">
              <div class="ro-separator">
                <span class="ro-separator-label">{{ opt.label }}</span>
              </div>
            </template>

            <!-- Поле ввода текста (text_field) -->
            <template v-else-if="opt.type === 'text_field'">
              <div class="ro-checkbox-row">
                <span class="ro-sub-label">{{ opt.label }}: </span>
                <span :class="answers[q.id + '_text_' + opt.value] ? 'ro-inline-text' : 'text-grey-5'">
                  {{ answers[q.id + '_text_' + opt.value] || '—' }}
                </span>
              </div>
            </template>

            <!-- Да / Нет inline -->
            <template v-else-if="opt.type === 'yes_no_inline'">
              <div class="ro-yn-row">
                <span class="ro-yn-label">{{ opt.label }}</span>
                <span class="ro-yn-line" />
                <span
                  class="ro-yn-badge"
                  :class="getCheckboxText(q.id, opt.value) === 'Да' ? 'ro-yn-yes'
                    : getCheckboxText(q.id, opt.value) === 'Нет' ? 'ro-yn-no'
                      : 'ro-yn-empty'"
                >
                  {{ getCheckboxText(q.id, opt.value) || '—' }}
                </span>
              </div>
            </template>

            <!-- Обычный чекбокс -->
            <template v-else>
              <div class="ro-checkbox-row">
                <q-icon
                  :name="isChecked(q.id, opt.value) ? 'check_box' : 'check_box_outline_blank'"
                  :color="isChecked(q.id, opt.value) ? 'purple' : 'grey-5'"
                  size="16px"
                />
                <span :class="opt.italic ? 'text-italic text-grey-7' : ''">{{ opt.label }}</span>
                <!-- Текст ручного ввода -->
                <span
                  v-if="opt.has_text_input && answers[q.id + '_text_' + opt.value]"
                  class="ro-inline-text"
                >: {{ answers[q.id + '_text_' + opt.value] }}</span>
                <!-- Выпадающий список -->
                <span
                  v-if="opt.has_select && answers[q.id + '_text_' + opt.value + '_sel']"
                  class="ro-select-value"
                >
                  <q-icon name="arrow_drop_down" size="12px" />
                  {{ opt.select_label ? opt.select_label + ' ' : '' }}{{ answers[q.id + '_text_' + opt.value + '_sel'] }}
                </span>
              </div>
              <!-- Дочерние чекбоксы -->
              <div v-if="opt.children && isChecked(q.id, opt.value)" class="ro-children">
                <div v-for="child in opt.children" :key="child.value" class="ro-checkbox-row ro-child">
                  <q-icon
                    :name="isChecked(q.id + '_sub_' + opt.value, child.value) ? 'check_box' : 'check_box_outline_blank'"
                    :color="isChecked(q.id + '_sub_' + opt.value, child.value) ? 'purple' : 'grey-5'"
                    size="14px"
                  />
                  <span :class="child.italic ? 'text-italic text-grey-7' : ''">{{ child.label }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>
      </template>

      <!-- electro_block -->
      <template v-else-if="q.type === 'electro_block'">
        <div class="ro-value">
          <!-- Subfields -->
          <div v-for="sf in q.subfields" :key="sf.key" class="ro-sub-row">
            <span class="ro-sub-label">{{ sf.label }}</span>
            <!-- yes_no — линия + цветной бэджик -->
            <template v-if="sf.type === 'yes_no'">
              <span class="ro-yn-line" />
              <span
                class="ro-yn-badge"
                :class="getElectroValue(q.id, sf.key) === 'Да' ? 'ro-yn-yes'
                  : getElectroValue(q.id, sf.key) === 'Нет' ? 'ro-yn-no'
                    : 'ro-yn-empty'"
              >
                {{ getElectroValue(q.id, sf.key) || '—' }}
              </span>
            </template>
            <!-- Текст -->
            <template v-else>
              <span :class="getElectroValue(q.id, sf.key) ? 'ro-inline-text' : ''">
                {{ getElectroValue(q.id, sf.key) || '—' }}
              </span>
            </template>
          </div>

          <!-- Checkboxes -->
          <div v-if="q.checkboxes?.length" class="q-mt-xs">
            <div
              v-for="opt in q.checkboxes"
              :key="opt.value"
              class="q-mb-xs"
            >
              <div class="ro-checkbox-row">
                <q-icon
                  :name="isElectroChecked(q.id, opt.value) ? 'check_box' : 'check_box_outline_blank'"
                  :color="isElectroChecked(q.id, opt.value) ? 'purple' : 'grey-5'"
                  size="16px"
                />
                <span>{{ opt.label }}</span>
                <!-- Текст ручного ввода -->
                <span v-if="opt.has_text_input && getElectroValue(q.id, opt.value + '_text')" class="ro-inline-text">
                  {{ opt.text_input_label ? opt.text_input_label + ': ' : ': ' }}{{ getElectroValue(q.id, opt.value + '_text') }}
                </span>
                <!-- Выпадающий список -->
                <span v-if="opt.has_select && getElectroValue(q.id, opt.value + '_select')" class="ro-select-value">
                  <q-icon name="arrow_drop_down" size="12px" />
                  {{ opt.select_label ? opt.select_label + ' ' : '' }}{{ getElectroValue(q.id, opt.value + '_select') }}
                </span>
              </div>
            </div>
          </div>

          <!-- Комментарий -->
          <div v-if="q.has_comment && getElectroValue(q.id, '_comment')" class="q-mt-xs ro-comment">
            <span class="ro-sub-label">{{ q.comment_label || 'Пожелания' }}: </span>
            <span>{{ getElectroValue(q.id, '_comment') }}</span>
          </div>
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

function isChecked(questionId, value) {
  const ans = props.answers[questionId]
  if (Array.isArray(ans)) return ans.includes(value)
  return ans === value
}

function getCheckboxText(questionId, optValue) {
  return props.answers[questionId + '_text_' + optValue] || ''
}

function getElectroValue(questionId, key) {
  const ans = props.answers[questionId]
  if (ans && typeof ans === 'object') return ans[key] || ''
  return ''
}

function isElectroChecked(questionId, value) {
  const ans = props.answers[questionId] || {}
  const checked = ans._checked || []
  return Array.isArray(checked) && checked.includes(value)
}
</script>

<style scoped>
.readonly-section {}

.readonly-row {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f0ff;
  align-items: start;
}

@media (max-width: 540px) {
  .readonly-row {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .ro-label {
    color: #888;
    font-size: 11px;
    padding-bottom: 2px;
  }

  .ro-inline-text {
    flex-basis: 100%;
    margin-top: 2px;
    margin-left: 20px;
    border-left: 2px solid #e0d9f0;
    padding-left: 6px;
  }

  .ro-select-value {
    flex-basis: 100%;
    margin-left: 20px;
    margin-top: 2px;
    border-left: 2px solid #e0d9f0;
    padding-left: 6px;
    border-radius: 0;
  }
}

.readonly-row:last-child {
  border-bottom: none;
}

.ro-label {
  font-size: 12px;
  color: #666;
  font-style: italic;
  line-height: 1.4;
  padding-top: 2px;
}

.ro-value {
  font-size: 13px;
  color: #222;
}

.ro-checkbox-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 2px;
  flex-wrap: wrap;
}

.ro-children {
  margin-left: 22px;
  margin-top: 2px;
  width: 100%;
  border-left: 2px solid #e0d9f0;
  padding-left: 8px;
}

.ro-child {
  margin-bottom: 1px;
}

.ro-inline-text {
  color: #6B4FA0;
  font-weight: 500;
  font-size: 11px;
}

.ro-select-value {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  color: #6B4FA0;
  font-weight: 500;
  background: #f0ebff;
  padding: 1px 7px 1px 4px;
  border-radius: 10px;
  margin-left: 2px;
}

.ro-sub-label {
  font-weight: 500;
  color: #555;
}

.ro-sub-row {
  display: flex;
  align-items: center;
  gap: 0;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.ro-comment {
  font-style: italic;
  color: #555;
}

/* Да / Нет бэджик */
.ro-yn-row {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 4px 8px;
  background: #fafafa;
  border: 1px solid #ede8f5;
  border-radius: 6px;
  margin-bottom: 3px;
}

.ro-yn-label {
  font-size: 13px;
  color: #333;
  line-height: 1.4;
}

.ro-yn-line {
  flex: 1;
  border-bottom: 1px dashed #c8c0d8;
  align-self: flex-end;
  margin: 0 8px 3px;
  min-width: 8px;
}

.ro-yn-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 12px;
  border-radius: 4px;
  min-width: 40px;
  text-align: center;
  flex-shrink: 0;
}

.ro-yn-yes {
  background: #EDE8F5;
  color: #6B4FA0;
}

.ro-yn-no {
  background: #FFEBEE;
  color: #C62828;
}

.ro-yn-empty {
  background: #f5f5f5;
  color: #999;
}

/* ─── Тёмная тема ─────────────────────────────────────────────── */
:global(.body--dark .readonly-row) {
  border-bottom-color: #3d3060;
}

:global(.body--dark .ro-label) {
  color: #9d94c0;
}

:global(.body--dark .ro-value) {
  color: #d0cce8;
}

:global(.body--dark .ro-sub-label) {
  color: #b8b0d8;
}

:global(.body--dark .ro-comment) {
  color: #aaa;
}

:global(.body--dark .ro-yn-row) {
  background: #22203a;
  border-color: #3d3060;
}

:global(.body--dark .ro-yn-line) {
  border-bottom-color: #4d3d80;
}

:global(.body--dark .ro-inline-text) {
  border-left-color: #4d3d80;
}

:global(.body--dark .ro-select-value) {
  border-left-color: #4d3d80;
}

:global(.body--dark .ro-yn-label) {
  color: #d0cce8;
}

:global(.body--dark .ro-yn-yes) {
  background: #2d2558;
  color: #c5b0f0;
}

:global(.body--dark .ro-yn-no) {
  background: #2a1515;
  color: #ef9a9a;
}

:global(.body--dark .ro-yn-empty) {
  background: #2a2a2a;
  color: #777;
}

:global(.body--dark .ro-children) {
  border-left-color: #4d3d80;
}

:global(.body--dark .ro-separator-label) {
  color: #b89ee0;
}

:global(.body--dark .ro-separator::before),
:global(.body--dark .ro-separator::after) {
  background: #4d3d80;
}

/* Разделитель секции */
.ro-separator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0 4px;
  width: 100%;
}

.ro-separator::before,
.ro-separator::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #d0c8e8;
}

.ro-separator-label {
  font-size: 11px;
  color: #7c6fa8;
  font-weight: 600;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
</style>
