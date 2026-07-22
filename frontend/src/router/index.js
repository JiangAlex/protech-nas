import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'files', name: 'Files', component: () => import('../views/Files.vue') },
      { path: 'storage', name: 'Storage', component: () => import('../views/Storage.vue') },
      { path: 'shares', name: 'Shares', component: () => import('../views/Shares.vue') },
      { path: 'docker', name: 'Docker', component: () => import('../views/Docker.vue') },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue') },
      { path: 'system', name: 'System', component: () => import('../views/System.vue') },
      { path: 'network', name: 'Network', component: () => import('../views/Network.vue') },
      { path: 'backup', name: 'Backup', component: () => import('../views/Backup.vue') },
      { path: 'remote', name: 'Remote', component: () => import('../views/Remote.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Auth guard
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'Login' && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
