<template>
  <q-dialog v-model="visible" maximized transition-show="fade" transition-hide="fade">
    <div style="background:#111;display:flex;flex-direction:column;height:100%;width:100%">
      <!-- Header -->
      <div class="row no-wrap items-center q-px-sm" style="min-height:48px;flex-shrink:0;gap:4px">
        <q-btn
          flat
          round
          dense
          icon="close"
          color="white"
          @click="visible = false"
        />
        <div class="col ellipsis text-white text-body2" style="font-size:13px">
          {{ currentImage?.filename || 'Изображение' }}
        </div>
        <div class="text-white text-caption" style="min-width:44px;text-align:right;flex-shrink:0">
          {{ idx + 1 }}/{{ images.length }}
        </div>
      </div>

      <!-- Image area with swipe and arrows -->
      <div
        v-touch-swipe.mouse="handleSwipe"
        class="col flex flex-center"
        style="position:relative;overflow:hidden"
      >
        <q-btn
          v-if="idx > 0"
          flat
          round
          icon="chevron_left"
          color="white"
          style="position:absolute;left:4px;z-index:2;opacity:0.8;background:rgba(0,0,0,0.35)"
          @click="idx--"
        />
        <img
          v-if="currentImage"
          :src="currentImage.src"
          style="max-width:100%;max-height:100%;object-fit:contain;border-radius:4px;padding:8px"
        >
        <q-btn
          v-if="idx < images.length - 1"
          flat
          round
          icon="chevron_right"
          color="white"
          style="position:absolute;right:4px;z-index:2;opacity:0.8;background:rgba(0,0,0,0.35)"
          @click="idx++"
        />
      </div>

      <!-- Footer: open in browser -->
      <div class="row justify-center q-pa-sm" style="flex-shrink:0">
        <q-btn
          flat
          no-caps
          icon="open_in_new"
          label="Открыть в браузере"
          color="white"
          size="sm"
          :disable="!currentImage?.url"
          @click="openInBrowser"
        />
      </div>
    </div>
  </q-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  images: { type: Array, default: () => [] },
  startIndex: { type: Number, default: 0 },
})
const emit = defineEmits(['update:modelValue'])

const idx = ref(props.startIndex)

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

watch(() => props.startIndex, (v) => { idx.value = v })
watch(() => props.modelValue, (v) => { if (v) idx.value = props.startIndex })

const currentImage = computed(() => props.images[idx.value] || null)

function handleSwipe({ direction }) {
  if (direction === 'right' && idx.value > 0) idx.value--
  else if (direction === 'left' && idx.value < props.images.length - 1) idx.value++
}

function openInBrowser() {
  if (currentImage.value?.url) window.open(currentImage.value.url, '_blank')
}
</script>
