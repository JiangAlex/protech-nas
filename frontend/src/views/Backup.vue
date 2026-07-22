<template>
  <div>
    <h2>備份管理</h2>
    <el-button type="primary" @click="openCreateDialog" style="margin-bottom:12px;">建立備份任務</el-button>

    <el-table :data="tasks" stripe v-loading="loading">
      <el-table-column prop="name" label="任務名稱" />
      <el-table-column prop="source" label="來源" />
      <el-table-column prop="destination" label="目的地" />
      <el-table-column prop="schedule" label="排程" width="120">
        <template #default="{ row }">{{ row.schedule || '手動' }}</template>
      </el-table-column>
      <el-table-column prop="last_status" label="狀態" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.last_status === 'success'" type="success" size="small">成功</el-tag>
          <el-tag v-else-if="row.last_status === 'failed'" type="danger" size="small">失敗</el-tag>
          <el-tag v-else type="info" size="small">未執行</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280">
        <template #default="{ row }">
          <el-button type="primary" size="small" :loading="runningId === row.id" @click="runTask(row.id)">執行</el-button>
          <el-button type="warning" size="small" @click="openEditDialog(row)">編輯</el-button>
          <el-button size="small" @click="openHistory(row)">歷史</el-button>
          <el-button type="danger" size="small" @click="deleteTask(row)">刪除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Snapshots Section -->
    <div style="margin-top:32px;">
      <h3>Btrfs 快照</h3>
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <el-button type="primary" @click="snapshotDialogVisible = true">建立快照</el-button>
        <el-button @click="loadSnapshots">重新整理</el-button>
      </div>
      <el-table :data="snapshots" stripe v-loading="snapshotsLoading" size="small">
        <el-table-column prop="path" label="快照路徑" />
        <el-table-column prop="created" label="建立時間" width="180" />
        <el-table-column prop="size" label="大小" width="100" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button type="danger" size="small" @click="deleteSnapshot(row.path)">刪除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Snapshot Create Dialog -->
    <el-dialog v-model="snapshotDialogVisible" title="建立 Btrfs 快照" width="400px">
      <el-form label-width="100px">
        <el-form-item label="來源路徑">
          <el-input v-model="snapshotSubvol" placeholder="/data" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="snapshotDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="snapshotCreating" @click="createSnapshot">建立</el-button>
      </template>
    </el-dialog>

    <!-- Create/Edit Task Dialog -->
    <el-dialog v-model="taskDialogVisible" :title="isEditing ? '編輯備份任務' : '建立備份任務'" width="500px">
      <el-form ref="taskFormRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="任務名稱" prop="name">
          <el-input v-model="form.name" placeholder="每日備份" />
        </el-form-item>
        <el-form-item label="來源路徑" prop="source">
          <el-input v-model="form.source" placeholder="/data" />
        </el-form-item>
        <el-form-item label="目的地" prop="destination">
          <el-input v-model="form.destination" placeholder="/backup/daily" />
        </el-form-item>
        <el-form-item label="排程">
          <el-input v-model="form.schedule" placeholder="0 2 * * * (cron 格式，留空為手動)" />
        </el-form-item>
        <el-form-item label="保留天數">
          <el-input-number v-model="form.retention_days" :min="1" :max="365" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="saveTask">{{ isEditing ? '儲存' : '建立' }}</el-button>
      </template>
    </el-dialog>

    <!-- Task History Drawer -->
    <el-drawer v-model="historyDrawerVisible" :title="`備份歷史 — ${historyTaskName}`" size="60%">
      <el-table :data="historyList" stripe v-loading="historyLoading">
        <el-table-column prop="timestamp" label="時間" width="180" />
        <el-table-column prop="status" label="狀態" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.status === 'success'" type="success" size="small">成功</el-tag>
            <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失敗</el-tag>
            <el-tag v-else type="info" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_sec" label="耗時 (秒)" width="100" />
        <el-table-column prop="size_mb" label="大小 (MB)" width="100" />
        <el-table-column prop="error" label="錯誤訊息" show-overflow-tooltip />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'success'"
              type="warning"
              size="small"
              @click="openRestoreDialog(row)"
            >還原</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- Restore Dialog -->
    <el-dialog v-model="restoreDialogVisible" title="還原備份" width="450px">
      <el-form :model="restoreForm" label-width="100px">
        <el-form-item label="版本">
          <el-input :model-value="restoreForm.version" disabled />
        </el-form-item>
        <el-form-item label="還原路徑">
          <el-input v-model="restoreForm.target_path" placeholder="留空則還原至原始位置" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="restoreDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="restoreLoading" @click="doRestore">確認還原</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

// Task list
const tasks = ref([])
const loading = ref(false)
const runningId = ref(null)

// Create/Edit dialog
const taskDialogVisible = ref(false)
const isEditing = ref(false)
const editingTaskId = ref(null)
const saveLoading = ref(false)
const taskFormRef = ref(null)
const form = reactive({ name: '', source: '', destination: '', schedule: '', retention_days: 30 })
const formRules = {
  name: [{ required: true, message: '請輸入任務名稱', trigger: 'blur' }],
  source: [{ required: true, message: '請輸入來源路徑', trigger: 'blur' }],
  destination: [{ required: true, message: '請輸入目的地', trigger: 'blur' }],
}

