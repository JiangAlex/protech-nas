<template>
  <div>
    <h2>網路管理</h2>
    <el-tabs>
      <!-- Interfaces Tab -->
      <el-tab-pane label="網路介面">
        <el-button @click="loadData" style="margin-bottom:12px;">重新整理</el-button>
        <el-table :data="interfaces" stripe v-loading="loading">
          <el-table-column prop="name" label="介面" width="120" />
          <el-table-column prop="ipv4" label="IPv4">
            <template #default="{ row }">{{ row.ipv4 || '—' }}</template>
          </el-table-column>
          <el-table-column prop="mac" label="MAC 位址" width="180" />
          <el-table-column prop="status" label="狀態" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'up' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="speed_mbps" label="速率" width="100">
            <template #default="{ row }">{{ row.speed_mbps ? row.speed_mbps + ' Mbps' : '—' }}</template>
          </el-table-column>
          <el-table-column prop="mtu" label="MTU" width="80" />
        </el-table>
      </el-tab-pane>

      <!-- Diagnostics Tab -->
      <el-tab-pane label="診斷工具">
        <el-row :gutter="16">
          <!-- Ping -->
          <el-col :span="8">
            <el-card header="Ping">
              <el-input v-model="diagPing.host" placeholder="主機或 IP" style="margin-bottom:8px;">
                <template #append>
                  <el-button :loading="diagPing.loading" @click="runPing">執行</el-button>
                </template>
              </el-input>
              <pre style="max-height:300px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:8px;border-radius:4px;font-size:12px;white-space:pre-wrap;">{{ diagPing.result || '結果將顯示在這裡' }}</pre>
            </el-card>
          </el-col>

          <!-- Traceroute -->
          <el-col :span="8">
            <el-card header="Traceroute">
              <el-input v-model="diagTrace.host" placeholder="主機或 IP" style="margin-bottom:8px;">
                <template #append>
                  <el-button :loading="diagTrace.loading" @click="runTraceroute">執行</el-button>
                </template>
              </el-input>
              <pre style="max-height:300px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:8px;border-radius:4px;font-size:12px;white-space:pre-wrap;">{{ diagTrace.result || '結果將顯示在這裡' }}</pre>
            </el-card>
          </el-col>

          <!-- DNS -->
          <el-col :span="8">
            <el-card header="DNS 查詢">
              <el-input v-model="diagDns.host" placeholder="網域名稱" style="margin-bottom:8px;">
                <template #append>
                  <el-button :loading="diagDns.loading" @click="runDns">執行</el-button>
                </template>
              </el-input>
              <pre style="max-height:300px;overflow:auto;background:#1e1e1e;color:#d4d4d4;padding:8px;border-radius:4px;font-size:12px;white-space:pre-wrap;">{{ diagDns.result || '結果將顯示在這裡' }}</pre>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- WOL Tab -->
      <el-tab-pane label="Wake-on-LAN">
        <el-form style="max-width:400px;">
          <el-form-item label="MAC 位址">
            <el-input v-model="wolMac" placeholder="AA:BB:CC:DD:EE:FF" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="wolLoading" @click="sendWol">發送喚醒封包</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const interfaces = ref([])
const loading = ref(false)

// Diagnostics
const diagPing = reactive({ host: '', result: '', loading: false })
const diagTrace = reactive({ host: '', result: '', loading: false })
const diagDns = reactive({ host: '', result: '', loading: false })

// WOL
const wolMac = ref('')
const wolLoading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const res = await api.get('/api/network/interfaces')
    interfaces.value = res.data.interfaces || []
  } catch { /* handled */ }
  finally { loading.value = false }
}

async function runPing() {
  if (!diagPing.host) { ElMessage.warning('請輸入主機'); return }
  diagPing.loading = true
  diagPing.result = ''
  try {
    const res = await api.post('/api/network/diagnostics/ping', { host: diagPing.host })
    diagPing.result = res.data.output || res.data.result || ''
  } catch (e) { diagPing.result = '執行失敗' }
  finally { diagPing.loading = false }
}

async function runTraceroute() {
  if (!diagTrace.host) { ElMessage.warning('請輸入主機'); return }
  diagTrace.loading = true
  diagTrace.result = ''
  try {
    const res = await api.post('/api/network/diagnostics/traceroute', { host: diagTrace.host })
    diagTrace.result = res.data.output || res.data.result || ''
  } catch (e) { diagTrace.result = '執行失敗' }
  finally { diagTrace.loading = false }
}

async function runDns() {
  if (!diagDns.host) { ElMessage.warning('請輸入網域'); return }
  diagDns.loading = true
  diagDns.result = ''
  try {
    const res = await api.post('/api/network/diagnostics/dns', { host: diagDns.host })
    diagDns.result = res.data.output || res.data.result || ''
  } catch (e) { diagDns.result = '執行失敗' }
  finally { diagDns.loading = false }
}

async function sendWol() {
  if (!wolMac.value) { ElMessage.warning('請輸入 MAC 位址'); return }
  wolLoading.value = true
  try {
    await api.post('/api/network/wol', { mac: wolMac.value })
    ElMessage.success('喚醒封包已發送')
  } catch { /* handled */ }
  finally { wolLoading.value = false }
}

onMounted(loadData)
</script>
