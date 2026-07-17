import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
    {
      path: '/sites',
      name: 'sites',
      component: () => import('@/views/SitesView.vue'),
    },
    {
      path: '/sites/:id',
      name: 'site-detail',
      component: () => import('@/views/SiteDetailView.vue'),
    },
    {
      path: '/system-services',
      name: 'system-services',
      component: () => import('@/views/SystemServicesView.vue'),
    },
    {
      path: '/disks',
      name: 'disks',
      component: () => import('@/views/DisksView.vue'),
    },
    {
      path: '/apps',
      name: 'apps',
      component: () => import('@/views/AppsView.vue'),
    },
    {
      path: '/docker',
      name: 'docker',
      component: () => import('@/views/DockerView.vue'),
    },
    {
      path: '/logs',
      name: 'logs',
      component: () => import('@/views/LogsView.vue'),
    },
    {
      path: '/cron',
      name: 'cron',
      component: () => import('@/views/CronView.vue'),
    },
    {
      path: '/sessions',
      name: 'sessions',
      component: () => import('@/views/SessionsView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // The session lives in an httpOnly cookie the client can't read directly,
  // so the first navigation has to ask the backend whether it's still valid.
  if (!auth.authChecked) {
    await auth.loadUser()
  }
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }
})

export default router
