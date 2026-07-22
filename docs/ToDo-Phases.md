# ProTech NAS — 開發階段計畫

> 建立日期：2026-07-22
>
> 本文件定義三個開發階段的完整工作項目。
> 目前專注 **Phase 1**，Phase 2/3 待 Phase 1 完成後啟動。

---

## Phase 1 — 核心體驗（🔴 高優先）

> 目標：讓系統可日常使用，核心 CRUD 功能完整可操作。
> 項目數：32

### 基礎設施

| # | 項目 | 說明 | 依賴套件 |
|---|------|------|----------|
| 1 | SQLite + SQLAlchemy 資料庫層 | `backend/src/database.py` + `models/`；DB session factory；Alembic migrations | `sqlalchemy[asyncio]`, `aiosqlite`, `alembic` |
| 2 | structlog 結構化日誌框架 | 統一取代 print/raw logging；JSON 格式輸出；request_id 追蹤 | `structlog` |

### 前端基礎設施

| # | 項目 | 說明 |
|---|------|------|
| 3 | 全域 API 錯誤處理 | `api/index.js` response interceptor：4xx → `ElMessage.error(detail)`；5xx → 「伺服器錯誤」；timeout → 「連線逾時」；401 → 跳轉登入 |
| 4 | 所有頁面 Loading 狀態 | 首次載入用 `el-skeleton`；後續刷新用 `v-loading` overlay；每頁加 `loading` ref |
| 5 | 所有 el-form 加 :rules 表單驗證 | 涵蓋：Login, 新增使用者, SMB/NFS, Docker 建立, 系統設定；使用 Element Plus async-validator |

### 檔案管理器 — Backend

| # | 項目 | 說明 | 安全要點 |
|---|------|------|----------|
| 6 | `file_service.list_directory()` | `os.scandir` + `os.stat`；回傳 name/type/size/modified/permissions | `realpath` 必須在允許根目錄內；禁止 `..` / symlink 逃脫 |
| 7 | `file_service.save_upload()` | `aiofiles` 串流寫入；同名檔加序號 | 檔名消毒（移除特殊字元）；大小限制（預設 2GB）；路徑穿越防護 |
| 8 | `file_service.get_download_path()` | 回傳 absolute_path + filename + size | 路徑穿越防護；必須是檔案非目錄；搭配 `StreamingResponse` |
| 9 | `file_service.make_directory()` | `os.makedirs(path, exist_ok=False)` | 路徑穿越防護；禁止在系統目錄建立 |
| 10 | `file_service.delete_item()` | `os.unlink`（檔案）/ `shutil.rmtree`（目錄） | 路徑穿越防護；禁止刪除 `/`、`/etc`、`/boot` 等系統目錄 |

### 檔案管理器 — API + Frontend

| # | 項目 | 說明 |
|---|------|------|
| 11 | 完善 `/api/files/*` 端點 | 確認 router ↔ service 正確串接；統一回傳格式 `{success, ...}` |
| 12 | Files.vue 主頁面 | el-table 列表 + 網格切換；麵包屑導航；排序（名稱/大小/日期）；雙擊資料夾進入 |
| 13 | Files.vue 上傳功能 | el-upload drag；限 3 並行；每檔獨立 progress bar；失敗可重試 |
| 14 | Files.vue 下載 + mkdir + 刪除 | 下載直接觸發；mkdir 用 dialog；刪除用 ElMessageBox 確認 |

### 儲存管理

| # | 項目 | 說明 |
|---|------|------|
| 15 | `storage_service.format_disk()` | `sudo mkfs.{ext4/xfs/btrfs}`；device 白名單；禁止 `/dev/sda`（系統碟）；必須已 unmount |
| 16 | Storage.vue 格式化 Dialog | el-steps 三步驟：選碟 → 選 FS → 輸入裝置名確認；⚠️ 紅色不可逆警告 |
| 17 | Storage.vue SMART 面板完善 | attributes el-table；溫度 progress bar（<50 綠, 50-70 黃, >70 紅）；每 60 秒自動刷新 |

### Docker 管理

| # | 項目 | 說明 |
|---|------|------|
| 18 | `docker_service.create_container()` | Docker SDK `client.containers.run(detach=True)`；ports/volumes/env/restart_policy；volumes host path 限制；禁止 privileged |
| 19 | `docker_service.restart_container()` | `container.restart(timeout=10)`；container_id 格式驗證 |
| 20 | `docker_service.remove_image()` | `client.images.remove(id, force=force)`；被使用中的映像禁止刪除（除非 force） |
| 21 | Docker.vue 建立容器精靈 | el-steps 五步驟：映像選擇 → 基本設定 → 埠對應（動態增減）→ Volume → 環境變數 → 確認 |
| 22 | Docker.vue 重啟 + 映像刪除按鈕 | 操作欄新增重啟按鈕（loading 狀態）；映像表格新增刪除按鈕（確認 dialog） |

