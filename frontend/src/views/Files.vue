<template>
  <div>
    <h2>檔案管理</h2>

    <!-- Toolbar -->
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px; flex-wrap:wrap;">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="(seg, i) in pathSegments" :key="i" @click="navigateTo(i)">
          <span style="cursor:pointer;">{{ seg || '根目錄' }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>
      <div style="flex:1;" />

      <!-- Always visible -->
      <el-button @click="loadFiles"><el-icon><Refresh /></el-icon>重新整理</el-button>
      <el-button type="primary" @click="mkdirDialogVisible = true"><el-icon><FolderAdd /></el-icon>新資料夾</el-button>
      <el-upload :action="uploadUrl" :headers="uploadHeaders" :data="{dest: currentPath}" :on-success="onUploadSuccess" :show-file-list="false" multiple>
        <el-button type="success"><el-icon><Upload /></el-icon>上傳</el-button>
      </el-upload>

      <!-- Clipboard paste -->
      <el-button v-if="clipboard.length > 0" type="warning" @click="pasteFiles"><el-icon><DocumentCopy /></el-icon>貼上 ({{ clipboard.length }})</el-button>

      <!-- Selection-based buttons -->
      <template v-if="selectedRows.length > 0">
        <el-button @click="openMoveDialog"><el-icon><Right /></el-icon>移動</el-button>
        <el-button @click="copyToClipboard"><el-icon><CopyDocument /></el-icon>複製</el-button>
        <el-button type="danger" @click="deleteSelected"><el-icon><Delete /></el-icon>刪除</el-button>
        <el-button @click="openCompressSelected"><el-icon><Files /></el-icon>壓縮</el-button>
        <el-button v-if="selectedRows.length === 1 && selectedRows[0].type === 'file'" @click="download(selectedRows[0])"><el-icon><Download /></el-icon>下載</el-button>
        <el-button v-if="hasArchiveSelected" type="info" @click="openExtractDialog"><el-icon><FolderOpened /></el-icon>解壓</el-button>
      </template>
    </div>

    <!-- File Table -->
    <el-table
      :data="items"
      v-loading="loading"
      stripe
      highlight-current-row
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="40" />
      <el-table-column prop="name" label="名稱" min-width="200">
        <template #default="{ row }">
          <div style="display:flex; align-items:center; gap:4px;">
            <el-icon v-if="row.type === 'dir'" style="color:#e6a23c;"><Folder /></el-icon>
            <el-icon v-else style="color:#909399;"><Document /></el-icon>
            <!-- Inline rename -->
            <el-input
              v-if="renamingRow === row"
              v-model="renameValue"
              size="small"
              style="width:200px;"
              @keyup.enter="submitRename(row)"
              @keyup.escape="cancelRename"
              @blur="submitRename(row)"
              ref="renameInputRef"
            />
            <span
              v-else
              style="cursor:pointer;"
              @click.stop="openPreview(row)"
              @dblclick.stop="startRename(row)"
            >{{ row.name }}</span>
          </div>
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

    <!-- Move Dialog -->
    <el-dialog v-model="moveDialogVisible" title="移動檔案" width="500px">
      <el-form label-width="100px">
        <el-form-item label="來源">
          <div>
            <el-tag v-for="f in moveFiles" :key="f" size="small" style="margin:2px;">{{ f }}</el-tag>
          </div>
        </el-form-item>
        <el-form-item label="目的路徑">
          <el-input v-model="moveDest" placeholder="例如 /data/backup" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="moveLoading" @click="submitMove">移動</el-button>
      </template>
    </el-dialog>

    <!-- Extract Dialog -->
    <el-dialog v-model="extractDialogVisible" title="解壓縮" width="500px">
      <el-form label-width="100px">
        <el-form-item label="壓縮檔">
          <el-input :model-value="extractArchive" disabled />
        </el-form-item>
        <el-form-item label="解壓到">
          <el-input v-model="extractDest" placeholder="目的資料夾路徑" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="extractDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="extractLoading" @click="submitExtract">解壓</el-button>
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

    <!-- Preview Drawer -->
    <el-drawer v-model="previewVisible" :title="previewFile?.name || '預覽'" size="45%" direction="rtl">
      <div v-loading="previewLoading" style="height:100%; overflow:auto; padding:12px;">
        <!-- Image -->
        <div v-if="previewType === 'image'" style="text-align:center;">
          <img :src="previewUrl" :alt="previewFile?.name" style="max-width:100%; max-height:80vh; object-fit:contain;" />
        </div>
        <!-- Video -->
        <div v-else-if="previewType === 'video'" style="text-align:center;">
          <video :src="previewUrl" controls style="max-width:100%; max-height:80vh;" />
        </div>
        <!-- PDF -->
        <div v-else-if="previewType === 'pdf'" style="height:100%;">
          <iframe :src="previewUrl" style="width:100%; height:calc(100vh - 120px); border:none;" />
        </div>
        <!-- Text/Code -->
        <div v-else-if="previewType === 'text'">
          <pre style="white-space:pre-wrap; word-break:break-all; font-size:13px; line-height:1.5; background:#f5f5f5; padding:12px; border-radius:4px; max-height:calc(100vh - 120px); overflow:auto;">{{ previewContent }}</pre>
        </div>
        <!-- File info -->
        <div v-else-if="previewType === 'info'">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="名稱">{{ previewInfo?.name }}</el-descriptions-item>
            <el-descriptions-item label="大小">{{ formatSize(previewInfo?.size || 0) }}</el-descriptions-item>
            <el-descriptions-item label="修改時間">{{ formatDate(previewInfo?.modified) }}</el-descriptions-item>
            <el-descriptions-item label="權限">{{ previewInfo?.permissions || '—' }}</el-descriptions-item>
            <el-descriptions-item label="擁有者">{{ previewInfo?.owner || '—' }}</el-descriptions-item>
            <el-descriptions-item label="類型">{{ previewInfo?.mime_type || '—' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const currentPath = ref('/home')
const items = ref([])
const loading = ref(false)
const mkdirDialogVisible = ref(false)
const newFolderName = ref('')

// Selection
const selectedRows = ref([])

// Clipboard (copy/paste)
const clipboard = ref([])

// Move
const moveDialogVisible = ref(false)
const moveLoading = ref(false)
const moveFiles = ref([])
const moveDest = ref('')

// Inline rename
const renamingRow = ref(null)
const renameValue = ref('')
const renameInputRef = ref(null)

// Extract
const extractDialogVisible = ref(false)
const extractLoading = ref(false)
const extractArchive = ref('')
const extractDest = ref('')

// Compress
const compressDialogVisible = ref(false)
const compressLoading = ref(false)
const compressForm = reactive({ paths: '', format: 'zip', dest: '' })

// Share
const shareDialogVisible = ref(false)
const shareLoading = ref(false)
const shareForm = reactive({ path: '', expires_hours: 24, password: '' })
const shareLink = ref('')

// Preview
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewFile = ref(null)
const previewType = ref('')
const previewUrl = ref('')
const previewContent = ref('')
const previewInfo = ref(null)

const pathSegments = computed(() => currentPath.value.split('/').filter(Boolean))

const uploadUrl = '/api/files/upload'
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
}))

