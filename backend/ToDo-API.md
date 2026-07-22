# Backend — 尚未實作 API 端點

> 更新日期：2026-07-20
>
> 僅列出 Router 層需新增的 HTTP 端點（對外介面）。

---

## 1. 儲存管理 (`/api/storage/*`)

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | POST | `/api/storage/format` | 格式化磁碟（指定 device、filesystem type: ext4/xfs/btrfs） |
| 🔴 高 | GET | `/api/storage/smart/{device}` | 讀取 S.M.A.R.T. 健康資訊 |
| 🔴 高 | POST | `/api/storage/smart/{device}/test` | 執行 S.M.A.R.T. 自檢 |
| 🟡 中 | POST | `/api/storage/partition` | 建立分割區（device、size、type） |
| 🟡 中 | DELETE | `/api/storage/partition/{device}` | 刪除分割區 |
| 🟡 中 | POST | `/api/storage/raid/create` | 建立 RAID 陣列（level、devices、spare） |
| 🟡 中 | DELETE | `/api/storage/raid/{name}` | 移除 RAID 陣列 |
| 🟡 中 | POST | `/api/storage/raid/{name}/add` | 向 RAID 加入磁碟 |
| 🟡 中 | GET | `/api/storage/fstab` | 讀取自動掛載設定 |
| 🟡 中 | POST | `/api/storage/fstab` | 新增自動掛載項目 |
| 🟡 中 | DELETE | `/api/storage/fstab` | 移除自動掛載項目 |
| 🟢 低 | GET | `/api/storage/usage/history` | 磁碟使用量歷史資料（需 DB） |

---

## 2. 檔案共享 (`/api/shares/*`)

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | PUT | `/api/shares/smb/{name}` | 編輯現有 SMB 共享設定 |
| 🔴 高 | PUT | `/api/shares/nfs/{path}` | 編輯現有 NFS 匯出設定 |
| 🟡 中 | GET | `/api/shares/smb/{name}/acl` | 取得共享資料夾 ACL 權限 |
| 🟡 中 | PUT | `/api/shares/smb/{name}/acl` | 設定共享資料夾存取權限 |
| 🟢 低 | GET | `/api/shares/smb/status` | Samba 服務狀態與連線數 |
| 🟢 低 | GET | `/api/shares/nfs/status` | NFS 服務狀態與客戶端連線 |

---

## 3. 檔案管理器 (`/api/files/*`) 🆕

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | GET | `/api/files/list` | 列出指定目錄的檔案與資料夾 |
| 🔴 高 | POST | `/api/files/upload` | 上傳檔案（multipart） |
| 🔴 高 | GET | `/api/files/download` | 下載檔案 |
| 🔴 高 | POST | `/api/files/mkdir` | 建立資料夾 |
| 🔴 高 | DELETE | `/api/files/delete` | 刪除檔案或資料夾 |
| 🟡 中 | POST | `/api/files/move` | 搬移 / 重新命名 |
| 🟡 中 | POST | `/api/files/copy` | 複製檔案或資料夾 |
| 🟡 中 | GET | `/api/files/info` | 檔案詳細資訊（大小、權限、修改時間） |
| 🟢 低 | POST | `/api/files/compress` | 壓縮檔案（zip/tar.gz） |
| 🟢 低 | POST | `/api/files/extract` | 解壓縮 |
| 🟢 低 | POST | `/api/files/share` | 產生公開分享連結 |

---

## 4. Docker 容器化 (`/api/docker/*`)

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | POST | `/api/docker/containers/create` | 建立新容器（image, ports, volumes, env） |
| 🔴 高 | POST | `/api/docker/containers/{id}/restart` | 重啟容器 |
| 🔴 高 | DELETE | `/api/docker/images/{id}` | 刪除映像 |
| 🟡 中 | GET | `/api/docker/containers/{id}/stats` | 容器即時資源使用（CPU/RAM） |
| 🟡 中 | GET | `/api/docker/containers/{id}/inspect` | 容器完整設定資訊 |
| 🟡 中 | POST | `/api/docker/images/prune` | 清理無用映像 |
| 🟡 中 | GET | `/api/docker/networks` | 列出 Docker 網路 |
| 🟡 中 | POST | `/api/docker/networks` | 建立 Docker 網路 |
| 🟡 中 | DELETE | `/api/docker/networks/{id}` | 刪除 Docker 網路 |
| 🟡 中 | GET | `/api/docker/volumes` | 列出 Docker Volume |
| 🟡 中 | POST | `/api/docker/volumes` | 建立 Volume |
| 🟡 中 | DELETE | `/api/docker/volumes/{name}` | 刪除 Volume |
| 🟢 低 | POST | `/api/docker/compose/deploy` | 上傳 docker-compose.yml 並部署 |
| 🟢 低 | GET | `/api/docker/compose/projects` | 列出 Compose 專案 |
| 🟢 低 | DELETE | `/api/docker/compose/projects/{name}` | 停止並移除 Compose 專案 |