### 系統管理

| # | 項目 | 說明 |
|---|------|------|
| 23 | `system_service.power_action()` | `sudo shutdown -h now` / `sudo reboot`；action 限 enum；⚠️ 高風險不可逆 |
| 24 | System.vue 系統日誌查看 | 上方過濾列（unit 下拉 + lines + since）；monospace 面板；依 priority 上色（error=紅, warn=黃） |
| 25 | System.vue 電源管理 | 大按鈕 + ⚠️ 紅色警告；二次確認需輸入「SHUTDOWN」或「REBOOT」；確認後倒數計時 |
| 26 | System.vue 溫度監控 | CPU gauge；各磁碟溫度列表 + progress bar；閾值色彩（<50 綠, 50-70 黃, >70 紅）；30 秒刷新 |
| 27 | Dashboard.vue 自動刷新 | `setInterval` 5 秒呼叫 `/api/dashboard`；右上角即時指示燈 + 手動暫停按鈕 |

### 使用者管理

| # | 項目 | 說明 |
|---|------|------|
| 28 | `user_service.update_user()` | `usermod -s {shell} -G {groups}`；禁止修改 root；shell 限 `/etc/shells` 列表 |
| 29 | Users.vue 編輯 + 修改密碼 | 編輯 Dialog（shell 下拉 + groups）；密碼 Dialog（>= 8 字元 + 強度指示 + 確認一致） |

### 網路管理

| # | 項目 | 說明 |
|---|------|------|
| 30 | 完善 `/api/network/interfaces` | 確認 `network_service.list_interfaces()` 回傳格式符合前端需求 |
| 31 | Network.vue 介面列表 Tab | el-table：name, IP, MAC, 狀態 tag（up=綠, down=灰）, 速率 |

### 備份管理

| # | 項目 | 說明 |
|---|------|------|
| 32 | Backup.vue 任務列表 + 建立精靈 | 列表：名稱/來源/目的/排程/狀態 tag；建立精靈 el-steps：來源 → 目的地 → 排程 → 保留策略 → 方法 |

---

## Phase 2 — 完善管理（🟡 中優先）

> 目標：進階管理功能完整，日常維運無需 SSH。
> 項目數：48
> 前置：Phase 1 完成

### 共享管理（6 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-1 | `samba_service.update_smb_share()` | 找到 smb.conf section → 替換 → restart smbd |
| P2-2 | `nfs_service.update_nfs_export()` | 修改 /etc/exports → `exportfs -ra` |
| P2-3 | `samba_service.get_share_acl()` / `set_share_acl()` | `getfacl` / `setfacl` 操作 |
| P2-4 | Shares.vue SMB/NFS 編輯 Dialog | 帶入現有值 → 儲存 → 刷新列表 |
| P2-5 | Shares.vue ACL 面板 | 使用者/群組 × rwx checkbox 表格 |
| P2-6 | Shares.vue 服務狀態 bar | SMB/NFS 運行狀態綠/紅點 + 連線數 badge |

### 使用者進階（6 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-7 | `user_service.disable_user()` / `enable_user()` | `usermod -L/-U` + `smbpasswd -d/-e` |
| P2-8 | `user_service.update_group_members()` | `gpasswd -a/-d` |
| P2-9 | `user_service.get_quota()` / `set_quota()` | `repquota` / `setquota` |
| P2-10 | Users.vue 停用/啟用 switch | el-switch；禁止停用唯一管理員 |
| P2-11 | Users.vue 群組管理 Tab | 群組 CRUD + 成員管理展開列 |
| P2-12 | Users.vue 配額 Dialog | 使用量 progress bar + soft/hard limit 設定 |

### 網路進階（6 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-13 | `network_service.configure_interface()` | Netplan/ifupdown 寫入 → apply |
| P2-14 | `network_service.list_firewall_rules()` / `add` / `delete` | iptables -L / -A / -D |
| P2-15 | `network_service.get_realtime_stats()` | `/sys/class/net/*/statistics` 兩次取差 |
| P2-16 | Network.vue 介面設定 Dialog | DHCP/Static radio → IP/netmask/gateway/DNS；⚠️ 斷線警告 |
| P2-17 | Network.vue 防火牆 Tab | 規則表格 + 新增 Dialog + SSH 保護規則不可刪 |
| P2-18 | Network.vue 即時速率圖表 | ECharts 折線圖；每介面 rx/tx；最近 60 秒 |

