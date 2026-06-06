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
    api.get('/api/v1/dashboard/reports/summary', { params }),
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
    api.get('/api/v1/statistics/employees', { params }),

  getSupervision: (params = {}) =>
    api.get('/api/v1/statistics/supervision', { params }),
}

// === CRM ===

export const crmApi = {
  getCards: (projectType, archived = false) =>
    api.get('/api/v1/crm/cards', {
      params: { ...(projectType ? { project_type: projectType } : {}), archived },
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

  reassignExecutor: (cardId, stageName, data) =>
    api.patch(`/api/v1/crm/cards/${cardId}/stage-executor/${encodeURIComponent(stageName)}`, data),

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
    api.post(`/api/v1/crm/cards/${cardId}/workflow/client-ok`),

  signAct: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/sign-act`),

  advanceRound: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/advance-round`),

  closeStage: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/close-stage`),

  addExtraRound: (cardId, data = {}) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/add-extra-round`, data),
  managerAcceptance: (cardId, data) =>
    api.post(`/api/v1/crm/cards/${cardId}/manager-acceptance`, data),
  completeApprovalStage: (cardId, data) =>
    api.post(`/api/v1/crm/cards/${cardId}/complete-approval-stage`, data),
  resetApproval: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/reset-approval`),
  resetDesigner: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/reset-designer`),
  resetDraftsman: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/reset-draftsman`),
  resetStageByName: (cardId, stageName) =>
    api.post(`/api/v1/crm/cards/${cardId}/reset-stage-by-name`, { stage_name: stageName }),

  repairWorkflow: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/workflow/repair`),

  getPayments: (contractId) =>
    api.get(`/api/v1/payments/crm/${contractId}`),

  getStageHistory: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/stage-history`),

  getActionHistory: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/action-history`),

  getAcceptedStages: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/accepted-stages`),

  getSubmittedStages: (cardId) =>
    api.get(`/api/v1/crm/cards/${cardId}/submitted-stages`),

  inviteClientToChat: (cardId) =>
    api.post(`/api/v1/crm/cards/${cardId}/invite-client`),
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
    api.delete(`/api/v1/clients/${clientId}`),

  uploadPhoto: (id, fileOrBlob) => {
    const fd = new FormData()
    const name = fileOrBlob instanceof File ? fileOrBlob.name : 'avatar.jpg'
    fd.append('file', fileOrBlob, name)
    return api.post(`/api/v1/clients/${id}/photo`, fd, {
      transformRequest: [(data, headers) => { delete headers['Content-Type']; return data }],
    })
  },

  deletePhoto: (id) =>
    api.delete(`/api/v1/clients/${id}/photo`),
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
    api.delete(`/api/v1/contracts/${contractId}`),

  updateFiles: (contractId, data) =>
    api.patch(`/api/v1/contracts/${contractId}/files`, data),
}

// === Notifications ===

export const notificationsApi = {
  getList: (unreadOnly = false) =>
    api.get('/api/v1/notifications', { params: { unread_only: unreadOnly } }),

  markRead: (notificationId) =>
    api.put(`/api/v1/notifications/${notificationId}/read`),

  getSettings: (empId) =>
    api.get(`/api/v1/notifications/settings/${empId}`),

  updateSettings: (empId, data) =>
    api.put(`/api/v1/notifications/settings/${empId}`, data),

  testNotification: () =>
    api.post('/api/v1/notifications/test'),

  markAllRead: (empId) =>
    api.post('/api/v1/notifications/mark-all-read', { employee_id: empId }),
}

// === Web Push ===

export const pushApi = {
  getVapidKey: () =>
    api.get('/api/v1/notifications/push/vapid-public-key'),

  subscribe: (subscription) =>
    api.post('/api/v1/notifications/push/subscribe', subscription),

  unsubscribe: () =>
    api.post('/api/v1/notifications/push/unsubscribe'),
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
    api.post(`/api/v1/employees/${id}/send-invite`),

  getPermissions: (id) =>
    api.get(`/api/v1/permissions/${id}`),

  updatePermissions: (id, data) =>
    api.put(`/api/v1/permissions/${id}`, data),

  resetPermissions: (id) =>
    api.post(`/api/v1/permissions/${id}/reset-to-defaults`),

  getTelegramLink: (id) =>
    api.get(`/api/v1/employees/${id}/telegram-link`),

  connectTelegram: (id, code) =>
    api.post(`/api/v1/employees/${id}/telegram-connect/${code}`),

  uploadPhoto: (id, fileOrBlob) => {
    const fd = new FormData()
    const name = fileOrBlob instanceof File ? fileOrBlob.name : 'avatar.jpg'
    fd.append('file', fileOrBlob, name)
    return api.post(`/api/v1/employees/${id}/photo`, fd, {
      transformRequest: [(data, headers) => { delete headers['Content-Type']; return data }],
    })
  },

  deletePhoto: (id) =>
    api.delete(`/api/v1/employees/${id}/photo`),
}

// === Payments ===

export const paymentsApi = {
  getList: (params = {}) =>
    api.get('/api/v1/payments/', { params }),

  calculate: (params) =>
    api.get('/api/v1/payments/calculate', { params }),

  create: (data) =>
    api.post('/api/v1/payments', data),

  update: (id, data) =>
    api.put(`/api/v1/payments/${id}`, data),

  delete: (id) =>
    api.delete(`/api/v1/payments/${id}`),

  markPaid: (id, employeeId) =>
    api.patch(`/api/v1/payments/${id}/mark-paid`, null, { params: { employee_id: employeeId } }),

  getById: (id) =>
    api.get(`/api/v1/payments/${id}`),

  getSummary: (params) =>
    api.get('/api/v1/payments/summary', { params }),

  getByType: (params) =>
    api.get('/api/v1/payments/by-type', { params }),

  markUnpaid: (id) =>
    api.patch(`/api/v1/payments/${id}/mark-unpaid`),
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
    api.delete(`/api/v1/salaries/${id}`),
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
    api.get('/api/v1/dashboard/contract-years'),

  getSupervisionAnalytics: (params = {}) =>
    api.get('/api/v1/dashboard/reports/supervision-analytics', { params }),
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

  getVisitsSummary: (cardId) =>
    api.get(`/api/v1/supervision-visits/${cardId}/visits/summary`),

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

  deleteVisit: (cardId, visitId) =>
    api.delete(`/api/v1/supervision-visits/${cardId}/visits/${visitId}`),

  updateTimelineEntry: (cardId, stageCode, data) =>
    api.put(`/api/v1/supervision-timeline/${cardId}/entry/${stageCode}`, data),

  addHistory: (cardId, data) =>
    api.post(`/api/v1/supervision/cards/${cardId}/history`, data),

  getMonthlyAssignments: (cardId) =>
    api.get(`/api/v1/supervision/cards/${cardId}/monthly-assignments`),

  createMonthlyAssignment: (cardId, data) =>
    api.post(`/api/v1/supervision/cards/${cardId}/monthly-assignments`, data),

  deleteMonthlyAssignment: (cardId, assignmentId) =>
    api.delete(`/api/v1/supervision/cards/${cardId}/monthly-assignments/${assignmentId}`),
}

// === Timeline ===

export const timelineApi = {
  get: (contractId) =>
    api.get(`/api/v1/timeline/${contractId}`),

  init: (contractId, data) =>
    api.post(`/api/v1/timeline/${contractId}/init`, data),

  getSummary: (contractId) =>
    api.get(`/api/v1/timeline/${contractId}/summary`),

  exportExcel: (contractId) =>
    api.get(`/api/v1/timeline/${contractId}/export/excel`, { responseType: 'blob' }),

  exportPdf: (contractId) =>
    api.get(`/api/v1/timeline/${contractId}/export/pdf`, { responseType: 'blob' }),
}

// === Глобальный поиск ===

export const searchApi = {
  global: (params) =>
    api.get('/api/v1/search', { params }),
}

// === История действий ===

export const actionHistoryApi = {
  getList: (params) =>
    api.get('/api/v1/action-history', { params }),

  getByEntity: (entityType, entityId) =>
    api.get(`/api/v1/action-history/${entityType}/${entityId}`),
}

// === Нормо-дни ===

export const normDaysApi = {
  get: (params) =>
    api.get('/api/v1/norm-days', { params }),

  preview: (params) =>
    api.get('/api/v1/norm-days/preview', { params }),

  save: (data) =>
    api.post('/api/v1/norm-days', data),
}

// === Locks (Блокировки при редактировании) ===

export const locksApi = {
  lock: (entityType, entityId) =>
    api.post('/api/v1/locks', { entity_type: entityType, entity_id: entityId }),

  unlock: (entityType, entityId) =>
    api.delete(`/api/v1/locks/${entityType}/${entityId}`),

  check: (entityType, entityId) =>
    api.get(`/api/v1/locks/${entityType}/${entityId}`),
}

// === Messenger (Telegram-чаты проектов) ===

export const messengerApi = {
  getChats: (params) => api.get('/api/v1/messenger/chats', { params }),
  createChat: (data) => api.post('/api/v1/messenger/chats', data),
  createSupervisionChat: (data) => api.post('/api/v1/messenger/chats/supervision', data),
  deleteChat: (chatId) => api.delete(`/api/v1/messenger/chats/${chatId}`),
  getChatMembers: (chatId) => api.get(`/api/v1/messenger/chats/${chatId}/members`),
  sendMessage: (chatId, data) => api.post(`/api/v1/messenger/chats/${chatId}/message`, data),
  getScripts: (params) => api.get('/api/v1/messenger/scripts', { params }),
  triggerScript: (scriptId, chatId) => api.post(`/api/v1/messenger/scripts/${scriptId}/trigger`, { chat_id: chatId }),
  sendSurvey: (chatId, data) => api.post(`/api/v1/messenger/chats/${chatId}/send-survey`, data),
  // Настройки сервера
  getSettings: () => api.get('/api/v1/messenger/settings'),
  updateSettings: (settings) => api.put('/api/v1/messenger/settings', {
    settings: Object.entries(settings).map(([setting_key, setting_value]) => ({ setting_key, setting_value: setting_value ?? '' })),
  }),
  getStatus: () => api.get('/api/v1/messenger/status'),
  // MTProto авторизация
  mtprotoSendCode: () => api.post('/api/v1/messenger/mtproto/send-code'),
  mtprotoVerifyCode: (code) => api.post('/api/v1/messenger/mtproto/verify-code', { code }),
  mtprotoResendSms: () => api.post('/api/v1/messenger/mtproto/resend-sms'),
  mtprotoSessionStatus: () => api.get('/api/v1/messenger/mtproto/session-status'),
  // Email шаблоны
  previewEmail: (type) => api.get(`/api/v1/messenger/email-preview/${type}`),
  getEmailTemplate: (type) => api.get(`/api/v1/messenger/email-template/${type}`),
  saveEmailTemplate: (type, html) => api.put(`/api/v1/messenger/email-template/${type}`, { html }),
  resetEmailTemplate: (type) => api.delete(`/api/v1/messenger/email-template/${type}`),
}

// === Files (Яндекс.Диск) ===

export const filesApi = {
  getContractFiles: (contractId, stage) =>
    api.get(`/api/v1/files/contract/${contractId}`, {
      params: stage ? { stage } : {},
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
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// === Surveys (опросы клиентов) ===

export const surveyApi = {
  getByContract: (contractId, projectType) =>
    api.get(`/api/v1/surveys/contract/${contractId}`, { params: projectType ? { project_type: projectType } : {} }),
  create: (data) =>
    api.post('/api/v1/surveys/create', data),
  resend: (surveyId) =>
    api.post(`/api/v1/surveys/${surveyId}/resend`),
  getStats: (params = {}) =>
    api.get('/api/v1/surveys/stats', { params }),
}

export const deletedContractsApi = {
  getList: () => api.get('/api/v1/admin/deleted-contracts/'),
  restore: (id) => api.post(`/api/v1/admin/deleted-contracts/${id}/restore`),
  permanentDelete: (id) => api.delete(`/api/v1/admin/deleted-contracts/${id}`),
}

export const adminApi = {
  triggerBackup: () => api.post('/api/v1/admin/backup/postgres'),
  getBackupStatus: () => api.get('/api/v1/admin/backup/status'),
  listBackups: () => api.get('/api/v1/admin/backup/list'),
}

// Push-уведомления для гостей клиентского чата (без JWT)
export const clientPushApi = {
  getVapidKey: (token) => api.get(`/api/v1/client-chat/${token}/push/vapid-key`),
  subscribe: (token, subscription) => api.post(`/api/v1/client-chat/${token}/push/subscribe`, subscription),
  unsubscribe: (token) => api.post(`/api/v1/client-chat/${token}/push/unsubscribe`),
}
