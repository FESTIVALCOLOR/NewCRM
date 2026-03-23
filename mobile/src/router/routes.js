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
        meta: { requiresAuth: false }
      }
    ]
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
        meta: { title: 'Главная', icon: 'dashboard' }
      },
      {
        path: 'crm',
        name: 'crm',
        component: () => import('src/pages/CrmBoardPage.vue'),
        meta: { title: 'CRM', icon: 'view_kanban' }
      },
      {
        path: 'crm/:id',
        name: 'crm-card',
        component: () => import('src/pages/CrmCardPage.vue'),
        meta: { title: 'Карточка проекта' }
      },
      {
        path: 'clients',
        name: 'clients',
        component: () => import('src/pages/ClientsPage.vue'),
        meta: { title: 'Клиенты', icon: 'people' }
      },
      {
        path: 'clients/:id',
        name: 'client-detail',
        component: () => import('src/pages/ClientDetailPage.vue'),
        meta: { title: 'Клиент' }
      },
      {
        path: 'contracts',
        name: 'contracts',
        component: () => import('src/pages/ContractsPage.vue'),
        meta: { title: 'Договоры', icon: 'description' }
      },
      {
        path: 'contracts/:id',
        name: 'contract-detail',
        component: () => import('src/pages/ContractDetailPage.vue'),
        meta: { title: 'Договор' }
      },
      {
        path: 'supervision',
        name: 'supervision',
        component: () => import('src/pages/SupervisionPage.vue'),
        meta: { title: 'Надзор', icon: 'engineering' }
      },
      {
        path: 'supervision/:id',
        name: 'supervision-detail',
        component: () => import('src/pages/SupervisionDetailPage.vue'),
        meta: { title: 'Карточка надзора' }
      },
      {
        path: 'employees',
        name: 'employees',
        component: () => import('src/pages/EmployeesPage.vue'),
        meta: { title: 'Сотрудники', icon: 'badge' }
      },
      {
        path: 'salaries',
        name: 'salaries',
        component: () => import('src/pages/SalariesPage.vue'),
        meta: { title: 'Зарплаты', icon: 'payments' }
      },
      {
        path: 'reports',
        name: 'reports',
        component: () => import('src/pages/ReportsPage.vue'),
        meta: { title: 'Отчёты и Статистика', icon: 'bar_chart' }
      },
      {
        path: 'employee-reports',
        name: 'employee-reports',
        component: () => import('src/pages/EmployeeReportsPage.vue'),
        meta: { title: 'Отчёты по сотрудникам', icon: 'assessment' }
      },
      {
        path: 'admin',
        name: 'admin',
        component: () => import('src/pages/AdminPage.vue'),
        meta: { title: 'Администрирование', icon: 'admin_panel_settings' }
      },
      {
        path: 'notifications',
        name: 'notifications',
        component: () => import('src/pages/NotificationsPage.vue'),
        meta: { title: 'Уведомления' }
      },
      {
        path: 'files',
        name: 'files',
        component: () => import('src/pages/FilesPage.vue'),
        meta: { title: 'Файлы', icon: 'folder' }
      },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('src/pages/ProfilePage.vue'),
        meta: { title: 'Профиль', icon: 'person' }
      }
    ]
  },

  // 404
  {
    path: '/:catchAll(.*)*',
    component: () => import('src/pages/ErrorNotFound.vue'),
    meta: { requiresAuth: false }
  }
]
