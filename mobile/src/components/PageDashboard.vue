<template>
  <transition name="slide-down">
    <div v-if="visible" class="page-dashboard" :style="{ borderTopColor: accentColor }">
      <div class="row q-col-gutter-xs">
        <div v-for="item in items" :key="item.label" :class="colClass">
          <div class="dash-item">
            <div class="dash-value" :style="{ color: item.color || '#333' }">{{ item.value }}</div>
            <div class="dash-label">{{ item.label }}</div>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  accentColor: { type: String, default: '#ffd93c' }
})

const visible = ref(true)
let lastScrollY = 0

const colClass = props.items.length <= 3 ? 'col-4' : props.items.length <= 4 ? 'col-3' : 'col'

function onScroll() {
  const currentY = window.scrollY
  visible.value = currentY <= 10 || currentY < lastScrollY
  lastScrollY = currentY
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.page-dashboard {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  border-top: 2px solid #ffd93c;
  padding: 6px 8px;
  z-index: 100;
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.3s ease }
.slide-down-enter-from, .slide-down-leave-to { transform: translateY(100%); opacity: 0 }
.dash-item { text-align: center; padding: 2px 0 }
.dash-value { font-size: 14px; font-weight: bold; color: #333 }
.dash-label { font-size: 9px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
</style>
