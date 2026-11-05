import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { requiresAuth: false, title: '用户登录' }
  },
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/chat',
    children: [
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/chat/index.vue'),
        meta: { requiresAuth: true, title: '智能问答' }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/knowledge/index.vue'),
        meta: { requiresAuth: true, requiresAdmin: true, title: '知识库管理' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { requiresAuth: true, requiresAdmin: true, title: '用户管理' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/index.vue'),
        meta: { requiresAuth: true, requiresAdmin: true, title: '系统配置' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/chat'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  document.title = `${to.meta.title ? to.meta.title + ' - ' : ''}企业内部知识问答平台`

  // 1. 登录白名单校验
  if (to.meta.requiresAuth === false) {
    if (userStore.isLoggedIn && to.path === '/login') {
      next('/chat')
      return
    }
    next()
    return
  }

  // 2. 未登录拦截
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录系统')
    next('/login')
    return
  }

  // 3. 管理员权限校验
  if (to.meta.requiresAdmin && !userStore.isAdmin) {
    ElMessage.error('权限不足：该页面仅限管理员访问')
    next('/chat')
    return
  }

  next()
})

export default router
