<template>
  <div>
    <h2>系統儀表板</h2>
    <el-row :gutter="16" v-if="info">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>CPU</template>
          <el-progress type="dashboard" :percentage="info.cpu.percent" :color="progressColor" />
          <p style="text-align:center;">{{ info.cpu.cores }} 核心 / {{ info.cpu.freq_mhz }} MHz</p>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>記憶體</template>
          <el-progress type="dashboard" :percentage="info.memory.percent" :color="progressColor" />
          <p style="text-align:center;">{{ info.memory.used_gb }} / {{ info.memory.total_gb }} GB</p>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>磁碟</template>
          <el-progress type="dashboard" :percentage="info.disk.percent" :color="progressColor" />
          <p style="text-align:center;">{{ info.disk.used_gb }} / {{ info.disk.total_gb }} GB</p>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>系統資訊</template>
          <p><strong>主機：</strong>{{ info.hostname }}</p>
          <p><strong>OS：</strong>{{ info.os }}</p>
          <p><strong>運行時間：</strong>{{ info.uptime }}</p>
          <p><strong>網路 ↑：</strong>{{ info.network.bytes_sent_mb }} MB</p>
          <p><strong>網路 ↓：</strong>{{ info.network.bytes_recv_mb }} MB</p>
        </el-card>
      </el-col>
    </el-row>
    <el-skeleton v-else :rows="4" animated />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const info = ref(null)

const progressColor = [
  { color: '#67c23a', percentage: 50 },
  { color: '#e6a23c', percentage: 80 },
  { color: '#f56c6c', percentage: 100 },
]

onMounted(async () => {
  const res = await api.get('/api/dashboard')
  info.value = res.data
})
</script>
