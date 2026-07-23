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

      <!-- Tailscale -->
      <el-tab-pane label="Tailscale">
        <el-button @click="loadTailscale" style="margin-bottom:12px;">重新整理</el-button>

        <!-- Not installed -->
        <el-alert v-if="ts.loaded && !ts.installed" type="warning" :closable="false" style="margin-bottom:16px;">
          Tailscale 尚未安裝。請執行：<code>curl -fsSL https://tailscale.com/install.sh | sh</code>
        </el-alert>

        <!-- Status -->
        <el-descriptions :column="2" border v-if="ts.installed" style="margin-bottom:16px;">
          <el-descriptions-item label="狀態">
            <el-tag :type="ts.running ? 'success' : 'info'">{{ ts.running ? '已連線' : '未連線' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="版本">{{ ts.version || '—' }}</el-descriptions-item>
          <el-descriptions-item label="主機名">{{ ts.self.hostname || '—' }}</el-descriptions-item>
          <el-descriptions-item label="Tailscale IP">{{ ts.self.ip || '—' }}</el-descriptions-item>
          <el-descriptions-item label="DNS 名稱">{{ ts.self.dns_name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="狀態">{{ ts.backend_state || '—' }}</el-descriptions-item>
        </el-descriptions>

        <!-- Controls -->
        <div v-if="ts.installed" style="margin-bottom:16px;">
          <el-button type="success" :loading="tsLoading" @click="tsConnect" :disabled="ts.running">連線</el-button>
          <el-button type="warning" :loading="tsLoading" @click="tsDisconnect" :disabled="!ts.running">斷線</el-button>
          <el-button type="danger" :loading="tsLoading" @click="tsLogout" :disabled="!ts.running">登出</el-button>
        </div>

        <!-- Tailscale SSH -->
        <el-card header="Tailscale SSH" style="margin-bottom:16px;" v-if="ts.installed && ts.running">
          <el-switch v-model="tsSshEnabled" :loading="tsSshLoading" active-text="啟用" inactive-text="停用" @change="toggleSsh" />
          <el-text type="info" size="small" style="margin-left:12px;">啟用後可透過 Tailscale 身分認證直接 SSH，不需密碼或金鑰</el-text>
        </el-card>

        <!-- Auth URL -->
        <el-alert v-if="tsAuthUrl" type="info" :closable="true" style="margin-bottom:16px;" @close="tsAuthUrl = ''">
          需要認證，請開啟此連結登入：<br>
          <a :href="tsAuthUrl" target="_blank" style="word-break:break-all;">{{ tsAuthUrl }}</a>
        </el-alert>

        <!-- Subnet Routes -->
        <el-card header="子網路由 (Subnet Routes)" style="margin-bottom:16px;" v-if="ts.installed">
          <el-form inline>
            <el-form-item>
              <el-input v-model="tsRoutes" placeholder="192.168.1.0/24,10.0.0.0/8" style="width:300px;" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="setRoutes">套用</el-button>
            </el-form-item>
          </el-form>
          <el-text type="info" size="small">設定後需到 Tailscale Admin Console 核准路由</el-text>
        </el-card>

        <!-- Exit Node -->
        <el-card header="Exit Node" style="margin-bottom:16px;" v-if="ts.installed && ts.running">
          <el-form inline>
            <el-form-item label="使用節點">
              <el-select v-model="tsExitNode" placeholder="不使用" clearable style="width:220px;">
                <el-option value="" label="不使用 (直連)" />
                <el-option v-for="p in tsExitNodeOptions" :key="p.ip" :value="p.ip" :label="p.hostname + ' (' + p.ip + ')'" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="setExitNode">套用</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Peers -->
        <h4 v-if="ts.installed && ts.running">網路中的裝置</h4>
        <el-table v-if="ts.installed && ts.running" :data="ts.peers" stripe>
          <el-table-column prop="hostname" label="主機名" />
          <el-table-column prop="ip" label="Tailscale IP" width="150" />
          <el-table-column prop="os" label="系統" width="100" />
          <el-table-column prop="online" label="狀態" width="80">
            <template #default="{ row }">
              <el-tag :type="row.online ? 'success' : 'info'" size="small">{{ row.online ? '在線' : '離線' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="exit_node" label="Exit Node" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.exit_node" type="warning" size="small">使用中</el-tag>
              <el-tag v-else-if="row.exit_node_option" type="info" size="small">可用</el-tag>
            </template>
          </el-table-column>
        </el-table>
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

// Tailscale
const ts = reactive({
  loaded: false,
  installed: false,
  running: false,
  version: '',
  backend_state: '',
  self: {},
  peers: [],
})
const tsLoading = ref(false)
const tsAuthUrl = ref('')
const tsRoutes = ref('')
const tsExitNode = ref('')
const tsExitNodeOptions = ref([])
const tsSshEnabled = ref(false)
const tsSshLoading = ref(false)

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

// --- Tailscale ---
async function loadTailscale() {
  try {
    const res = await api.get('/api/remote/tailscale/status')
    ts.loaded = true
    ts.installed = res.data.installed || false
    ts.running = res.data.running || false
    ts.version = res.data.version || ''
    ts.backend_state = res.data.backend_state || ''
    ts.self = res.data.self || {}
    ts.peers = res.data.peers || []
    // Populate exit node options
    tsExitNodeOptions.value = ts.peers.filter(p => p.exit_node_option || p.exit_node)
    // Set current exit node
    const activeExit = ts.peers.find(p => p.exit_node)
    tsExitNode.value = activeExit ? activeExit.ip : ''
    // Load SSH status
    if (ts.running) {
      try {
        const sshRes = await api.get('/api/remote/tailscale/ssh')
        tsSshEnabled.value = sshRes.data.ssh_enabled || false
      } catch { tsSshEnabled.value = false }
    }
  } catch {
    ts.loaded = true
    ts.installed = false
  }
}

async function toggleSsh(val) {
  tsSshLoading.value = true
  try {
    await api.put('/api/remote/tailscale/ssh', { enabled: val })
    ElMessage.success(val ? 'Tailscale SSH 已啟用' : 'Tailscale SSH 已停用')
  } catch {
    // Revert switch on failure
    tsSshEnabled.value = !val
  }
  finally { tsSshLoading.value = false }
}

async function tsConnect() {
  tsLoading.value = true
  tsAuthUrl.value = ''
  try {
    const res = await api.post('/api/remote/tailscale/up', { accept_routes: true })
    if (res.data.auth_url) {
      tsAuthUrl.value = res.data.auth_url
      ElMessage.info('請開啟連結完成認證')
    } else {
      ElMessage.success('Tailscale 已連線')
    }
    loadTailscale()
  } catch { /* handled */ }
  finally { tsLoading.value = false }
}

async function tsDisconnect() {
  tsLoading.value = true
  try {
    await api.post('/api/remote/tailscale/down')
    ElMessage.success('Tailscale 已斷線')
    loadTailscale()
  } catch { /* handled */ }
  finally { tsLoading.value = false }
}

async function tsLogout() {
  await ElMessageBox.confirm('登出後需重新認證才能連線，確定？', '確認', { type: 'warning' })
  tsLoading.value = true
  try {
    await api.post('/api/remote/tailscale/logout')
    ElMessage.success('已登出 Tailscale')
    loadTailscale()
  } catch { /* handled */ }
  finally { tsLoading.value = false }
}

async function setRoutes() {
  try {
    await api.put('/api/remote/tailscale/routes', { routes: tsRoutes.value })
    ElMessage.success('子網路由已更新')
    loadTailscale()
  } catch { /* handled */ }
}

async function setExitNode() {
  try {
    await api.put('/api/remote/tailscale/exit-node', { peer_ip: tsExitNode.value })
    ElMessage.success(tsExitNode.value ? `Exit Node 已設為 ${tsExitNode.value}` : 'Exit Node 已清除')
    loadTailscale()
  } catch { /* handled */ }
}

onMounted(() => { loadDDNS(); loadSSL(); loadVPN(); loadProxyRules(); loadTailscale() })
</script>
