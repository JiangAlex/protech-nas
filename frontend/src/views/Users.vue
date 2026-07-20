<template>
  <div>
    <h2>使用者管理</h2>
    <el-button type="primary" @click="dialogVisible = true" style="margin-bottom:12px;">新增使用者</el-button>
    <el-table :data="users" stripe>
      <el-table-column prop="username" label="帳號" />
      <el-table-column prop="uid" label="UID" width="80" />
      <el-table-column prop="home" label="家目錄" />
      <el-table-column prop="shell" label="Shell" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="danger" size="small" @click="deleteUser(row.username)">刪除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新增使用者">
      <el-form :model="form" label-width="100px">
        <el-form-item label="帳號"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密碼"><el-input v-model="form.password" type="password" show-password /></el-form-item>
        <el-form-item label="群組"><el-input v-model="form.groups" placeholder="用逗號分隔" /></el-form-item>
        <el-form-item label="啟用 SMB"><el-switch v-model="form.smb_enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser">確認</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const users = ref([])
const dialogVisible = ref(false)
const form = reactive({ username: '', password: '', groups: '', smb_enabled: true })

async function loadData() {
  const res = await api.get('/api/users')
  users.value = res.data.users || []
}

async function addUser() {
  await api.post('/api/users', form)
  ElMessage.success('使用者已建立')
  dialogVisible.value = false
  loadData()
}

async function deleteUser(username) {
  await api.delete(`/api/users/${username}`)
  ElMessage.success('已刪除')
  loadData()
}

onMounted(loadData)
</script>