// Archive detection
const archiveExtensions = ['.zip', '.tar.gz', '.tar', '.tgz', '.tar.bz2', '.tar.xz']
const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp']
const textExtensions = ['.txt', '.json', '.js', '.py', '.md', '.yml', '.yaml', '.sh', '.conf', '.log', '.css', '.html', '.xml', '.ts', '.vue']
const videoExtensions = ['.mp4', '.webm', '.mkv']

function getFileExtension(name) {
  if (!name) return ''
  const lower = name.toLowerCase()
  // Check multi-part extensions first
  if (lower.endsWith('.tar.gz')) return '.tar.gz'
  if (lower.endsWith('.tar.bz2')) return '.tar.bz2'
  if (lower.endsWith('.tar.xz')) return '.tar.xz'
  const dot = lower.lastIndexOf('.')
  return dot >= 0 ? lower.slice(dot) : ''
}

function isArchive(name) {
  const ext = getFileExtension(name)
  return archiveExtensions.includes(ext)
}

const hasArchiveSelected = computed(() => {
  return selectedRows.value.some(r => r.type === 'file' && isArchive(r.name))
})

function getFullPath(row) {
  return currentPath.value.replace(/\/$/, '') + '/' + row.name
}

// --- Selection ---
function onSelectionChange(rows) {
  selectedRows.value = rows
}

// --- Load ---
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
  const path = getFullPath(row)
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
    const path = getFullPath(row)
    await api.delete('/api/files/delete', { data: { path } })
    ElMessage.success('已刪除')
    loadFiles()
  } catch { /* cancelled or error handled */ }
}

