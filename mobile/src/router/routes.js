export default [
  // Авторизация
  {
    path: '/login',
    component: () => import('src/layouts/AuthLayout.vue'),
    children: [
      {
        path: '',
        name: 'login',
        component: () => import('src/pages/LoginPage.vue'),
        meta: { requiresAuth: false },
      },
    ],
  },

  // Основное приложение
  {
    path: '/',
    component: () => import('src/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('src/pages/DashboardPage.vue'),
        meta: { title: 'Главная', icon: 'dashboard' },
      },
      {
        path: 'crm',
        name: 'crm',
        component: () => import('src/pages/CrmBoardPage.vue'),
        meta: { title: 'CRM', icon: 'view_kanban', requiresPermission: 'access.crm' },
      },
      {
        path: 'crm/:id',
        name: 'crm-card',
        component: () => import('src/pages/CrmCardPage.vue'),
        meta: { title: 'Карточка проекта', requiresPermission: 'access.crm' },
      },
      {
        path: 'clients',
        name: 'clients',
        component: () => import('src/pages/ClientsPage.vue'),
        meta: { title: 'Клиенты', icon: 'people', requiresPermission: 'access.clients' },
      },
      {
        path: 'clients/:id',
        name: 'client-detail',
        component: () => import('src/pages/ClientDetailPage.vue'),
        meta: { title: 'Клиент', requiresPermission: 'access.clients' },
      },
      {
        path: 'contracts',
        name: 'contracts',
        component: () => import('src/pages/ContractsPage.vue'),
        meta: { title: 'Договоры', icon: 'description', requiresPermission: 'access.contracts' },
      },
      {
        path: 'contracts/:id',
        name: 'contract-detail',
        component: () => import('src/pages/ContractDetailPage.vue'),
        meta: { title: 'Договор', requiresPermission: 'access.contracts' },
      },
      {
        path: 'supervision',
        name: 'supervision',
        component: () => import('src/pages/SupervisionPage.vue'),
        meta: { title: 'Надзор', icon: 'engineering', requiresPermission: 'access.supervision' },
      },
      {
        path: 'supervision/:id',
        name: 'supervision-detail',
        component: () => import('src/pages/SupervisionDetailPage.vue'),
        meta: { title: 'Карточка надзора', requiresPermission: 'access.supervision' },
      },
      {
        path: 'employees',
        name: 'employees',
        component: () => import('src/pages/EmployeesPage.vue'),
        meta: { title: 'Сотрудники', icon: 'badge', requiresPermission: 'access.employees' },
      },
      {
        path: 'salaries',
        name: 'salaries',
        component: () => import('src/pages/SalariesPage.vue'),
        meta: { title: 'Зарплаты', icon: 'payments', requiresPermission: 'access.salaries' },
      },
      {
        path: 'reports',
        name: 'reports',
        component: () => import('src/pages/ReportsPage.vue'),
        meta: { title: 'Отчёты и Статистика', icon: 'bar_chart', requiresPermission: 'access.reports' },
      },
      {
        path: 'employee-reports',
        name: 'employee-reports',
        component: () => import('src/pages/EmployeeReportsPage.vue'),
        meta: { title: 'Отчёты по сотрудникам', icon: 'assessment', requiresPermission: 'access.employee_reports' },
      },
      {
        path: 'admin',
        name: 'admin',
        component: () => import('src/pages/AdminPage.vue'),
        meta: { title: 'Администрирование', icon: 'admin_panel_settings', requiresPermission: 'access.admin' },
      },
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('src/pages/NotificationsPage.vue'),
        meta: { title: 'Уведомления' },
      },
      {
        path: 'notification-settings',
        component: () => import('../pages/NotificationSettingsPage.vue'),
      },
      {
        path: 'files',
        name: 'files',
        component: () => import('src/pages/FilesPage.vue'),
        meta: { title: 'Файлы', icon: 'folder' },
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('src/pages/ProfilePage.vue'),
        meta: { title: 'Профиль', icon: 'person' },
      },
      // === Чаты сотрудников ===
      {
        path: 'employee-chats',
        name: 'employee-chats',
        component: () => import('src/pages/EmployeeChatsPage.vue'),
        meta: { title: 'Чат сотрудников', icon: 'chat', requiresPermission: 'chat.employee.view' },
      },
      {
        path: 'employee-chats/:chatId',
        name: 'employee-chat-room',
        component: () => import('src/pages/EmployeeChatRoomPage.vue'),
        meta: { title: 'Чат', requiresPermission: 'chat.employee.view' },
      },
      // === Чаты с клиентами ===
      {
        path: 'client-chats',
        name: 'client-chats',
        component: () => import('src/pages/ClientChatsPage.vue'),
        meta: { title: 'Чат с клиентами', icon: 'support_agent', requiresPermission: 'chat.client.view' },
      },
      {
        path: 'client-chats/:chatId',
        name: 'client-chat-room',
        component: () => import('src/pages/ClientChatRoomPage.vue'),
        meta: { title: 'Чат с клиентом', requiresPermission: 'chat.client.view' },
      },
    ],
  },

  // === Клиентский PWA (без авторизации) ===
  {
    path: '/c/:token',
    component: () => import('src/layouts/ClientLayout.vue'),
    children: [
      {
        path: '',
        name: 'client-chat',
        component: () => import('src/pages/ClientChatPage.vue'),
        meta: { requiresAuth: false },
      },
    ],
  },
  {
    path: '/c/:token/register',
    component: () => import('src/layouts/ClientLayout.vue'),
    children: [
      {
        path: '',
        name: 'client-register',
        component: () => import('src/pages/ClientRegisterPage.vue'),
        meta: { requiresAuth: false },
      },
    ],
  },

  // 404
  {
    path: '/:catchAll(.*)*',
    component: () => import('src/pages/ErrorNotFound.vue'),
    meta: { requiresAuth: false },
  },
]
