<template>
  <q-dialog v-model="open" persistent>
    <q-card class="avatar-crop-card">
      <q-card-section class="q-pb-xs">
        <div class="text-subtitle2 text-weight-bold">
          Обрезать фото
        </div>
        <div class="text-caption" style="color: #999">
          Перемещайте и масштабируйте фото
        </div>
      </q-card-section>

      <!-- Область обрезки -->
      <div
        ref="stageRef"
        class="crop-stage"
        @touchstart.prevent="onTouchStart"
        @touchmove.prevent="onTouchMove"
        @touchend.prevent="onTouchEnd"
        @mousedown.prevent="onMouseDown"
        @mousemove.prevent="onMouseMove"
        @mouseup.prevent="onMouseUp"
        @mouseleave.prevent="onMouseUp"
      >
        <img
          ref="imgRef"
          :src="src"
          class="crop-img"
          :style="imgStyle"
          draggable="false"
          @load="onImgLoad"
        >
        <!-- Круговой кроп-оверлей — box-shadow затемняет всё за пределами круга -->
        <div class="crop-circle" />
      </div>

      <q-card-actions align="right" class="q-pt-xs">
        <q-btn flat dense label="Отмена" @click="cancel" />
        <q-btn
          unelevated
          dense
          color="accent"
          text-color="dark"
          label="Применить"
          @click="applyCrop"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  src: String,
})
const emit = defineEmits(['update:modelValue', 'cropped'])

const STAGE = 280   // размер контейнера в px (квадрат)
const CROP_D = 220  // диаметр круга обрезки
const CROP_R = CROP_D / 2
const OUTPUT = 400  // размер итогового изображения

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const stageRef = ref(null)
const imgRef = ref(null)

// Начальные размеры отображения изображения
const dispW = ref(STAGE)
const dispH = ref(STAGE)
// Текущая позиция и масштаб
const tx = ref(0)
const ty = ref(0)
const sc = ref(1)

function onImgLoad() {
  const img = imgRef.value
  if (!img) return
  const nat = img.naturalWidth / img.naturalHeight

  // Начальный масштаб: изображение заполняет круг обрезки
  let dW, dH
  if (nat >= 1) {
    dH = CROP_D
    dW = dH * nat
  } else {
    dW = CROP_D
    dH = dW / nat
  }

  dispW.value = dW
  dispH.value = dH
  sc.value = 1

  // Центрируем в stage
  tx.value = (STAGE - dW) / 2
  ty.value = (STAGE - dH) / 2
}

// Ограничение: изображение всегда покрывает круг обрезки
function clamp() {
  const scaledW = dispW.value * sc.value
  const scaledH = dispH.value * sc.value
  const cropL = STAGE / 2 - CROP_R
  const cropT = STAGE / 2 - CROP_R
  const maxTx = cropL
  const minTx = cropL + CROP_D - scaledW
  const maxTy = cropT
  const minTy = cropT + CROP_D - scaledH
  tx.value = Math.min(maxTx, Math.max(minTx, tx.value))
  ty.value = Math.min(maxTy, Math.max(minTy, ty.value))
}

const imgStyle = computed(() => ({
  position: 'absolute',
  left: 0,
  top: 0,
  width: `${dispW.value}px`,
  height: `${dispH.value}px`,
  transform: `translate(${tx.value}px, ${ty.value}px) scale(${sc.value})`,
  transformOrigin: '0 0',
  userSelect: 'none',
  pointerEvents: 'none',
}))

// ===== Перетаскивание мышью =====
let dragging = false
let lastMX = 0
let lastMY = 0

function onMouseDown(e) {
  dragging = true
  lastMX = e.clientX
  lastMY = e.clientY
}
function onMouseMove(e) {
  if (!dragging) return
  tx.value += e.clientX - lastMX
  ty.value += e.clientY - lastMY
  lastMX = e.clientX
  lastMY = e.clientY
  clamp()
}
function onMouseUp() {
  dragging = false
}

// ===== Touch: drag + pinch =====
let pinchStartDist = 0
let pinchStartSc = 1
let touchDragging = false
let lastTX = 0
let lastTY = 0

function onTouchStart(e) {
  if (e.touches.length === 1) {
    touchDragging = true
    lastTX = e.touches[0].clientX
    lastTY = e.touches[0].clientY
  } else if (e.touches.length === 2) {
    touchDragging = false
    pinchStartDist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY,
    )
    pinchStartSc = sc.value
  }
}

function onTouchMove(e) {
  if (e.touches.length === 1 && touchDragging) {
    tx.value += e.touches[0].clientX - lastTX
    ty.value += e.touches[0].clientY - lastTY
    lastTX = e.touches[0].clientX
    lastTY = e.touches[0].clientY
    clamp()
  } else if (e.touches.length === 2) {
    const dist = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY,
    )
    const newSc = pinchStartSc * (dist / pinchStartDist)
    sc.value = Math.max(0.5, Math.min(5, newSc))
    clamp()
  }
}

function onTouchEnd() {
  touchDragging = false
}

// ===== Применить обрезку =====
function applyCrop() {
  const img = imgRef.value
  if (!img) return

  // Область crop-круга в координатах stage
  const cropStageX = STAGE / 2 - CROP_R
  const cropStageY = STAGE / 2 - CROP_R

  // Преобразуем в координаты отображаемого изображения (до масштаба)
  const dispX = (cropStageX - tx.value) / sc.value
  const dispY = (cropStageY - ty.value) / sc.value
  const dispCropW = CROP_D / sc.value
  const dispCropH = CROP_D / sc.value

  // Преобразуем в натуральные координаты изображения
  const ratioX = img.naturalWidth / dispW.value
  const ratioY = img.naturalHeight / dispH.value
  const srcX = Math.max(0, dispX * ratioX)
  const srcY = Math.max(0, dispY * ratioY)
  const srcW = Math.min(dispCropW * ratioX, img.naturalWidth - srcX)
  const srcH = Math.min(dispCropH * ratioY, img.naturalHeight - srcY)

  const canvas = document.createElement('canvas')
  canvas.width = OUTPUT
  canvas.height = OUTPUT
  const ctx = canvas.getContext('2d')

  // Обрезаем по кругу
  ctx.beginPath()
  ctx.arc(OUTPUT / 2, OUTPUT / 2, OUTPUT / 2, 0, Math.PI * 2)
  ctx.clip()

  ctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, OUTPUT, OUTPUT)

  canvas.toBlob(
    (blob) => {
      emit('cropped', blob)
      open.value = false
    },
    'image/jpeg',
    0.9,
  )
}

function cancel() {
  open.value = false
}
</script>

<style scoped>
.avatar-crop-card {
  width: 320px;
  max-width: 95vw;
}

.crop-stage {
  width: 280px;
  height: 280px;
  position: relative;
  overflow: hidden;
  background: #111;
  margin: 0 auto;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.crop-stage:active {
  cursor: grabbing;
}

.crop-img {
  display: block;
}

/* Круговой оверлей: box-shadow затемняет область вне круга */
.crop-circle {
  position: absolute;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 0 1000px rgba(0, 0, 0, 0.55);
  border: 2px solid rgba(255, 255, 255, 0.8);
  pointer-events: none;
  z-index: 2;
}
</style>
