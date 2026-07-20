<template>
  <div>
    <h2>儲存管理</h2>
    <el-tabs>
      <el-tab-pane label="磁碟">
        <el-table :data="disks" stripe>
          <el-table-column prop="name" label="裝置" />
          <el-table-column prop="size" label="大小" />
          <el-table-column prop="type" label="類型" />
          <el-table-column prop="fstype" label="檔案系統" />
          <el-table-column prop="mountpoint" label="掛載點" />
          <el-table-column prop="model" label="型號" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="掛載">
        <el-table :data="mounts" stripe>
          <el-table-column prop="device" label="裝置" />
          <el-table-column prop="mount_point" label="掛載點" />
          <el-table-column prop="fstype" label="檔案系統" />
          <el-table-column prop="size" label="大小" />
          <el-table-column prop="used" label="已用" />
          <el-table-column prop="use_percent" label="使用率" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="RAID">
        <pre style="background:#f5f5f5;padding:16px;border-radius:4px;">{{ raid }}</pre>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const disks = ref([])
const mounts = ref([])
const raid = ref('')

onMounted(async () => {
  const [d, m, r] = await Promise.all([
    api.get('/api/storage/disks'),
    api.get('/api/storage/mounts'),
    api.get('/api/storage/raid'),
  ])
  disks.value = d.data.devices || []
  mounts.value = m.data.mounts || []
  raid.value = r.data.mdstat || 'N/A'
})
</script>
