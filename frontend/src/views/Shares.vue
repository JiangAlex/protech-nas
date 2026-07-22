<template>
  <div>
    <h2>檔案共享管理</h2>

    <!-- Service Status Bar -->
    <div style="display:flex; gap:16px; margin-bottom:16px;">
      <el-tag :type="smbStatus.running ? 'success' : 'danger'" size="large">
        SMB: {{ smbStatus.running ? '運行中' : '已停止' }}
        <span v-if="smbStatus.connections"> ({{ smbStatus.connections.length }} 連線)</span>
      </el-tag>
      <el-tag :type="nfsStatus.running ? 'success' : 'danger'" size="large">
        NFS: {{ nfsStatus.running ? '運行中' : '已停止' }}
        <span v-if="nfsStatus.clients"> ({{ nfsStatus.clients.length }} 客戶端)</span>
      </el-tag>
    </div>

    <el-tabs>
      <!-- SMB Tab -->
      <el-tab-pane label="SMB 共享">
        <el-button type="primary" @click="openSmbCreate" style="margin-bottom:12px;">新增 SMB 共享</el-button>
        <el-table :data="smbShares" stripe v-loading="loading">
          <el-table-column prop="name" label="名稱" />
          <el-table-column prop="path" label="路徑" />
          <el-table-column prop="comment" label="說明" />
          <el-table-column label="操作" width="220">
            <template #default="{ row }">
              <el-button size="small" @click="openSmbEdit(row)">編輯</el-button>
              <el-button size="small" @click="openAcl(row.name, row.path)">ACL</el-button>
              <el-button type="danger" size="small" @click="deleteSMB(row.name)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- NFS Tab -->
      <el-tab-pane label="NFS 匯出">
        <el-button type="primary" @click="openNfsCreate" style="margin-bottom:12px;">新增 NFS 匯出</el-button>
        <el-table :data="nfsExports" stripe v-loading="loading">
          <el-table-column prop="path" label="路徑" />
          <el-table-column prop="clients" label="客戶端" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" @click="openNfsEdit(row)">編輯</el-button>
              <el-button type="danger" size="small" @click="deleteNFS(row.path)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- SMB Create/Edit Dialog -->
    <el-dialog v-model="smbDialogVisible" :title="smbEditing ? '編輯 SMB 共享' : '新增 SMB 共享'">
      <el-form ref="smbFormRef" :model="smbForm" :rules="smbRules" label-width="100px">
        <el-form-item label="名稱" prop="name">
          <el-input v-model="smbForm.name" :disabled="smbEditing" />
        </el-form-item>
        <el-form-item label="路徑" prop="path">
          <el-input v-model="smbForm.path" placeholder="/data/share" />
        </el-form-item>
        <el-form-item label="說明">
          <el-input v-model="smbForm.comment" />
        </el-form-item>
        <el-form-item label="允許使用者">
          <el-input v-model="smbForm.valid_users" placeholder="user1,user2 (留空為全部)" />
        </el-form-item>
        <el-form-item label="唯讀">
          <el-switch v-model="smbForm.read_only" />
        </el-form-item>
        <el-form-item label="允許訪客">
          <el-switch v-model="smbForm.guest_ok" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="smbDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSMB">{{ smbEditing ? '儲存' : '建立' }}</el-button>
      </template>
    </el-dialog>

    <!-- NFS Create/Edit Dialog -->
    <el-dialog v-model="nfsDialogVisible" :title="nfsEditing ? '編輯 NFS 匯出' : '新增 NFS 匯出'">
      <el-form ref="nfsFormRef" :model="nfsForm" :rules="nfsRules" label-width="80px">
        <el-form-item label="路徑" prop="path">
          <el-input v-model="nfsForm.path" :disabled="nfsEditing" placeholder="/data/nfs" />
        </el-form-item>
        <el-form-item label="客戶端" prop="clients">
          <el-input v-model="nfsForm.clients" placeholder="192.168.1.0/24(rw,sync,no_subtree_check)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nfsDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveNFS">{{ nfsEditing ? '儲存' : '建立' }}</el-button>
      </template>
    </el-dialog>

    <!-- ACL Dialog -->
    <el-dialog v-model="aclDialogVisible" :title="'ACL 權限 — ' + aclShareName" width="600px">
      <p style="margin-bottom:12px;">路徑：<code>{{ aclPath }}</code></p>
      <el-table :data="aclEntries" border size="small">
        <el-table-column prop="type" label="類型" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.type === 'user' ? '' : 'warning'">{{ row.type === 'user' ? '使用者' : '群組' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名稱" />
        <el-table-column label="讀取" width="70" align="center">
          <template #default="{ row }"><el-checkbox v-model="row.read" /></template>
        </el-table-column>
        <el-table-column label="寫入" width="70" align="center">
          <template #default="{ row }"><el-checkbox v-model="row.write" /></template>
        </el-table-column>
        <el-table-column label="執行" width="70" align="center">
          <template #default="{ row }"><el-checkbox v-model="row.execute" /></template>
        </el-table-column>
        <el-table-column label="" width="60">
          <template #default="{ $index }">
            <el-button type="danger" size="small" text @click="aclEntries.splice($index, 1)">✕</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div style="display:flex; gap:8px; margin-top:12px;">
        <el-select v-model="newAcl.type" style="width:100px;">
          <el-option value="user" label="使用者" />
          <el-option value="group" label="群組" />
        </el-select>
        <el-input v-model="newAcl.name" placeholder="名稱" style="width:150px;" />
        <el-button @click="addAclEntry">+ 新增</el-button>
      </div>
      <template #footer>
        <el-button @click="aclDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="aclSaving" @click="saveAcl">儲存 ACL</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const smbShares = ref([])
