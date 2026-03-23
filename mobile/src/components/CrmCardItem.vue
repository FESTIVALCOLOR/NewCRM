<template>
  <q-card
    flat
    bordered
    class="q-mb-sm cursor-pointer"
    style="border-radius: 8px"
    @click="$emit('click')"
  >
    <q-card-section class="q-pa-sm">
      <!-- Номер договора + deadline -->
      <div class="row items-center justify-between q-mb-xs">
        <div class="text-caption text-weight-bold text-primary">
          {{ card.contract_number || `#${card.id}` }}
        </div>
        <q-badge
          v-if="deadlineStatus"
          :color="deadlineStatus.color"
          :label="deadlineStatus.label"
          dense
        />
      </div>

      <!-- Адрес -->
      <div class="text-body2 ellipsis-2-lines q-mb-xs">
        {{ card.address || 'Без адреса' }}
      </div>

      <!-- Клиент + площадь -->
      <div class="row items-center justify-between text-caption text-grey-7">
        <span class="ellipsis" style="max-width: 60%">{{ card.client_name || '' }}</span>
        <span v-if="card.area">{{ card.area }} м²</span>
      </div>

      <!-- Исполнители -->
      <div v-if="executors.length > 0" class="q-mt-xs">
        <q-chip
          v-for="exec in executors"
          :key="exec"
          dense
          size="sm"
          color="grey-3"
          text-color="grey-8"
          class="q-mr-xs"
        >
          {{ exec }}
        </q-chip>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  card: { type: Object, required: true }
})

defineEmits(['click'])

const deadlineStatus = computed(() => {
  if (!props.card.deadline) return null
  const deadline = new Date(props.card.deadline)
  const now = new Date()
  const daysLeft = Math.ceil((deadline - now) / 86400000)

  if (daysLeft < 0) return { color: 'negative', label: 'Просрочено' }
  if (daysLeft <= 3) return { color: 'warning', label: `${daysLeft} дн.` }
  if (daysLeft <= 7) return { color: 'orange-4', label: `${daysLeft} дн.` }
  return null
})

const executors = computed(() => {
  const names = []
  if (props.card.designer_name) names.push(props.card.designer_name.split(' ')[0])
  if (props.card.draftsman_name) names.push(props.card.draftsman_name.split(' ')[0])
  return names.slice(0, 2)
})
</script>
