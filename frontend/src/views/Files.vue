<template>
  <div>
    <h2>檔案管理</h2>

    <!-- Toolbar -->
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="(seg, i) in pathSegments" :key="i" @click="navigateTo(i)">
          <span style="cursor:pointer;">{{ seg || '根目錄' }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>
      <div style="flex:1;" />
      <el-button type="primary" @click="mkdirDialogVisible = true"><el-icon><FolderAdd /></el-icon>新資料夾</el-button>
      <el-button @click="compressDialogVisible = true"><el-icon><Files /></el-icon>壓縮</el-button>
      <el-upload :action="uploadUrl" :headers="uploadHeaders" :data="{dest: currentPath}" :on-success="onUploadSuccess" :show-file-list="false" multiple>
        <el-button type="success"><el-icon><Upload /></el-icon>上傳</el-button>
      </el-upload>
    </div>

    <!-- File Table -->
    <el-table :data="items" v-loading="loading" stripe @row-dblclick="handleDblClick" highlight-current-row>
      <el-table-column prop="name" label="名稱" min-width="200">
        <template #default="{ row }">
          <el-icon v-if="row.type === 'dir'" style="color:#e6a23c;"><Folder /></el-icon>
          <el-icon v-else style="color:#909399;"><Document /></el-icon>
          {{ row.name }}
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="120">
        <template #default="{ row }">{{ row.type === 'dir' ? '—' : formatSize(row.size) }}</template>
      </el-table-column>
      <el-table-column prop="modified" label="修改時間" width="180">
        <template #default="{ row }">{{ formatDate(row.modified) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button v-if="row.type === 'file'" size="small" @click="download(row)">下載</el-button>
          <el-button v-if="row.type === 'file'" size="small" type="success" @click="openShareDialog(row)">分享</el-button>
          <el-button type="danger" size="small" @click="confirmDelete(row)">刪除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Mkdir Dialog -->
    <el-dialog v-model="mkdirDialogVisible" title="新建資料夾" width="400px">
      <el-input v-model="newFolderName" placeholder="資料夾名稱" @keyup.enter="createFolder" />
      <template #footer>
        <el-button @click="mkdirDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createFolder">建立</el-button>
      </template>
    </el-dialog>

    <!-- Compress Dialog -->
    <el-dialog v-model="compressDialogVisible" title="壓縮檔案" width="500px">
      <el-form :model="compressForm" label-width="100px">
        <el-form-item label="來源路徑">
          <el-input v-model="compressForm.paths" placeholder="檔案或資料夾路徑（多個以逗號分隔）" />
        </el-form-item>
        <el-form-item label="格式">
          <el-radio-group v-model="compressForm.format">
            <el-radio value="zip">ZIP</el-radio>
            <el-radio value="tar.gz">TAR.GZ</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="輸出路徑">
          <el-input v-model="compressForm.dest" placeholder="/data/archive.zip" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="compressDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="compressLoading" @click="compressFiles">壓縮</el-button>
      </template>
    </el-dialog>

    <!-- Share Dialog -->
    <el-dialog v-model="shareDialogVisible" title="建立分享連結" width="450px">
      <el-form :model="shareForm" label-width="100px">
        <el-form-item label="檔案">{{ shareForm.path }}</el-form-item>
        <el-form-item label="有效時數">
          <el-input-number v-model="shareForm.expires_hours" :min="1" :max="720" />
        </el-form-item>
        <el-form-item label="密碼（選填）">
          <el-input v-model="shareForm.password" placeholder="留空則無密碼保護" />
        </el-form-item>
      </el-form>
      <div v-if="shareLink" style="margin-top:12px;">
        <el-alert type="success" :closable="false">
          <p>分享連結：</p>
          <el-input v-model="shareLink" readonly>
            <template #append>
              <el-button @click="copyShareLink">複製</el-button>
            </template>
          </el-input>
        </el-alert>
      </div>
      <template #footer>
        <el-button @click="shareDialogVisible = false">關閉</el-button>
        <el-button type="primary" :loading="shareLoading" @click="createShareLink" v-if="!shareLink">建立連結</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const currentPath = ref('/data')
const items = ref([])
const loading = ref(false)
const mkdirDialogVisible = ref(false)
const newFolderName = ref('')

// Compress
const compressDialogVisible = ref(false)
const compressLoading = ref(false)
const compressForm = reactive({ paths: '', format: 'zip', dest: '' })

// Share
const shareDialogVisible = ref(false)
const shareLoading = ref(false)
const shareForm = reactive({ path: '', expires_hours: 24, password: '' })
const shareLink = ref('')

const pathSegments = computed(() => currentPath.value.split('/').filter(Boolean))

const uploadUrl = '/api/files/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
}))