const nfsExports = ref([])
const loading = ref(false)
const smbStatus = reactive({ running: false, connections: [] })
const nfsStatus = reactive({ running: false, clients: [] })

// SMB form
const smbDialogVisible = ref(false)
const smbEditing = ref(false)
const smbFormRef = ref(null)
const smbForm = reactive({ name: '', path: '', comment: '', valid_users: '', read_only: false, guest_ok: false })
const smbRules = {
  name: [{ required: true, message: '請輸入共享名稱', trigger: 'blur' }],
  path: [{ required: true, message: '請輸入路徑', trigger: 'blur' }],
}

// NFS form
const nfsDialogVisible = ref(false)
const nfsEditing = ref(false)
const nfsFormRef = ref(null)
const nfsForm = reactive({ path: '', clients: '' })
const nfsRules = {
  path: [{ required: true, message: '請輸入匯出路徑', trigger: 'blur' }],
  clients: [{ required: true, message: '請輸入客戶端規則', trigger: 'blur' }],
}

// ACL
const aclDialogVisible = ref(false)
const aclShareName = ref('')
const aclPath = ref('')
const aclEntries = ref([])
const aclSaving = ref(false)
const newAcl = reactive({ type: 'user', name: '' })

// --- Load Data ---
async function loadData() {
  loading.value = true
  try {
    const [s, n] = await Promise.all([api.get('/api/shares/smb'), api.get('/api/shares/nfs')])
    smbShares.value = s.data.shares || []
    nfsExports.value = n.data.exports || []
  } catch { /* handled */ }
  finally { loading.value = false }
  // Load status in background
  loadStatus()
}

async function loadStatus() {
  try {
    const [s, n] = await Promise.all([api.get('/api/shares/smb/status'), api.get('/api/shares/nfs/status')])
    smbStatus.running = s.data.service_running || false
    smbStatus.connections = s.data.connections || []
    nfsStatus.running = n.data.service_running || false
    nfsStatus.clients = n.data.clients || []
  } catch { /* ignore status errors */ }
}

