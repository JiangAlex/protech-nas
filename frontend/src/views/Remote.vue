<template>
  <div>
    <h2>遠端存取</h2>
    <el-tabs>
      <!-- DDNS -->
      <el-tab-pane label="DDNS">
        <el-form :model="ddnsForm" label-width="100px" style="max-width:500px;">
          <el-form-item label="啟用"><el-switch v-model="ddnsForm.enabled" /></el-form-item>
          <el-form-item label="供應商">
            <el-select v-model="ddnsForm.provider">
              <el-option value="cloudflare" label="Cloudflare" />
              <el-option value="duckdns" label="DuckDNS" />
              <el-option value="noip" label="No-IP" />
            </el-select>
          </el-form-item>
          <el-form-item label="網域"><el-input v-model="ddnsForm.domain" /></el-form-item>
          <el-form-item label="Token"><el-input v-model="ddnsForm.token" type="password" show-password /></el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveDDNS">儲存</el-button>
            <el-button @click="updateIP">立即更新 IP</el-button>
          </el-form-item>
        </el-form>
        <el-descriptions :column="2" border style="margin-top:16px;" v-if="ddnsStatus">
          <el-descriptions-item label="目前 IP">{{ ddnsStatus.current_ip || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="上次更新">{{ ddnsStatus.last_update || '從未' }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>

      <!-- SSL -->
      <el-tab-pane label="SSL 憑證">
        <el-button type="primary" @click="sslDialogVisible = true" style="margin-bottom:12px;">申請憑證</el-button>
        <el-table :data="sslCerts" stripe>
          <el-table-column prop="domain" label="網域" />
          <el-table-column prop="expires" label="到期日" />
          <el-table-column prop="days_remaining" label="剩餘天數">
            <template #default="{ row }">
              <el-tag :type="row.days_remaining > 30 ? 'success' : row.days_remaining > 7 ? 'warning' : 'danger'">
                {{ row.days_remaining }} 天
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="sslDialogVisible" title="申請 SSL 憑證" width="400px">
          <el-form :model="sslForm" label-width="80px">
            <el-form-item label="網域"><el-input v-model="sslForm.domain" /></el-form-item>
            <el-form-item label="Email"><el-input v-model="sslForm.email" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="sslDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="issueCert">申請</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- VPN -->
      <el-tab-pane label="VPN">
        <el-descriptions :column="2" border v-if="vpnStatus">
          <el-descriptions-item label="狀態">
            <el-tag :type="vpnStatus.running ? 'success' : 'info'">{{ vpnStatus.running ? '運行中' : '停止' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="監聽埠">{{ vpnStatus.listen_port || '—' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top:16px;">
          <el-button type="warning" size="small" @click="openVpnConfigDialog">編輯設定</el-button>
        </div>

        <h4 style="margin-top:16px;">Peers</h4>
        <el-button type="primary" size="small" @click="vpnPeerDialogVisible = true" style="margin-bottom:8px;">新增 Peer</el-button>
        <el-table :data="vpnStatus?.peers || []" stripe>
          <el-table-column prop="public_key" label="Public Key" show-overflow-tooltip />
          <el-table-column prop="endpoint" label="Endpoint" />
          <el-table-column prop="allowed_ips" label="Allowed IPs" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteVpnPeer(row.public_key)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- VPN Peer Dialog -->
        <el-dialog v-model="vpnPeerDialogVisible" title="新增 VPN Peer" width="450px">
          <el-form :model="vpnPeerForm" label-width="100px">
            <el-form-item label="Public Key">
              <el-input v-model="vpnPeerForm.public_key" placeholder="Peer 的 public key" />
            </el-form-item>
            <el-form-item label="Allowed IPs">
              <el-input v-model="vpnPeerForm.allowed_ips" placeholder="10.0.0.2/32" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="vpnPeerDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="vpnPeerSaving" @click="addVpnPeer">新增</el-button>
          </template>
        </el-dialog>

        <!-- VPN Config Dialog -->
        <el-dialog v-model="vpnConfigDialogVisible" title="編輯 VPN 設定" width="450px">
          <el-form :model="vpnConfigForm" label-width="100px">
            <el-form-item label="位址">
              <el-input v-model="vpnConfigForm.address" placeholder="10.0.0.1/24" />
            </el-form-item>
            <el-form-item label="監聽埠">
              <el-input-number v-model="vpnConfigForm.listen_port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="DNS">
              <el-input v-model="vpnConfigForm.dns" placeholder="1.1.1.1" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="vpnConfigDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="vpnConfigSaving" @click="saveVpnConfig">儲存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- Reverse Proxy -->
      <el-tab-pane label="反向代理">
        <el-button type="primary" @click="proxyDialogVisible = true" style="margin-bottom:12px;">新增規則</el-button>
        <el-button @click="loadProxyRules" style="margin-bottom:12px;">重新整理</el-button>

        <el-table :data="proxyRules" stripe v-loading="proxyLoading">
          <el-table-column prop="domain" label="網域" />
          <el-table-column prop="upstream" label="上游位址" />
          <el-table-column prop="ssl" label="SSL" width="80">
            <template #default="{ row }">
              <el-tag :type="row.ssl ? 'success' : 'info'" size="small">{{ row.ssl ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="danger" size="small" @click="deleteProxyRule(row.id || row.domain)">刪除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-dialog v-model="proxyDialogVisible" title="新增反向代理規則" width="500px">
          <el-form :model="proxyForm" label-width="100px">
            <el-form-item label="網域">
              <el-input v-model="proxyForm.domain" placeholder="app.example.com" />
            </el-form-item>
            <el-form-item label="上游位址">
              <el-input v-model="proxyForm.upstream" placeholder="http://127.0.0.1:3000" />
            </el-form-item>
            <el-form-item label="啟用 SSL">
              <el-switch v-model="proxyForm.ssl" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="proxyDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="proxySaving" @click="addProxyRule">新增</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

// DDNS
const ddnsForm = reactive({ enabled: false, provider: 'cloudflare', domain: '', token: '' })
const ddnsStatus = ref(null)

// SSL
const sslCerts = ref([])
const sslDialogVisible = ref(false)
const sslForm = reactive({ domain: '', email: 'admin@localhost' })

// VPN
const vpnStatus = ref(null)

// VPN Peers
const vpnPeerDialogVisible = ref(false)
const vpnPeerSaving = ref(false)
const vpnPeerForm = reactive({ public_key: '', allowed_ips: '' })

// VPN Config
const vpnConfigDialogVisible = ref(false)
const vpnConfigSaving = ref(false)
const vpnConfigForm = reactive({ address: '', listen_port: 51820, dns: '' })

// Reverse Proxy
const proxyRules = ref([])
const proxyLoading = ref(false)
const proxyDialogVisible = ref(false)
const proxySaving = ref(false)
const proxyForm = reactive({ domain: '', upstream: '', ssl: false })

// --- DDNS ---
async function loadDDNS() {
  try {
    const res = await api.get('/api/remote/ddns')
    Object.assign(ddnsForm, { enabled: res.data.enabled, provider: res.data.provider, domain: res.data.domain, token: '' })
    ddnsStatus.value = res.data
  } catch {}
}

async function saveDDNS() {
  await api.put('/api/remote/ddns', ddnsForm)
  ElMessage.success('DDNS 設定已儲存')
  loadDDNS()
}

async function updateIP() {
  const res = await api.post('/api/remote/ddns/update')
  ElMessage.success(`IP 已更新：${res.data.ip}`)
  loadDDNS()
}

// --- SSL ---
async function loadSSL() {
  try {
    const res = await api.get('/api/remote/ssl')
    sslCerts.value = res.data.certs || []
  } catch {}
}

async function issueCert() {
  await api.post('/api/remote/ssl/issue', sslForm)
  ElMessage.success('憑證申請成功')
  sslDialogVisible.value = false
  loadSSL()
}

// --- VPN ---
async function loadVPN() {
  try {
    const res = await api.get('/api/remote/vpn/status')
    vpnStatus.value = res.data
  } catch {}
}

// VPN Config
function openVpnConfigDialog() {
  // Pre-fill from current status if available
  if (vpnStatus.value) {
    vpnConfigForm.address = vpnStatus.value.address || ''
    vpnConfigForm.listen_port = vpnStatus.value.listen_port || 51820
    vpnConfigForm.dns = vpnStatus.value.dns || ''
  }
  vpnConfigDialogVisible.value = true
}

async function saveVpnConfig() {
  if (!vpnConfigForm.address) {
    ElMessage.warning('請填寫 VPN 位址')
    return
  }
  vpnConfigSaving.value = true
  try {
    await api.put('/api/remote/vpn/config', {
      address: vpnConfigForm.address,
      listen_port: vpnConfigForm.listen_port,
      dns: vpnConfigForm.dns,
    })
    ElMessage.success('VPN 設定已儲存')
    vpnConfigDialogVisible.value = false
    loadVPN()
  } catch { /* handled */ }
  finally { vpnConfigSaving.value = false }
}

// VPN Peers
async function addVpnPeer() {
  if (!vpnPeerForm.public_key || !vpnPeerForm.allowed_ips) {
    ElMessage.warning('請填寫 Public Key 和 Allowed IPs')
    return
  }
  vpnPeerSaving.value = true
  try {
    await api.post('/api/remote/vpn/peers', {
      public_key: vpnPeerForm.public_key,
      allowed_ips: vpnPeerForm.allowed_ips,
    })
    ElMessage.success('Peer 已新增')
    vpnPeerDialogVisible.value = false
    vpnPeerForm.public_key = ''
    vpnPeerForm.allowed_ips = ''
    loadVPN()
  } catch { /* handled */ }
  finally { vpnPeerSaving.value = false }
}

async function deleteVpnPeer(publicKey) {
  await ElMessageBox.confirm('確定要刪除此 Peer？', '確認', { type: 'warning' })
  try {
    await api.delete('/api/remote/vpn/peers', { data: { public_key: publicKey } })
    ElMessage.success('Peer 已刪除')
    loadVPN()
  } catch { /* handled */ }
}

// --- Reverse Proxy ---
async function loadProxyRules() {
  proxyLoading.value = true
  try {
    const res = await api.get('/api/remote/proxy/rules')
    proxyRules.value = res.data.rules || []
  } catch { /* handled */ }
  finally { proxyLoading.value = false }
}

async function addProxyRule() {
  if (!proxyForm.domain || !proxyForm.upstream) {
    ElMessage.warning('請填寫網域和上游位址')
    return
  }
  proxySaving.value = true
  try {
    await api.post('/api/remote/proxy/rules', {
      domain: proxyForm.domain,
      upstream: proxyForm.upstream,
      ssl: proxyForm.ssl,
    })
    ElMessage.success('規則已新增')
    proxyDialogVisible.value = false
    proxyForm.domain = ''
    proxyForm.upstream = ''
    proxyForm.ssl = false
    loadProxyRules()
  } catch { /* handled */ }
  finally { proxySaving.value = false }
}

async function deleteProxyRule(id) {
  await ElMessageBox.confirm('確定要刪除此規則？', '確認', { type: 'warning' })
  try {
    await api.delete(`/api/remote/proxy/rules/${id}`)
    ElMessage.success('規則已刪除')
    loadProxyRules()
  } catch { /* handled */ }
}

onMounted(() => { loadDDNS(); loadSSL(); loadVPN(); loadProxyRules() })
</script>
