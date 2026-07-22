<template>
  <div>
    <h2>使用者管理</h2>
    <el-button type="primary" @click="addDialogVisible = true" style="margin-bottom:12px;">新增使用者</el-button>
    <el-table :data="users" stripe v-loading="loading">
      <el-table-column prop="username" label="帳號" />
      <el-table-column prop="uid" label="UID" width="80" />
      <el-table-column prop="home" label="家目錄" />
      <el-table-column prop="shell" label="Shell" />
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">編輯</el-button>
          <el-button size="small" @click="openPassword(row)">密碼</el-button>
          <el-button type="danger" size="small" @click="deleteUser(row.username)">刪除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add User Dialog -->
    <el-dialog v-model="addDialogVisible" title="新增使用者">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="帳號"><el-input v-model="addForm.username" /></el-form-item>
        <el-form-item label="密碼"><el-input v-model="addForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="群組"><el-input v-model="addForm.groups" placeholder="用逗號分隔" /></el-form-item>
        <el-form-item label="啟用 SMB"><el-switch v-model="addForm.smb_enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addUser">確認</el-button>
      </template>
    </el-dialog>

    <!-- Edit User Dialog -->
    <el-dialog v-model="editDialogVisible" title="編輯使用者">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="帳號">
          <el-input :model-value="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="Shell">
          <el-select v-model="editForm.shell">
            <el-option value="/bin/bash" label="/bin/bash" />
            <el-option value="/bin/sh" label="/bin/sh" />
            <el-option value="/usr/sbin/nologin" label="/usr/sbin/nologin" />
          </el-select>
        </el-form-item>
        <el-form-item label="群組">
          <el-input v-model="editForm.groups" placeholder="docker,data (逗號分隔)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">儲存</el-button>
      </template>
    </el-dialog>

    <!-- Change Password Dialog -->
    <el-dialog v-model="pwDialogVisible" title="修改密碼">
      <el-form :model="pwForm" label-width="100px">
        <el-form-item label="帳號">
          <el-input :model-value="pwForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密碼">
          <el-input v-model="pwForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="確認密碼">
          <el-input v-model="pwForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!pwForm.password || pwForm.password !== pwForm.confirm" @click="savePassword">儲存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const users = ref([])
const loading = ref(false)

// Add
const addDialogVisible = ref(false)
const addForm = reactive({ username: '', password: '', groups: '', smb_enabled: true })

// Edit
const editDialogVisible = ref(false)
const editForm = reactive({ username: '', shell: '/bin/bash', groups: '' })

// Password
const pwDialogVisible = ref(false)
const pwForm = reactive({ username: '', password: '', confirm: '' })

async function loadData() {
  loading.value = true
  try {
    const res = await api.get('/api/users')
    users.value = res.data.users || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function addUser() {
  await api.post('/api/users', addForm)
  ElMessage.success('使用者已建立')
  addDialogVisible.value = false
  addForm.username = ''; addForm.password = ''; addForm.groups = ''
  loadData()
}

async function deleteUser(username) {
  await ElMessageBox.confirm(`確定要刪除使用者「${username}」？`, '確認刪除', { type: 'warning' })
  await api.delete(`/api/users/${username}`)
  ElMessage.success('已刪除')
  loadData()
}

function openEdit(row) {
  editForm.username = row.username
  editForm.shell = row.shell || '/bin/bash'
  editForm.groups = ''
  editDialogVisible.value = true
}

async function saveEdit() {
  const data = {}
  if (editForm.shell) data.shell = editForm.shell
  if (editForm.groups) data.groups = editForm.groups
  await api.put(`/api/users/${editForm.username}`, data)
  ElMessage.success('已更新')
  editDialogVisible.value = false
  loadData()
}

function openPassword(row) {
  pwForm.username = row.username
  pwForm.password = ''
  pwForm.confirm = ''
  pwDialogVisible.value = true
}

async function savePassword() {
  if (pwForm.password.length < 8) {
    ElMessage.warning('密碼至少 8 個字元')
    return
  }
  await api.put(`/api/users/${pwForm.username}/password`, { password: pwForm.password })
  ElMessage.success('密碼已更新')
  pwDialogVisible.value = false
}

onMounted(loadData)
</script>
