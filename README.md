# ProTech NAS

自建 NAS 管理系統 — 仿 fnOS 功能，基於 FastAPI + Vue.js 3 + Element Plus

## Features

- **系統儀表板** — CPU / RAM / 磁碟 / 網路即時監控
- **儲存管理** — 磁碟列表、RAID 狀態、掛載/卸載操作
- **檔案共享** — SMB (Samba) + NFS 共享資料夾 CRUD 管理
- **Docker 管理** — 容器啟停/刪除、映像管理、即時日誌查看
- **使用者管理** — 系統帳號 + Samba 帳號 + 群組管理

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI + Uvicorn |
| Frontend | Vue.js 3 + Vite + Element Plus + Pinia |
| Auth | JWT (python-jose) |
| System Integration | psutil, Docker SDK, subprocess (samba/nfs/mdadm) |
| Target Hardware | Intel N100 Mini-ITX |
| Target OS | Debian 12 / Ubuntu Server |

## Architecture

```
┌─────────────────────────────────────────────┐
│            Browser (Vue.js 3)                │
│         Element Plus + Pinia + Router        │
└─────────────────┬───────────────────────────┘
                  │ REST API (/api/*)
                  ▼
┌─────────────────────────────────────────────┐
│           FastAPI Backend                     │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌────┐ ┌────┐  │
│  │Dashbd│ │Storag│ │Shares│ │Dock│ │User│  │
│  └──┬───┘ └──┬───┘ └──┬───┘ └─┬──┘ └─┬──┘  │
│     │        │        │       │      │      │
│  psutil   lsblk    smb.conf Docker useradd  │
│           mdadm    exports   SDK   smbpasswd│
└─────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│     Linux (Debian 12 / Ubuntu Server)        │
│     Intel N100 + 16GB RAM + HDDs             │
└─────────────────────────────────────────────┘
```

## Installation

```bash
# 1. Clone
git clone https://github.com/JiangAlex/protech-nas.git
cd protech-nas

# 2. Install system dependencies (Debian/Ubuntu)
chmod +x scripts/install.sh
sudo ./scripts/install.sh

# 3. Install project dependencies
chmod +x scripts/setup_deps.sh
./scripts/setup_deps.sh

# 4. Configure
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY and admin credentials

# 5. Start backend
cd backend
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 6. Access Web UI
# http://<your-ip>:5173 (dev) or serve frontend/dist/ with nginx
```

## Development

```bash
# Backend (with auto-reload)
cd backend && source .venv/bin/activate
uvicorn src.main:app --reload --port 8000

# Frontend (dev server with HMR)
cd frontend
npm run dev
# → http://localhost:5173
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | 登入取得 JWT |
| GET | `/api/dashboard` | 系統監控資料 |
| GET | `/api/storage/disks` | 磁碟列表 |
| GET | `/api/storage/mounts` | 掛載點列表 |
| GET | `/api/storage/raid` | RAID 狀態 |
| GET | `/api/shares/smb` | SMB 共享列表 |
| POST | `/api/shares/smb` | 建立 SMB 共享 |
| GET | `/api/shares/nfs` | NFS 匯出列表 |
| GET | `/api/docker/containers` | Docker 容器列表 |
| POST | `/api/docker/containers/{id}/start` | 啟動容器 |
| POST | `/api/docker/containers/{id}/stop` | 停止容器 |
| GET | `/api/users` | 使用者列表 |
| POST | `/api/users` | 建立使用者 |

## Default Credentials

```
Username: admin
Password: admin123
```

## Related Projects

- **[barcode-warehouse-server](https://github.com/JiangAlex/barcode-warehouse-server)** — 倉管條碼系統後端
- **[esp32s3-barcode-scanner](https://github.com/JiangAlex/esp32s3-barcode-scanner)** — ESP32-S3 條碼掃描器

## License

MIT