async function loadFiles() {
  loading.value = true
  try {
    const res = await api.get('/api/files/list', { params: { path: currentPath.value } })
    items.value = res.data.items || []
  } catch { /* handled by interceptor */ }
  finally { loading.value = false }
}

function navigateTo(index) {
  const segments = currentPath.value.split('/').filter(Boolean)
  currentPath.value = '/' + segments.slice(0, index + 1).join('/')
  loadFiles()
}

function handleDblClick(row) {
  if (row.type === 'dir') {
    currentPath.value = currentPath.value.replace(/\/$/, '') + '/' + row.name
    loadFiles()
  }
}

function download(row) {
  const path = currentPath.value.replace(/\/$/, '') + '/' + row.name
  const token = localStorage.getItem('token')
  window.open(`/api/files/download?path=${encodeURIComponent(path)}&token=${token}`, '_blank')
}

async function createFolder() {
  if (!newFolderName.value.trim()) return
  const path = currentPath.value.replace(/\/$/, '') + '/' + newFolderName.value.trim()
  try {
    await api.post('/api/files/mkdir', { path })
    ElMessage.success('資料夾已建立')
    mkdirDialogVisible.value = false
    newFolderName.value = ''
    loadFiles()
  } catch { /* handled */ }
}

async function confirmDelete(row) {
  try {
    await ElMessageBox.confirm(`確定要刪除「${row.name}」？此操作不可復原。`, '確認刪除', {
      confirmButtonText: '刪除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const path = currentPath.value.replace(/\/$/, '') + '/' + row.name
    await api.delete('/api/files/delete', { data: { path } })
    ElMessage.success('已刪除')
    loadFiles()
  } catch { /* cancelled or error handled */ }
}

function onUploadSuccess() {
  ElMessage.success('上傳完成')
  loadFiles()
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-TW')
}

// Compress
async function compressFiles() {
  if (!compressForm.paths || !compressForm.dest) {
    ElMessage.warning('請填寫來源路徑和輸出路徑')
    return
  }
  compressLoading.value = true
  try {
    const paths = compressForm.paths.split(',').map(p => p.trim()).filter(Boolean)
    await api.post('/api/files/compress', {
      paths,
      format: compressForm.format,
      dest: compressForm.dest,
    })
    ElMessage.success('壓縮完成')
    compressDialogVisible.value = false
    compressForm.paths = ''
    compressForm.dest = ''
    loadFiles()
  } catch { /* handled */ }
  finally { compressLoading.value = false }
}

// Share
function openShareDialog(row) {
  shareForm.path = currentPath.value.replace(/\/$/, '') + '/' + row.name
  shareForm.expires_hours = 24
  shareForm.password = ''
  shareLink.value = ''
  shareDialogVisible.value = true
}

async function createShareLink() {
  shareLoading.value = true
  try {
    const payload = {
      path: shareForm.path,
      expires_hours: shareForm.expires_hours,
    }
    if (shareForm.password) payload.password = shareForm.password
    const res = await api.post('/api/files/share', payload)
    shareLink.value = res.data.link || res.data.url || ''
    ElMessage.success('分享連結已建立')
  } catch { /* handled */ }
  finally { shareLoading.value = false }
}

function copyShareLink() {
  navigator.clipboard.writeText(shareLink.value)
  ElMessage.success('已複製到剪貼簿')
}

onMounted(loadFiles)
</script>
