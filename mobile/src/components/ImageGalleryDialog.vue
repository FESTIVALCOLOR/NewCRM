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
        @wheel.prevent="handleWheel"
      >
        <q-btn
          v-if="idx > 0"
          flat
          round
          icon="chevron_left"
          color="white"
          style="position:absolute;left:4px;z-index:2;opacity:0.8;background:rgba(0,0,0,0.35)"
          @click="prevImage"
        />
        <img
          v-if="currentImage"
          :src="currentImage.src"
          :style="{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: '4px', padding: '8px', transform: `scale(${scale})`, transformOrigin: 'center center', transition: 'transform 0.2s ease' }"
        >
        <q-btn
          v-if="idx < images.length - 1"
          flat
          round
          icon="chevron_right"
          color="white"
          style="position:absolute;right:4px;z-index:2;opacity:0.8;background:rgba(0,0,0,0.35)"
          @click="nextImage"
        />
      </div>

      <!-- Footer: zoom + open in browser -->
      <div class="row items-center justify-between q-pa-sm" style="flex-shrink:0">
        <div class="row no-wrap" style="gap:4px">
          <q-btn
            flat
            round
            dense
            icon="remove"
            color="white"
            size="sm"
            :disable="scale <= MIN_SCALE"
            @click="zoomOut"
          />
          <q-btn
            flat
            round
            dense
            icon="search"
            color="white"
            size="sm"
            :disable="scale === 1"
            @click="resetZoom"
          />
          <q-btn
            flat
            round
            dense
            icon="add"
            color="white"
            size="sm"
            :disable="scale >= MAX_SCALE"
            @click="zoomIn"
          />
        </div>
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

const MIN_SCALE = 0.5
const MAX_SCALE = 4
const ZOOM_STEP = 0.5

const idx = ref(props.startIndex)
const scale = ref(1)

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

watch(() => props.startIndex, (v) => { idx.value = v })
watch(() => props.modelValue, (v) => { if (v) { idx.value = props.startIndex; scale.value = 1 } })
watch(idx, () => { scale.value = 1 })

const currentImage = computed(() => props.images[idx.value] || null)

function prevImage() { if (idx.value > 0) idx.value-- }
function nextImage() { if (idx.value < props.images.length - 1) idx.value++ }

function zoomIn() { scale.value = Math.min(MAX_SCALE, +(scale.value + ZOOM_STEP).toFixed(1)) }
function zoomOut() { scale.value = Math.max(MIN_SCALE, +(scale.value - ZOOM_STEP).toFixed(1)) }
function resetZoom() { scale.value = 1 }

function handleWheel(e) {
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

function handleSwipe({ direction }) {
  if (scale.value !== 1) return
  if (direction === 'right') prevImage()
  else if (direction === 'left') nextImage()
}

function openInBrowser() {
  if (currentImage.value?.url) window.open(currentImage.value.url, '_blank')
}
</script>
