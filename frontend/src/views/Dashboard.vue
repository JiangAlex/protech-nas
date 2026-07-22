<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <h2 style="margin:0;">系統儀表板</h2>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:12px; color:#67c23a;">● 即時</span>
        <el-switch v-model="autoRefresh" active-text="自動刷新" />
      </div>
    </div>
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

    <!-- History Chart -->
    <el-card style="margin-top:20px;" shadow="hover" v-if="historyData.length > 0">
      <template #header>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span>歷史趨勢（24 小時）</span>
          <el-button size="small" @click="loadHistory">重新整理</el-button>
        </div>
      </template>
      <v-chart :option="chartOption" style="height:280px;" autoresize />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import api from '../api'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const info = ref(null)
const autoRefresh = ref(true)
let timer = null

// History chart
const historyData = ref([])

const chartOption = computed(() => {
  const timestamps = historyData.value.map(d => d.timestamp?.substring(11, 16) || '')
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['CPU %', '記憶體 %'] },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: timestamps },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      { name: 'CPU %', type: 'line', smooth: true, data: historyData.value.map(d => d.cpu_percent) },
      { name: '記憶體 %', type: 'line', smooth: true, data: historyData.value.map(d => d.memory_percent) },
    ],
  }
})

async function loadHistory() {
  try {
    const res = await api.get('/api/dashboard/history', { params: { hours: 24 } })
    historyData.value = res.data.data || []
  } catch { /* handled */ }
}

const progressColor = [
  { color: '#67c23a', percentage: 50 },
  { color: '#e6a23c', percentage: 80 },
  { color: '#f56c6c', percentage: 100 },
]

async function fetchData() {
  try {
    const res = await api.get('/api/dashboard')
    info.value = res.data
  } catch { /* handled by interceptor */ }
}

function startTimer() {
  stopTimer()
  timer = setInterval(fetchData, 5000)
}

function stopTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(autoRefresh, (val) => {
  if (val) startTimer()
  else stopTimer()
})

onMounted(() => {
  fetchData()
  loadHistory()
  if (autoRefresh.value) startTimer()
})

onUnmounted(stopTimer)
</script>
