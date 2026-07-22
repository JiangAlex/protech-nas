<template>
  <el-container style="height: 100vh;">
    <el-aside :width="isCollapsed ? '64px' : '200px'" style="background: #304156; transition: width 0.3s;">
      <div style="padding: 16px; text-align: center; color: #fff; font-size: 18px; font-weight: bold; white-space: nowrap; overflow: hidden;">
        {{ isCollapsed ? 'P' : 'ProTech NAS' }}
      </div>
      <el-menu
        :default-active="route.path"
        router
        :collapse="isCollapsed"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        :collapse-transition="false"
      >
        <el-menu-item index="/dashboard"><el-icon><Monitor /></el-icon><span>儀表板</span></el-menu-item>
        <el-menu-item index="/files"><el-icon><Document /></el-icon><span>檔案管理</span></el-menu-item>
        <el-menu-item index="/storage"><el-icon><Coin /></el-icon><span>儲存管理</span></el-menu-item>
        <el-menu-item index="/shares"><el-icon><FolderOpened /></el-icon><span>檔案共享</span></el-menu-item>
        <el-menu-item index="/docker"><el-icon><Box /></el-icon><span>Docker</span></el-menu-item>
        <el-menu-item index="/network"><el-icon><Connection /></el-icon><span>網路</span></el-menu-item>
        <el-menu-item index="/backup"><el-icon><UploadFilled /></el-icon><span>備份</span></el-menu-item>
        <el-menu-item index="/remote"><el-icon><Link /></el-icon><span>遠端存取</span></el-menu-item>
        <el-menu-item index="/system"><el-icon><Setting /></el-icon><span>系統</span></el-menu-item>
        <el-menu-item index="/users"><el-icon><User /></el-icon><span>使用者</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display:flex; align-items:center; border-bottom:1px solid var(--el-border-color-light); padding: 0 16px;">
        <!-- Collapse Toggle -->
        <el-icon style="font-size:20px; cursor:pointer;" @click="toggleCollapse">
          <Fold v-if="!isCollapsed" /><Expand v-else />
        </el-icon>

        <div style="flex:1;" />

        <!-- Dark Mode Toggle -->
        <el-switch
          v-model="isDark"
          :active-icon="Moon"
          :inactive-icon="Sunny"
          @change="toggleDark"
          style="margin-right:12px;"
        />

        <!-- Language Switch -->
        <el-select v-model="locale" size="small" style="width:90px; margin-right:12px;" @change="changeLocale">
          <el-option value="zh-TW" label="中文" />
          <el-option value="en" label="EN" />
        </el-select>

        <!-- Notifications -->
        <el-popover placement="bottom" :width="320" trigger="click">
          <template #reference>
            <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" style="margin-right:16px;">
              <el-icon style="font-size:20px; cursor:pointer;"><Bell /></el-icon>
            </el-badge>
          </template>
          <div style="max-height:300px; overflow:auto;">
            <div v-if="notifications.length === 0" style="text-align:center; color:#999; padding:20px;">暫無通知</div>
            <div v-for="n in notifications" :key="n.id" style="padding:8px 0; border-bottom:1px solid var(--el-border-color-lighter);">
              <div style="font-weight:bold; font-size:13px;">{{ n.title }}</div>
              <div style="font-size:12px; color:var(--el-text-color-secondary);">{{ n.body }}</div>
              <div style="font-size:11px; color:var(--el-text-color-placeholder); margin-top:4px;">{{ formatTime(n.created_at) }}</div>
            </div>
          </div>
        </el-popover>

        <!-- User -->
        <el-dropdown>
          <span style="cursor:pointer;">admin <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="background: var(--el-bg-color-page); padding:20px; overflow:auto;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, markRaw } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { locale: i18nLocale } = useI18n()

// Sidebar collapse
const isCollapsed = ref(localStorage.getItem('sidebarCollapsed') === 'true')

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebarCollapsed', isCollapsed.value)
}

// Responsive: auto-collapse on small screens
function checkWidth() {
  if (window.innerWidth < 768) {
    isCollapsed.value = true
  }
}

// Dark mode
const isDark = ref(localStorage.getItem('darkMode') === 'true')

function toggleDark(val) {
  isDark.value = val
  localStorage.setItem('darkMode', val)
  if (val) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// Apply dark mode on load
if (isDark.value) {
  document.documentElement.classList.add('dark')
}

// Language
const locale = ref(localStorage.getItem('locale') || 'zh-TW')

function changeLocale(val) {
  i18nLocale.value = val
  localStorage.setItem('locale', val)
}

// Notifications
const notifications = ref([])
const unreadCount = ref(0)
let notifTimer = null

async function loadNotifications() {
  try {
    const res = await api.get('/api/notifications', { params: { unread_only: true } })
    notifications.value = (res.data.notifications || []).slice(0, 10)
    unreadCount.value = notifications.value.length
  } catch {}
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-TW')
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  checkWidth()
  window.addEventListener('resize', checkWidth)
  loadNotifications()
  notifTimer = setInterval(loadNotifications, 30000)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkWidth)
  if (notifTimer) clearInterval(notifTimer)
})
</script>
