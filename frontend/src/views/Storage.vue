<template>
  <div>
    <h2>儲存管理</h2>
    <el-tabs>
      <!-- Disks Tab -->
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

      <!-- SMART Tab -->
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

      <!-- Mounts Tab -->
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

      <!-- Partitions Tab -->
      <el-tab-pane label="分割區">
        <el-button type="primary" @click="partDialogVisible = true" style="margin-bottom:12px;">建立分割區</el-button>
        <el-table :data="partitions" stripe>
          <el-table-column prop="name" label="裝置" />
          <el-table-column prop="size" label="大小" />
          <el-table-column prop="fstype" label="檔案系統" />
          <el-table-column prop="mountpoint" label="掛載點" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" :disabled="row.name === 'sda1'" @click="deletePartition(row.name)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- RAID Tab -->
      <el-tab-pane label="RAID">
        <el-button type="primary" @click="raidStep = 0; raidWizardVisible = true" style="margin-bottom:12px;">建立 RAID</el-button>
        <pre style="background:#f5f5f5;padding:16px;border-radius:4px;white-space:pre-wrap;">{{ raid }}</pre>
      </el-tab-pane>

      <!-- fstab Tab -->
      <el-tab-pane label="fstab">
        <el-button type="primary" @click="fstabDialogVisible = true" style="margin-bottom:12px;">新增項目</el-button>
        <el-button @click="loadFstab" style="margin-bottom:12px;">重新整理</el-button>
        <el-table :data="fstabEntries" stripe v-loading="fstabLoading">
          <el-table-column prop="device" label="裝置" />
          <el-table-column prop="mount" label="掛載點" />
          <el-table-column prop="fs" label="檔案系統" width="100" />
          <el-table-column prop="options" label="選項" show-overflow-tooltip />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button type="danger" size="small" :disabled="row.mount === '/' || row.mount === '/boot'" @click="deleteFstabEntry(row.mount)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Usage History Section -->
    <div style="margin-top:24px;">
      <h3>磁碟使用歷史</h3>
      <el-button @click="loadUsageHistory" size="small" style="margin-bottom:12px;">重新整理</el-button>
      <el-table :data="usageHistory" stripe size="small" v-loading="usageLoading">
        <el-table-column prop="timestamp" label="時間" width="180" />
        <el-table-column prop="device" label="裝置" width="120" />
        <el-table-column prop="used_gb" label="已用 (GB)" width="100" />
        <el-table-column label="使用率">
          <template #default="{ row }">
            <el-progress :percentage="Math.round(row.percent || 0)" :stroke-width="14" :text-inside="true" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Format Dialog -->
    <el-dialog v-model="formatDialogVisible" title="格式化磁碟" width="450px">
      <el-alert type="error" :closable="false" style="margin-bottom:16px;">⚠️ 格式化將清除所有資料，不可復原！</el-alert>
      <el-form ref="formatFormRef" :model="formatForm" :rules="formatRules" label-width="100px">
        <el-form-item label="裝置" prop="device">
          <el-select v-model="formatForm.device" placeholder="選擇裝置">
            <el-option v-for="d in formatableDevices" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="檔案系統" prop="fs_type">
          <el-radio-group v-model="formatForm.fs_type">
            <el-radio value="ext4">ext4</el-radio>
            <el-radio value="xfs">XFS</el-radio>
            <el-radio value="btrfs">Btrfs</el-radio>
            <el-radio value="exfat">exFAT</el-radio>
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

    <!-- Partition Dialog -->
    <el-dialog v-model="partDialogVisible" title="建立分割區" width="450px">
      <el-form :model="partForm" label-width="100px">
        <el-form-item label="磁碟"><el-select v-model="partForm.device" placeholder="選擇磁碟">
          <el-option v-for="d in wholeDiskDevices" :key="d" :label="d" :value="d" />
        </el-select></el-form-item>
        <el-form-item label="大小"><el-input v-model="partForm.size" placeholder="100G 或 100%" /></el-form-item>
        <el-form-item label="類型"><el-select v-model="partForm.part_type">
          <el-option value="primary" label="Primary" /><el-option value="logical" label="Logical" />
        </el-select></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="partDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="partLoading" @click="createPartition">建立</el-button>
      </template>
    </el-dialog>

    <!-- RAID Wizard Dialog -->
    <el-dialog v-model="raidWizardVisible" title="建立 RAID 陣列" width="550px">
      <el-steps :active="raidStep" finish-status="success" style="margin-bottom:20px;">
        <el-step title="等級" /><el-step title="選碟" /><el-step title="備用碟" /><el-step title="確認" />
      </el-steps>
      <!-- Step 0: Level -->
      <div v-if="raidStep === 0">
        <el-form-item label="RAID 等級">
          <el-radio-group v-model="raidForm.level">
            <el-radio :value="0">RAID 0 (最少 2 碟)</el-radio>
            <el-radio :value="1">RAID 1 (最少 2 碟)</el-radio>
            <el-radio :value="5">RAID 5 (最少 3 碟)</el-radio>
            <el-radio :value="6">RAID 6 (最少 4 碟)</el-radio>
            <el-radio :value="10">RAID 10 (最少 4 碟)</el-radio>
          </el-radio-group>
        </el-form-item>
      </div>
      <!-- Step 1: Devices -->
      <div v-if="raidStep === 1">
        <p>選擇成員磁碟：</p>
        <el-checkbox-group v-model="raidForm.devices">
          <el-checkbox v-for="d in formatableDevices" :key="d" :value="d" :label="d" style="display:block;margin-bottom:4px;" />
        </el-checkbox-group>
      </div>
      <!-- Step 2: Spare -->
      <div v-if="raidStep === 2">
        <p>選擇備用碟（可選）：</p>
        <el-checkbox-group v-model="raidForm.spare">
          <el-checkbox v-for="d in availableSpares" :key="d" :value="d" :label="d" style="display:block;margin-bottom:4px;" />
        </el-checkbox-group>
      </div>
      <!-- Step 3: Confirm -->
      <div v-if="raidStep === 3">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="等級">RAID {{ raidForm.level }}</el-descriptions-item>
          <el-descriptions-item label="名稱">md0</el-descriptions-item>
          <el-descriptions-item label="成員碟">{{ raidForm.devices.join(', ') }}</el-descriptions-item>
          <el-descriptions-item label="備用碟">{{ raidForm.spare.join(', ') || '無' }}</el-descriptions-item>
        </el-descriptions>
        <el-alert type="warning" style="margin-top:12px;" :closable="false">⚠️ 成員磁碟上的資料將被清除！</el-alert>
      </div>
      <template #footer>
        <el-button v-if="raidStep > 0" @click="raidStep--">上一步</el-button>
        <el-button v-if="raidStep < 3" type="primary" @click="raidStep++">下一步</el-button>
        <el-button v-if="raidStep === 3" type="danger" :loading="raidCreating" @click="createRaid">建立 RAID</el-button>
      </template>
    </el-dialog>

    <!-- fstab Dialog -->
    <el-dialog v-model="fstabDialogVisible" title="新增 fstab 項目" width="480px">
      <el-form :model="fstabForm" label-width="100px">
        <el-form-item label="裝置"><el-input v-model="fstabForm.device" placeholder="/dev/sdb1" /></el-form-item>
        <el-form-item label="掛載點"><el-input v-model="fstabForm.mount" placeholder="/mnt/data" /></el-form-item>
        <el-form-item label="檔案系統"><el-select v-model="fstabForm.fs">
          <el-option value="ext4" /><el-option value="xfs" /><el-option value="btrfs" /><el-option value="exfat" /><el-option value="ntfs" />
        </el-select></el-form-item>
        <el-form-item label="選項"><el-input v-model="fstabForm.options" placeholder="defaults,noatime" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fstabDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="fstabAdding" @click="addFstabEntry">新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const disks = ref([])
