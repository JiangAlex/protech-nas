<template>
  <div>
    <h2>儲存管理</h2>
    <el-tabs>
      <el-tab-pane label="磁碟">
        <el-button type="warning" @click="formatDialogVisible = true" style="margin-bottom:12px;">格式化磁碟</el-button>
        <el-table :data="disks" stripe v-loading="loading">
          <el-table-column prop="name" label="裝置" />
          <el-table-column prop="size" label="大小" />
          <el-table-column prop="type" label="類型" />
          <el-table-column prop="fstype" label="檔案系統" />
          <el-table-column prop="mountpoint" label="掛載點" />
          <el-table-column prop="model" label="型號" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="S.M.A.R.T.">
        <el-select v-model="smartDevice" placeholder="選擇磁碟" style="width:200px; margin-bottom:12px;" @change="loadSmart">
          <el-option v-for="d in diskDevices" :key="d" :label="d" :value="d" />
        </el-select>
        <el-button :disabled="!smartDevice" @click="runSmartTest" style="margin-left:8px;">執行短測試</el-button>

        <div v-if="smartData" style="margin-top:16px;">
          <el-descriptions :column="3" border>
            <el-descriptions-item label="狀態">
              <el-tag :type="smartData.smart_status === 'PASSED' ? 'success' : 'danger'">{{ smartData.smart_status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="溫度">{{ smartData.temperature ?? 'N/A' }} °C</el-descriptions-item>
            <el-descriptions-item label="通電時數">{{ smartData.power_on_hours ?? 'N/A' }} h</el-descriptions-item>
          </el-descriptions>

          <el-table :data="smartData.attributes" stripe style="margin-top:12px;" size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="name" label="屬性" />
            <el-table-column prop="value" label="值" width="80" />
            <el-table-column prop="worst" label="最差" width="80" />
            <el-table-column prop="thresh" label="閾值" width="80" />
            <el-table-column prop="raw_value" label="原始值" width="120" />
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="掛載">
        <el-table :data="mounts" stripe>
          <el-table-column prop="device" label="裝置" />
          <el-table-column prop="mount_point" label="掛載點" />
          <el-table-column prop="fstype" label="檔案系統" />
          <el-table-column prop="size" label="大小" />
          <el-table-column prop="used" label="已用" />
          <el-table-column prop="use_percent" label="使用率" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="RAID">
        <pre style="background:#f5f5f5;padding:16px;border-radius:4px;">{{ raid }}</pre>
      </el-tab-pane>
    </el-tabs>

    <!-- Format Dialog -->
    <el-dialog v-model="formatDialogVisible" title="格式化磁碟" width="450px">
      <el-alert type="error" :closable="false" style="margin-bottom:16px;">
        ⚠️ 格式化將清除磁碟上所有資料，此操作不可復原！
      </el-alert>
      <el-form :model="formatForm" label-width="100px">
        <el-form-item label="裝置">
          <el-select v-model="formatForm.device" placeholder="選擇裝置">
            <el-option v-for="d in formatableDevices" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="檔案系統">
          <el-radio-group v-model="formatForm.fs_type">
            <el-radio value="ext4">ext4</el-radio>
            <el-radio value="xfs">XFS</el-radio>
            <el-radio value="btrfs">Btrfs</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="確認裝置">
          <el-input v-model="formatConfirm" placeholder="請輸入裝置名稱以確認" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formatDialogVisible = false">取消</el-button>
        <el-button type="danger" :disabled="formatConfirm !== formatForm.device" :loading="formatLoading" @click="doFormat">確認格式化</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const disks = ref([])
const mounts = ref([])
const raid = ref('')
const loading = ref(false)

// Format
const formatDialogVisible = ref(false)
const formatForm = reactive({ device: '', fs_type: 'ext4' })
const formatConfirm = ref('')
const formatLoading = ref(false)

// SMART
const smartDevice = ref('')
const smartData = ref(null)

const diskDevices = computed(() =>
  disks.value.filter(d => d.type === 'disk').map(d => `/dev/${d.name}`)
)

const formatableDevices = computed(() =>
  disks.value
    .filter(d => (d.type === 'part' || d.type === 'disk') && !d.mountpoint && d.name !== 'sda')
    .map(d => `/dev/${d.name}`)
)

async function loadData() {
  loading.value = true
  try {
    const [d, m, r] = await Promise.all([
      api.get('/api/storage/disks'),
      api.get('/api/storage/mounts'),
      api.get('/api/storage/raid'),
    ])
    disks.value = d.data.devices || []
    mounts.value = m.data.mounts || []
    raid.value = r.data.mdstat || 'N/A'
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function doFormat() {
  formatLoading.value = true
  try {
    await api.post('/api/storage/format', formatForm)
    ElMessage.success('格式化完成')
    formatDialogVisible.value = false
    formatConfirm.value = ''
    loadData()
  } catch { /* handled */ }
  finally { formatLoading.value = false }
}

async function loadSmart() {
  if (!smartDevice.value) return
  try {
    const res = await api.get(`/api/storage/smart${smartDevice.value}`)
    smartData.value = res.data
  } catch { smartData.value = null }
}

async function runSmartTest() {
  if (!smartDevice.value) return
  try {
    const res = await api.post(`/api/storage/smart${smartDevice.value}/test`, { test_type: 'short' })
    ElMessage.success(`測試已開始，預計 ${res.data.estimated_minutes} 分鐘`)
  } catch { /* handled */ }
}

onMounted(loadData)
</script>
