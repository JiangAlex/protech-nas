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
          <el-table-column label="操作" width="300">
            <template #default="{ row }">
              <el-button v-if="row.state !== 'running'" type="success" size="small" @click="start(row.id)">啟動</el-button>
              <el-button v-if="row.state === 'running'" type="warning" size="small" @click="stop(row.id)">停止</el-button>
              <el-button type="primary" size="small" @click="restart(row.id)">重啟</el-button>
              <el-button size="small" @click="showLogs(row.id, row.name)">日誌</el-button>
              <el-button type="danger" size="small" @click="remove(row.id)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <h3 style="margin-top:24px;">映像</h3>
        <el-table :data="images" stripe>
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
    </el-tabs>

    <!-- Log Dialog -->
    <el-dialog v-model="logVisible" :title="'日誌 — ' + logName" width="70%">
      <pre style="max-height:400px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:4px;font-size:12px;">{{ logs }}</pre>
    </el-dialog>

    <!-- Create Container Dialog -->
    <el-dialog v-model="createDialogVisible" title="建立容器" width="550px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="映像" required>
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

const containers = ref([])
const images = ref([])
const loading = ref(false)
const logVisible = ref(false)
const logName = ref('')
const logs = ref('')

// Create container
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  image: '',
  name: '',
  portList: [],
  envList: [],
  restart_policy: 'no',
})

// Compose
const composeProjects = ref([])
const composeLoading = ref(false)
const composeDeployVisible = ref(false)
const composeDeployLoading = ref(false)
const composeForm = reactive({ name: '', yaml: '' })

async function loadData() {
  loading.value = true
  try {
    const [c, i] = await Promise.all([api.get('/api/docker/containers'), api.get('/api/docker/images')])
    containers.value = c.data.containers || []
    images.value = i.data.images || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

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

async function deleteImage(id) {
  await ElMessageBox.confirm('確定要刪除此映像？', '確認', { type: 'warning' })
  await api.delete(`/api/docker/images/${id}`)
  ElMessage.success('映像已刪除')
  loadData()
}

async function createContainer() {
  if (!createForm.image) { ElMessage.warning('請輸入映像名稱'); return }
  createLoading.value = true

  // Build ports dict
  const ports = {}
  createForm.portList.forEach(p => {
    if (p.host && p.container) ports[`${p.container}/tcp`] = parseInt(p.host)
  })

  // Build environment dict
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

// Compose functions
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
  loadComposeProjects()
})
</script>