const mounts = ref([])
const raid = ref('')
const loading = ref(false)

// Format
const formatDialogVisible = ref(false)
const formatFormRef = ref(null)
const formatForm = reactive({ device: '', fs_type: 'ext4' })
const formatConfirm = ref('')
const formatLoading = ref(false)
const formatRules = {
  device: [{ required: true, message: '請選擇裝置', trigger: 'change' }],
  fs_type: [{ required: true, message: '請選擇檔案系統', trigger: 'change' }],
}

// SMART
const smartDevice = ref('')
const smartData = ref(null)

// Partition
const partDialogVisible = ref(false)
const partLoading = ref(false)
const partForm = reactive({ device: '', size: '', part_type: 'primary' })

// RAID Wizard
const raidWizardVisible = ref(false)
const raidStep = ref(0)
const raidCreating = ref(false)
const raidForm = reactive({ level: 1, devices: [], spare: [] })

// fstab
const fstabDialogVisible = ref(false)
const fstabEntries = ref([])
const fstabLoading = ref(false)
const fstabAdding = ref(false)
const fstabForm = reactive({ device: '', mount: '', fs: 'ext4', options: 'defaults' })

// Usage History
const usageHistory = ref([])
const usageLoading = ref(false)

// Computed
const diskDevices = computed(() =>
  disks.value.filter(d => d.type === 'disk').map(d => `/dev/${d.name}`)
)

