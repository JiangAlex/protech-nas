<template>
  <div>
    <h2>使用者管理</h2>
    <el-tabs v-model="activeTab">
      <!-- Users Tab -->
      <el-tab-pane label="使用者" name="users">
        <el-button type="primary" @click="addDialogVisible = true" style="margin-bottom:12px;">新增使用者</el-button>
        <el-table :data="users" stripe v-loading="loading">
          <el-table-column prop="username" label="帳號" />
          <el-table-column prop="uid" label="UID" width="80" />
          <el-table-column prop="home" label="家目錄" />
          <el-table-column prop="shell" label="Shell" />
          <el-table-column label="狀態" width="80">
            <template #default="{ row }">
              <el-switch
                :model-value="row.enabled !== false"
                @change="(val) => toggleUserStatus(row.username, val)"
                :disabled="row.username === 'root'"
                size="small"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="340">
            <template #default="{ row }">
              <el-button size="small" @click="openEdit(row)">編輯</el-button>
              <el-button size="small" @click="openPassword(row)">密碼</el-button>
              <el-button size="small" @click="openQuota(row.username)">配額</el-button>
              <el-button size="small" type="warning" @click="open2FA(row.username)">2FA</el-button>
              <el-button type="danger" size="small" @click="deleteUser(row.username)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Groups Tab -->
      <el-tab-pane label="群組" name="groups">
        <el-button type="primary" @click="groupDialogVisible = true" style="margin-bottom:12px;">新增群組</el-button>
        <el-table :data="groups" stripe v-loading="groupLoading">
          <el-table-column prop="name" label="群組名稱" />
          <el-table-column prop="gid" label="GID" width="80" />
          <el-table-column prop="members" label="成員">
            <template #default="{ row }">{{ (row.members || []).join(', ') || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button size="small" @click="openMembers(row)">成員</el-button>
              <el-button type="danger" size="small" @click="deleteGroup(row.name)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Sessions Tab -->
      <el-tab-pane label="Sessions" name="sessions">
        <el-button @click="loadSessions" style="margin-bottom:12px;"><el-icon><Refresh /></el-icon>重新整理</el-button>
        <el-table :data="sessions" stripe v-loading="sessionsLoading">
          <el-table-column prop="id" label="Session ID" width="220" />
          <el-table-column prop="username" label="使用者" width="120" />
          <el-table-column prop="ip" label="IP" width="150" />
          <el-table-column prop="created_at" label="建立時間" width="180">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="last_active" label="最後活動" width="180">
            <template #default="{ row }">{{ formatDate(row.last_active) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="revokeSession(row.id)">撤銷</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Audit Log Tab -->
      <el-tab-pane label="稽核日誌" name="audit">
        <div style="display:flex; gap:8px; margin-bottom:12px; flex-wrap:wrap; align-items:center;">
          <el-input v-model="auditFilters.username" placeholder="使用者" style="width:140px;" clearable />
          <el-input v-model="auditFilters.action" placeholder="動作" style="width:140px;" clearable />
          <el-date-picker v-model="auditFilters.since" type="datetime" placeholder="起始時間" style="width:200px;" />
          <el-button type="primary" @click="loadAuditLog(true)"><el-icon><Search /></el-icon>查詢</el-button>
          <el-button @click="resetAuditFilters">重置</el-button>
        </div>
        <el-table :data="auditLogs" stripe v-loading="auditLoading">
          <el-table-column prop="timestamp" label="時間" width="180">
            <template #default="{ row }">{{ formatDate(row.timestamp) }}</template>
          </el-table-column>
          <el-table-column prop="username" label="使用者" width="120" />
          <el-table-column prop="action" label="動作" width="150" />
          <el-table-column prop="detail" label="詳情" min-width="200" show-overflow-tooltip />
          <el-table-column prop="ip" label="IP" width="140" />
        </el-table>
        <div style="margin-top:12px; display:flex; justify-content:center;">
          <el-pagination
            layout="prev, pager, next"
            :total="auditTotal"
            :page-size="auditPageSize"
            :current-page="auditPage"
            @current-change="onAuditPageChange"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Add User Dialog -->
    <el-dialog v-model="addDialogVisible" title="新增使用者">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="100px">
        <el-form-item label="帳號" prop="username"><el-input v-model="addForm.username" /></el-form-item>
        <el-form-item label="密碼" prop="password"><el-input v-model="addForm.password" type="password" show-password /></el-form-item>
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
        <el-form-item label="帳號"><el-input :model-value="editForm.username" disabled /></el-form-item>
        <el-form-item label="Shell">
          <el-select v-model="editForm.shell">
            <el-option value="/bin/bash" label="/bin/bash" />
            <el-option value="/bin/sh" label="/bin/sh" />
            <el-option value="/usr/sbin/nologin" label="/usr/sbin/nologin" />
          </el-select>
        </el-form-item>
        <el-form-item label="群組"><el-input v-model="editForm.groups" placeholder="docker,data (逗號分隔)" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">儲存</el-button>
      </template>
    </el-dialog>

    <!-- Change Password Dialog -->
    <el-dialog v-model="pwDialogVisible" title="修改密碼">
      <el-form ref="pwFormRef" :model="pwForm" :rules="pwRules" label-width="100px">
        <el-form-item label="帳號"><el-input :model-value="pwForm.username" disabled /></el-form-item>
        <el-form-item label="新密碼" prop="password"><el-input v-model="pwForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="確認密碼" prop="confirm"><el-input v-model="pwForm.confirm" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!pwForm.password || pwForm.password !== pwForm.confirm" @click="savePassword">儲存</el-button>
      </template>
    </el-dialog>

    <!-- Quota Dialog -->
    <el-dialog v-model="quotaDialogVisible" :title="'磁碟配額 — ' + quotaUser">
      <div v-if="quotaData" style="margin-bottom:16px;">
        <p>目前使用：{{ quotaData.used_mb }} MB</p>
        <el-progress :percentage="quotaData.hard_limit_mb ? Math.round(quotaData.used_mb / quotaData.hard_limit_mb * 100) : 0" :status="quotaData.used_mb > quotaData.soft_limit_mb ? 'warning' : ''" />
      </div>
      <el-form :model="quotaForm" label-width="120px">
        <el-form-item label="軟限制 (MB)">
          <el-input-number v-model="quotaForm.soft_mb" :min="0" :max="1000000" />
        </el-form-item>
        <el-form-item label="硬限制 (MB)">
          <el-input-number v-model="quotaForm.hard_mb" :min="0" :max="1000000" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quotaDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveQuota">儲存</el-button>
      </template>
    </el-dialog>

    <!-- 2FA Dialog -->
    <el-dialog v-model="tfaDialogVisible" :title="'雙重驗證 (2FA) — ' + tfaUsername" width="500px">
      <div v-if="!tfaSetupData">
        <p style="margin-bottom:16px;">此使用者尚未設定 2FA。點擊下方按鈕產生金鑰。</p>
        <el-button type="primary" :loading="tfaLoading" @click="setup2FA">啟用 2FA</el-button>
      </div>
      <div v-else>
        <el-alert type="info" :closable="false" style="margin-bottom:16px;">
          <p>請使用 Authenticator App（如 Google Authenticator）掃描以下金鑰，或手動輸入。</p>
        </el-alert>
        <el-descriptions :column="1" border style="margin-bottom:16px;">
          <el-descriptions-item label="Secret">
            <code style="font-size:14px; letter-spacing:1px;">{{ tfaSetupData.secret }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="OTPAuth URI">
            <el-input :model-value="tfaSetupData.qr_uri || tfaSetupData.otpauth_uri || ''" readonly size="small">
              <template #append>
                <el-button @click="copyTfaUri">複製</el-button>
              </template>
            </el-input>
          </el-descriptions-item>
        </el-descriptions>
        <div v-if="tfaSetupData.qr_uri || tfaSetupData.otpauth_uri" style="text-align:center; margin-bottom:16px;">
          <img :src="'https://chart.googleapis.com/chart?chs=200x200&cht=qr&chl=' + encodeURIComponent(tfaSetupData.qr_uri || tfaSetupData.otpauth_uri)" alt="QR Code" style="border:1px solid #eee; border-radius:4px;" />
        </div>
        <el-divider />
        <p style="margin-bottom:8px;">輸入 App 產生的 6 位數驗證碼以完成設定：</p>
        <div style="display:flex; gap:8px;">
          <el-input v-model="tfaVerifyCode" placeholder="000000" maxlength="6" style="width:160px;" @keyup.enter="verify2FA" />
          <el-button type="success" :loading="tfaVerifyLoading" @click="verify2FA">驗證</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- Group Create Dialog -->
    <el-dialog v-model="groupDialogVisible" title="新增群組">
      <el-form :model="groupForm" label-width="80px">
        <el-form-item label="名稱"><el-input v-model="groupForm.name" placeholder="群組名稱" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createGroup">建立</el-button>
      </template>
    </el-dialog>

    <!-- Group Members Dialog -->
    <el-dialog v-model="membersDialogVisible" :title="'群組成員 — ' + membersGroup">
      <p style="margin-bottom:8px;">目前成員：<strong>{{ membersList.join(', ') || '無' }}</strong></p>
      <el-form label-width="100px" style="margin-top:12px;">
        <el-form-item label="加入使用者">
          <div style="display:flex; gap:8px;">
            <el-input v-model="memberAdd" placeholder="帳號" style="width:200px;" />
            <el-button type="primary" @click="addMember">加入</el-button>
          </div>
        </el-form-item>
        <el-form-item label="移除使用者">
          <div style="display:flex; gap:8px;">
            <el-select v-model="memberRemove" placeholder="選擇" style="width:200px;">
              <el-option v-for="m in membersList" :key="m" :label="m" :value="m" />
            </el-select>
            <el-button type="danger" @click="removeMember">移除</el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const activeTab = ref('users')

const users = ref([])
const loading = ref(false)
const groups = ref([])
const groupLoading = ref(false)

// Add User
const addDialogVisible = ref(false)
const addFormRef = ref(null)
const addForm = reactive({ username: '', password: '', groups: '', smb_enabled: true })
const addRules = {
  username: [
    { required: true, message: '請輸入帳號', trigger: 'blur' },
    { min: 2, max: 32, message: '帳號長度 2-32 字元', trigger: 'blur' },
    { pattern: /^[a-z_][a-z0-9_-]*$/, message: '僅限小寫英文、數字、底線、連字號', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '請輸入密碼', trigger: 'blur' },
    { min: 8, message: '密碼至少 8 個字元', trigger: 'blur' },
  ],
}

// Edit User
const editDialogVisible = ref(false)
const editForm = reactive({ username: '', shell: '/bin/bash', groups: '' })

// Password
const pwDialogVisible = ref(false)
const pwFormRef = ref(null)
const pwForm = reactive({ username: '', password: '', confirm: '' })
const pwRules = {
  password: [
    { required: true, message: '請輸入新密碼', trigger: 'blur' },
    { min: 8, message: '密碼至少 8 個字元', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '請再次輸入密碼', trigger: 'blur' },
    { validator: (_r, v, cb) => { v !== pwForm.password ? cb(new Error('兩次密碼不一致')) : cb() }, trigger: 'blur' },
  ],
}

// Quota
const quotaDialogVisible = ref(false)
const quotaUser = ref('')
const quotaData = ref(null)
const quotaForm = reactive({ soft_mb: 0, hard_mb: 0 })

// 2FA
const tfaDialogVisible = ref(false)
const tfaUsername = ref('')
const tfaLoading = ref(false)
const tfaSetupData = ref(null)
const tfaVerifyCode = ref('')
const tfaVerifyLoading = ref(false)

// Sessions
const sessions = ref([])
const sessionsLoading = ref(false)

// Audit Log
const auditLogs = ref([])
const auditLoading = ref(false)
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = 50
const auditFilters = reactive({ username: '', action: '', since: null })

// Groups
const groupDialogVisible = ref(false)
const groupForm = reactive({ name: '' })
const membersDialogVisible = ref(false)
const membersGroup = ref('')
const membersList = ref([])
const memberAdd = ref('')
const memberRemove = ref('')

// --- Utility ---
function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-TW')
}

