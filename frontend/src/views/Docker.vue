<template>
  <div>
    <h2>Docker 容器管理</h2>

    <el-tabs>
      <!-- Containers & Images Tab -->
      <el-tab-pane label="容器 / 映像">
        <el-button type="primary" @click="createDialogVisible = true" style="margin-bottom:12px;">建立容器</el-button>

        <el-table :data="containers" stripe v-loading="loading">
          <el-table-column prop="name" label="名稱" />
          <el-table-column prop="image" label="映像" />
          <el-table-column prop="status" label="狀態">
            <template #default="{ row }">
              <el-tag :type="row.state === 'running' ? 'success' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="420">
            <template #default="{ row }">
              <el-button v-if="row.state !== 'running'" type="success" size="small" @click="start(row.id)">啟動</el-button>
              <el-button v-if="row.state === 'running'" type="warning" size="small" @click="stop(row.id)">停止</el-button>
              <el-button type="primary" size="small" @click="restart(row.id)">重啟</el-button>
              <el-button size="small" @click="showLogs(row.id, row.name)">日誌</el-button>
              <el-button size="small" @click="showStats(row.id, row.name)">Stats</el-button>
              <el-button size="small" @click="showInspect(row.id, row.name)">Inspect</el-button>
              <el-button type="danger" size="small" @click="remove(row.id)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div style="display:flex; align-items:center; gap:12px; margin-top:24px;">
          <h3 style="margin:0;">映像</h3>
          <el-button type="warning" size="small" @click="pruneImages">清理未使用映像</el-button>
        </div>
        <el-table :data="images" stripe style="margin-top:12px;">
          <el-table-column prop="tags" label="標籤">
            <template #default="{ row }">{{ (row.tags || []).join(', ') || row.id }}</template>
          </el-table-column>
          <el-table-column prop="size_mb" label="大小 (MB)" width="120" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteImage(row.id)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Networks Tab -->
      <el-tab-pane label="網路">
        <el-button type="primary" @click="networkDialogVisible = true" style="margin-bottom:12px;">建立網路</el-button>
        <el-button @click="loadNetworks" style="margin-bottom:12px;">重新整理</el-button>

        <el-table :data="networks" stripe v-loading="networksLoading">
          <el-table-column prop="id" label="ID" width="140">
            <template #default="{ row }">{{ row.id?.substring(0, 12) }}</template>
          </el-table-column>
          <el-table-column prop="name" label="名稱" />
          <el-table-column prop="driver" label="驅動" width="120" />
          <el-table-column prop="scope" label="範圍" width="100" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button
                type="danger"
                size="small"
                :disabled="['bridge', 'host', 'none'].includes(row.name)"
                @click="deleteNetwork(row.id, row.name)"
              >刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Volumes Tab -->
      <el-tab-pane label="Volumes">
        <el-button type="primary" @click="volumeDialogVisible = true" style="margin-bottom:12px;">建立 Volume</el-button>
        <el-button @click="loadVolumes" style="margin-bottom:12px;">重新整理</el-button>

        <el-table :data="volumes" stripe v-loading="volumesLoading">
          <el-table-column prop="name" label="名稱" />
          <el-table-column prop="driver" label="驅動" width="120" />
          <el-table-column prop="mountpoint" label="掛載點" show-overflow-tooltip />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteVolume(row.name)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Compose Tab -->
      <el-tab-pane label="Compose">
        <el-button type="primary" @click="composeDeployVisible = true" style="margin-bottom:12px;">部署專案</el-button>
        <el-button @click="loadComposeProjects" style="margin-bottom:12px;">重新整理</el-button>

        <el-table :data="composeProjects" stripe v-loading="composeLoading">
          <el-table-column prop="name" label="專案名稱" />
          <el-table-column prop="status" label="狀態">
            <template #default="{ row }">
              <el-tag :type="row.status === 'running' ? 'success' : 'info'">{{ row.status || '未知' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="services" label="服務數" width="100" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="removeComposeProject(row.name)">移除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- App Store Tab -->
      <el-tab-pane label="應用商店">
        <p style="margin-bottom:16px;color:#666;">點擊「安裝」將自動填入 Compose YAML，您可在部署前修改設定。</p>
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="app in appTemplates" :key="app.name" style="margin-bottom:16px;">
            <el-card shadow="hover" style="height:100%;">
              <div style="text-align:center; margin-bottom:12px;">
                <span style="font-size:48px;">{{ app.icon }}</span>
              </div>
              <h3 style="margin:0 0 8px 0; text-align:center;">{{ app.name }}</h3>
              <p style="color:#666; font-size:13px; text-align:center; margin:0 0 16px 0;">{{ app.desc }}</p>
              <div style="text-align:center;">
                <el-button type="primary" @click="installApp(app)">安裝</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>

    <!-- Log Dialog -->
    <el-dialog v-model="logVisible" :title="'日誌 — ' + logName" width="70%">
      <pre style="max-height:400px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:4px;font-size:12px;">{{ logs }}</pre>
    </el-dialog>

    <!-- Stats Dialog -->
    <el-dialog v-model="statsVisible" :title="'容器狀態 — ' + statsName" width="500px">
      <el-descriptions :column="1" border v-if="statsData">
        <el-descriptions-item label="CPU 使用率">{{ statsData.cpu_percent?.toFixed(2) }} %</el-descriptions-item>
        <el-descriptions-item label="記憶體使用">{{ statsData.memory_mb?.toFixed(1) }} MB / {{ statsData.memory_limit_mb?.toFixed(0) }} MB</el-descriptions-item>
        <el-descriptions-item label="記憶體使用率">{{ statsData.memory_percent?.toFixed(2) }} %</el-descriptions-item>
        <el-descriptions-item label="網路 RX">{{ statsData.network_rx_mb?.toFixed(2) }} MB</el-descriptions-item>
        <el-descriptions-item label="網路 TX">{{ statsData.network_tx_mb?.toFixed(2) }} MB</el-descriptions-item>
      </el-descriptions>
      <div v-else v-loading="statsLoading" style="min-height:100px;"></div>
    </el-dialog>

    <!-- Inspect Dialog -->
    <el-dialog v-model="inspectVisible" :title="'詳細設定 — ' + inspectName" width="70%">
      <pre style="max-height:500px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:4px;font-size:12px;">{{ inspectContent }}</pre>
    </el-dialog>

    <!-- Create Container Dialog -->
    <el-dialog v-model="createDialogVisible" title="建立容器" width="550px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="映像" prop="image">
          <el-input v-model="createForm.image" placeholder="nginx:latest" />
        </el-form-item>
        <el-form-item label="容器名稱">
          <el-input v-model="createForm.name" placeholder="my-container (可選)" />
        </el-form-item>
        <el-form-item label="埠對應">
          <div v-for="(p, i) in createForm.portList" :key="i" style="display:flex; gap:4px; margin-bottom:4px;">
            <el-input v-model="p.host" placeholder="主機埠" style="width:100px;" />
            <span>:</span>
            <el-input v-model="p.container" placeholder="容器埠" style="width:100px;" />
            <el-button size="small" @click="createForm.portList.splice(i, 1)">✕</el-button>
          </div>
          <el-button size="small" @click="createForm.portList.push({host:'',container:''})">+ 新增埠</el-button>
        </el-form-item>
        <el-form-item label="環境變數">
          <div v-for="(e, i) in createForm.envList" :key="i" style="display:flex; gap:4px; margin-bottom:4px;">
            <el-input v-model="e.key" placeholder="KEY" style="width:120px;" />
            <span>=</span>
            <el-input v-model="e.value" placeholder="VALUE" style="width:180px;" />
            <el-button size="small" @click="createForm.envList.splice(i, 1)">✕</el-button>
          </div>
          <el-button size="small" @click="createForm.envList.push({key:'',value:''})">+ 新增變數</el-button>
        </el-form-item>
        <el-form-item label="重啟策略">
          <el-select v-model="createForm.restart_policy">
            <el-option value="no" label="不重啟" />
            <el-option value="always" label="總是重啟" />
            <el-option value="on-failure" label="失敗時重啟" />
            <el-option value="unless-stopped" label="除非手動停止" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="createContainer">建立</el-button>
      </template>
    </el-dialog>

    <!-- Create Network Dialog -->
    <el-dialog v-model="networkDialogVisible" title="建立網路" width="450px">
      <el-form :model="networkForm" label-width="80px">
        <el-form-item label="名稱" required>
          <el-input v-model="networkForm.name" placeholder="my-network" />
        </el-form-item>
        <el-form-item label="驅動">
          <el-select v-model="networkForm.driver">
            <el-option value="bridge" label="bridge" />
            <el-option value="overlay" label="overlay" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="networkDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="networkCreating" @click="createNetwork">建立</el-button>
      </template>
    </el-dialog>

    <!-- Create Volume Dialog -->
    <el-dialog v-model="volumeDialogVisible" title="建立 Volume" width="450px">
      <el-form :model="volumeForm" label-width="80px">
        <el-form-item label="名稱" required>
          <el-input v-model="volumeForm.name" placeholder="my-volume" />
        </el-form-item>
        <el-form-item label="驅動">
          <el-select v-model="volumeForm.driver">
            <el-option value="local" label="local" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="volumeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="volumeCreating" @click="createVolume">建立</el-button>
      </template>
    </el-dialog>

    <!-- Compose Deploy Dialog -->
    <el-dialog v-model="composeDeployVisible" title="部署 Compose 專案" width="600px">
      <el-form :model="composeForm" label-width="100px">
        <el-form-item label="專案名稱" required>
          <el-input v-model="composeForm.name" placeholder="my-project" />
        </el-form-item>
        <el-form-item label="YAML 內容" required>
          <el-input v-model="composeForm.yaml" type="textarea" :rows="12" placeholder="version: '3'&#10;services:&#10;  web:&#10;    image: nginx" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="composeDeployVisible = false">取消</el-button>
        <el-button type="primary" :loading="composeDeployLoading" @click="deployCompose">部署</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

// --- App Store Templates ---
const appTemplates = [
  { name: 'Nextcloud', icon: '☁️', desc: '私有雲端儲存', yaml: "version: '3'\nservices:\n  nextcloud:\n    image: nextcloud:latest\n    ports:\n      - \"8080:80\"\n    volumes:\n      - nextcloud_data:/var/www/html\nvolumes:\n  nextcloud_data:" },
  { name: 'Jellyfin', icon: '🎬', desc: '開源媒體伺服器', yaml: "version: '3'\nservices:\n  jellyfin:\n    image: jellyfin/jellyfin:latest\n    ports:\n      - \"8096:8096\"\n    volumes:\n      - jellyfin_config:/config\n      - jellyfin_cache:/cache\n      - /media:/media:ro\nvolumes:\n  jellyfin_config:\n  jellyfin_cache:" },
  { name: 'Pi-hole', icon: '🛡️', desc: 'DNS 廣告過濾器', yaml: "version: '3'\nservices:\n  pihole:\n    image: pihole/pihole:latest\n    ports:\n      - \"53:53/tcp\"\n      - \"53:53/udp\"\n      - \"8081:80\"\n    environment:\n      TZ: Asia/Taipei\n      WEBPASSWORD: changeme\n    volumes:\n      - pihole_data:/etc/pihole\nvolumes:\n  pihole_data:" },
  { name: 'Portainer', icon: '🐳', desc: 'Docker 管理 UI', yaml: "version: '3'\nservices:\n  portainer:\n    image: portainer/portainer-ce:latest\n    ports:\n      - \"9000:9000\"\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n      - portainer_data:/data\nvolumes:\n  portainer_data:" },
  { name: 'Nginx Proxy Manager', icon: '🌐', desc: '反向代理管理', yaml: "version: '3'\nservices:\n  npm:\n    image: jc21/nginx-proxy-manager:latest\n    ports:\n      - \"80:80\"\n      - \"443:443\"\n      - \"81:81\"\n    volumes:\n      - npm_data:/data\n      - npm_letsencrypt:/etc/letsencrypt\nvolumes:\n  npm_data:\n  npm_letsencrypt:" },
  { name: 'Home Assistant', icon: '🏠', desc: '智慧家庭平台', yaml: "version: '3'\nservices:\n  homeassistant:\n    image: ghcr.io/home-assistant/home-assistant:stable\n    ports:\n      - \"8123:8123\"\n    volumes:\n      - ha_config:/config\n    environment:\n      TZ: Asia/Taipei\nvolumes:\n  ha_config:" },
  { name: 'Gitea', icon: '🍵', desc: '輕量 Git 託管', yaml: "version: '3'\nservices:\n  gitea:\n    image: gitea/gitea:latest\n    ports:\n      - \"3000:3000\"\n      - \"2222:22\"\n    volumes:\n      - gitea_data:/data\n    environment:\n      USER_UID: 1000\n      USER_GID: 1000\nvolumes:\n  gitea_data:" },
  { name: 'Uptime Kuma', icon: '📈', desc: '服務監控面板', yaml: "version: '3'\nservices:\n  uptime-kuma:\n    image: louislam/uptime-kuma:latest\n    ports:\n      - \"3001:3001\"\n    volumes:\n      - kuma_data:/app/data\nvolumes:\n  kuma_data:" },
]

function installApp(app) {
  composeForm.name = app.name.toLowerCase().replace(/\s+/g, '-')
  composeForm.yaml = app.yaml
  composeDeployVisible.value = true
}

// --- Containers & Images ---
const containers = ref([])
const images = ref([])
const loading = ref(false)
const logVisible = ref(false)
const logName = ref('')
const logs = ref('')

// Stats
const statsVisible = ref(false)
const statsName = ref('')
const statsData = ref(null)
const statsLoading = ref(false)

// Inspect
const inspectVisible = ref(false)
const inspectName = ref('')
const inspectContent = ref('')

// Create container
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  image: '',
  name: '',
  portList: [],
  envList: [],
  restart_policy: 'no',
})
const createRules = {
  image: [{ required: true, message: '請輸入映像名稱', trigger: 'blur' }],
}