const formatableDevices = computed(() =>
  disks.value
    .filter(d => (d.type === 'part' || d.type === 'disk') && !d.mountpoint && d.name !== 'sda')
    .map(d => `/dev/${d.name}`)
)

const wholeDiskDevices = computed(() =>
  disks.value.filter(d => d.type === 'disk' && d.name !== 'sda').map(d => `/dev/${d.name}`)
)

const partitions = computed(() =>
  disks.value.filter(d => d.type === 'part')
)

const availableSpares = computed(() =>
  formatableDevices.value.filter(d => !raidForm.devices.includes(d))
)

// --- Load Data ---
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
    raid.value = r.data.mdstat || ''
  } catch { /* handled */ }
  finally { loading.value = false }
}

// --- SMART ---
async function loadSmart() {
  if (!smartDevice.value) return
  try {
    const res = await api.get(`/api/storage/smart${smartDevice.value}`)
    smartData.value = res.data
  } catch { smartData.value = null }
}

async function runSmartTest() {
  try {
    const res = await api.post(`/api/storage/smart${smartDevice.value}/test`, { test_type: 'short' })
    ElMessage.success(res.data.message || '自檢已啟動')
  } catch { /* handled */ }
}

// --- Format ---
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

// --- Partition ---
async function createPartition() {
  if (!partForm.device || !partForm.size) { ElMessage.warning('請填寫必要欄位'); return }
  partLoading.value = true
  try {
    await api.post('/api/storage/partition', partForm)
    ElMessage.success('分割區已建立')
    partDialogVisible.value = false
    partForm.device = ''; partForm.size = ''
    loadData()
  } catch { /* handled */ }
  finally { partLoading.value = false }
}

async function deletePartition(name) {
  await ElMessageBox.confirm(`確定刪除分割區 /dev/${name}？資料將無法恢復！`, '警告', { type: 'error' })
  await api.delete(`/api/storage/partition/${name}`)
  ElMessage.success('分割區已刪除')
  loadData()
}

// --- RAID ---
async function createRaid() {
  raidCreating.value = true
  try {
    await api.post('/api/storage/raid/create', {
      name: 'md0',
      level: raidForm.level,
      devices: raidForm.devices,
      spare: raidForm.spare,
    })
    ElMessage.success('RAID 陣列已建立')
    raidWizardVisible.value = false
    raidForm.devices = []; raidForm.spare = []
    loadData()
  } catch { /* handled */ }
  finally { raidCreating.value = false }
}

// --- fstab ---
async function loadFstab() {
  fstabLoading.value = true
  try {
    const res = await api.get('/api/storage/fstab')
    fstabEntries.value = res.data.entries || []
  } catch { /* handled */ }
  finally { fstabLoading.value = false }
}

async function addFstabEntry() {
  if (!fstabForm.device || !fstabForm.mount) { ElMessage.warning('請填寫裝置和掛載點'); return }
  fstabAdding.value = true
  try {
    await api.post('/api/storage/fstab', fstabForm)
    ElMessage.success('fstab 項目已新增')
    fstabDialogVisible.value = false
    fstabForm.device = ''; fstabForm.mount = ''
    loadFstab()
  } catch { /* handled */ }
  finally { fstabAdding.value = false }
}

async function deleteFstabEntry(mount) {
  await ElMessageBox.confirm(`確定移除掛載點「${mount}」的 fstab 項目？`, '確認', { type: 'warning' })
  await api.delete('/api/storage/fstab', { params: { mount } })
  ElMessage.success('已移除')
  loadFstab()
}

// --- Usage History ---
async function loadUsageHistory() {
  usageLoading.value = true
  try {
    const res = await api.get('/api/storage/usage/history', { params: { days: 30 } })
    usageHistory.value = res.data.history || []
  } catch { /* handled */ }
  finally { usageLoading.value = false }
}

onMounted(() => { loadData(); loadFstab(); loadUsageHistory() })
</script>
