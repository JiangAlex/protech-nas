<template>
  <div>
    <h2>備份管理</h2>
    <el-button type="primary" @click="createDialogVisible = true" style="margin-bottom:12px;">建立備份任務</el-button>

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
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" size="small" :loading="runningId === row.id" @click="runTask(row.id)">執行</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Task Dialog -->
    <el-dialog v-model="createDialogVisible" title="建立備份任務" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="任務名稱" required>
          <el-input v-model="form.name" placeholder="每日備份" />
        </el-form-item>
        <el-form-item label="來源路徑" required>
          <el-input v-model="form.source" placeholder="/data" />
        </el-form-item>
        <el-form-item label="目的地" required>
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
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="createTask">建立</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const tasks = ref([])
const loading = ref(false)
const createDialogVisible = ref(false)
const createLoading = ref(false)
const runningId = ref(null)
const form = reactive({ name: '', source: '', destination: '', schedule: '', retention_days: 30 })

async function loadTasks() {
  loading.value = true
  try {
    const res = await api.get('/api/backup/tasks')
    tasks.value = res.data.tasks || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function createTask() {
  if (!form.name || !form.source || !form.destination) {
    ElMessage.warning('請填寫必要欄位')
    return
  }
  createLoading.value = true
  try {
    await api.post('/api/backup/tasks', form)
    ElMessage.success('備份任務已建立')
    createDialogVisible.value = false
    form.name = ''; form.source = ''; form.destination = ''; form.schedule = ''
    loadTasks()
  } catch { /* handled */ }
  finally { createLoading.value = false }
}

async function runTask(taskId) {
  runningId.value = taskId
  try {
    const res = await api.post(`/api/backup/tasks/${taskId}/run`)
    ElMessage.success(`備份完成！耗時 ${res.data.duration_sec}s，${res.data.files_transferred} 個檔案`)
    loadTasks()
  } catch { /* handled */ }
  finally { runningId.value = null }
}

onMounted(loadTasks)
</script>
