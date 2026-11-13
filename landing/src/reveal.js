// Плавное появление блоков при прокрутке: элементы с классом .reveal
let observer = null

export function refreshReveal() {
  if (!observer) {
    observer = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target) } })
    }, { threshold: 0.1 })
  }
  document.querySelectorAll('.reveal:not(.visible)').forEach(el => observer.observe(el))
}

// Вызывается после смены страницы или подгрузки данных: новым блокам нужно время появиться в разметке
export function scheduleReveal(delay = 100) {
  setTimeout(refreshReveal, delay)
}
