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

      <template v-if="q.type === 'text' || q.type === 'textarea'">
        <div class="ro-value">
          {{ answers[q.id] || '—' }}
        </div>
      </template>

      <template v-else-if="q.type === 'contacts'">
        <div class="ro-value">
          <div v-for="sf in q.subfields" :key="sf.key">
            <span class="ro-sub-label">{{ sf.label }}: </span>
            {{ (answers[q.id] || {})[sf.key] || '—' }}
          </div>
        </div>
      </template>

      <template v-else-if="q.type === 'checkbox_group'">
        <div class="ro-value">
          <div
            v-for="opt in q.options"
            :key="opt.value"
            class="ro-checkbox-row"
          >
            <template v-if="opt.type === 'text_field'">
              <span class="ro-sub-label">{{ opt.label }}</span>
              <span>{{ answers[q.id + '_text_' + opt.value] || '—' }}</span>
            </template>
            <template v-else>
              <q-icon
                :name="isChecked(q.id, opt.value) ? 'check_box' : 'check_box_outline_blank'"
                :color="isChecked(q.id, opt.value) ? 'purple' : 'grey-5'"
                size="16px"
              />
              <span :class="opt.italic ? 'text-italic text-grey-7' : ''">{{ opt.label }}</span>
              <span
                v-if="opt.has_text_input && answers[q.id + '_text_' + opt.value]"
                class="ro-inline-text"
              >: {{ answers[q.id + '_text_' + opt.value] }}</span>
              <!-- Дочерние -->
              <div v-if="opt.children && isChecked(q.id, opt.value)" class="ro-children">
                <div v-for="child in opt.children" :key="child.value" class="ro-checkbox-row ro-child">
                  <q-icon
                    :name="isChecked(q.id + '_children', child.value) ? 'check_box' : 'check_box_outline_blank'"
                    :color="isChecked(q.id + '_children', child.value) ? 'purple' : 'grey-5'"
                    size="14px"
                  />
                  <span :class="child.italic ? 'text-italic text-grey-7' : ''">{{ child.label }}</span>
                </div>
              </div>
            </template>
          </div>
        </div>
      </template>

      <template v-else-if="q.type === 'electro_block'">
        <div class="ro-value">
          <div v-for="sf in q.subfields" :key="sf.key" class="ro-sub-row">
            <span class="ro-sub-label">{{ sf.label }}</span>
            <span>{{ getElectroValue(q.id, sf.key) || '—' }}</span>
          </div>
          <div v-if="q.checkboxes?.length" class="q-mt-xs">
            <div
              v-for="opt in q.checkboxes"
              :key="opt.value"
              class="ro-checkbox-row"
            >
              <q-icon
                :name="isElectroChecked(q.id, opt.value) ? 'check_box' : 'check_box_outline_blank'"
                :color="isElectroChecked(q.id, opt.value) ? 'purple' : 'grey-5'"
                size="16px"
              />
              <span>{{ opt.label }}</span>
              <span v-if="opt.has_text_input && getElectroValue(q.id, opt.value + '_text')" class="ro-inline-text">
                : {{ getElectroValue(q.id, opt.value + '_text') }}
              </span>
            </div>
          </div>
          <div v-if="q.has_comment && getElectroValue(q.id, '_comment')" class="q-mt-xs">
            <span class="ro-sub-label">{{ q.comment_label }}</span>
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
}

.ro-child {
  margin-bottom: 1px;
}

.ro-inline-text {
  color: #6B4FA0;
  font-weight: 500;
}

.ro-sub-label {
  font-weight: 500;
  color: #555;
  margin-right: 4px;
}

.ro-sub-row {
  margin-bottom: 4px;
}
</style>
