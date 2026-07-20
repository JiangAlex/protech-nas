<template>
  <div>
    <h2>檔案共享管理</h2>
    <el-tabs>
      <el-tab-pane label="SMB 共享">
        <el-button type="primary" @click="smbDialogVisible = true" style="margin-bottom:12px;">新增 SMB 共享</el-button>
        <el-table :data="smbShares" stripe>
          <el-table-column prop="name" label="名稱" />
          <el-table-column prop="path" label="路徑" />
          <el-table-column prop="comment" label="說明" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteSMB(row.name)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="NFS 匯出">
        <el-button type="primary" @click="nfsDialogVisible = true" style="margin-bottom:12px;">新增 NFS 匯出</el-button>
        <el-table :data="nfsExports" stripe>
          <el-table-column prop="path" label="路徑" />
          <el-table-column prop="clients" label="客戶端" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteNFS(row.path)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- SMB Dialog -->
    <el-dialog v-model="smbDialogVisible" title="新增 SMB 共享">
      <el-form :model="smbForm" label-width="80px">
        <el-form-item label="名稱"><el-input v-model="smbForm.name" /></el-form-item>
        <el-form-item label="路徑"><el-input v-model="smbForm.path" /></el-form-item>
        <el-form-item label="說明"><el-input v-model="smbForm.comment" /></el-form-item>
        <el-form-item label="唯讀"><el-switch v-model="smbForm.read_only" /></el-form-item>
        <el-form-item label="訪客"><el-switch v-model="smbForm.guest_ok" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="smbDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addSMB">確認</el-button>
      </template>
    </el-dialog>

    <!-- NFS Dialog -->
    <el-dialog v-model="nfsDialogVisible" title="新增 NFS 匯出">
      <el-form :model="nfsForm" label-width="80px">
        <el-form-item label="路徑"><el-input v-model="nfsForm.path" /></el-form-item>
        <el-form-item label="客戶端"><el-input v-model="nfsForm.clients" placeholder="192.168.1.0/24(rw,sync)" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nfsDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addNFS">確認</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const smbShares = ref([])
const nfsExports = ref([])
const smbDialogVisible = ref(false)
const nfsDialogVisible = ref(false)
const smbForm = reactive({ name: '', path: '', comment: '', read_only: false, guest_ok: false })
const nfsForm = reactive({ path: '', clients: '' })

async function loadData() {
  const [s, n] = await Promise.all([api.get('/api/shares/smb'), api.get('/api/shares/nfs')])
  smbShares.value = s.data.shares || []
  nfsExports.value = n.data.exports || []
}

async function addSMB() {
  await api.post('/api/shares/smb', smbForm)
  ElMessage.success('SMB 共享已建立')
  smbDialogVisible.value = false
  loadData()
}

async function deleteSMB(name) {
  await api.delete(`/api/shares/smb/${name}`)
  ElMessage.success('已刪除')
  loadData()
}

async function addNFS() {
  await api.post('/api/shares/nfs', nfsForm)
  ElMessage.success('NFS 匯出已建立')
  nfsDialogVisible.value = false
  loadData()
}

async function deleteNFS(path) {
  await api.delete('/api/shares/nfs', { params: { path } })
  ElMessage.success('已刪除')
  loadData()
}

onMounted(loadData)
</script>
