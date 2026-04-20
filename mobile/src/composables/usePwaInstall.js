/**
 * Composable для управления установкой PWA на главный экран.
 * Поддерживает Android (beforeinstallprompt) и iOS (ручные инструкции).
 *
 * Важно: слушатель beforeinstallprompt регистрируется на уровне модуля,
 * чтобы перехватить событие до монтирования Vue-компонентов.
 */

import { ref, onMounted, onUnmounted } from 'vue'

// Сохраняем событие на уровне модуля (срабатывает раньше монтирования)
let _deferredPrompt = null
const _updateCallbacks = []

function _handleBeforeInstallPrompt(e) {
  e.preventDefault()
  _deferredPrompt = e
  _updateCallbacks.forEach(fn => fn())
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', _handleBeforeInstallPrompt)
}

export function usePwaInstall() {
  const canInstall = ref(false)
  const isIos = ref(false)
  const isInstalled = ref(false)
  const dismissed = ref(false)

  function _isInstalled() {
    return (
      window.navigator.standalone === true ||
      window.matchMedia('(display-mode: standalone)').matches
    )
  }

  function _isIos() {
    return /iPhone|iPad|iPod/i.test(navigator.userAgent) && !window.navigator.standalone
  }

  function dismiss() {
    dismissed.value = true
    localStorage.setItem('pwa_install_dismissed', '1')
  }

  async function install() {
    if (!_deferredPrompt) return false
    _deferredPrompt.prompt()
    const { outcome } = await _deferredPrompt.userChoice
    _deferredPrompt = null
    canInstall.value = false
    return outcome === 'accepted'
  }

  function _onPromptAvailable() {
    canInstall.value = !!_deferredPrompt
  }

  onMounted(() => {
    isInstalled.value = _isInstalled()
    isIos.value = _isIos()
    dismissed.value = localStorage.getItem('pwa_install_dismissed') === '1'
    canInstall.value = !!_deferredPrompt
    _updateCallbacks.push(_onPromptAvailable)
  })

  onUnmounted(() => {
    const idx = _updateCallbacks.indexOf(_onPromptAvailable)
    if (idx !== -1) _updateCallbacks.splice(idx, 1)
  })

  return { canInstall, isIos, isInstalled, dismissed, install, dismiss }
}
