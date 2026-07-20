<template>
  <div>
    <h2>Docker 容器管理</h2>
    <el-table :data="containers" stripe>
      <el-table-column prop="name" label="名稱" />
      <el-table-column prop="image" label="映像" />
      <el-table-column prop="status" label="狀態">
        <template #default="{ row }">
          <el-tag :type="row.state === 'running' ? 'success' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button v-if="row.state !== 'running'" type="success" size="small" @click="start(row.id)">啟動</el-button>
          <el-button v-if="row.state === 'running'" type="warning" size="small" @click="stop(row.id)">停止</el-button>
          <el-button size="small" @click="showLogs(row.id, row.name)">日誌</el-button>
          <el-button type="danger" size="small" @click="remove(row.id)">刪除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h3 style="margin-top:24px;">映像</h3>
    <el-table :data="images" stripe>
      <el-table-column prop="tags" label="標籤" />
      <el-table-column prop="size_mb" label="大小 (MB)" />
    </el-table>

    <!-- Log Dialog -->
    <el-dialog v-model="logVisible" :title="'日誌 — ' + logName" width="70%">
      <pre style="max-height:400px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:4px;font-size:12px;">{{ logs }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const containers = ref([])
const images = ref([])
const logVisible = ref(false)
const logName = ref('')
const logs = ref('')

async function loadData() {
  const [c, i] = await Promise.all([api.get('/api/docker/containers'), api.get('/api/docker/images')])
  containers.value = c.data.containers || []
  images.value = i.data.images || []
}

async function start(id) { await api.post(`/api/docker/containers/${id}/start`); ElMessage.success('已啟動'); loadData() }
async function stop(id) { await api.post(`/api/docker/containers/${id}/stop`); ElMessage.success('已停止'); loadData() }
async function remove(id) { await api.delete(`/api/docker/containers/${id}`, { params: { force: true } }); ElMessage.success('已刪除'); loadData() }

async function showLogs(id, name) {
  logName.value = name
  const res = await api.get(`/api/docker/containers/${id}/logs`)
  logs.value = res.data.logs || 'No logs'
  logVisible.value = true
}

onMounted(loadData)
</script>