### Docker 進階（7 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-19 | `docker_service.get_container_stats()` | `container.stats(stream=False)` → 計算 CPU/Memory % |
| P2-20 | `docker_service.inspect_container()` | `container.attrs` 完整資訊 |
| P2-21 | `docker_service.prune_images()` | `client.images.prune()` 清理 dangling |
| P2-22 | `docker_service.list/create/remove_networks()` | Docker 網路 CRUD |
| P2-23 | `docker_service.list/create/remove_volumes()` | Docker Volume CRUD |
| P2-24 | Docker.vue Networks/Volumes Tab | 表格 + 建立/刪除 |
| P2-25 | Docker.vue 容器 Stats + Inspect | Stats gauge + Inspect JSON 顯示 |

### 系統進階（7 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-26 | `system_service.list_services()` / `control_service()` | systemctl list-units / start/stop/restart |
| P2-27 | `system_service.update_system_settings()` | hostnamectl + timedatectl |
| P2-28 | `system_service.get_hardware_info()` | lscpu + dmidecode + lspci |
| P2-29 | `system_service.check_updates()` / `apply_updates()` | apt update → apt list --upgradable → apt upgrade |
| P2-30 | System.vue 服務管理 Tab | 表格 + 啟/停/重啟按鈕 + enabled switch |
| P2-31 | System.vue 系統設定 Tab | hostname + timezone + NTP 表單 |
| P2-32 | System.vue 硬體資訊 + 更新 Tab | el-descriptions + 檢查/套用更新 |

### 備份進階（5 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-33 | `backup_service.update/delete_backup_task()` | UPDATE/DELETE DB + scheduler |
| P2-34 | `backup_service.run_backup()` | rsync -avz --delete；lock 防並行 |
| P2-35 | `backup_service.get_backup_history()` / `restore_backup()` | SELECT history；rsync/borg restore |
| P2-36 | Backup.vue 編輯/刪除 + 立即執行 | 按鈕 + 執行中 loading + 結果顯示 |
| P2-37 | Backup.vue 執行歷史 + 還原 | drawer 歷史表格 + 還原 Dialog |

### 遠端存取完善（4 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-38 | `remote_service.update_ddns_config()` 驗證 | 呼叫 provider API 驗證 token 有效性 |
| P2-39 | `remote_service.issue_ssl_cert()` 完善 | certbot 錯誤處理 + staging 模式 |
| P2-40 | `remote_service.update_vpn_config()` | 寫入 wg0.conf → wg-quick restart |
| P2-41 | Remote.vue 各 Tab 完善 | DDNS 狀態顯示 + SSL 到期 bar + VPN Peer 列表 |

### 通知系統（4 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-42 | `notification_service.send_notification()` | smtplib / Telegram API / Webhook |
| P2-43 | `notification_service.get/update_settings()` | DB/JSON 讀寫；token 遮罩 |
| P2-44 | AppLayout.vue Header 通知 badge | el-badge 未讀數 + el-popover 下拉 |
| P2-45 | 通知設定頁面 | Email/Telegram/Webhook 各有 switch + 表單 + 測試按鈕 |

### 前端體驗（3 項）

| # | 項目 | 說明 |
|---|------|------|
| P2-46 | i18n 國際化 | vue-i18n 掛載；zh-TW.json + en.json；~200 key |
| P2-47 | 深色模式 | Element Plus dark class toggle + localStorage + 跟隨系統 |
| P2-48 | 響應式 + 側邊欄收合 | 手機 hamburger；collapse 按鈕；偏好存 localStorage |

---

## Phase 3 — 進階功能（🟢 低優先）

> 目標：企業級加值功能、進階體驗優化。
> 項目數：32
> 前置：Phase 2 完成

### Docker 進階（4 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-1 | `docker_service.deploy_compose()` | 上傳 YAML → `docker compose up -d`；禁止 privileged |
| P3-2 | `docker_service.list/remove_compose_projects()` | `docker compose ls / down` |
| P3-3 | Docker.vue Compose Tab | 上傳/編輯 YAML + 專案列表 |
| P3-4 | Docker.vue 應用商店 | 卡片列表（Nextcloud, Jellyfin...）→ 一鍵 Compose 部署 |

### 儲存進階（5 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-5 | `storage_service.create/delete_partition()` | parted 操作；系統碟黑名單 |
| P3-6 | `storage_service.create/remove_raid()` + `add_raid_disk()` | mdadm 操作 |
| P3-7 | `storage_service.get/add/remove_fstab_entry()` | /etc/fstab 解析與修改 |
| P3-8 | Storage.vue 分割區 + RAID 精靈 + fstab Tab | 視覺化 bar + 建立精靈 |
| P3-9 | Storage.vue 使用量歷史圖表 | ECharts 折線圖；7d/30d/90d 切換 |

