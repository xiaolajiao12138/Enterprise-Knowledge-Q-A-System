<template>
  <el-container class="app-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '230px'" class="app-aside">
      <div class="logo-box">
        <el-icon class="logo-icon" :size="24"><Compass /></el-icon>
        <span v-show="!isCollapse" class="logo-text">企业知识问答</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        class="aside-menu"
      >
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能问答</template>
        </el-menu-item>

        <el-menu-item v-if="userStore.isAdmin" index="/knowledge">
          <el-icon><FolderOpened /></el-icon>
          <template #title>知识库管理</template>
        </el-menu-item>

        <el-menu-item v-if="userStore.isAdmin" index="/users">
          <el-icon><UserFilled /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>

        <el-menu-item v-if="userStore.isAdmin" index="/settings">
          <el-icon><Setting /></el-icon>
          <template #title>系统配置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主体区域 -->
    <el-container>
      <!-- 顶部 Header -->
      <el-header class="app-header">
        <div class="header-left">
          <el-button
            link
            @click="isCollapse = !isCollapse"
            class="collapse-btn"
          >
            <el-icon :size="20">
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
          </el-button>
          <span class="page-title">{{ currentRouteTitle }}</span>
        </div>

        <div class="header-right">
          <el-tag
            :type="userStore.isAdmin ? 'danger' : 'info'"
            size="small"
            effect="light"
            class="role-tag"
          >
            {{ userStore.roleName }}
          </el-tag>

          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-profile">
              <el-avatar :size="32" class="user-avatar">
                {{ userStore.username.substring(0, 1).toUpperCase() }}
              </el-avatar>
              <span class="username">{{ userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>

            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 页面主要内容 -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  Compass, ChatDotRound, FolderOpened, UserFilled,
  Setting, Fold, Expand, ArrowDown, SwitchButton
} from '@element-plus/icons-vue'

const isCollapse = ref(false)
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const currentRouteTitle = computed(() => route.meta.title || '')

const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出当前登录账号吗？', '系统提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await userStore.logout()
      ElMessage.success('已安全退出')
      router.push('/login')
    } catch (e) {
      // 取消操作
    }
  }
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.app-aside {
  background-color: #0f172a;
  color: #fff;
  transition: width 0.25s ease-in-out;
  display: flex;
  flex-direction: column;
}

.logo-box {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  background-color: #0b1120;
  color: #38bdf8;
  font-weight: 700;
  font-size: 16px;
  gap: 12px;
  white-space: nowrap;
  overflow: hidden;
}

.aside-menu {
  border-right: none;
  background-color: transparent;
  flex: 1;
}

:deep(.el-menu-item) {
  color: #94a3b8;
}

:deep(.el-menu-item.is-active) {
  color: #ffffff;
  background-color: #1e293b;
  border-left: 3px solid #38bdf8;
}

:deep(.el-menu-item:hover) {
  background-color: #1e293b;
  color: #f1f5f9;
}

.app-header {
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.collapse-btn {
  color: #64748b;
  font-size: 18px;
}

.page-title {
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.role-tag {
  font-weight: 500;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}

.user-profile:hover {
  background-color: #f1f5f9;
}

.user-avatar {
  background-color: #3b82f6;
  color: #ffffff;
  font-weight: 600;
}

.username {
  font-size: 14px;
  color: #334155;
  font-weight: 500;
}

.app-main {
  background-color: #f8fafc;
  padding: 16px;
  overflow-y: auto;
  height: calc(100vh - 60px);
}
</style>
