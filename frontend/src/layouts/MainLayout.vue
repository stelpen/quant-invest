<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Odometer,
  Document,
  TrendCharts,
  DataAnalysis,
  Histogram,
  Bell,
  Setting,
  Fold,
  Expand,
  SwitchButton,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const collapsed = ref(false)

interface MenuItem {
  index: string
  title: string
  icon: string
}

const menuItems = ref<MenuItem[]>([
  { index: '/', title: '仪表盘', icon: 'Odometer' },
  { index: '/stocks', title: '股票列表', icon: 'Document' },
  { index: '/kline', title: 'K线图', icon: 'TrendCharts' },
  { index: '/screener', title: '选股器', icon: 'DataAnalysis' },
  { index: '/backtest', title: '回测', icon: 'Histogram' },
  { index: '/signals', title: '信号', icon: 'Bell' },
  { index: '/settings', title: '设置', icon: 'Setting' },
])

const iconMap: Record<string, unknown> = {
  Odometer,
  Document,
  TrendCharts,
  DataAnalysis,
  Histogram,
  Bell,
  Setting,
}

const activeMenu = computed(() => {
  // 让 /kline/600000 高亮在 /kline 上
  if (route.path.startsWith('/kline')) return '/kline'
  return route.path
})

const username = computed(() => auth.user?.username || '用户')

function handleSelect(index: string) {
  if (route.path !== index) router.push(index)
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
    })
      .then(() => {
        auth.logout()
        router.replace('/login')
      })
      .catch(() => {})
  }
}
</script>

<template>
  <el-container class="main-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <span v-if="!collapsed">量化投资</span>
        <span v-else>Q</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        background-color="#001529"
        text-color="#ffffffcc"
        active-text-color="#ffffff"
        @select="handleSelect"
      >
        <el-menu-item v-for="m in menuItems" :key="m.index" :index="m.index">
          <el-icon>
            <component :is="iconMap[m.icon]" />
          </el-icon>
          <template #title>{{ m.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button text :icon="collapsed ? Expand : Fold" @click="collapsed = !collapsed" />
          <span class="page-title">{{ (route.meta?.title as string) || '' }}</span>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="28" style="margin-right: 8px">{{ username.slice(0, 1).toUpperCase() }}</el-avatar>
              {{ username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.main-layout {
  height: 100vh;
  width: 100%;
}
.sidebar {
  background: #001529;
  transition: width 0.2s;
  overflow: hidden;
}
.sidebar :deep(.el-menu) {
  border-right: none;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #1f2d3d;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0 16px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 16px;
  font-weight: 500;
  margin-left: 8px;
}
.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #303133;
}
.main-content {
  background: #f5f7fa;
  padding: 16px;
  overflow: auto;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