async function deleteSelected() {
  if (selectedRows.value.length === 0) return
  try {
    await ElMessageBox.confirm(`確定要刪除已選取的 ${selectedRows.value.length} 個項目？此操作不可復原。`, '確認刪除', {
      confirmButtonText: '刪除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    for (const row of selectedRows.value) {
      const path = getFullPath(row)
      await api.delete('/api/files/delete', { data: { path } })
    }
    ElMessage.success('已刪除所選項目')
    loadFiles()
  } catch { /* cancelled */ }
}

function onUploadSuccess() {
  ElMessage.success('上傳完成')
  loadFiles()
}

function formatSize(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-TW')
}

// --- Move/Rename ---
function openMoveDialog() {
  moveFiles.value = selectedRows.value.map(r => getFullPath(r))
  moveDest.value = currentPath.value
  moveDialogVisible.value = true
}

async function submitMove() {
  if (!moveDest.value.trim()) {
    ElMessage.warning('請輸入目的路徑')
    return
  }
  moveLoading.value = true
  try {
    for (const src of moveFiles.value) {
      const fileName = src.split('/').pop()
      const dst = moveDest.value.replace(/\/$/, '') + '/' + fileName
      await api.post('/api/files/move', { src, dst })
    }
    ElMessage.success('移動完成')
    moveDialogVisible.value = false
    loadFiles()
  } catch { /* handled */ }
  finally { moveLoading.value = false }
}

function startRename(row) {
  renamingRow.value = row
  renameValue.value = row.name
  nextTick(() => {
    // Focus the input
    const input = document.querySelector('.el-table .el-input__inner')
    if (input) input.focus()
  })
}

function cancelRename() {
  renamingRow.value = null
  renameValue.value = ''
}

async function submitRename(row) {
  const newName = renameValue.value.trim()
  if (!newName || newName === row.name) {
    cancelRename()
    return
  }
  const src = getFullPath(row)
  const dst = currentPath.value.replace(/\/$/, '') + '/' + newName
  try {
    await api.post('/api/files/move', { src, dst })
    ElMessage.success('已重新命名')
    loadFiles()
  } catch { /* handled */ }
  finally { cancelRename() }
}

// --- Copy/Paste ---
function copyToClipboard() {
  clipboard.value = selectedRows.value.map(r => getFullPath(r))
  ElMessage.success(`已複製 ${clipboard.value.length} 個項目到剪貼簿`)
}

async function pasteFiles() {
  if (clipboard.value.length === 0) return
  try {
    for (const src of clipboard.value) {
      const fileName = src.split('/').pop()
      const dst = currentPath.value.replace(/\/$/, '') + '/' + fileName
      await api.post('/api/files/copy', { src, dst })
    }
    ElMessage.success('貼上完成')
    clipboard.value = []
    loadFiles()
  } catch { /* handled */ }
}

// --- Extract ---
function openExtractDialog() {
  const archiveRow = selectedRows.value.find(r => r.type === 'file' && isArchive(r.name))
  if (!archiveRow) return
  extractArchive.value = getFullPath(archiveRow)
  extractDest.value = currentPath.value
  extractDialogVisible.value = true
}

async function submitExtract() {
  if (!extractDest.value.trim()) {
    ElMessage.warning('請輸入解壓目的路徑')
    return
  }
  extractLoading.value = true
  try {
    await api.post('/api/files/extract', { archive: extractArchive.value, dest: extractDest.value })
    ElMessage.success('解壓完成')
    extractDialogVisible.value = false
    loadFiles()
  } catch { /* handled */ }
  finally { extractLoading.value = false }
}

// --- Compress (from selection) ---
function openCompressSelected() {
  const paths = selectedRows.value.map(r => getFullPath(r))
  compressForm.paths = paths.join(', ')
  compressForm.dest = currentPath.value.replace(/\/$/, '') + '/archive.zip'
  compressForm.format = 'zip'
  compressDialogVisible.value = true
}

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

// --- Share ---
function openShareDialog(row) {
  shareForm.path = getFullPath(row)
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

// --- Preview ---
function getPreviewType(name) {
  const ext = getFileExtension(name)
  if (imageExtensions.includes(ext)) return 'image'
  if (videoExtensions.includes(ext)) return 'video'
  if (ext === '.pdf') return 'pdf'
  if (textExtensions.includes(ext)) return 'text'
  return 'info'
}

async function openPreview(row) {
  if (row.type === 'dir') {
    // Navigate into directory on click
    currentPath.value = currentPath.value.replace(/\/$/, '') + '/' + row.name
    loadFiles()
    return
  }

  previewFile.value = row
  const path = getFullPath(row)
  const token = localStorage.getItem('token')
  const type = getPreviewType(row.name)
  previewType.value = type
  previewContent.value = ''
  previewInfo.value = null
  previewUrl.value = ''
  previewLoading.value = true
  previewVisible.value = true

  try {
    if (type === 'image' || type === 'video' || type === 'pdf') {
      previewUrl.value = `/api/files/download?path=${encodeURIComponent(path)}&token=${token}`
    } else if (type === 'text') {
      // Fetch as text (limit 100KB check done on display)
      const res = await api.get('/api/files/download', {
        params: { path },
        responseType: 'blob',
      })
      // Check size
      if (res.data.size > 100 * 1024) {
        const sliced = res.data.slice(0, 100 * 1024)
        previewContent.value = await sliced.text() + '\n\n... (檔案超過 100KB，僅顯示部分內容)'
      } else {
        previewContent.value = await res.data.text()
      }
    } else {
      // File info
      const res = await api.get('/api/files/info', { params: { path } })
      previewInfo.value = res.data
    }
  } catch {
    ElMessage.error('無法載入預覽')
  } finally {
    previewLoading.value = false
  }
}

onMounted(loadFiles)
</script>
