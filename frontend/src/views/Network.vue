<template>
  <div>
    <h2>網路管理</h2>
    <el-tabs>
      <!-- Interfaces Tab -->
      <el-tab-pane label="網路介面">
        <el-button @click="loadData" style="margin-bottom:12px;">重新整理</el-button>
        <el-table :data="interfaces" stripe v-loading="loading">
          <el-table-column prop="name" label="介面" width="120" />
          <el-table-column prop="ipv4" label="IPv4">
            <template #default="{ row }">{{ row.ipv4 || '—' }}</template>
          </el-table-column>
          <el-table-column prop="mac" label="MAC" width="160" />
          <el-table-column prop="status" label="狀態" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'up' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="speed_mbps" label="速率" width="100">
            <template #default="{ row }">{{ row.speed_mbps ? row.speed_mbps + ' Mbps' : '—' }}</template>
          </el-table-column>
          <el-table-column prop="mtu" label="MTU" width="80" />
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button size="small" @click="openIfConfig(row)">設定</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Firewall Tab -->
      <el-tab-pane label="防火牆">
        <el-button type="primary" @click="fwDialogVisible = true" style="margin-bottom:12px;">新增規則</el-button>
        <el-button @click="loadFirewall" style="margin-bottom:12px;">重新整理</el-button>
        <el-table :data="fwRules_data" stripe v-loading="fwLoading">
          <el-table-column prop="id" label="#" width="50" />
          <el-table-column prop="chain" label="Chain" width="90" />
          <el-table-column prop="protocol" label="協定" width="80" />
          <el-table-column prop="port" label="埠" width="80" />
          <el-table-column prop="source" label="來源" />
          <el-table-column prop="target" label="動作" width="90">
            <template #default="{ row }">
              <el-tag :type="row.target === 'ACCEPT' ? 'success' : 'danger'" size="small">{{ row.target }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button type="danger" size="small" :disabled="row.port === '22' || row.port === 22" @click="deleteFwRule(row)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Realtime Stats Tab -->
      <el-tab-pane label="即時速率">
        <el-button @click="refreshStats" style="margin-bottom:12px;">更新</el-button>
        <el-switch v-model="statsAuto" active-text="自動刷新 (2s)" style="margin-left:12px;margin-bottom:12px;" />
        <el-table :data="netStats" stripe>
          <el-table-column prop="name" label="介面" width="120" />
          <el-table-column label="接收速率">
            <template #default="{ row }">{{ formatSpeed(row.rx_bytes_per_sec) }}</template>
          </el-table-column>
          <el-table-column label="發送速率">
            <template #default="{ row }">{{ formatSpeed(row.tx_bytes_per_sec) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Diagnostics Tab -->
      <el-tab-pane label="診斷工具">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-card header="Ping">
              <el-input v-model="diagPing.host" placeholder="主機或 IP" style="margin-bottom:8px;">
                <template #append><el-button :loading="diagPing.loading" @click="runPing">執行</el-button></template>
              </el-input>
              <pre class="diag-output">{{ diagPing.result || '結果將顯示在這裡' }}</pre>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card header="Traceroute">
              <el-input v-model="diagTrace.host" placeholder="主機或 IP" style="margin-bottom:8px;">
                <template #append><el-button :loading="diagTrace.loading" @click="runTraceroute">執行</el-button></template>
              </el-input>
              <pre class="diag-output">{{ diagTrace.result || '結果將顯示在這裡' }}</pre>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card header="DNS 查詢">
              <el-input v-model="diagDns.host" placeholder="網域名稱" style="margin-bottom:8px;">
                <template #append><el-button :loading="diagDns.loading" @click="runDns">執行</el-button></template>
              </el-input>
              <pre class="diag-output">{{ diagDns.result || '結果將顯示在這裡' }}</pre>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- WOL Tab -->
      <el-tab-pane label="WOL">
        <el-form style="max-width:400px;">
          <el-form-item label="MAC 位址">
            <el-input v-model="wolMac" placeholder="AA:BB:CC:DD:EE:FF" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="wolLoading" @click="sendWol">發送喚醒封包</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <!-- Interface Config Dialog -->
    <el-dialog v-model="ifDialogVisible" :title="'設定介面 — ' + ifForm.name" width="500px">
      <el-alert type="warning" :closable="false" style="margin-bottom:16px;">
        ⚠️ 錯誤的網路設定可能導致遠端連線中斷！
      </el-alert>
      <el-form ref="ifFormRef" :model="ifForm" :rules="ifRules" label-width="100px">
        <el-form-item label="模式">
          <el-radio-group v-model="ifForm.method">
            <el-radio value="dhcp">DHCP</el-radio>
            <el-radio value="static">Static</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="ifForm.method === 'static'">
          <el-form-item label="IP 位址" prop="ip">
            <el-input v-model="ifForm.ip" placeholder="192.168.1.100" />
          </el-form-item>
          <el-form-item label="子網掩碼" prop="netmask">
            <el-input v-model="ifForm.netmask" placeholder="255.255.255.0" />
          </el-form-item>
          <el-form-item label="閘道" prop="gateway">
            <el-input v-model="ifForm.gateway" placeholder="192.168.1.1" />
          </el-form-item>
          <el-form-item label="DNS">
            <el-input v-model="ifForm.dns" placeholder="8.8.8.8, 1.1.1.1 (逗號分隔)" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="ifDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="ifSaving" @click="saveIfConfig">套用</el-button>
      </template>
    </el-dialog>

    <!-- Firewall Add Rule Dialog -->
    <el-dialog v-model="fwDialogVisible" title="新增防火牆規則" width="450px">
      <el-form ref="fwFormRef" :model="fwForm" :rules="fwRules" label-width="80px">
        <el-form-item label="Chain" prop="chain">
          <el-select v-model="fwForm.chain">
            <el-option value="INPUT" /><el-option value="OUTPUT" /><el-option value="FORWARD" />
          </el-select>
        </el-form-item>
        <el-form-item label="協定" prop="protocol">
          <el-select v-model="fwForm.protocol">
            <el-option value="tcp" /><el-option value="udp" /><el-option value="icmp" />
          </el-select>
        </el-form-item>
        <el-form-item label="埠" prop="port">
          <el-input v-model="fwForm.port" placeholder="80 或 1-65535" />
        </el-form-item>
        <el-form-item label="來源">
          <el-input v-model="fwForm.source" placeholder="0.0.0.0/0 (全部)" />
        </el-form-item>
        <el-form-item label="動作" prop="target">
          <el-radio-group v-model="fwForm.target">
            <el-radio value="ACCEPT">ACCEPT</el-radio>
            <el-radio value="DROP">DROP</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fwDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addFwRule">新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const interfaces = ref([])
const loading = ref(false)

// Interface Config
const ifDialogVisible = ref(false)
const ifSaving = ref(false)
const ifFormRef = ref(null)
const ifForm = reactive({ name: '', method: 'dhcp', ip: '', netmask: '', gateway: '', dns: '' })
const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
const ifRules = {
  ip: [{ pattern: ipPattern, message: '無效 IP 格式', trigger: 'blur' }],
  netmask: [{ pattern: ipPattern, message: '無效子網掩碼', trigger: 'blur' }],
  gateway: [{ pattern: ipPattern, message: '無效閘道', trigger: 'blur' }],
}

// Firewall
const fwRules_data = ref([])
const fwLoading = ref(false)
const fwDialogVisible = ref(false)
const fwFormRef = ref(null)
const fwForm = reactive({ chain: 'INPUT', protocol: 'tcp', port: '', source: '0.0.0.0/0', target: 'ACCEPT' })
const fwRules = {
  chain: [{ required: true, message: '必選', trigger: 'change' }],
  protocol: [{ required: true, message: '必選', trigger: 'change' }],
  port: [{ required: true, message: '請輸入埠號', trigger: 'blur' }],
  target: [{ required: true, message: '必選', trigger: 'change' }],
}
// Use computed alias for template
const fwRulesAlias = fwRules_data

// Realtime Stats
const netStats = ref([])
const statsAuto = ref(false)
let statsTimer = null

// Diagnostics
const diagPing = reactive({ host: '', result: '', loading: false })
const diagTrace = reactive({ host: '', result: '', loading: false })
const diagDns = reactive({ host: '', result: '', loading: false })

// WOL
const wolMac = ref('')
const wolLoading = ref(false)

// --- Load ---
async function loadData() {
  loading.value = true
  try {
    const res = await api.get('/api/network/interfaces')
    interfaces.value = res.data.interfaces || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

// --- Interface Config ---
function openIfConfig(row) {
  ifForm.name = row.name
  ifForm.method = 'dhcp'
  ifForm.ip = row.ipv4 || ''
  ifForm.netmask = '255.255.255.0'
  ifForm.gateway = ''
  ifForm.dns = ''
  ifDialogVisible.value = true
}

async function saveIfConfig() {
  if (ifForm.method === 'static') {
    const valid = await ifFormRef.value.validate().catch(() => false)
    if (!valid) return
  }
  await ElMessageBox.confirm('修改網路設定可能導致連線中斷，確定繼續？', '警告', { type: 'warning' })
  ifSaving.value = true
  try {
    const payload = { method: ifForm.method }
    if (ifForm.method === 'static') {
      payload.ip = ifForm.ip
      payload.netmask = ifForm.netmask
      payload.gateway = ifForm.gateway
      payload.dns = ifForm.dns ? ifForm.dns.split(',').map(s => s.trim()) : []
    }
    await api.put(`/api/network/interfaces/${ifForm.name}`, payload)
    ElMessage.success('介面設定已套用')
    ifDialogVisible.value = false
    loadData()
  } catch { /* handled */ }
  finally { ifSaving.value = false }
}

// --- Firewall ---
async function loadFirewall() {
  fwLoading.value = true
  try {
    const res = await api.get('/api/network/firewall/rules')
    fwRules_data.value = res.data.rules || []
  } catch { /* handled */ }
  finally { fwLoading.value = false }
}

async function addFwRule() {
  const valid = await fwFormRef.value.validate().catch(() => false)
  if (!valid) return
  await api.post('/api/network/firewall/rules', fwForm)
  ElMessage.success('規則已新增')
  fwDialogVisible.value = false
  loadFirewall()
}

async function deleteFwRule(rule) {
  await ElMessageBox.confirm('確定要刪除此防火牆規則？', '確認', { type: 'warning' })
  await api.delete(`/api/network/firewall/rules/${rule.id}`, { params: { chain: rule.chain } })
  ElMessage.success('規則已刪除')
  loadFirewall()
}

// --- Realtime Stats ---
async function refreshStats() {
  try {
    const res = await api.get('/api/network/stats')
    netStats.value = res.data.interfaces || []
  } catch { /* handled */ }
}

function formatSpeed(bytesPerSec) {
  if (!bytesPerSec || bytesPerSec === 0) return '0 B/s'
  if (bytesPerSec > 1048576) return (bytesPerSec / 1048576).toFixed(1) + ' MB/s'
  if (bytesPerSec > 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s'
  return bytesPerSec + ' B/s'
}

watch(statsAuto, (val) => {
  if (val) {
    refreshStats()
    statsTimer = setInterval(refreshStats, 2000)
  } else {
    if (statsTimer) { clearInterval(statsTimer); statsTimer = null }
  }
})

// --- Diagnostics ---
async function runPing() {
  if (!diagPing.host) { ElMessage.warning('請輸入主機'); return }
  diagPing.loading = true; diagPing.result = ''
  try {
    const res = await api.post('/api/network/diag/ping', { host: diagPing.host })
    diagPing.result = res.data.output || JSON.stringify(res.data, null, 2)
  } catch { diagPing.result = '執行失敗' }
  finally { diagPing.loading = false }
}

async function runTraceroute() {
  if (!diagTrace.host) { ElMessage.warning('請輸入主機'); return }
  diagTrace.loading = true; diagTrace.result = ''
  try {
    const res = await api.post('/api/network/diag/traceroute', { host: diagTrace.host })
    diagTrace.result = res.data.output || JSON.stringify(res.data, null, 2)
  } catch { diagTrace.result = '執行失敗' }
  finally { diagTrace.loading = false }
}

async function runDns() {
  if (!diagDns.host) { ElMessage.warning('請輸入網域'); return }
  diagDns.loading = true; diagDns.result = ''
  try {
    const res = await api.post('/api/network/diag/dns', { domain: diagDns.host })
    diagDns.result = res.data.records ? res.data.records.join('\n') : JSON.stringify(res.data, null, 2)
  } catch { diagDns.result = '執行失敗' }
  finally { diagDns.loading = false }
}

// --- WOL ---
async function sendWol() {
  if (!wolMac.value) { ElMessage.warning('請輸入 MAC 位址'); return }
  wolLoading.value = true
  try {
    await api.post('/api/network/wol', { mac: wolMac.value })
    ElMessage.success('喚醒封包已發送')
  } catch { /* handled */ }
  finally { wolLoading.value = false }
}

onMounted(() => { loadData(); loadFirewall() })
onUnmounted(() => { if (statsTimer) clearInterval(statsTimer) })
</script>

<style scoped>
.diag-output {
  max-height: 300px; overflow: auto; background: #1e1e1e; color: #d4d4d4;
  padding: 8px; border-radius: 4px; font-size: 12px; white-space: pre-wrap;
}
</style>