---

## 5. 使用者 & 權限 (`/api/users/*`)

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | PUT | `/api/users/{username}` | 編輯使用者資訊（shell、群組） |
| 🟡 中 | PUT | `/api/users/{username}/status` | 停用 / 啟用使用者 |
| 🟡 中 | PUT | `/api/users/groups/{name}/members` | 群組成員管理（加入/移除） |
| 🟡 中 | GET | `/api/users/{username}/quota` | 取得使用者磁碟配額 |
| 🟡 中 | PUT | `/api/users/{username}/quota` | 設定磁碟配額 |
| 🟢 低 | GET | `/api/users/audit` | 使用者操作稽核日誌 |
| 🟢 低 | POST | `/api/users/{username}/2fa/setup` | 設定 TOTP 兩步驟驗證 |
| 🟢 低 | POST | `/api/users/{username}/2fa/verify` | 驗證 TOTP |
| 🟢 低 | GET | `/api/auth/sessions` | 目前活躍 session 列表 |
| 🟢 低 | DELETE | `/api/auth/sessions/{id}` | 踢出指定 session |

---

## 6. 系統管理 (`/api/system/*`) 🆕

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | GET | `/api/system/logs` | 系統日誌（journalctl，支援過濾） |
| 🔴 高 | POST | `/api/system/power/shutdown` | 關機 |
| 🔴 高 | POST | `/api/system/power/reboot` | 重啟 |
| 🔴 高 | GET | `/api/system/temperature` | CPU / HDD 溫度 |
| 🟡 中 | GET | `/api/system/services` | 列出系統服務狀態 |
| 🟡 中 | POST | `/api/system/services/{name}/start` | 啟動服務 |
| 🟡 中 | POST | `/api/system/services/{name}/stop` | 停止服務 |
| 🟡 中 | POST | `/api/system/services/{name}/restart` | 重啟服務 |
| 🟡 中 | PUT | `/api/system/settings` | 修改系統設定（hostname/timezone/NTP） |
| 🟡 中 | GET | `/api/system/hardware` | 詳細硬體資訊 |
| 🟡 中 | GET | `/api/system/updates` | 檢查可用更新 |
| 🟡 中 | POST | `/api/system/updates/apply` | 套用系統更新 |
| 🟢 低 | GET | `/api/system/cron` | 列出排程任務 |
| 🟢 低 | POST | `/api/system/cron` | 新增排程任務 |
| 🟢 低 | DELETE | `/api/system/cron/{id}` | 刪除排程任務 |
| 🟢 低 | GET | `/api/dashboard/history` | 歷史監控資料（CPU/RAM 趨勢） |

---

## 7. 網路管理 (`/api/network/*`) 🆕

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | GET | `/api/network/interfaces` | 列出網路介面（name, MAC, IP, status, speed） |
| 🟡 中 | PUT | `/api/network/interfaces/{name}` | 設定網路介面（static IP/DHCP/DNS/gateway） |
| 🟡 中 | GET | `/api/network/firewall/rules` | 列出防火牆規則 |
| 🟡 中 | POST | `/api/network/firewall/rules` | 新增防火牆規則 |
| 🟡 中 | DELETE | `/api/network/firewall/rules/{id}` | 刪除防火牆規則 |
| 🟡 中 | GET | `/api/network/stats` | 即時網路速率（每介面 tx/rx per sec） |
| 🟢 低 | POST | `/api/network/diag/ping` | Ping 測試 |
| 🟢 低 | POST | `/api/network/diag/traceroute` | Traceroute 測試 |
| 🟢 低 | POST | `/api/network/diag/dns` | DNS 查詢 |
| 🟢 低 | POST | `/api/network/wol` | 發送 Wake-on-LAN 封包 |

