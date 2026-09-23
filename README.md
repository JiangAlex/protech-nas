# ProTech NAS

自建 NAS 管理系統 — 仿 fnOS 功能，基於 FastAPI + Vue.js 3 + Element Plus

## Features

- **系統儀表板** — CPU / RAM / 磁碟 / 網路 / 溫度即時監控（5 秒自動刷新）
- **檔案管理器** — Web 檔案瀏覽 / 上傳 / 下載 / 搬移 / 壓縮 / 分享連結
- **儲存管理** — 磁碟列表、格式化、S.M.A.R.T. 健康監控、RAID 狀態、掛載操作
- **檔案共享** — SMB (Samba) + NFS 共享資料夾 CRUD + ACL 權限管理
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
│             FastAPI Backend (92 endpoints)        │
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

### 方式一：腳本安裝（推薦）

```bash
# 1. Clone
git clone https://github.com/JiangAlex/protech-nas.git
cd protech-nas

# 2. 安裝系統依賴（samba / nfs / docker / node.js 20.x / smartmontools ...）
./scripts/install.sh
# 提示：安裝後需登出再登入，docker 群組權限才會生效

# 3. 安裝專案依賴（建立 Python venv、npm install、build 前端）
./scripts/setup_deps.sh

# 4. 設定環境變數
cp backend/.env.example backend/.env   # 編輯：務必設定 SECRET_KEY

# 5. 啟動（開發模式）
cd backend && source .venv/bin/activate
uvicorn src.main:app --reload --port 8000   # 後端
cd ../frontend && npm run dev                # 前端（另開終端）

# 6. Access
# Web UI:  http://localhost:5173
# API Doc: http://localhost:8000/docs
# Login:   admin / admin123
```

> #### 為什麼安裝後需登出再登入，docker 群組權限才會生效？
>
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
> # 驗證：/etc/group 已更新，但目前 session 尚未生效時，兩者輸出會不一致
> getent group docker   # 檔案設定 — usermod 後立即包含你的帳號
> groups                # 目前 session 生效中的群組 — 重新登入後才會出現 docker
> ```
>
> 不想登出，可用以下方式在新 session 套用群組（僅該 shell 生效）：
>
> ```bash
> newgrp docker         # 開啟一個帶 docker 群組的子 shell
> # 或重新建立一次 SSH 連線
> ```

### 方式二：手動安裝

```bash
# 1. Clone
git clone https://github.com/JiangAlex/protech-nas.git
cd protech-nas

# 2. Backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit: set SECRET_KEY

# 3. Start backend
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 4. Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# 5. Access
# Web UI:  http://localhost:5173
# API Doc: http://localhost:8000/docs
# Login:   admin / admin123
```

## Production Deployment

### 方式一：一鍵部署（推薦）

```bash
# 前置：先完成 setup_deps.sh 並設定好 backend/.env
# deploy.sh 會自動完成：build 前端、部署到 web root、安裝 systemd service、
# 設定 Nginx、設定 sudoers、開機自動啟動
sudo NAS_USER=$USER ./scripts/deploy.sh

# 部署後常用指令
systemctl status protech-nas
journalctl -u protech-nas -f
systemctl restart protech-nas
```

### 方式二：手動部署

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

## Project Structure

```
protech-nas/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI app + router mounting
│   │   ├── auth.py              # JWT auth + login endpoint
│   │   ├── config.py            # Environment settings
│   │   ├── routers/             # 12 API routers (92 endpoints)
│   │   │   ├── dashboard.py
│   │   │   ├── storage.py
│   │   │   ├── shares.py
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
│   ├── ota-update.sh            # OTA update
│   ├── protech-nas.service      # systemd service unit
│   ├── protech-nas-nginx.conf   # Nginx site config
│   └── sudoers-protech-nas      # sudoers rules for privileged commands
└── README.md
```

## API Endpoints (92 total)

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
