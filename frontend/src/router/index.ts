import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'stocks',
        name: 'StockList',
        component: () => import('@/views/StockList.vue'),
        meta: { title: '股票列表' },
      },
      {
        path: 'kline/:symbol?',
        name: 'KLine',
        component: () => import('@/views/KLine.vue'),
        meta: { title: 'K线图' },
      },
      {
        path: 'screener',
        name: 'Screener',
        component: () => import('@/views/Screener.vue'),
        meta: { title: '选股器' },
      },
      {
        path: 'backtest',
        name: 'Backtest',
        component: () => import('@/views/Backtest.vue'),
        meta: { title: '回测' },
      },
      {
        path: 'signals',
        name: 'Signals',
        component: () => import('@/views/Signals.vue'),
        meta: { title: '信号' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/Settings.vue'),
        meta: { title: '设置' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && auth.token) {
    return { path: '/' }
  }
  return true
})

export default router
