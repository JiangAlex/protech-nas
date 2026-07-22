<template>
  <div>
    <h2>系統管理</h2>
    <el-tabs>
      <!-- Logs -->
      <el-tab-pane label="系統日誌">
        <div style="display:flex; gap:8px; margin-bottom:12px;">
          <el-input v-model="logUnit" placeholder="過濾 unit (如 smbd)" style="width:160px;" clearable />
          <el-input-number v-model="logLines" :min="10" :max="1000" :step="50" />
          <el-button type="primary" @click="loadLogs">載入日誌</el-button>
        </div>
        <pre style="max-height:500px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:4px;font-size:12px;" v-loading="logsLoading">{{ logContent }}</pre>
      </el-tab-pane>

      <!-- Temperature -->
      <el-tab-pane label="溫度">
        <el-button @click="loadTemp" style="margin-bottom:12px;">重新整理</el-button>
        <el-descriptions :column="2" border v-if="temp">
          <el-descriptions-item label="CPU 溫度">
            <span :style="{color: tempColor(temp.cpu_temp_c)}">{{ temp.cpu_temp_c ?? 'N/A' }} °C</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-table :data="temp?.disks || []" stripe style="margin-top:12px;">
          <el-table-column prop="device" label="裝置" />
          <el-table-column label="溫度">
            <template #default="{ row }">
              <span :style="{color: tempColor(row.temp_c)}">{{ row.temp_c }} °C</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Services -->
      <el-tab-pane label="服務">
        <el-button @click="loadServices" style="margin-bottom:12px;">重新整理</el-button>

        <el-table :data="services" stripe v-loading="servicesLoading">
          <el-table-column prop="name" label="服務名稱" />
          <el-table-column prop="status" label="狀態" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'running' ? 'success' : row.status === 'stopped' ? 'danger' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="enabled" label="開機啟動" width="120">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已啟用' : '未啟用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" show-overflow-tooltip />
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button type="success" size="small" @click="serviceAction(row.name, 'start')">啟動</el-button>
              <el-button type="warning" size="small" @click="serviceAction(row.name, 'stop')">停止</el-button>
              <el-button type="primary" size="small" @click="serviceAction(row.name, 'restart')">重啟</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Power -->
      <el-tab-pane label="電源">
        <el-alert type="warning" :closable="false" style="margin-bottom:16px;">
          以下操作將立即執行，請確認所有工作已儲存。
        </el-alert>
        <el-space>
          <el-button type="warning" size="large" @click="confirmPower('reboot')">
            <el-icon><RefreshRight /></el-icon> 重新啟動
          </el-button>
          <el-button type="danger" size="large" @click="confirmPower('shutdown')">
            <el-icon><SwitchButton /></el-icon> 關機
          </el-button>
        </el-space>
      </el-tab-pane>

      <!-- Cron -->
      <el-tab-pane label="排程任務">
        <el-button type="primary" @click="cronDialogVisible = true" style="margin-bottom:12px;">新增排程</el-button>
        <el-button @click="loadCronJobs" style="margin-bottom:12px;">重新整理</el-button>

        <el-table :data="cronJobs" stripe v-loading="cronLoading">
          <el-table-column prop="schedule" label="排程" width="180" />
          <el-table-column prop="command" label="指令" show-overflow-tooltip />
          <el-table-column prop="user" label="使用者" width="100" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteCronJob(row.id)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="cronDialogVisible" title="新增排程任務" width="500px">
          <el-form :model="cronForm" label-width="80px">
            <el-form-item label="排程">
              <el-input v-model="cronForm.schedule" placeholder="*/5 * * * * (cron 格式)" />
            </el-form-item>
            <el-form-item label="指令">
              <el-input v-model="cronForm.command" placeholder="/usr/bin/backup.sh" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="cronDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="cronSaving" @click="addCronJob">新增</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- Settings -->
      <el-tab-pane label="系統設定">
        <el-form :model="settingsForm" label-width="120px" style="max-width:500px;">
          <el-form-item label="主機名稱">
            <el-input v-model="settingsForm.hostname" placeholder="protech-nas" />
          </el-form-item>
          <el-form-item label="時區">
            <el-input v-model="settingsForm.timezone" placeholder="Asia/Taipei" />
          </el-form-item>
          <el-form-item label="NTP 同步">
            <el-switch v-model="settingsForm.ntp_enabled" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="settingsSaving" @click="saveSettings">儲存設定</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- Hardware -->
      <el-tab-pane label="硬體資訊">
        <el-button @click="loadHardware" style="margin-bottom:12px;">重新整理</el-button>

        <div v-if="hardware" v-loading="hardwareLoading">
          <el-descriptions title="CPU" :column="3" border style="margin-bottom:20px;">
            <el-descriptions-item label="型號">{{ hardware.cpu?.model }}</el-descriptions-item>
            <el-descriptions-item label="核心數">{{ hardware.cpu?.cores }}</el-descriptions-item>
            <el-descriptions-item label="執行緒數">{{ hardware.cpu?.threads }}</el-descriptions-item>
          </el-descriptions>

          <el-descriptions title="記憶體" :column="2" border style="margin-bottom:20px;">
            <el-descriptions-item label="總容量">{{ hardware.memory?.total_gb }} GB</el-descriptions-item>
            <el-descriptions-item label="插槽數">{{ hardware.memory?.slots }}</el-descriptions-item>
          </el-descriptions>

          <h4>PCI 裝置</h4>
          <el-table :data="pciDevices" stripe>
            <el-table-column prop="device" label="裝置名稱" />
          </el-table>
        </div>
        <div v-else v-loading="hardwareLoading" style="min-height:100px;"></div>
      </el-tab-pane>

      <!-- Updates -->
      <el-tab-pane label="系統更新">
        <div style="display:flex; gap:8px; align-items:center; margin-bottom:12px;">
          <el-button type="primary" :loading="updatesLoading" @click="checkUpdates">檢查更新</el-button>
          <el-button
            v-if="updatesData && updatesData.upgradable_count > 0"
            type="success"
            @click="applyUpdates"
            :loading="updatesApplying"
          >套用所有更新</el-button>
          <span v-if="updatesData" style="margin-left:8px; color:#909399;">
            可升級套件：{{ updatesData.upgradable_count }} 個
          </span>
        </div>

        <el-table v-if="updatesData && updatesData.packages?.length" :data="updatesData.packages" stripe>
          <el-table-column prop="name" label="套件名稱" />
          <el-table-column prop="current" label="目前版本" />
          <el-table-column prop="available" label="可用版本" />
        </el-table>
        <el-empty v-else-if="updatesData && updatesData.upgradable_count === 0" description="系統已是最新版本" />
      </el-tab-pane>

      <!-- Metrics -->
      <el-tab-pane label="歷史監控">
        <div style="display:flex; gap:8px; margin-bottom:12px;">
          <el-select v-model="metricsHours" style="width:120px;">
            <el-option :value="1" label="1 小時" />
            <el-option :value="6" label="6 小時" />
            <el-option :value="24" label="24 小時" />
            <el-option :value="72" label="3 天" />
          </el-select>
          <el-button type="primary" @click="loadMetrics">載入數據</el-button>
        </div>
        <div v-loading="metricsLoading">
          <div v-if="metricsData.length">
            <el-table :data="metricsData" stripe max-height="500">
              <el-table-column prop="timestamp" label="時間" width="180">
                <template #default="{ row }">{{ formatMetricTime(row.timestamp) }}</template>
              </el-table-column>
              <el-table-column prop="cpu_percent" label="CPU %" width="100" />
              <el-table-column prop="memory_percent" label="記憶體 %" width="100" />
              <el-table-column prop="disk_percent" label="磁碟 %" width="100" />
            </el-table>
          </div>
          <el-empty v-else description="尚無數據，點擊「載入數據」獲取歷史監控資料" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