// --- SMB CRUD ---
function openSmbCreate() {
  smbEditing.value = false
  Object.assign(smbForm, { name: '', path: '', comment: '', valid_users: '', read_only: false, guest_ok: false })
  smbDialogVisible.value = true
}

function openSmbEdit(row) {
  smbEditing.value = true
  Object.assign(smbForm, {
    name: row.name,
    path: row.path || '',
    comment: row.comment || '',
    valid_users: row.valid_users || '',
    read_only: row.read_only || false,
    guest_ok: row.guest_ok || false,
  })
  smbDialogVisible.value = true
}

async function saveSMB() {
  const valid = await smbFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (smbEditing.value) {
    await api.put(`/api/shares/smb/${smbForm.name}`, {
      path: smbForm.path, comment: smbForm.comment,
      valid_users: smbForm.valid_users, read_only: smbForm.read_only, guest_ok: smbForm.guest_ok,
    })
    ElMessage.success('SMB 共享已更新')
  } else {
    await api.post('/api/shares/smb', smbForm)
    ElMessage.success('SMB 共享已建立')
  }
  smbDialogVisible.value = false
  loadData()
}

async function deleteSMB(name) {
  await ElMessageBox.confirm(`確定要刪除共享「${name}」？`, '確認', { type: 'warning' })
  await api.delete(`/api/shares/smb/${name}`)
  ElMessage.success('已刪除')
  loadData()
}

// --- NFS CRUD ---
function openNfsCreate() {
  nfsEditing.value = false
  Object.assign(nfsForm, { path: '', clients: '' })
  nfsDialogVisible.value = true
}

function openNfsEdit(row) {
  nfsEditing.value = true
  Object.assign(nfsForm, { path: row.path, clients: row.clients || '' })
  nfsDialogVisible.value = true
}

async function saveNFS() {
  const valid = await nfsFormRef.value.validate().catch(() => false)
  if (!valid) return
  if (nfsEditing.value) {
    await api.put('/api/shares/nfs', { clients: nfsForm.clients }, { params: { path: nfsForm.path } })
    ElMessage.success('NFS 匯出已更新')
  } else {
    await api.post('/api/shares/nfs', nfsForm)
    ElMessage.success('NFS 匯出已建立')
  }
  nfsDialogVisible.value = false
  loadData()
}

async function deleteNFS(path) {
  await ElMessageBox.confirm(`確定要刪除匯出「${path}」？`, '確認', { type: 'warning' })
  await api.delete('/api/shares/nfs', { params: { path } })
  ElMessage.success('已刪除')
  loadData()
}

// --- ACL ---
async function openAcl(name, path) {
  aclShareName.value = name
  aclPath.value = path
  try {
    const res = await api.get(`/api/shares/smb/${name}/acl`)
    const raw = res.data.acl || []
    aclEntries.value = raw.map(a => ({
      type: a.type || 'user',
      name: a.name || a['user/group'] || '',
      read: (a.perms || '').includes('r'),
      write: (a.perms || '').includes('w'),
      execute: (a.perms || '').includes('x'),
    }))
  } catch {
    aclEntries.value = []
  }
  aclDialogVisible.value = true
}

function addAclEntry() {
  if (!newAcl.name) { ElMessage.warning('請輸入名稱'); return }
  aclEntries.value.push({ type: newAcl.type, name: newAcl.name, read: true, write: false, execute: false })
  newAcl.name = ''
}

async function saveAcl() {
  aclSaving.value = true
  try {
    const acl = aclEntries.value.map(e => ({
      type: e.type,
      name: e.name,
      perms: (e.read ? 'r' : '-') + (e.write ? 'w' : '-') + (e.execute ? 'x' : '-'),
    }))
    await api.put(`/api/shares/smb/${aclShareName.value}/acl`, { acl })
    ElMessage.success('ACL 已儲存')
    aclDialogVisible.value = false
  } catch { /* handled */ }
  finally { aclSaving.value = false }
}

onMounted(loadData)
</script>
