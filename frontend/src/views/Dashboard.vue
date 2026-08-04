<template>
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
      <h2 style="margin:0;">系統儀表板</h2>
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:12px; color:#67c23a;">● 即時</span>
        <el-switch v-model="autoRefresh" active-text="自動刷新" />
      </div>
    </div>

    <!-- ═══ 區塊一：核心硬件數據 ═══ -->
    <h3 style="margin:0 0 12px 0; color:#606266;">核心硬件數據</h3>
    <el-row :gutter="16" v-if="info">
      <!-- CPU -->
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <template #header>CPU</template>
          <el-progress type="dashboard" :percentage="info.cpu.percent" :color="progressColor" />
          <p style="text-align:center; margin:8px 0 0;">{{ info.cpu.cores }} 核心 / {{ info.cpu.freq_mhz }} MHz</p>
        </el-card>
      </el-col>
      <!-- 記憶體 -->
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <template #header>記憶體</template>
          <el-progress type="dashboard" :percentage="info.memory.percent" :color="progressColor" />
          <p style="text-align:center; margin:8px 0 0;">{{ info.memory.used_gb }} / {{ info.memory.total_gb }} GB</p>
        </el-card>
      </el-col>
      <!-- 網路速率 -->
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <template #header>網路速率</template>
          <div style="text-align:center; padding:16px 0;">
            <div style="margin-bottom:12px;">
              <span style="color:#67c23a; font-size:20px;">↑</span>
              <span style="font-size:24px; font-weight:bold;">{{ formatRate(info.network.upload_kb_s) }}</span>
            </div>
            <div>
              <span style="color:#409eff; font-size:20px;">↓</span>
              <span style="font-size:24px; font-weight:bold;">{{ formatRate(info.network.download_kb_s) }}</span>
            </div>
          </div>
          <p style="text-align:center; font-size:12px; color:#909399; margin:0;">
            累計 ↑{{ info.network.bytes_sent_mb }} MB / ↓{{ info.network.bytes_recv_mb }} MB
          </p>
        </el-card>
      </el-col>
      <!-- 磁碟 IO -->
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover">
          <template #header>磁碟 I/O</template>
          <div style="text-align:center; padding:16px 0;">
            <div style="margin-bottom:12px;">
              <span style="color:#e6a23c; font-size:16px;">讀取</span>
              <span style="font-size:24px; font-weight:bold; margin-left:8px;">{{ formatRate(info.disk_io.read_kb_s) }}</span>
            </div>
            <div>
              <span style="color:#f56c6c; font-size:16px;">寫入</span>
              <span style="font-size:24px; font-weight:bold; margin-left:8px;">{{ formatRate(info.disk_io.write_kb_s) }}</span>
            </div>
          </div>
          <el-progress :percentage="info.disk.percent" :color="progressColor" :stroke-width="10" style="margin-top:8px;" />
          <p style="text-align:center; font-size:12px; color:#909399; margin:4px 0 0;">
            {{ info.disk.used_gb }} / {{ info.disk.total_gb }} GB
          </p>
        </el-card>
      </el-col>
    </el-row>
    <el-skeleton v-else :rows="4" animated />

    <!-- ═══ 區塊二：系統與服務狀態 ═══ -->
    <h3 style="margin:20px 0 12px 0; color:#606266;">系統與服務狀態</h3>
    <el-row :gutter="16" v-if="info">
      <!-- RAID 狀態 -->
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover">
          <template #header>RAID 陣列</template>
          <div v-if="info.raid">
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="陣列">{{ info.raid.array }}</el-descriptions-item>
              <el-descriptions-item label="等級">{{ info.raid.level }}</el-descriptions-item>
              <el-descriptions-item label="狀態">
                <el-tag :type="info.raid.degraded ? 'danger' : 'success'" size="small">
                  {{ info.raid.degraded ? '降級' : '正常' }} [{{ info.raid.health }}]
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="裝置">{{ info.raid.active_devices }} / {{ info.raid.total_devices }}</el-descriptions-item>
            </el-descriptions>
            <div v-if="info.raid.rebuild" style="margin-top:8px;">
              <el-progress :percentage="Math.round(info.raid.rebuild.percent)" status="warning" :stroke-width="12" />
              <p style="font-size:12px; color:#e6a23c; margin:4px 0 0;">重建中，預計 {{ Math.round(info.raid.rebuild.finish_min) }} 分鐘</p>
            </div>
          </div>
          <div v-else style="color:#909399; text-align:center; padding:20px 0;">
            無 RAID 陣列
          </div>
        </el-card>
      </el-col>

      <!-- 溫度 -->
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span>溫度監控</span>
              <span v-if="fans.length > 0" style="font-size:12px; color:#909399;">🌀 {{ fans.length }} 風扇</span>
            </div>
          </template>
          <div v-if="Object.keys(filteredTemps).length > 0">
            <div v-for="(temp, label) in filteredTemps" :key="label" style="margin-bottom:8px;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-size:13px;">{{ label }}</span>
                <span :style="{ color: temp.current > 70 ? '#f56c6c' : temp.current > 50 ? '#e6a23c' : '#67c23a', fontWeight: 'bold' }">
                  {{ temp.current }}°C
                </span>
              </div>
              <el-progress
                :percentage="Math.min(100, Math.round((temp.current / (temp.critical || 100)) * 100))"
                :color="temp.current > 70 ? '#f56c6c' : temp.current > 50 ? '#e6a23c' : '#67c23a'"
                :stroke-width="6"
                :show-text="false"
              />
            </div>
          </div>
          <div v-else style="color:#909399; text-align:center; padding:20px 0;">
            未偵測到溫度感測器<br><span style="font-size:12px;">安裝 lm-sensors 啟用</span>
          </div>

          <!-- Fan Control -->
          <div v-if="fans.length > 0" style="margin-top:16px; border-top:1px solid #ebeef5; padding-top:12px;">
            <h4 style="margin:0 0 8px 0; font-size:13px; color:#606266;">風扇控制</h4>
            <div v-for="fan in fans" :key="fan.id" style="margin-bottom:12px;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span style="font-size:12px;">風扇 {{ fan.id }}</span>
                <span style="font-size:12px; color:#909399;">{{ fan.rpm }} RPM
                  <el-tag :type="fan.mode === 'auto' ? 'success' : fan.mode === 'manual' ? 'warning' : 'info'" size="small" style="margin-left:4px;">{{ fan.mode === 'auto' ? '自動' : fan.mode === 'manual' ? '手動' : fan.mode }}</el-tag>
                </span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <el-slider v-model="fan.percent" :min="0" :max="100" :step="5" style="flex:1;" :disabled="fan.mode === 'auto'" @change="setFanSpeed(fan.id, fan.percent)" />
                <el-button v-if="fan.mode !== 'auto'" size="small" @click="setFanAuto(fan.id)">自動</el-button>
                <el-button v-else size="small" type="warning" @click="setFanSpeed(fan.id, fan.percent)">手動</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- Docker -->
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span>Docker 容器</span>
              <el-tag size="small" type="info">{{ info.docker.total }} 個</el-tag>
            </div>
          </template>
          <div v-if="info.docker.total > 0">
            <div style="display:flex; gap:16px; margin-bottom:12px;">
              <div style="text-align:center;">
                <div style="font-size:24px; font-weight:bold; color:#67c23a;">{{ info.docker.running }}</div>
                <div style="font-size:12px; color:#909399;">運行中</div>
              </div>
              <div style="text-align:center;">
                <div style="font-size:24px; font-weight:bold; color:#909399;">{{ info.docker.stopped }}</div>
                <div style="font-size:12px; color:#909399;">已停止</div>
              </div>
            </div>
            <div v-for="c in info.docker.containers.slice(0, 5)" :key="c.name"
                 style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px solid #f0f0f0;">
              <span style="font-size:12px; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{{ c.name }}</span>
              <el-tag :type="c.running ? 'success' : 'info'" size="small">{{ c.running ? '運行' : '停止' }}</el-tag>
            </div>
            <p v-if="info.docker.total > 5" style="font-size:12px; color:#909399; margin:8px 0 0; text-align:center;">
              ... 還有 {{ info.docker.total - 5 }} 個容器
            </p>
          </div>
          <div v-else style="color:#909399; text-align:center; padding:20px 0;">
            無 Docker 容器
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系統資訊 -->
    <el-row :gutter="16" style="margin-top:16px;" v-if="info">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>系統資訊</template>
          <el-descriptions :column="4" border size="small">
            <el-descriptions-item label="主機名稱">{{ info.hostname }}</el-descriptions-item>
            <el-descriptions-item label="作業系統">{{ info.os }}</el-descriptions-item>
            <el-descriptions-item label="架構">{{ info.arch }}</el-descriptions-item>
            <el-descriptions-item label="運行時間">{{ info.uptime }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

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
import { ElMessage } from 'element-plus'
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

// Fans
const fans = ref([])

// Filter out invalid temperature readings
const filteredTemps = computed(() => {
  const temps = info.value?.temperatures || {}
  const result = {}
  for (const [label, temp] of Object.entries(temps)) {
    if (temp.current > -40 && temp.current < 120) {
      result[label] = temp
    }
  }
  return result
})

async function loadFans() {
  try {
    const res = await api.get('/api/system/fans')
    fans.value = res.data.fans || []
  } catch { /* no fan support */ }
}

async function setFanSpeed(fanId, percent) {
  try {
    await api.post('/api/system/fans/speed', { fan_id: fanId, percent })
    ElMessage.success(`風扇 ${fanId} 設定為 ${percent}%`)
    loadFans()
  } catch { /* handled */ }
}

async function setFanAuto(fanId) {
  try {
    await api.post('/api/system/fans/auto', { fan_id: fanId })
    ElMessage.success(`風扇 ${fanId} 切回自動模式`)
    loadFans()
  } catch { /* handled */ }
}

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

function formatRate(kb) {
  if (kb == null) return '0 KB/s'
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB/s`
  return `${Math.round(kb)} KB/s`
}

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
  loadFans()
  if (autoRefresh.value) startTimer()
})

onUnmounted(stopTimer)
</script>
