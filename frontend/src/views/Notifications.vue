<template>
  <div>
    <h2>通知管理</h2>
    <el-tabs>
      <!-- Settings Tab -->
      <el-tab-pane label="通知設定">
        <el-card v-loading="settingsLoading" style="max-width:600px;">
          <!-- Email -->
          <h4>Email 通知</h4>
          <el-form :model="settings.email" label-width="120px" style="margin-bottom:24px;">
            <el-form-item label="啟用"><el-switch v-model="settings.email.enabled" /></el-form-item>
            <template v-if="settings.email.enabled">
              <el-form-item label="SMTP 主機"><el-input v-model="settings.email.smtp_host" placeholder="smtp.gmail.com" /></el-form-item>
              <el-form-item label="SMTP 埠"><el-input-number v-model="settings.email.smtp_port" :min="1" :max="65535" /></el-form-item>
              <el-form-item label="使用者名稱"><el-input v-model="settings.email.username" /></el-form-item>
              <el-form-item label="密碼"><el-input v-model="settings.email.password" type="password" show-password placeholder="••••••" /></el-form-item>
              <el-form-item label="寄件人"><el-input v-model="settings.email.from" placeholder="nas@example.com" /></el-form-item>
            </template>
          </el-form>

          <!-- Telegram -->
          <h4>Telegram 通知</h4>
          <el-form :model="settings.telegram" label-width="120px" style="margin-bottom:24px;">
            <el-form-item label="啟用"><el-switch v-model="settings.telegram.enabled" /></el-form-item>
            <template v-if="settings.telegram.enabled">
              <el-form-item label="Bot Token"><el-input v-model="settings.telegram.bot_token" placeholder="123456:ABC-DEF..." /></el-form-item>
              <el-form-item label="Chat ID"><el-input v-model="settings.telegram.chat_id" placeholder="-1001234567890" /></el-form-item>
            </template>
          </el-form>

          <!-- Webhook -->
          <h4>Webhook 通知</h4>
          <el-form :model="settings.webhook" label-width="120px" style="margin-bottom:24px;">
            <el-form-item label="啟用"><el-switch v-model="settings.webhook.enabled" /></el-form-item>
            <template v-if="settings.webhook.enabled">
              <el-form-item label="URL"><el-input v-model="settings.webhook.url" placeholder="https://hooks.example.com/..." /></el-form-item>
            </template>
          </el-form>

          <div style="display:flex; gap:12px;">
            <el-button type="primary" :loading="saving" @click="saveSettings">儲存設定</el-button>
            <el-button @click="testEmail" :loading="testing === 'email'">測試 Email</el-button>
            <el-button @click="testTelegram" :loading="testing === 'telegram'">測試 Telegram</el-button>
            <el-button @click="testWebhook" :loading="testing === 'webhook'">測試 Webhook</el-button>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- History Tab -->
      <el-tab-pane label="通知歷史">
        <el-button @click="loadNotifications" style="margin-bottom:12px;">重新整理</el-button>
        <el-button @click="markAllRead" style="margin-bottom:12px;">全部標記已讀</el-button>
        <el-table :data="notifications" stripe v-loading="notifLoading">
          <el-table-column prop="title" label="標題">
            <template #default="{ row }">
              <strong v-if="!row.read">{{ row.title }}</strong>
              <span v-else>{{ row.title }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="body" label="內容" show-overflow-tooltip />
          <el-table-column prop="level" label="等級" width="80">
            <template #default="{ row }">
              <el-tag :type="levelType(row.level)" size="small">{{ row.level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="時間" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="" width="80">
            <template #default="{ row }">
              <el-button v-if="!row.read" size="small" text @click="markRead(row.id)">已讀</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

// Settings
const settingsLoading = ref(false)
const saving = ref(false)
const testing = ref('')
const settings = reactive({
  email: { enabled: false, smtp_host: '', smtp_port: 587, username: '', password: '', from: '' },
  telegram: { enabled: false, bot_token: '', chat_id: '' },
  webhook: { enabled: false, url: '' },
})

// Notifications history
const notifications = ref([])
const notifLoading = ref(false)

async function loadSettings() {
  settingsLoading.value = true
  try {
    const res = await api.get('/api/notifications/settings')
    if (res.data.email) Object.assign(settings.email, res.data.email)
    if (res.data.telegram) Object.assign(settings.telegram, res.data.telegram)
    if (res.data.webhook) Object.assign(settings.webhook, res.data.webhook)
  } catch { /* handled */ }
  finally { settingsLoading.value = false }
}

async function saveSettings() {
  saving.value = true
  try {
    await api.put('/api/notifications/settings', settings)
    ElMessage.success('通知設定已儲存')
  } catch { /* handled */ }
  finally { saving.value = false }
}

async function testChannel(channel) {
  testing.value = channel
  try {
    await api.post('/api/notifications/test', { channel })
    ElMessage.success(`${channel} 測試通知已發送`)
  } catch { /* handled */ }
  finally { testing.value = '' }
}

function testEmail() { testChannel('email') }
function testTelegram() { testChannel('telegram') }
function testWebhook() { testChannel('webhook') }

// Notifications history
async function loadNotifications() {
  notifLoading.value = true
  try {
    const res = await api.get('/api/notifications')
    notifications.value = res.data.notifications || []
  } catch { /* handled */ }
  finally { notifLoading.value = false }
}

async function markRead(id) {
  await api.put(`/api/notifications/${id}/read`)
  notifications.value = notifications.value.map(n => n.id === id ? { ...n, read: true } : n)
}

async function markAllRead() {
  const unread = notifications.value.filter(n => !n.read)
  for (const n of unread) {
    await api.put(`/api/notifications/${n.id}/read`)
  }
  notifications.value = notifications.value.map(n => ({ ...n, read: true }))
  ElMessage.success('全部標記已讀')
}

function levelType(level) {
  if (level === 'error' || level === 'critical') return 'danger'
  if (level === 'warning') return 'warning'
  if (level === 'info') return ''
  return 'info'
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-TW')
}

onMounted(() => { loadSettings(); loadNotifications() })
</script>
