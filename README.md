# ProTech NAS

自建 NAS 管理系統 — 仿 fnOS 功能，基於 FastAPI + Vue.js 3 + Element Plus

## Features

- **系統儀表板** — CPU / RAM / 磁碟 / 網路 / 溫度即時監控（5 秒自動刷新）
- **檔案管理器** — Web 檔案瀏覽 / 上傳 / 下載 / 搬移 / 壓縮 / 分享連結
- **儲存管理** — 磁碟列表、格式化、S.M.A.R.T. 健康監控、RAID 狀態、掛載操作
- **檔案共享** — SMB (Samba) + NFS 共享資料夾 CRUD + ACL 權限管理
- **印表機分享** — USB 印表機透過 CUPS/IPP 分享到網路（偵測 / 新增 / 分享 / 佇列 / 測試頁）
- **Docker 管理** — 容器建立/啟停/重啟/刪除、映像管理、Networks/Volumes、Compose 部署
- **使用者管理** — 系統帳號 + Samba 帳號 + 群組 + 配額 + 2FA (TOTP)
- **系統管理** — 日誌查看、服務管理、排程任務、電源控制、系統更新
- **網路管理** — 介面設定、防火牆規則、即時速率、診斷工具 (Ping/Traceroute/DNS)、WOL
- **備份 & 同步** — rsync 增量備份任務、排程、歷史、還原、Btrfs 快照
- **遠端存取** — DDNS 自動更新、SSL 憑證 (Let's Encrypt)、WireGuard VPN、反向代理
- **通知系統** — Email / Telegram / Webhook 通知管道 + 歷史記錄
- **國際化** — 中文 / English 雙語介面
- **深色模式** — 一鍵切換 + 跟隨系統偏好
- **響應式** — 手機 / 平板自適應 sidebar 收合

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI / Uvicorn |
| Frontend | Vue.js 3 / Vite / Element Plus / Pinia / vue-i18n |
| Auth | JWT (python-jose) / TOTP 2FA |
| System Integration | psutil, Docker SDK, subprocess (samba/nfs/mdadm/iptables/wg) |
| Target Hardware | Intel Atom D2550 / 4GB RAM |
| Target OS | Debian 12 / Ubuntu Server 22.04+ |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Browser (Vue.js 3)                   │
│    Element Plus + Pinia + Router + vue-i18n       │
│    Dark Mode / Responsive / Page Transitions     │
└───────────────────┬─────────────────────────────┘
                    │ REST API (/api/*)
                    ▼
┌─────────────────────────────────────────────────┐
│             FastAPI Backend (100 endpoints)       │
│  ┌──────┐ ┌─────┐ ┌─────┐ ┌────┐ ┌────┐ ┌───┐ │
│  │Files │ │Store│ │Share│ │Dock│ │Sys │ │Net│  │
│  │Backup│ │Users│ │Remot│ │Noti│ │Auth│ │   │  │
│  └──┬───┘ └──┬──┘ └──┬──┘ └─┬──┘ └─┬──┘ └─┬─┘ │
│     │        │       │      │      │      │    │
│  os/shutil lsblk  smb.conf Docker systemd  ip  │
│  zipfile   mdadm  exports  SDK    psutil iptab │
│            smartctl setfacl        journald wg  │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│       Linux (Debian 12 / Ubuntu Server)          │
│       Intel Atom D2550 + 4GB RAM + HDDs           │
└─────────────────────────────────────────────────┘
```

## Quick Start

整個流程分成兩步：**① 安裝**（每台機器只做一次）→ **② 選一種方式運行**
（開發模式 or 生產部署）。三個腳本的分工如下：

| 腳本 | 何時跑 | 身分 | 做什麼 |
|------|--------|------|--------|
| `scripts/install.sh` | 安裝步驟 1 | `sudo` | 裝系統套件（samba / nfs / docker / node.js / nginx…） |
| `scripts/setup_deps.sh` | 安裝步驟 2 | **一般使用者**（勿 sudo） | 建 Python venv、npm install、build 前端 |
| `scripts/deploy.sh` | 生產部署 | `sudo` | build 前端 + Nginx + systemd + sudoers + **開機自啟** |

> ⚠️ **兩個常見陷阱（先看再動手）**
> 1. **`setup_deps.sh` 不要加 `sudo`** — 否則 `.venv` 與 `frontend/dist` 會變成 root 擁有，之後 build/部署會 `EACCES` 失敗。腳本本身也會擋 root。
> 2. **`setup_deps.sh` 與 `deploy.sh` 必須在「同一份專案目錄」下跑** — 若你在 `~/projects/...` 建 venv，卻在 `~/Documents/...` 跑 deploy，會出現 `Backend venv not found`。認準一個目錄從頭到尾用。

### 步驟 1 — 安裝（開發 / 生產共用）

```bash
# 1. Clone（選定一個固定目錄，例如 ~/protech-nas，之後都在這裡操作）
git clone https://github.com/JiangAlex/protech-nas.git
cd protech-nas

# 2. 安裝系統依賴（sudo）
./scripts/install.sh
#    完成後「登出再登入」一次，docker 群組權限才會生效（原因見下方摺疊說明）

# 3. 安裝專案依賴 —— 不要加 sudo！（建 venv、npm install、build 前端）
./scripts/setup_deps.sh

# 4. 確認 venv 已建好（應印出 uvicorn 路徑，沒有代表上一步失敗）
ls backend/.venv/bin/uvicorn
```

> 💡 **不需要手動設定 `.env` / `SECRET_KEY`。** 生產部署時 `deploy.sh` 會自動從
> `.env.example` 建立 `.env` 並產生一組隨機 `SECRET_KEY`（已存在的自訂值不會被覆蓋）。
> 若要跑「開發模式」而 `.env` 還沒建，先 `cp backend/.env.example backend/.env`。

### 步驟 2A — 開發模式（本機測試用，不開機自啟）

```bash
# 後端（終端一）
cd backend && source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# 前端（終端二）
cd frontend && npm run dev

# 存取：http://localhost:5173   （API 文件：http://localhost:8000/docs）
# 登入：admin / admin123
```

### 步驟 2B — 生產部署（含開機自啟，正式使用建議這個）

```bash
# 前置：nginx 已裝（install.sh 已含）；在「步驟 1 的同一個目錄」下執行
sudo NAS_USER=$USER ./scripts/deploy.sh
```

`deploy.sh` 會一次完成：自動產生 `SECRET_KEY` → build 前端 → 部署到 `/var/www/protech-nas`
→ 安裝並 `enable` systemd service（**開機自啟**）→ 設定 Nginx（listen 80）→ 設定 sudoers
→ `enable` nginx。完成後可直接用 `http://<NAS-IP>`（免加 port）存取。

```bash
# 部署後常用指令
systemctl status protech-nas       # 目前狀態（預期 active (running)）
journalctl -u protech-nas -f       # 即時日誌
systemctl restart protech-nas      # 重啟
```

<details>
<summary>為什麼安裝後需登出再登入，docker 群組權限才會生效？</summary>

> `install.sh` 最後會執行 `sudo usermod -aG docker $USER` 把目前使用者加入 `docker` 群組。
> Docker daemon 透過 Unix socket `/var/run/docker.sock` 溝通，該 socket 擁有者為 `root`、
> 群組為 `docker`（權限 `srw-rw----`），只有 root 或 docker 群組成員能存取，否則執行 `docker ps`
> 會出現 `permission denied while trying to connect to the Docker daemon socket`。
>
> 關鍵在於 **群組成員資格是在「登入」當下載入 session 的**：登入時系統讀取 `/etc/group`，
> 把所屬群組附加到 session，並由 shell 及其子行程繼承。`usermod` 只修改了 `/etc/group` 檔案，
> 不會更新「當前正在運行」的 session，因此需要登出再登入（重建 session、重新讀取群組）才會生效。
>
> ```bash
> getent group docker   # 檔案設定 — usermod 後立即包含你的帳號
> groups                # 目前 session 生效中的群組 — 重新登入後才會出現 docker
> newgrp docker         # 不想登出時：開一個帶 docker 群組的子 shell（僅該 shell 生效）
> ```
</details>

## 開機自啟：兩種範圍 & 驗證

「開機自啟」由 **systemd** 負責（service 一旦 `enable`，開機就自動啟動）；
「免 port 存取」（直接 `http://<IP>` 不加 `:5173`）由 **Nginx（listen 80）** 達成。
依需求選一個腳本：

| 腳本 | 內容 | 開機自啟範圍 | 存取方式 |
|------|------|-------------|----------|
| `scripts/deploy.sh` | 後端 + 前端 build + Nginx(80) | 後端 + Nginx | ✅ `http://<IP>`（推薦） |
| `scripts/deploy-service.sh` | 只安裝後端 systemd service | 後端(8000) | `http://<IP>:8000` |

```bash
# 推薦：完整部署（免 port 存取）
sudo NAS_USER=$USER ./scripts/deploy.sh

# 或：只要後端開機自啟、不裝 Nginx
sudo ./scripts/deploy-service.sh

# 驗證是否會開機自啟（enabled = 開機會自動啟動）
systemctl is-enabled protech-nas   # 預期：enabled
systemctl status protech-nas       # 預期：active (running)
sudo systemctl disable protech-nas # 取消開機自啟
```

### 手動部署（進階，不使用腳本時）

<details>
<summary>展開手動 systemd + Nginx 步驟</summary>

```bash
# Backend — systemd service
sudo cp scripts/protech-nas.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now protech-nas

# Frontend — build & serve with Nginx
cd frontend && npm run build
sudo cp -r dist/* /var/www/protech-nas/
sudo cp scripts/protech-nas-nginx.conf /etc/nginx/sites-available/protech-nas
sudo ln -sf /etc/nginx/sites-available/protech-nas /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# Nginx 提供 /var/www/protech-nas/ 並反向代理 /api/* 至 localhost:8000
```
</details>

> ⚠️ 前置條件：`backend/.venv` 已建立（`setup_deps.sh`），否則 systemd service 會啟動失敗。
> `deploy.sh` 會在部署前 pre-flight 檢查並提示。

## 印表機分享設定（CUPS/IPP）

將接在 NAS 上的 USB 印表機（如 Epson）透過 CUPS/IPP 分享到區域網路，
區網內的 Windows / macOS / Linux 可經 IPP / AirPrint 連線列印。

```bash
# 1. 安裝 CUPS 列印系統（Epson 建議加裝 ESC/P-R 驅動）
sudo apt install cups cups-client
sudo apt install printer-driver-escpr        # Epson（可選）

# 2. 更新專案（取得印表機功能）
cd ~/protech-nas    # 或你的專案路徑
git pull

# 3. 重新 build 前端（前端有新增「印表機」頁）
./scripts/setup_deps.sh

# 4. 執行測試（預期 17 passed）
cd backend && source .venv/bin/activate
python -m pytest tests/test_printers.py -q

# 5. 重新套用 sudoers（新增 lpadmin/cupsenable/cupsaccept/cancel）
#    deploy.sh 會自動處理；手動套用：
sudo sed 's/nas/your_user/g' scripts/sudoers-protech-nas | sudo tee /etc/sudoers.d/protech-nas
sudo chmod 0440 /etc/sudoers.d/protech-nas && sudo visudo -c

# 6. 重啟後端服務
sudo systemctl restart protech-nas
```

完成後於 Web UI 的「印表機」頁操作：**偵測 USB 印表機 → 新增並分享 → 列出/測試頁/佇列管理**。

> 💡 USB 印表機需已插上 NAS。CUPS 也提供自身管理介面於 `http://<NAS-IP>:631`。

### 其他電腦如何連線至分享印表機

分享的印表機透過 **IPP（port 631）** 對外提供，並相容 **AirPrint**。先在 NAS 開啟對外分享：

```bash
sudo cupsctl --share-printers --remote-any   # 開啟分享 + 允許遠端存取
sudo systemctl restart cups
```

> ⚠️ 若其他電腦與 NAS 在同一實體區網，請用 NAS 的區網 IP（例如 `192.168.x.x`），
> 而非 Tailscale 的 `100.x` 位址（後者僅同一 tailnet 內可達）。

分享 URL 格式（`<NAS-IP>` 換成實際位址，`EPSON_L310` 換成你的印表機名稱）：

```
ipp://<NAS-IP>:631/printers/EPSON_L310
```

| OS | 連線方式 |
|----|----------|
| **Windows** | 印表機與掃描器 → 新增裝置 →「我想要的印表機不在清單中」→「使用 TCP/IP 位址或主機名稱」→ 類型選 **IPP** → URL 填 `http://<NAS-IP>:631/printers/<名稱>` |
| **macOS** | 印表機與掃描器 → 加入（+）→ 多半 Bonjour 直接列出（選 AirPrint）；否則「IP」分頁：位址 `<NAS-IP>`、協定 **IPP**、佇列 `printers/<名稱>` |
| **Linux** | `sudo lpadmin -p <本地名稱> -v "ipp://<NAS-IP>:631/printers/<名稱>" -E -m everywhere`（用戶端走 IPP，故 `everywhere` 適用） |

驗證連通性：在其他電腦瀏覽器開 `http://<NAS-IP>:631/printers/<名稱>`，看得到頁面即代表分享與網路皆正常。

若搜尋不到或連不上，在 NAS 放行防火牆（IPP=tcp 631；AirPrint/Bonjour 自動探索=mDNS udp 5353）：

```bash
sudo iptables -A INPUT -p tcp --dport 631 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 5353 -j ACCEPT
sudo apt install -y avahi-daemon        # 讓其他裝置能自動探索
```

## Project Structure

```
protech-nas/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI app + router mounting
│   │   ├── auth.py              # JWT auth + login endpoint
│   │   ├── config.py            # Environment settings
│   │   ├── routers/             # 13 API routers
│   │   │   ├── dashboard.py
│   │   │   ├── storage.py
│   │   │   ├── shares.py
│   │   │   ├── printers.py
│   │   │   ├── files.py
│   │   │   ├── docker_mgr.py
│   │   │   ├── users.py
│   │   │   ├── system.py
│   │   │   ├── network.py
│   │   │   ├── backup.py
│   │   │   ├── remote.py
│   │   │   └── notifications.py
│   │   └── services/            # 12 service modules (103 functions)
│   │       ├── storage_service.py
│   │       ├── samba_service.py
│   │       ├── nfs_service.py
│   │       ├── printer_service.py
│   │       ├── file_service.py
│   │       ├── docker_service.py
│   │       ├── user_service.py
│   │       ├── system_service.py
│   │       ├── network_service.py
│   │       ├── backup_service.py
│   │       ├── remote_service.py
│   │       ├── tailscale_service.py
│   │       └── notification_service.py
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── views/               # 11 pages
│   │   ├── components/          # AppLayout (sidebar, header, notifications)
│   │   ├── stores/              # Pinia (auth)
│   │   ├── api/                 # Axios + global error handling
│   │   ├── i18n/                # vue-i18n setup
│   │   ├── locales/             # zh-TW.json, en.json
│   │   ├── router/              # Vue Router + auth guard
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── ToDo-Phases.md           # Development phase specs
│   ├── versioning-convention.md # Version numbering rules
│   └── UserGuide.md             # User guide
├── scripts/
│   ├── install.sh               # System dependencies
│   ├── setup_deps.sh            # Project dependencies
│   ├── deploy.sh                # One-click production deployment
│   ├── deploy-service.sh        # Backend-only systemd autostart
│   ├── ota-update.sh            # OTA update
│   ├── protech-nas.service      # systemd service unit
│   ├── protech-nas-nginx.conf   # Nginx site config
│   └── sudoers-protech-nas      # sudoers rules for privileged commands
└── README.md
```

## API Endpoints (100 total)

### Core
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | JWT 登入 |
| GET | `/api/auth/me` | 目前使用者 |
| GET | `/api/dashboard` | 系統監控資料 |
| GET | `/api/health` | 健康檢查 |

### Storage (8)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/storage/disks` | 磁碟列表 |
| GET | `/api/storage/mounts` | 掛載點 |
| GET | `/api/storage/raid` | RAID 狀態 |
| POST | `/api/storage/mount` | 掛載 |
| POST | `/api/storage/unmount` | 卸載 |
| POST | `/api/storage/format` | 格式化 |
| GET | `/api/storage/smart/{device}` | S.M.A.R.T. |
| POST | `/api/storage/smart/{device}/test` | SMART 自檢 |

### Files (11)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/files/list` | 目錄列表 |
| POST | `/api/files/upload` | 上傳 |
| GET | `/api/files/download` | 下載 |
| POST | `/api/files/mkdir` | 建立資料夾 |
| DELETE | `/api/files/delete` | 刪除 |
| POST | `/api/files/move` | 搬移/重命名 |
| POST | `/api/files/copy` | 複製 |
| GET | `/api/files/info` | 檔案資訊 |
| POST | `/api/files/compress` | 壓縮 |
| POST | `/api/files/extract` | 解壓 |
| POST | `/api/files/share` | 分享連結 |

### Shares (10)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/shares/smb` | SMB 列表 |
| POST | `/api/shares/smb` | 建立 SMB |
| PUT | `/api/shares/smb/{name}` | 編輯 SMB |
| DELETE | `/api/shares/smb/{name}` | 刪除 SMB |
| GET/PUT | `/api/shares/smb/{name}/acl` | ACL 管理 |
| GET | `/api/shares/smb/status` | SMB 狀態 |
| GET | `/api/shares/nfs` | NFS 列表 |
| POST | `/api/shares/nfs` | 建立 NFS |
| PUT | `/api/shares/nfs` | 編輯 NFS |
| GET | `/api/shares/nfs/status` | NFS 狀態 |

### Printers (8)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/printers` | 印表機列表 |
| GET | `/api/printers/discover` | 偵測已連接裝置 |
| POST | `/api/printers` | 新增並分享 |
| PUT | `/api/printers/{name}/share` | 啟用/停用分享 |
| DELETE | `/api/printers/{name}` | 移除印表機 |
| GET | `/api/printers/{name}/jobs` | 列印佇列 |
| POST | `/api/printers/jobs/{job_id}/cancel` | 取消工作 |
| POST | `/api/printers/{name}/test` | 列印測試頁 |

### Docker (18)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/docker/containers` | 容器列表 |
| POST | `/api/docker/containers/create` | 建立容器 |
| POST | `/api/docker/containers/{id}/start` | 啟動 |
| POST | `/api/docker/containers/{id}/stop` | 停止 |
| POST | `/api/docker/containers/{id}/restart` | 重啟 |
| DELETE | `/api/docker/containers/{id}` | 刪除 |
| GET | `/api/docker/containers/{id}/logs` | 日誌 |
| GET | `/api/docker/containers/{id}/stats` | 資源使用 |
| GET | `/api/docker/containers/{id}/inspect` | 詳細設定 |
| GET | `/api/docker/images` | 映像列表 |
| POST | `/api/docker/images/pull` | 拉取映像 |
| DELETE | `/api/docker/images/{id}` | 刪除映像 |
| POST | `/api/docker/images/prune` | 清理映像 |
| GET/POST/DELETE | `/api/docker/networks` | 網路管理 |
| GET/POST/DELETE | `/api/docker/volumes` | Volume 管理 |
| POST | `/api/docker/compose/deploy` | Compose 部署 |
| GET | `/api/docker/compose/projects` | Compose 列表 |
| DELETE | `/api/docker/compose/projects/{name}` | 移除 Compose |

### System (16)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/logs` | 系統日誌 |
| GET | `/api/system/temperature` | 溫度 |
| POST | `/api/system/power/shutdown` | 關機 |
| POST | `/api/system/power/reboot` | 重啟 |
| GET | `/api/system/services` | 服務列表 |
| POST | `/api/system/services/{name}/{action}` | 服務管理 |
| PUT | `/api/system/settings` | 系統設定 |
| GET | `/api/system/hardware` | 硬體資訊 |
| GET | `/api/system/updates` | 檢查更新 |
| POST | `/api/system/updates/apply` | 套用更新 |
| GET/POST/DELETE | `/api/system/cron` | 排程管理 |
| GET | `/api/dashboard/history` | 歷史監控 |

### Network (10)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/network/interfaces` | 介面列表 |
| PUT | `/api/network/interfaces/{name}` | 介面設定 |
| GET/POST/DELETE | `/api/network/firewall/rules` | 防火牆 |
| GET | `/api/network/stats` | 即時速率 |
| POST | `/api/network/diag/ping` | Ping |
| POST | `/api/network/diag/traceroute` | Traceroute |
| POST | `/api/network/diag/dns` | DNS 查詢 |
| POST | `/api/network/wol` | Wake-on-LAN |

### Backup (10)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/backup/tasks` | 任務 CRUD |
| PUT/DELETE | `/api/backup/tasks/{id}` | 編輯/刪除 |
| POST | `/api/backup/tasks/{id}/run` | 立即執行 |
| GET | `/api/backup/tasks/{id}/history` | 執行歷史 |
| POST | `/api/backup/restore` | 還原 |
| PUT | `/api/backup/tasks/{id}/schedule` | 排程設定 |
| GET/POST/DELETE | `/api/backup/snapshots` | 快照管理 |

### Remote Access (9)
| Method | Path | Description |
|--------|------|-------------|
| GET/PUT | `/api/remote/ddns` | DDNS 設定 |
| POST | `/api/remote/ddns/update` | 更新 IP |
| GET | `/api/remote/ssl` | SSL 狀態 |
| POST | `/api/remote/ssl/issue` | 申請憑證 |
| GET | `/api/remote/vpn/status` | VPN 狀態 |
| PUT | `/api/remote/vpn/config` | VPN 設定 |
| GET/POST/DELETE | `/api/remote/vpn/peers` | Peer 管理 |
| GET/POST | `/api/remote/reverse-proxy` | 反向代理 |

### Users (15)
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/users` | 列表/建立 |
| PUT | `/api/users/{username}` | 編輯 |
| DELETE | `/api/users/{username}` | 刪除 |
| PUT | `/api/users/{username}/password` | 修改密碼 |
| PUT | `/api/users/{username}/status` | 啟用/停用 |
| GET/PUT | `/api/users/{username}/quota` | 配額 |
| POST | `/api/users/{username}/2fa/setup` | 設定 2FA |
| POST | `/api/users/{username}/2fa/verify` | 驗證 2FA |
| GET | `/api/users/audit` | 稽核日誌 |
| GET/POST/DELETE | `/api/users/groups` | 群組 CRUD |
| PUT | `/api/users/groups/{name}/members` | 成員管理 |

### Notifications (5)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notifications` | 通知列表 |
| GET/PUT | `/api/notifications/settings` | 設定 |
| POST | `/api/notifications/test` | 測試通知 |
| PUT | `/api/notifications/{id}/read` | 標記已讀 |

## Default Credentials

```
Username: admin
Password: admin123
```

⚠️ **請在生產環境中修改 `.env` 的 `SECRET_KEY` 和預設密碼。**

## System Requirements

- **OS:** Debian 12 / Ubuntu 22.04+
- **Python:** 3.11+
- **Node.js:** 20.x (install.sh 安裝；18+ 亦可)
- **RAM:** 512 MB (minimum), 2 GB (recommended)
- **Disk:** 200 MB (application only)
- **Optional:** Docker, smartmontools, lm-sensors, WireGuard, Nginx, certbot

## Optional System Dependencies

部分功能需要安裝額外系統套件才能正常運作。使用 `./scripts/install.sh` 會一次裝好核心與常用套件；
若手動安裝，下表列出各功能對應的套件與是否需要 root 權限：

| 功能 | 需要套件 | 需要 root |
|------|----------|-----------|
| S.M.A.R.T. 讀取 | smartmontools | ✅ |
| S.M.A.R.T. 自檢 | smartmontools | ✅ |
| 磁碟格式化 | — (內建 mkfs)；exFAT 需 exfatprogs | ✅ |
| CPU 溫度 | lm-sensors | ❌ |
| 磁碟溫度 | smartmontools | ✅ |
| Ping/Traceroute | traceroute | ❌ |
| DNS 查詢 | dnsutils (dig) | ❌ |
| WireGuard VPN | wireguard | ✅ |
| SSL 憑證 | certbot | ✅ |
| 反向代理 | nginx | ✅ |
| 印表機分享 | cups, cups-client（Epson 可加 printer-driver-escpr） | ✅ |
| Docker | docker.io | docker group |
| 服務管理 | — (內建 systemctl) | ✅ |
| 電源控制 | — (內建 shutdown) | ✅ |
| Btrfs 快照 | btrfs-progs | ✅ |

> ⚠️ **權限注意：** 需要 root 的操作，backend 已透過 `_sudo_run()` 自動加上 `sudo` 前綴。
> 以一般使用者運行時需設定免密碼 sudoers（`scripts/deploy.sh` 會自動完成，或手動套用）：
>
> ```bash
> sudo sed 's/nas/your_user/g' scripts/sudoers-protech-nas | sudo tee /etc/sudoers.d/protech-nas
> sudo chmod 0440 /etc/sudoers.d/protech-nas && sudo visudo -c
> ```
>
> 未設定時，需 root 的功能會出現 `Permission denied` 或 `Interactive authentication required`。
> 完整規則見 `scripts/sudoers-protech-nas`。

## License

MIT
