/**
 * API сервис — централизованные вызовы к Interior Studio CRM API
 */
import { api } from 'src/boot/axios'

// === Dashboard ===

export const dashboardApi = {
  getClients: (params = {}) =>
    api.get('/api/v1/dashboard/clients', { params }),

  getContracts: (params = {}) =>
    api.get('/api/v1/dashboard/contracts', { params }),

  getCrm: (params) =>
    api.get('/api/v1/dashboard/crm', { params }),

  getEmployees: () =>
    api.get('/api/v1/dashboard/employees'),

  getReportsSummary: (params = {}) =>
    api.get('/api/v1/dashboard/reports/summary', { params })
}

// === Statistics ===

export const statisticsApi = {
  getDashboard: (params = {}) =>
    api.get('/api/v1/statistics/dashboard', { params }),

  getGeneral: (params) =>
    api.get('/api/v1/statistics/general', { params }),

  getFunnel: (params = {}) =>
    api.get('/api/v1/statistics/funnel', { params }),

  getProjects: (params = {}) =>
    api.get('/api/v1/statistics/projects', { params }),

  getContractsByPeriod: (params = {}) =>
    api.get('/api/v1/statistics/contracts-by-period', { params }),

  getEmployees: (params = {}) =>
    api.get('/api/v1/statistics/employees', { params })
}

// === CRM ===