// === Logs ===
const logUnit = ref('')
const logLines = ref(100)
const logContent = ref('按「載入日誌」查看系統日誌')
const logsLoading = ref(false)

// === Temperature ===
const temp = ref(null)

// === Services ===
const services = ref([])
const servicesLoading = ref(false)

// === Cron ===
const cronJobs = ref([])
const cronLoading = ref(false)
const cronDialogVisible = ref(false)
const cronSaving = ref(false)
const cronForm = reactive({ schedule: '', command: '' })

// === Settings ===
const settingsForm = reactive({ hostname: '', timezone: '', ntp_enabled: true })
const settingsSaving = ref(false)

// === Hardware ===
const hardware = ref(null)
const hardwareLoading = ref(false)
const pciDevices = computed(() => {
  if (!hardware.value?.pci_devices) return []
  return hardware.value.pci_devices.map(d => ({ device: d }))
})

// === Updates ===
const updatesData = ref(null)
const updatesLoading = ref(false)
const updatesApplying = ref(false)

// === Metrics ===
const metricsHours = ref(24)
const metricsData = ref([])
const metricsLoading = ref(false)

// === Logs Functions ===
async function loadLogs() {
  logsLoading.value = true
  try {
    const params = { lines: logLines.value }
    if (logUnit.value) params.unit = logUnit.value
    const res = await api.get('/api/system/logs', { params })
    const logs = res.data.logs || []
    logContent.value = logs.map(l => `[${l.unit}] ${l.message}`).join('\n') || '無日誌'
  } catch { logContent.value = '載入失敗' }
  finally { logsLoading.value = false }
}

