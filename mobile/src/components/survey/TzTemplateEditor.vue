<template>
  <div class="tz-template-editor">
    <!-- Вкладки: секции до комнат / секции после комнат -->
    <q-tabs v-model="activeTab" dense align="justify" class="tz-editor-tabs">
      <q-tab name="before" label="Секции до комнат" />
      <q-tab name="rooms" label="Шаблоны комнат" />
      <q-tab name="after" label="Секции после комнат" />
    </q-tabs>

    <q-tab-panels v-model="activeTab" animated>
      <!-- Секции до комнат -->
      <q-tab-panel name="before" class="q-pa-sm">
        <SectionListEditor
          :sections="localTemplate.sections_before_rooms || []"
          @update="v => updateSections('sections_before_rooms', v)"
        />
      </q-tab-panel>

      <!-- Шаблоны комнат (только просмотр имён) -->
      <q-tab-panel name="rooms" class="q-pa-sm">
        <div class="text-caption text-grey-7 q-mb-sm">
          Шаблоны помещений — названия и иконки. Вопросы комнат редактируются через JSON (сложная структура).
        </div>
        <div
          v-for="rt in (localTemplate.room_templates || [])"
          :key="rt.id"
          class="room-tpl-item q-mb-xs"
        >
          <q-icon :name="rt.icon || 'door_front'" color="purple" size="20px" />
          <span class="room-tpl-name">{{ rt.name }}</span>
          <span class="text-caption text-grey-6">({{ rt.questions?.length || 0 }} вопросов)</span>
        </div>
      </q-tab-panel>

      <!-- Секции после комнат -->
      <q-tab-panel name="after" class="q-pa-sm">
        <SectionListEditor
          :sections="localTemplate.sections_after_rooms || []"
          @update="v => updateSections('sections_after_rooms', v)"
        />
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import SectionListEditor from './SectionListEditor.vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

const activeTab = ref('before')
const localTemplate = ref(JSON.parse(JSON.stringify(props.modelValue || {})))

watch(() => props.modelValue, (val) => {
  localTemplate.value = JSON.parse(JSON.stringify(val || {}))
}, { deep: true })

function updateSections(key, newSections) {
  localTemplate.value = { ...localTemplate.value, [key]: newSections }
  emit('update:modelValue', JSON.parse(JSON.stringify(localTemplate.value)))
}
</script>

<style scoped>
.tz-template-editor {
  border: 1px solid #e0d9f0;
  border-radius: 10px;
  overflow: hidden;
}

.tz-editor-tabs {
  background: #f0f0f0;
  color: #2a2a2a;
}

.room-tpl-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #faf9ff;
  border: 1px solid #e0d9f0;
  border-radius: 6px;
}

.room-tpl-name {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}
</style>
