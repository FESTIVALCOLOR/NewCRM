const BASE = '/api/v1'

function token() { return localStorage.getItem('admin_token') || '' }

async function req(method, path, body, isForm = false) {
  const headers = { Authorization: `Bearer ${token()}` }
  if (body && !isForm) headers['Content-Type'] = 'application/json'
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: isForm ? body : (body ? JSON.stringify(body) : undefined),
  })
  if (res.status === 401) { logout(); throw new Error('401') }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export function logout() {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_user')
  window.location.reload()
}

export async function login(username, password) {
  const body = new URLSearchParams({ username, password })
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Неверный логин или пароль')
  }
  const data = await res.json()
  // Войти в CRM может любой сотрудник, а в панель сайта — только руководитель: проверяем сразу
  const check = await fetch(`${BASE}/site/admin/settings`, { headers: { Authorization: `Bearer ${data.access_token}` } })
  if (!check.ok) throw new Error('Доступ к панели сайта есть только у Руководителя студии')
  localStorage.setItem('admin_token', data.access_token)
  return data
}

// ── Settings ────────────────────────────────
export const settings = {
  list: () => req('GET', '/site/admin/settings'),
  update: (key, value) => req('PUT', `/site/admin/settings/${key}`, { value }),
}

// ── Sections ────────────────────────────────
export const sections = {
  list: () => req('GET', '/site/admin/sections'),
  update: (key, data) => req('PUT', `/site/admin/sections/${key}`, data),
  reorder: (items) => req('PUT', '/site/admin/sections/reorder', items),
}

// ── Team ────────────────────────────────────
export const team = {
  list: () => req('GET', '/site/admin/team'),
  create: (d) => req('POST', '/site/admin/team', d),
  update: (id, d) => req('PUT', `/site/admin/team/${id}`, d),
  delete: (id) => req('DELETE', `/site/admin/team/${id}`),
  reorder: (items) => req('PUT', '/site/admin/team/reorder', items),
}

// ── Stats ───────────────────────────────────
export const stats = {
  list: () => req('GET', '/site/admin/stats'),
  create: (d) => req('POST', '/site/admin/stats', d),
  update: (id, d) => req('PUT', `/site/admin/stats/${id}`, d),
  delete: (id) => req('DELETE', `/site/admin/stats/${id}`),
  reorder: (items) => req('PUT', '/site/admin/stats/reorder', items),
}

// ── Services ────────────────────────────────
export const services = {
  list: () => req('GET', '/site/admin/services'),
  create: (d) => req('POST', '/site/admin/services', d),
  update: (id, d) => req('PUT', `/site/admin/services/${id}`, d),
  delete: (id) => req('DELETE', `/site/admin/services/${id}`),
  reorder: (items) => req('PUT', '/site/admin/services/reorder', items),
}

// ── Pricing ─────────────────────────────────
export const pricing = {
  list: () => req('GET', '/site/admin/pricing'),
  create: (d) => req('POST', '/site/admin/pricing', d),
  update: (id, d) => req('PUT', `/site/admin/pricing/${id}`, d),
  delete: (id) => req('DELETE', `/site/admin/pricing/${id}`),
  reorder: (items) => req('PUT', '/site/admin/pricing/reorder', items),
}

// ── Reviews ─────────────────────────────────
export const reviews = {
  list: () => req('GET', '/site/admin/reviews'),
  create: (d) => req('POST', '/site/admin/reviews', d),
  update: (id, d) => req('PUT', `/site/admin/reviews/${id}`, d),
  delete: (id) => req('DELETE', `/site/admin/reviews/${id}`),
  reorder: (items) => req('PUT', '/site/admin/reviews/reorder', items),
}

// ── Portfolio ───────────────────────────────
export const portfolio = {
  list: () => req('GET', '/site/admin/portfolio'),
  create: (d) => req('POST', '/site/admin/portfolio', d),
  update: (id, d) => req('PUT', `/site/admin/portfolio/${id}`, d),
  delete: (id) => req('DELETE', `/site/admin/portfolio/${id}`),
  reorder: (items) => req('PUT', '/site/admin/portfolio/reorder', items),
  upload: async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return req('POST', '/site/admin/upload', fd, true)
  },
}

// ── Карта объектов ──────────────────────────
export const map = {
  status: () => req('GET', '/site/admin/map/status'),
  sync: () => req('POST', '/site/admin/map/sync'),
  setHidden: (contractId, hidden) => req('PUT', `/site/admin/map/points/${contractId}`, { hidden }),
}

// ── Analytics / SEO ─────────────────────────
export const analytics = {
  get: () => req('GET', '/site/admin/analytics'),
  update: (d) => req('PUT', '/site/admin/analytics', d),
}
