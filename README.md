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
| Target Hardware | Intel N100 Mini-ITX / 16GB RAM |
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
│       Intel N100 + 16GB RAM + HDDs               │
└─────────────────────────────────────────────────┘
```

## Quick Start

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

```bash
# Backend — systemd service
sudo cp scripts/protech-nas.service /etc/systemd/system/
sudo systemctl enable --now protech-nas

# Frontend — build & serve with Nginx
cd frontend && npm run build
sudo cp -r dist/ /var/www/protech-nas/
# Configure Nginx to serve /var/www/protech-nas/ and proxy /api/* to localhost:8000
```

## Development

```bash
# Backend (auto-reload)
cd backend && source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Frontend (HMR)
cd frontend && npm run dev
# → http://localhost:5173
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
│   ├── ToDo-API.md              # API endpoint specs
│   ├── ToDo-Services.md         # Service function specs
│   ├── ToDo-Frontend.md         # Frontend feature specs
│   ├── Hermes-Auto-Runner.md    # Auto-execution setup
│   └── hw_specs.md              # Hardware specifications
├── scripts/
│   ├── install.sh               # System dependencies
│   └── setup_deps.sh            # Project dependencies
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
- **Node.js:** 18+
- **RAM:** 512 MB (minimum), 2 GB (recommended)
- **Disk:** 200 MB (application only)
- **Optional:** Docker, smartmontools, lm-sensors, WireGuard, Nginx, certbot

## Optional System Dependencies

部分功能需要安裝額外系統套件才能正常運作：

```bash
# 儲存管理 — S.M.A.R.T. 健康監控（需要 root 執行 smartctl）
sudo apt install smartmontools

# 系統管理 — CPU/磁碟溫度監控
sudo apt install lm-sensors
sudo sensors-detect  # 偵測硬體感測器

# 網路管理 — 診斷工具
sudo apt install traceroute dnsutils

# 遠端存取 — VPN
sudo apt install wireguard

# 遠端存取 — SSL 憑證
sudo apt install certbot

# 遠端存取 — 反向代理
sudo apt install nginx

# Docker 管理
sudo apt install docker.io docker-compose-v2

# 備份 — Btrfs 快照（若使用 Btrfs 檔案系統）
sudo apt install btrfs-progs
```

> ⚠️ **權限注意：** 部分操作需要 root 權限（格式化、SMART 自檢、服務管理、電源控制等）。
> 開發環境可用 `sudo` 啟動 uvicorn，生產環境建議透過 systemd service 以適當權限運行。

### Sudoers 設定（免密碼執行特權指令）

Backend 以一般使用者身份運行時，`smartctl` 等指令需要 root 權限。
專案已透過 `_sudo_run()` 自動加上 `sudo` 前綴，但需要設定 sudoers 允許免密碼執行：

```bash
# 方法一：使用專案提供的設定檔（將 "nas" 替換為實際執行 backend 的使用者）
sudo cp scripts/sudoers-protech-nas /etc/sudoers.d/protech-nas
sudo chmod 0440 /etc/sudoers.d/protech-nas
sudo visudo -c  # 驗證語法

# 方法二：手動新增（將 your_user 替換為實際使用者）
echo 'your_user ALL=(ALL) NOPASSWD: /usr/sbin/smartctl' | sudo tee /etc/sudoers.d/protech-nas
sudo chmod 0440 /etc/sudoers.d/protech-nas
```

> 💡 若未設定 sudoers，S.M.A.R.T. 相關功能會出現 `Permission denied` 錯誤。

| 功能 | 需要套件 | 需要 root |
|------|----------|-----------|
| S.M.A.R.T. 讀取 | smartmontools | ✅ |
| S.M.A.R.T. 自檢 | smartmontools | ✅ |
| 磁碟格式化 | — (內建 mkfs) | ✅ |
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

## License

MIT