// --- Load ---
async function loadData() {
  loading.value = true
  try {
    const res = await api.get('/api/users')
    users.value = res.data.users || []
  } catch { /* handled */ }
  finally { loading.value = false }
  loadGroups()
}

async function loadGroups() {
  groupLoading.value = true
  try {
    const res = await api.get('/api/users/groups')
    groups.value = res.data.groups || []
  } catch { /* handled */ }
  finally { groupLoading.value = false }
}

// --- User CRUD ---
async function addUser() {
  const valid = await addFormRef.value.validate().catch(() => false)
  if (!valid) return
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
  pwForm.username = row.username; pwForm.password = ''; pwForm.confirm = ''
  pwDialogVisible.value = true
}

async function savePassword() {
  const valid = await pwFormRef.value.validate().catch(() => false)
  if (!valid) return
  await api.put(`/api/users/${pwForm.username}/password`, { password: pwForm.password })
  ElMessage.success('密碼已更新')
  pwDialogVisible.value = false
}

// --- Enable/Disable ---
async function toggleUserStatus(username, enabled) {
  await api.put(`/api/users/${username}/status`, { enabled })
  ElMessage.success(enabled ? '已啟用' : '已停用')
  loadData()
}

// --- Quota ---
async function openQuota(username) {
  quotaUser.value = username
  try {
    const res = await api.get(`/api/users/${username}/quota`)
    quotaData.value = res.data
    quotaForm.soft_mb = res.data.soft_limit_mb || 0
    quotaForm.hard_mb = res.data.hard_limit_mb || 0
  } catch {
    quotaData.value = { used_mb: 0, soft_limit_mb: 0, hard_limit_mb: 0 }
    quotaForm.soft_mb = 0; quotaForm.hard_mb = 0
  }
  quotaDialogVisible.value = true
}