### 檔案進階（5 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-10 | `file_service.move_item()` / `copy_item()` | shutil.move / shutil.copy2 + copytree |
| P3-11 | `file_service.compress()` / `extract()` | zipfile / tarfile；Zip Slip 防護 |
| P3-12 | `file_service.create_share_link()` | UUID token → DB；可選密碼 hash |
| P3-13 | Files.vue 搬移/複製/重命名 | 目錄選擇器 + inline rename |
| P3-14 | Files.vue 壓縮/解壓/分享連結/預覽 | 各功能 Dialog + 預覽 drawer（圖片/文字/PDF/影片） |

### 使用者進階（4 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-15 | `user_service.setup_totp()` / `verify_totp()` | pyotp 產生 secret + QR URI |
| P3-16 | `user_service.list_sessions()` / `revoke_session()` | JWT blacklist table |
| P3-17 | `user_service.get_audit_log()` | SQLite audit_log table 查詢 |
| P3-18 | Users.vue 2FA 設定 + 稽核日誌頁 | QR code 顯示 + 驗證碼輸入；稽核表格 + 過濾 |

### 網路進階（3 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-19 | `network_service.ping()` / `traceroute()` / `dns_lookup()` | subprocess 呼叫 + 解析輸出 |
| P3-20 | `network_service.send_wol()` | UDP magic packet broadcast |
| P3-21 | Network.vue 診斷工具 + WOL Tab | Ping/Traceroute/DNS 面板 + WOL MAC 輸入 |

### 備份進階（3 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-22 | `backup_service.list/create/delete_snapshot()` | btrfs subvolume 操作 |
| P3-23 | `backup_service.schedule_backup()` | APScheduler CronTrigger 註冊 |
| P3-24 | Backup.vue 快照 Tab + 排程視覺化 | 快照表格 + cron 視覺化選擇器 |

### 遠端進階（2 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-25 | `remote_service.add/remove_vpn_peer()` 完善 | wg0.conf Peer section 管理 + client config 產生 |
| P3-26 | Remote.vue VPN Peer 管理 + 反向代理完善 | Peer 新增/刪除 + QR code；Proxy 規則 CRUD |

### 通知進階（1 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-27 | 通知歷史頁面 | 表格 + 未讀粗體 + 全部標記已讀 + 分頁 |

### 前端體驗進階（3 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-28 | Dashboard 歷史圖表 + 自訂 Widget | ECharts 多折線（CPU/RAM/Temp）+ vue-grid-layout 拖拽 |
| P3-29 | PWA 支援 + 頁面過渡動畫 | vite-plugin-pwa + router-view transition |
| P3-30 | 鍵盤快捷鍵 | Ctrl+K 搜尋；Delete 刪除；Ctrl+U 上傳 |

### 測試 & 品質（2 項）

| # | 項目 | 說明 |
|---|------|------|
| P3-31 | pytest 測試框架 + httpx TestClient | 每個 service 函式 unit test |
| P3-32 | 測試覆蓋率 80%+ | coverage report + CI 整合 |

---

## 總覽統計

| Phase | 項目數 | 優先級 | 狀態 |
|-------|--------|--------|------|
| Phase 1 | 32 | 🔴 高 | 🚧 進行中 |
| Phase 2 | 48 | 🟡 中 | ⏳ 待啟動 |
| Phase 3 | 32 | 🟢 低 | ⏳ 待啟動 |
| **合計** | **112** | | |

---

## 新增依賴套件總覽

| 套件 | 用途 | Phase |
|------|------|-------|
| `sqlalchemy[asyncio]` + `aiosqlite` | 資料庫 ORM | 1 |
| `alembic` | DB migrations | 1 |
| `structlog` | 結構化日誌 | 1 |
| `aiofiles` | 非同步檔案寫入 | 1 |
| `echarts` + `vue-echarts` | 圖表 | 2 |
| `vue-i18n` | 國際化 | 2 |
| `apscheduler` | 背景排程任務 | 2 |
| `slowapi` | API 速率限制 | 2 |
| `httpx` | HTTP client（DDNS/通知） | 2 |
| `@vueuse/core` | Vue 工具函式 | 2-3 |
| `pyotp` + `qrcode` | 2FA TOTP | 3 |
| `pyyaml` | Compose YAML 驗證 | 3 |
| `vite-plugin-pwa` | PWA | 3 |
| `vue-grid-layout` | Dashboard 拖拽 | 3 |
| `pytest` + `pytest-asyncio` + `coverage` | 測試 | 3 |
