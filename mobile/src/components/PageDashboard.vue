<template>
  <div class="page-dashboard" :class="{ hidden: !visible }">
    <div class="row q-col-gutter-xs">
      <div v-for="item in items" :key="item.label" :class="colClass">
        <div class="dash-item">
          <div class="dash-value" :style="{ color: item.color || '#333' }">
            {{ item.value }}
          </div>
          <div class="dash-label">
            {{ item.label }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const visible = ref(true)
let lastScrollY = 0
let ticking = false

const colClass = computed(() => {
  const len = props.items.length
  if (len <= 2) return 'col-6'
  if (len <= 3) return 'col-4'
  return 'col-3'
})

function onScroll() {
  if (ticking) return
  ticking = true
  requestAnimationFrame(() => {
    const currentY = window.scrollY
    // Показываем если вверху страницы или скроллим вверх (с порогом 20px)
    if (currentY <= 20) { visible.value = true }
    else if (currentY < lastScrollY - 5) { visible.value = true }
    else if (currentY > lastScrollY + 5) { visible.value = false }
    lastScrollY = currentY
    ticking = false
  })
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.page-dashboard {
  position: fixed;
  bottom: 48px; /* над нижним меню */
  left: 0;
  right: 0;
  background: white;
  border-top: 2px solid #ffd93c;
  padding: 4px 8px;
  z-index: 90;
  transition: transform 0.3s ease;
}
.page-dashboard.hidden {
  transform: translateY(100%);
}
.dash-item { text-align: center; padding: 2px 0 }
.dash-value { font-size: 14px; font-weight: bold; color: #333 }
.dash-label { font-size: 9px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }

@media (min-width: 1024px) {
  .page-dashboard { bottom: 0; left: 260px; } /* На десктопе учитываем ширину sidebar */
}
</style>