export const crmApi = {
  getCards: (projectType, archived = false) =>
    api.get('/api/v1/crm/cards', {
      params: { project_type: projectType, archived }
    }),

  getCard: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}`),

  getWorkflowState: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/workflow/state`),

  getStageHistory: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/stage-history`),

  moveCard: (cardId, columnName) =>
    api.patch(`/api/v1/crm/cards/${cardId}/column`, { column_name: columnName }),

  updateCard: (cardId, data) =>
    api.patch(`/api/v1/crm/cards/${cardId}`, data),

  assignExecutor: (cardId, data) =>
    api.post(`/api/v1/crm/cards/${cardId}/stage-executor`, data),

  completeStage: (cardId, stageName, executorId) =>
    api.patch(`/api/v1/crm/cards/${cardId}/stage-executor/${encodeURIComponent(stageName)}/complete`, { executor_id: executorId }),

  updateDeadline: (cardId, stageName, deadline) =>
    api.patch(`/api/v1/crm/cards/${cardId}/stage-executor-deadline`, { stage_name: stageName, deadline }),

  // Workflow actions
  submitWork: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/submit`),

  acceptWork: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/accept`),

  rejectWork: (cardId, data) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/reject`, data),

  sendToClient: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/client-send`),

  clientApproved: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/client-approved`),

  signAct: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/sign-act`),

  getTimeline: (contractId) =>
    api.get(`/api/v1/timeline/${contractId}`),

  getPayments: (cardId) =>
    api.get('/api/v1/payments', { params: { crm_card_id: cardId } }),

  getStageHistory: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/stage-history`),

  getActionHistory: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/action-history`),

  getAcceptedStages: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/accepted-stages`),

  getSubmittedStages: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/submitted-stages`)
}

// === Clients ===

export const clientsApi = {
  getList: (params = {}) =>
    api.get('/api/v1/clients', { params }),

  getById: (clientId) =>
    api.get(`/api/v1/clients/${clientId}`),

  create: (data) =>
    api.post('/api/v1/clients', data),

  update: (clientId, data) =>
    api.put(`/api/v1/clients/${clientId}`, data),

  delete: (clientId) =>
    api.delete(`/api/v1/clients/${clientId}`)
}

// === Contracts ===

export const contractsApi = {
  getList: (params = {}) =>
    api.get('/api/v1/contracts', { params }),

  getById: (contractId) =>
    api.get(`/api/v1/contracts/${contractId}`),

  create: (data) =>
    api.post('/api/v1/contracts', data),

  update: (contractId, data) =>
    api.put(`/api/v1/contracts/${contractId}`, data),

  delete: (contractId) =>
    api.delete(`/api/v1/contracts/${contractId}`)
}

// === Notifications ===

export const notificationsApi = {
  getList: (unreadOnly = false) =>
    api.get('/api/v1/notifications', { params: { unread_only: unreadOnly } }),

  markRead: (notificationId) =>
    api.put(`/api/v1/notifications/${notificationId}/read`)
}

// === Employees ===

export const employeesApi = {
  getList: (params = {}) =>
    api.get('/api/v1/employees', { params }),

  getById: (id) =>
    api.get(`/api/v1/employees/${id}`),

  create: (data) =>
    api.post('/api/v1/employees', data),

  update: (id, data) =>
    api.put(`/api/v1/employees/${id}`, data),

  delete: (id) =>
    api.delete(`/api/v1/employees/${id}`),

  getTelegramInfo: (id) =>
    api.get(`/api/v1/employees/${id}/telegram-info`),

  createTelegramToken: (id) =>
    api.post(`/api/v1/employees/${id}/create-telegram-token`),

  sendInvite: (id) =>
    api.post(`/api/v1/employees/${id}/send-invite`)
}

// === Payments ===

export const paymentsApi = {
  getList: (params = {}) =>
    api.get('/api/v1/payments', { params }),

  calculate: (params) =>
    api.get('/api/v1/payments/calculate', { params }),

  create: (data) =>
    api.post('/api/v1/payments', data),

  update: (id, data) =>
    api.put(`/api/v1/payments/${id}`, data),

  delete: (id) =>
    api.delete(`/api/v1/payments/${id}`),

  markPaid: (id, employeeId) =>
    api.patch(`/api/v1/payments/${id}/mark-paid`, null, { params: { employee_id: employeeId || 0 } })
}

// === Salaries ===

export const salariesApi = {
  getList: (params = {}) =>
    api.get('/api/v1/salaries', { params }),

  getReport: (params = {}) =>
    api.get('/api/v1/salaries/report', { params }),

  create: (data) =>
    api.post('/api/v1/salaries', data),

  update: (id, data) =>
    api.put(`/api/v1/salaries/${id}`, data),

  delete: (id) =>
    api.delete(`/api/v1/salaries/${id}`)
}

// === Reports ===

export const reportsApi = {
  getSummary: (params = {}) =>
    api.get('/api/v1/dashboard/reports/summary', { params }),

  getClientsDynamics: (params = {}) =>
    api.get('/api/v1/dashboard/reports/clients-dynamics', { params }),

  getCrmAnalytics: (params = {}) =>
    api.get('/api/v1/statistics/projects', { params }),

  getCrmAnalyticsDetailed: (params = {}) =>
    api.get('/api/v1/dashboard/reports/crm-analytics', { params }),

  getFunnel: (params = {}) =>
    api.get('/api/v1/statistics/funnel', { params }),

  getAgentTypes: () =>
    api.get('/api/v1/statistics/agent-types'),

  getCities: () =>
    api.get('/api/v1/statistics/cities'),

  getContractYears: () =>
    api.get('/api/v1/dashboard/contract-years')
}

// === Supervision ===

export const supervisionApi = {
  getCards: (params = {}) =>
    api.get('/api/v1/supervision/cards', { params }),

  getCard: (cardId) =>
    api.get(`/api/v1/supervision/cards/${cardId}`),

  getTimeline: (cardId) =>
    api.get(`/api/v1/supervision-timeline/${cardId}`),

  getTimelineSummary: (cardId) =>
    api.get(`/api/v1/supervision-timeline/${cardId}/summary`),

  getVisits: (cardId) =>
    api.get(`/api/v1/supervision-visits/${cardId}/visits`),

  getHistory: (cardId) =>
    api.get(`/api/v1/supervision/cards/${cardId}/history`),

  updateCard: (cardId, data) =>
    api.patch(`/api/v1/supervision/cards/${cardId}`, data),

  moveCard: (cardId, columnName) =>
    api.patch(`/api/v1/supervision/cards/${cardId}/column`, { column_name: columnName }),

  pause: (cardId, reason) =>
    api.post(`/api/v1/supervision/cards/${cardId}/pause`, { pause_reason: reason }),

  resume: (cardId) =>
    api.post(`/api/v1/supervision/cards/${cardId}/resume`),

  completeStage: (cardId) =>
    api.post(`/api/v1/supervision/cards/${cardId}/complete-stage`),

  createVisit: (cardId, data) =>
    api.post(`/api/v1/supervision-visits/${cardId}/visits`, data),

  updateTimelineEntry: (cardId, stageCode, data) =>
    api.put(`/api/v1/supervision-timeline/${cardId}/entry/${stageCode}`, data),

  addHistory: (cardId, data) =>
    api.post(`/api/v1/supervision/cards/${cardId}/history`, data)
}

// === Files (Яндекс.Диск) ===

export const filesApi = {
  getContractFiles: (contractId, stage) =>
    api.get(`/api/v1/files/contract/${contractId}`, {
      params: stage ? { stage } : {}
    }),

  listFolder: (folderPath) =>
    api.get('/api/v1/files/list', { params: { folder_path: folderPath } }),

  getPublicLink: (yandexPath) =>
    api.get('/api/v1/files/public-link', { params: { yandex_path: yandexPath } }),

  upload: (file, yandexPath) => {
    const formData = new FormData()
    formData.append('file', file)
    // yandex_path передаётся как query parameter (не form field!)
    const params = yandexPath ? { yandex_path: yandexPath } : {}
    return api.post('/api/v1/files/upload', formData, {
      params,
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}