// --- Networks ---
const networks = ref([])
const networksLoading = ref(false)
const networkDialogVisible = ref(false)
const networkCreating = ref(false)
const networkForm = reactive({ name: '', driver: 'bridge' })

// --- Volumes ---
const volumes = ref([])
const volumesLoading = ref(false)
const volumeDialogVisible = ref(false)
const volumeCreating = ref(false)
const volumeForm = reactive({ name: '', driver: 'local' })

// --- Compose ---
const composeProjects = ref([])
const composeLoading = ref(false)
const composeDeployVisible = ref(false)
const composeDeployLoading = ref(false)
const composeForm = reactive({ name: '', yaml: '' })

// === Data Loading ===
async function loadData() {
  loading.value = true
  try {
    const [c, i] = await Promise.all([api.get('/api/docker/containers'), api.get('/api/docker/images')])
    containers.value = c.data.containers || []
    images.value = i.data.images || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function loadNetworks() {
  networksLoading.value = true
  try {
    const res = await api.get('/api/docker/networks')
    networks.value = res.data.networks || []
  } catch { /* handled */ }
  finally { networksLoading.value = false }
}

async function loadVolumes() {
  volumesLoading.value = true
  try {
    const res = await api.get('/api/docker/volumes')
    volumes.value = res.data.volumes || []
  } catch { /* handled */ }
  finally { volumesLoading.value = false }
}

// === Container Actions ===
async function start(id) { await api.post(`/api/docker/containers/${id}/start`); ElMessage.success('已啟動'); loadData() }
async function stop(id) { await api.post(`/api/docker/containers/${id}/stop`); ElMessage.success('已停止'); loadData() }
async function restart(id) { await api.post(`/api/docker/containers/${id}/restart`); ElMessage.success('已重啟'); loadData() }
async function remove(id) {
  await ElMessageBox.confirm('確定要刪除此容器？', '確認', { type: 'warning' })
  await api.delete(`/api/docker/containers/${id}`, { params: { force: true } })
  ElMessage.success('已刪除')
  loadData()
}

async function showLogs(id, name) {
  logName.value = name
  const res = await api.get(`/api/docker/containers/${id}/logs`)
  logs.value = res.data.logs || 'No logs'
  logVisible.value = true
}

async function showStats(id, name) {
  statsName.value = name
  statsData.value = null
  statsLoading.value = true
  statsVisible.value = true
  try {
    const res = await api.get(`/api/docker/containers/${id}/stats`)
    statsData.value = res.data
  } catch { ElMessage.error('無法載入容器狀態') }
  finally { statsLoading.value = false }
}

async function showInspect(id, name) {
  inspectName.value = name
  inspectContent.value = '載入中...'
  inspectVisible.value = true
  try {
    const res = await api.get(`/api/docker/containers/${id}/inspect`)
    inspectContent.value = JSON.stringify(res.data.config || res.data, null, 2)
  } catch { inspectContent.value = '載入失敗' }
}

// === Image Actions ===
async function deleteImage(id) {
  await ElMessageBox.confirm('確定要刪除此映像？', '確認', { type: 'warning' })
  await api.delete(`/api/docker/images/${id}`)
  ElMessage.success('映像已刪除')
  loadData()
}

async function pruneImages() {
  await ElMessageBox.confirm('確定要清理所有未使用的映像？此操作無法撤銷。', '清理映像', { type: 'warning' })
  try {
    const res = await api.post('/api/docker/images/prune')
    const data = res.data
    ElMessage.success(`已清理 ${data.deleted_count || 0} 個映像，釋放 ${data.space_reclaimed_mb || 0} MB`)
    loadData()
  } catch { /* handled */ }
}

// === Create Container ===
async function createContainer() {
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return
  createLoading.value = true

  const ports = {}
  createForm.portList.forEach(p => {
    if (p.host && p.container) ports[`${p.container}/tcp`] = parseInt(p.host)
  })

  const environment = {}
  createForm.envList.forEach(e => {
    if (e.key) environment[e.key] = e.value
  })

  try {
    await api.post('/api/docker/containers/create', {
      image: createForm.image,
      name: createForm.name || undefined,
      ports: Object.keys(ports).length ? ports : undefined,
      environment: Object.keys(environment).length ? environment : undefined,
      restart_policy: createForm.restart_policy,
    })
    ElMessage.success('容器已建立')
    createDialogVisible.value = false
    createForm.image = ''
    createForm.name = ''
    createForm.portList = []
    createForm.envList = []
    loadData()
  } catch { /* handled */ }
  finally { createLoading.value = false }
}

// === Network Actions ===
async function createNetwork() {
  if (!networkForm.name) {
    ElMessage.warning('請輸入網路名稱')
    return
  }
  networkCreating.value = true
  try {
    await api.post('/api/docker/networks', {
      name: networkForm.name,
      driver: networkForm.driver,
    })
    ElMessage.success('網路已建立')
    networkDialogVisible.value = false
    networkForm.name = ''
    networkForm.driver = 'bridge'
    loadNetworks()
  } catch { /* handled */ }
  finally { networkCreating.value = false }
}

async function deleteNetwork(id, name) {
  await ElMessageBox.confirm(`確定要刪除網路「${name}」？`, '確認', { type: 'warning' })
  try {
    await api.delete(`/api/docker/networks/${id}`)
    ElMessage.success('網路已刪除')
    loadNetworks()
  } catch { /* handled */ }
}

// === Volume Actions ===
async function createVolume() {
  if (!volumeForm.name) {
    ElMessage.warning('請輸入 Volume 名稱')
    return
  }
  volumeCreating.value = true
  try {
    await api.post('/api/docker/volumes', {
      name: volumeForm.name,
      driver: volumeForm.driver,
    })
    ElMessage.success('Volume 已建立')
    volumeDialogVisible.value = false
    volumeForm.name = ''
    volumeForm.driver = 'local'
    loadVolumes()
  } catch { /* handled */ }
  finally { volumeCreating.value = false }
}

async function deleteVolume(name) {
  await ElMessageBox.confirm(`確定要刪除 Volume「${name}」？刪除後資料將無法恢復！`, '警告', { type: 'error' })
  try {
    await api.delete(`/api/docker/volumes/${name}`)
    ElMessage.success('Volume 已刪除')
    loadVolumes()
  } catch { /* handled */ }
}

// === Compose ===
async function loadComposeProjects() {
  composeLoading.value = true
  try {
    const res = await api.get('/api/docker/compose/projects')
    composeProjects.value = res.data.projects || []
  } catch { /* handled */ }
  finally { composeLoading.value = false }
}

async function deployCompose() {
  if (!composeForm.name || !composeForm.yaml) {
    ElMessage.warning('請填寫專案名稱和 YAML 內容')
    return
  }
  composeDeployLoading.value = true
  try {
    await api.post('/api/docker/compose/deploy', {
      name: composeForm.name,
      yaml: composeForm.yaml,
    })
    ElMessage.success('Compose 專案已部署')
    composeDeployVisible.value = false
    composeForm.name = ''
    composeForm.yaml = ''
    loadComposeProjects()
  } catch { /* handled */ }
  finally { composeDeployLoading.value = false }
}

async function removeComposeProject(name) {
  await ElMessageBox.confirm(`確定要移除 Compose 專案「${name}」？`, '確認', { type: 'warning' })
  try {
    await api.delete(`/api/docker/compose/projects/${name}`)
    ElMessage.success('專案已移除')
    loadComposeProjects()
  } catch { /* handled */ }
}

onMounted(() => {
  loadData()
  loadNetworks()
  loadVolumes()
  loadComposeProjects()
})
</script>