// === Temperature Functions ===
async function loadTemp() {
  try {
    const res = await api.get('/api/system/temperature')
    temp.value = res.data
  } catch { /* handled */ }
}

function tempColor(t) {
  if (t == null) return '#909399'
  if (t < 50) return '#67c23a'
  if (t < 70) return '#e6a23c'
  return '#f56c6c'
}

// === Services Functions ===
async function loadServices() {
  servicesLoading.value = true
  try {
    const res = await api.get('/api/system/services')
    services.value = res.data.services || []
  } catch { /* handled */ }
  finally { servicesLoading.value = false }
}

async function serviceAction(name, action) {
  try {
    const res = await api.post(`/api/system/services/${name}/${action}`)
    ElMessage.success(res.data.message || `${action} 成功`)
    loadServices()
  } catch { /* handled */ }
}

// === Power Functions ===
async function confirmPower(action) {
  const label = action === 'shutdown' ? '關機' : '重新啟動'
  try {
    await ElMessageBox.prompt(`請輸入「${label}」以確認操作`, `確認${label}`, {
      confirmButtonText: '確認',
      cancelButtonText: '取消',
      inputPattern: new RegExp(`^${label}$`),
      inputErrorMessage: `請正確輸入「${label}」`,
      type: 'warning',
    })
    await api.post(`/api/system/power/${action}`)
    ElMessage.success(`${label}指令已送出`)
  } catch { /* cancelled */ }
}

// === Cron Functions ===
async function loadCronJobs() {
  cronLoading.value = true
  try {
    const res = await api.get('/api/system/cron')
    cronJobs.value = res.data.jobs || []
  } catch { /* handled */ }
  finally { cronLoading.value = false }
}

async function addCronJob() {
  if (!cronForm.schedule || !cronForm.command) {
    ElMessage.warning('請填寫排程和指令')
    return
  }
  cronSaving.value = true
  try {
    await api.post('/api/system/cron', {
      schedule: cronForm.schedule,
      command: cronForm.command,
    })
    ElMessage.success('排程已新增')
    cronDialogVisible.value = false
    cronForm.schedule = ''
    cronForm.command = ''
    loadCronJobs()
  } catch { /* handled */ }
  finally { cronSaving.value = false }
}

async function deleteCronJob(id) {
  await ElMessageBox.confirm('確定要刪除此排程任務？', '確認', { type: 'warning' })
  try {
    await api.delete(`/api/system/cron/${id}`)
    ElMessage.success('排程已刪除')
    loadCronJobs()
  } catch { /* handled */ }
}

// === Settings Functions ===
async function saveSettings() {
  settingsSaving.value = true
  try {
    await api.put('/api/system/settings', {
      hostname: settingsForm.hostname,
      timezone: settingsForm.timezone,
      ntp_enabled: settingsForm.ntp_enabled,
    })
    ElMessage.success('設定已儲存')
  } catch { /* handled */ }
  finally { settingsSaving.value = false }
}

// === Hardware Functions ===
async function loadHardware() {
  hardwareLoading.value = true
  try {
    const res = await api.get('/api/system/hardware')
    hardware.value = res.data
  } catch { /* handled */ }
  finally { hardwareLoading.value = false }
}

// === Updates Functions ===
async function checkUpdates() {
  updatesLoading.value = true
  try {
    const res = await api.get('/api/system/updates')
    updatesData.value = res.data
  } catch { /* handled */ }
  finally { updatesLoading.value = false }
}

async function applyUpdates() {
  await ElMessageBox.confirm('確定要套用所有更新？這可能需要一段時間。', '確認更新', { type: 'warning' })
  updatesApplying.value = true
  try {
    const res = await api.post('/api/system/updates/apply', {})
    ElMessage.success(res.data.message || `已更新 ${res.data.updated_count} 個套件`)
    updatesData.value = null
  } catch { /* handled */ }
  finally { updatesApplying.value = false }
}

// === Metrics Functions ===
async function loadMetrics() {
  metricsLoading.value = true
  try {
    const res = await api.get('/api/dashboard/history', { params: { hours: metricsHours.value } })
    metricsData.value = res.data.history || res.data.metrics || []
  } catch { /* handled */ }
  finally { metricsLoading.value = false }
}

function formatMetricTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-TW')
}

// === Init ===
onMounted(() => {
  loadTemp()
  loadCronJobs()
  loadServices()
  loadHardware()
})
</script>
