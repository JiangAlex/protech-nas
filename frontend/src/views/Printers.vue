<template>
  <div>
    <h2>印表機分享</h2>
    <p style="color:var(--el-text-color-secondary); margin-top:-8px;">
      將接在 NAS 上的 USB 印表機透過 CUPS/IPP 分享到區域網路（支援 AirPrint / IPP Everywhere）。
    </p>

    <div style="margin-bottom:12px;">
      <el-button type="primary" @click="openAdd">新增並分享印表機</el-button>
      <el-button @click="loadPrinters">重新整理</el-button>
    </div>

    <el-table :data="printers" stripe v-loading="loading">
      <el-table-column prop="name" label="名稱" />
      <el-table-column label="狀態" width="120">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'">{{ row.state || '未知' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="網路分享" width="120">
        <template #default="{ row }">
          <el-switch :model-value="row.shared === true"
                     @change="(val) => toggleShare(row.name, val)" />
        </template>
      </el-table-column>
      <el-table-column prop="device_uri" label="裝置" show-overflow-tooltip />
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button size="small" @click="openJobs(row.name)">佇列</el-button>
          <el-button size="small" @click="testPage(row.name)">測試頁</el-button>
          <el-button type="danger" size="small" @click="removePrinter(row.name)">刪除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && printers.length === 0" description="尚未設定任何印表機" />

    <!-- Add / Share Dialog -->
    <el-dialog v-model="addVisible" title="新增並分享印表機" width="620px">
      <div style="margin-bottom:12px;">
        <el-button size="small" :loading="discovering" @click="discover">偵測已連接的印表機</el-button>
        <span style="color:var(--el-text-color-secondary); margin-left:8px; font-size:12px;">
          （USB 印表機需已插上 NAS）
        </span>
      </div>

      <el-form :model="form" label-width="90px">
        <el-form-item label="裝置">
          <el-select v-model="form.device_uri" placeholder="選擇偵測到的裝置，或手動輸入 URI"
                     filterable allow-create style="width:100%;">
            <el-option v-for="d in devices" :key="d.uri" :label="`${d.uri}  (${d.class})`" :value="d.uri" />
          </el-select>
        </el-form-item>
        <el-form-item label="名稱">
          <el-input v-model="form.name" placeholder="例如 EPSON_L3150（僅英數、_ . -）" />
        </el-form-item>
        <el-form-item label="驅動">
          <el-select v-model="form.driver" style="width:100%;">
            <el-option label="IPP Everywhere / 無驅動（推薦）" value="everywhere" />
          </el-select>
        </el-form-item>
        <el-form-item label="網路分享">
          <el-switch v-model="form.shared" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAdd">新增</el-button>
      </template>
    </el-dialog>

    <!-- Jobs Dialog -->
    <el-dialog v-model="jobsVisible" :title="`列印佇列 — ${jobsPrinter}`" width="560px">
      <el-table :data="jobs" stripe>
        <el-table-column prop="job" label="工作" />
        <el-table-column prop="raw" label="詳細" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="cancelJob(row.job)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="jobs.length === 0" description="佇列是空的" />
      <template #footer>
        <el-button @click="jobsVisible = false">關閉</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const printers = ref([])
const loading = ref(false)

// Add dialog state
const addVisible = ref(false)
const saving = ref(false)
const discovering = ref(false)
const devices = ref([])
const form = reactive({ name: '', device_uri: '', driver: 'everywhere', shared: true })

// Jobs dialog state
const jobsVisible = ref(false)
const jobsPrinter = ref('')
const jobs = ref([])

async function loadPrinters() {
  loading.value = true
  try {
    const res = await api.get('/api/printers')
    printers.value = res.data.printers || []
  } catch { /* handled by interceptor */ }
  finally { loading.value = false }
}

function openAdd() {
  form.name = ''
  form.device_uri = ''
  form.driver = 'everywhere'
  form.shared = true
  devices.value = []
  addVisible.value = true
}

async function discover() {
  discovering.value = true
  try {
    const res = await api.get('/api/printers/discover')
    devices.value = res.data.devices || []
    if (devices.value.length === 0) {
      ElMessage.info('未偵測到印表機裝置')
    }
  } catch { /* handled */ }
  finally { discovering.value = false }
}

async function submitAdd() {
  if (!form.name || !form.device_uri) {
    ElMessage.warning('請輸入名稱並選擇裝置')
    return
  }
  saving.value = true
  try {
    await api.post('/api/printers', {
      name: form.name,
      device_uri: form.device_uri,
      driver: form.driver,
      shared: form.shared,
    })
    ElMessage.success('印表機已新增')
    addVisible.value = false
    loadPrinters()
  } catch { /* handled */ }
  finally { saving.value = false }
}

async function toggleShare(name, shared) {
  try {
    await api.put(`/api/printers/${encodeURIComponent(name)}/share`, { shared })
    ElMessage.success(shared ? '已啟用網路分享' : '已停用網路分享')
    loadPrinters()
  } catch {
    loadPrinters() // revert switch to server truth
  }
}

async function removePrinter(name) {
  try {
    await ElMessageBox.confirm(`確定要刪除印表機「${name}」？`, '確認刪除', {
      type: 'warning', confirmButtonText: '刪除', cancelButtonText: '取消',
    })
  } catch { return }
  try {
    await api.delete(`/api/printers/${encodeURIComponent(name)}`)
    ElMessage.success('印表機已刪除')
    loadPrinters()
  } catch { /* handled */ }
}

async function testPage(name) {
  try {
    await api.post(`/api/printers/${encodeURIComponent(name)}/test`)
    ElMessage.success('已送出測試頁')
  } catch { /* handled */ }
}

async function openJobs(name) {
  jobsPrinter.value = name
  jobs.value = []
  jobsVisible.value = true
  try {
    const res = await api.get(`/api/printers/${encodeURIComponent(name)}/jobs`)
    jobs.value = res.data.jobs || []
  } catch { /* handled */ }
}

async function cancelJob(jobId) {
  try {
    await api.post(`/api/printers/jobs/${encodeURIComponent(jobId)}/cancel`)
    ElMessage.success('已取消工作')
    openJobs(jobsPrinter.value)
  } catch { /* handled */ }
}

onMounted(loadPrinters)
</script>