---

## 8. 備份 & 同步 (`/api/backup/*`) 🆕

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🔴 高 | GET | `/api/backup/tasks` | 列出所有備份任務 |
| 🔴 高 | POST | `/api/backup/tasks` | 建立備份任務（來源、目的地、排程、保留策略） |
| 🔴 高 | POST | `/api/backup/tasks/{id}/run` | 立即執行備份 |
| 🟡 中 | PUT | `/api/backup/tasks/{id}` | 編輯備份任務 |
| 🟡 中 | DELETE | `/api/backup/tasks/{id}` | 刪除備份任務 |
| 🟡 中 | GET | `/api/backup/tasks/{id}/history` | 備份執行歷史 |
| 🟡 中 | POST | `/api/backup/restore` | 還原指定版本 |
| 🟢 低 | GET | `/api/backup/snapshots` | 列出檔案系統快照 |
| 🟢 低 | POST | `/api/backup/snapshots` | 建立快照 |
| 🟢 低 | DELETE | `/api/backup/snapshots/{id}` | 刪除快照 |

---

## 9. 遠端存取 (`/api/remote/*`) 🆕

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🟡 中 | GET | `/api/remote/ddns` | DDNS 設定狀態 |
| 🟡 中 | PUT | `/api/remote/ddns` | 設定 DDNS（provider, domain, token） |
| 🟡 中 | GET | `/api/remote/ssl` | SSL 憑證狀態 |
| 🟡 中 | POST | `/api/remote/ssl/issue` | 申請 Let's Encrypt 憑證 |
| 🟡 中 | GET | `/api/remote/vpn/status` | VPN 連線狀態 |
| 🟡 中 | PUT | `/api/remote/vpn/config` | VPN 設定（WireGuard config） |
| 🟢 低 | GET | `/api/remote/vpn/peers` | VPN Peer 列表 |
| 🟢 低 | POST | `/api/remote/vpn/peers` | 新增 Peer |
| 🟢 低 | DELETE | `/api/remote/vpn/peers/{id}` | 刪除 Peer |
| 🟢 低 | GET | `/api/remote/reverse-proxy` | 反向代理規則列表 |
| 🟢 低 | POST | `/api/remote/reverse-proxy` | 新增反向代理規則 |

---

## 10. 通知系統 (`/api/notifications/*`) 🆕

| 優先級 | Method | Path | 功能說明 |
|--------|--------|------|----------|
| 🟡 中 | GET | `/api/notifications` | 通知列表 |
| 🟡 中 | GET | `/api/notifications/settings` | 通知管道設定 |
| 🟡 中 | PUT | `/api/notifications/settings` | 設定通知管道（Email/Telegram/Webhook） |
| 🟡 中 | POST | `/api/notifications/test` | 發送測試通知 |
| 🟢 低 | PUT | `/api/notifications/{id}/read` | 標記已讀 |

---

## 優先順序統計

| 優先級 | 數量 | 說明 |
|--------|------|------|
| 🔴 高 | 26 | NAS 核心功能、使用者最常操作 |
| 🟡 中 | 46 | 進階管理功能、日常維運 |
| 🟢 低 | 34 | 加值功能、企業級需求 |
| **總計** | **106** | |

### 建議開發順序

1. **Phase 1 — 核心體驗**（🔴 高）
   - 檔案管理器（瀏覽/上傳/下載）
   - 儲存格式化 + SMART
   - 系統電源 + 溫度 + 日誌
   - Docker 建立容器 + 重啟 + 刪映像

2. **Phase 2 — 完善管理**（🟡 中）
   - 共享編輯 + ACL
   - 網路介面 + 防火牆
   - 備份任務 + 執行
   - 服務管理 + 系統更新
   - 通知系統

3. **Phase 3 — 進階功能**（🟢 低）
   - Docker Compose
   - VPN / DDNS / 反向代理
   - 2FA / 稽核日誌
   - 壓縮 / 快照 / 歷史圖表
