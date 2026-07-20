<template>
  <el-container style="height: 100vh;">
    <el-aside width="200px" style="background: #304156;">
      <div style="padding: 20px; text-align: center; color: #fff; font-size: 18px; font-weight: bold;">
        ProTech NAS
      </div>
      <el-menu :default-active="route.path" router background-color="#304156" text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item index="/dashboard"><el-icon><Monitor /></el-icon><span>儀表板</span></el-menu-item>
        <el-menu-item index="/storage"><el-icon><Coin /></el-icon><span>儲存管理</span></el-menu-item>
        <el-menu-item index="/shares"><el-icon><FolderOpened /></el-icon><span>檔案共享</span></el-menu-item>
        <el-menu-item index="/docker"><el-icon><Box /></el-icon><span>Docker</span></el-menu-item>
        <el-menu-item index="/users"><el-icon><User /></el-icon><span>使用者</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display:flex; justify-content:flex-end; align-items:center; border-bottom:1px solid #e6e6e6;">
        <el-dropdown>
          <span style="cursor:pointer;">admin <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="handleLogout">登出</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="background:#f0f2f5; padding:20px;">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>