async function saveQuota() {
  if (quotaForm.soft_mb > quotaForm.hard_mb && quotaForm.hard_mb > 0) {
    ElMessage.warning('軟限制不可大於硬限制')
    return
  }
  await api.put(`/api/users/${quotaUser.value}/quota`, quotaForm)
  ElMessage.success('配額已設定')
  quotaDialogVisible.value = false
}

// --- 2FA ---
function open2FA(username) {
  tfaUsername.value = username
  tfaSetupData.value = null
  tfaVerifyCode.value = ''
  tfaDialogVisible.value = true
}

async function setup2FA() {
  tfaLoading.value = true
  try {
    const res = await api.post(`/api/users/${tfaUsername.value}/2fa/setup`)
    tfaSetupData.value = res.data
    ElMessage.success('2FA 金鑰已產生，請掃描或手動輸入')
  } catch { /* handled */ }
  finally { tfaLoading.value = false }
}

async function verify2FA() {
  if (!tfaVerifyCode.value || tfaVerifyCode.value.length !== 6) {
    ElMessage.warning('請輸入 6 位數驗證碼')
    return
  }
  tfaVerifyLoading.value = true
  try {
    await api.post(`/api/users/${tfaUsername.value}/2fa/verify`, { code: tfaVerifyCode.value })
    ElMessage.success('2FA 驗證成功，已啟用')
    tfaDialogVisible.value = false
  } catch { /* handled */ }
  finally { tfaVerifyLoading.value = false }
}

