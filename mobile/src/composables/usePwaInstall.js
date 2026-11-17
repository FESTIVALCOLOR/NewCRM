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
  const isYandex = ref(false)
  const isMobile = ref(false)
  const isMacSafari = ref(false)

  function _isInstalled() {
    return (
      window.navigator.standalone === true ||
      window.matchMedia('(display-mode: standalone)').matches
    )
  }

  function _isIos() {
    const ua = navigator.userAgent
    const isIpad = /iPad/i.test(ua) || (/Macintosh/i.test(ua) && navigator.maxTouchPoints > 1)
    return (isIpad || /iPhone|iPod/i.test(ua)) && !window.navigator.standalone
  }

  function _isYandex() {
    return /YaBrowser/i.test(navigator.userAgent)
  }

  function _isMobile() {
    return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  }

  function _isMacSafari() {
    const ua = navigator.userAgent
    const isMac = /Macintosh/i.test(ua) && navigator.maxTouchPoints === 0
    const isSafari = /Safari/i.test(ua) && !/Chrome|Chromium|CriOS|EdgA?/i.test(ua) && !/YaBrowser/i.test(ua)
    return isMac && isSafari
  }

  function dismiss() {
    dismissed.value = true
    localStorage.setItem('pwa_install_dismissed', Date.now().toString())
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
    isYandex.value = _isYandex()
    isMobile.value = _isMobile()
    isMacSafari.value = _isMacSafari()
    const ts = localStorage.getItem('pwa_install_dismissed')
    dismissed.value = !!ts && Date.now() - parseInt(ts) < 14 * 24 * 60 * 60 * 1000
    canInstall.value = !!_deferredPrompt
    _updateCallbacks.push(_onPromptAvailable)
  })

  onUnmounted(() => {
    const idx = _updateCallbacks.indexOf(_onPromptAvailable)
    if (idx !== -1) _updateCallbacks.splice(idx, 1)
  })

  return { canInstall, isIos, isInstalled, dismissed, isYandex, isMobile, isMacSafari, install, dismiss }
}