// History
const historyDrawerVisible = ref(false)
const historyLoading = ref(false)
const historyTaskName = ref('')
const historyTaskId = ref(null)
const historyList = ref([])

// Restore
const restoreDialogVisible = ref(false)
const restoreLoading = ref(false)
const restoreForm = reactive({ task_id: null, version: '', target_path: '' })

// Snapshots
const snapshots = ref([])
const snapshotsLoading = ref(false)
const snapshotDialogVisible = ref(false)
const snapshotCreating = ref(false)
const snapshotSubvol = ref('/data')

// --- Load tasks ---
async function loadTasks() {
  loading.value = true
  try {
    const res = await api.get('/api/backup/tasks')
    tasks.value = res.data.tasks || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

// --- Create dialog ---
function openCreateDialog() {
  isEditing.value = false
  editingTaskId.value = null
  form.name = ''
  form.source = ''
  form.destination = ''
  form.schedule = ''
  form.retention_days = 30
  taskDialogVisible.value = true
}

// --- Edit dialog ---
function openEditDialog(row) {
  isEditing.value = true
  editingTaskId.value = row.id
  form.name = row.name
  form.source = row.source
  form.destination = row.destination
  form.schedule = row.schedule || ''
  form.retention_days = row.retention_days || 30
  taskDialogVisible.value = true
}

// --- Save (create or update) ---
async function saveTask() {
  const valid = await taskFormRef.value.validate().catch(() => false)
  if (!valid) return
  saveLoading.value = true
  try {
    const body = {
      name: form.name,
      source: form.source,
      destination: form.destination,
      schedule: form.schedule,
      retention_days: form.retention_days,
    }
    if (isEditing.value) {
      await api.put(`/api/backup/tasks/${editingTaskId.value}`, body)
      ElMessage.success('備份任務已更新')
    } else {
      await api.post('/api/backup/tasks', body)
      ElMessage.success('備份任務已建立')
    }
    taskDialogVisible.value = false
    loadTasks()
  } catch { /* handled */ }
  finally { saveLoading.value = false }
}

// --- Delete task ---
async function deleteTask(row) {
  try {
    await ElMessageBox.confirm(`確定要刪除任務「${row.name}」？此操作無法復原。`, '確認刪除', { type: 'warning' })
  } catch { return }
  try {
    await api.delete(`/api/backup/tasks/${row.id}`)
    ElMessage.success('任務已刪除')
    loadTasks()
  } catch { /* handled */ }
}

// --- Run task ---
async function runTask(taskId) {
  runningId.value = taskId
  try {
    const res = await api.post(`/api/backup/tasks/${taskId}/run`)
    ElMessage.success(`備份完成！耗時 ${res.data.duration_sec}s，${res.data.files_transferred} 個檔案`)
    loadTasks()
  } catch { /* handled */ }
  finally { runningId.value = null }
}

// --- History ---
async function openHistory(row) {
  historyTaskId.value = row.id
  historyTaskName.value = row.name
  historyList.value = []
  historyDrawerVisible.value = true
  historyLoading.value = true
  try {
    const res = await api.get(`/api/backup/tasks/${row.id}/history`)
    historyList.value = res.data.history || []
  } catch { /* handled */ }
  finally { historyLoading.value = false }
}

// --- Restore ---
function openRestoreDialog(historyRow) {
  restoreForm.task_id = historyTaskId.value
  restoreForm.version = historyRow.run_id || historyRow.timestamp
  restoreForm.target_path = ''
  restoreDialogVisible.value = true
}

async function doRestore() {
  try {
    await ElMessageBox.confirm('確定要執行還原？目標路徑中的現有檔案可能被覆蓋。', '確認還原', { type: 'warning' })
  } catch { return }
  restoreLoading.value = true
  try {
    const res = await api.post('/api/backup/restore', {
      task_id: restoreForm.task_id,
      version: restoreForm.version,
      target_path: restoreForm.target_path,
    })
    ElMessage.success(`還原成功！路徑：${res.data.restored_to}，共 ${res.data.files_count} 個檔案`)
    restoreDialogVisible.value = false
  } catch { /* handled */ }
  finally { restoreLoading.value = false }
}

// --- Snapshots ---
async function loadSnapshots() {
  snapshotsLoading.value = true
  try {
    const res = await api.get('/api/backup/snapshots')
    snapshots.value = res.data.snapshots || []
  } catch { /* handled */ }
  finally { snapshotsLoading.value = false }
}

async function createSnapshot() {
  if (!snapshotSubvol.value) { ElMessage.warning('請輸入來源路徑'); return }
  snapshotCreating.value = true
  try {
    const res = await api.post('/api/backup/snapshots', { subvol: snapshotSubvol.value })
    ElMessage.success(`快照已建立：${res.data.snapshot_path}`)
    snapshotDialogVisible.value = false
    loadSnapshots()
  } catch { /* handled */ }
  finally { snapshotCreating.value = false }
}

async function deleteSnapshot(path) {
  await ElMessageBox.confirm(`確定刪除快照「${path}」？此操作不可復原。`, '確認', { type: 'warning' })
  try {
    await api.delete('/api/backup/snapshots', { data: { path } })
    ElMessage.success('快照已刪除')
    loadSnapshots()
  } catch { /* handled */ }
}

onMounted(() => { loadTasks(); loadSnapshots() })
</script>