function copyTfaUri() {
  const uri = tfaSetupData.value?.qr_uri || tfaSetupData.value?.otpauth_uri || ''
  navigator.clipboard.writeText(uri)
  ElMessage.success('已複製到剪貼簿')
}

// --- Sessions ---
async function loadSessions() {
  sessionsLoading.value = true
  try {
    const res = await api.get('/api/auth/sessions')
    sessions.value = res.data.sessions || []
  } catch { /* handled */ }
  finally { sessionsLoading.value = false }
}

async function revokeSession(id) {
  try {
    await ElMessageBox.confirm('確定要撤銷此 Session？', '確認', { type: 'warning' })
    await api.delete(`/api/auth/sessions/${id}`)
    ElMessage.success('Session 已撤銷')
    loadSessions()
  } catch { /* cancelled */ }
}

// --- Audit Log ---
async function loadAuditLog(reset = false) {
  if (reset) {
    auditPage.value = 1
  }
  auditLoading.value = true
  try {
    const params = {
      limit: auditPageSize,
      offset: (auditPage.value - 1) * auditPageSize,
    }
    if (auditFilters.username) params.username = auditFilters.username
    if (auditFilters.action) params.action = auditFilters.action
    if (auditFilters.since) {
      params.since = new Date(auditFilters.since).toISOString()
    }
    const res = await api.get('/api/users/audit', { params })
    auditLogs.value = res.data.logs || res.data.items || []
    auditTotal.value = res.data.total || auditLogs.value.length
  } catch { /* handled */ }
  finally { auditLoading.value = false }
}

function onAuditPageChange(page) {
  auditPage.value = page
  loadAuditLog()
}

function resetAuditFilters() {
  auditFilters.username = ''
  auditFilters.action = ''
  auditFilters.since = null
  loadAuditLog(true)
}

// --- Groups ---
async function createGroup() {
  if (!groupForm.name) { ElMessage.warning('請輸入群組名稱'); return }
  await api.post('/api/users/groups', groupForm)
  ElMessage.success('群組已建立')
  groupDialogVisible.value = false
  groupForm.name = ''
  loadGroups()
}

async function deleteGroup(name) {
  await ElMessageBox.confirm(`確定要刪除群組「${name}」？`, '確認', { type: 'warning' })
  await api.delete(`/api/users/groups/${name}`)
  ElMessage.success('已刪除')
  loadGroups()
}

function openMembers(row) {
  membersGroup.value = row.name
  membersList.value = [...(row.members || [])]
  memberAdd.value = ''
  memberRemove.value = ''
  membersDialogVisible.value = true
}

async function addMember() {
  if (!memberAdd.value) return
  await api.put(`/api/users/groups/${membersGroup.value}/members`, { add: [memberAdd.value], remove: [] })
  ElMessage.success(`已加入 ${memberAdd.value}`)
  membersList.value.push(memberAdd.value)
  memberAdd.value = ''
  loadGroups()
}

async function removeMember() {
  if (!memberRemove.value) return
  await api.put(`/api/users/groups/${membersGroup.value}/members`, { add: [], remove: [memberRemove.value] })
  ElMessage.success(`已移除 ${memberRemove.value}`)
  membersList.value = membersList.value.filter(m => m !== memberRemove.value)
  memberRemove.value = ''
  loadGroups()
}

// --- Tab change handler ---
watch(activeTab, (tab) => {
  if (tab === 'sessions') loadSessions()
  if (tab === 'audit') loadAuditLog(true)
})

onMounted(loadData)
</script>
