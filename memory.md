# ProTech NAS — Architecture & Design Notes

## 系統概述

ProTech NAS 是一套自建 NAS 管理系統，以 FastAPI 為後端 API 層，包裝 Linux 系統工具（Samba, NFS, Docker, mdadm 等），前端使用 Vue.js 3 + Element Plus 提供桌面式管理介面。

## 模組架構

### Backend Services

| Service | 職責 | 底層工具 |
|---------|------|---------|
| system_service | 系統監控 (CPU/RAM/Disk/Network) | psutil |
| storage_service | 磁碟/RAID/掛載管理 | lsblk, mdadm, mount, df |
| samba_service | SMB 共享管理 | /etc/samba/smb.conf, smbd |
| nfs_service | NFS 匯出管理 | /etc/exports, exportfs |
| docker_service | Docker 容器/映像管理 | Docker SDK (docker-py) |
| user_service | 系統帳號管理 | useradd, userdel, smbpasswd |

### Frontend Pages

| 頁面 | 路由 | 功能 |
|------|------|------|
| Login | /login | JWT 登入 |
| Dashboard | /dashboard | 系統狀態儀表板 |
| Storage | /storage | 磁碟/掛載/RAID |
| Shares | /shares | SMB + NFS 管理 |
| Docker | /docker | 容器管理 + 日誌 |
| Users | /users | 帳號/群組管理 |

## API 路由表

```
POST /api/auth/login         → JWT token
GET  /api/auth/me            → 當前使用者

GET  /api/dashboard          → 系統資訊

GET  /api/storage/disks      → lsblk 磁碟列表
GET  /api/storage/mounts     → df 掛載列表
GET  /api/storage/raid       → /proc/mdstat
POST /api/storage/mount      → 掛載磁碟
POST /api/storage/unmount    → 卸載磁碟

GET  /api/shares/smb         → SMB 共享列表
POST /api/shares/smb         → 建立 SMB 共享
DEL  /api/shares/smb/{name}  → 刪除 SMB 共享
GET  /api/shares/nfs         → NFS 匯出列表
POST /api/shares/nfs         → 建立 NFS 匯出
DEL  /api/shares/nfs         → 刪除 NFS 匯出

GET  /api/docker/containers  → 容器列表
POST /api/docker/containers/{id}/start → 啟動
POST /api/docker/containers/{id}/stop  → 停止
DEL  /api/docker/containers/{id}       → 刪除
GET  /api/docker/containers/{id}/logs  → 日誌
GET  /api/docker/images      → 映像列表
POST /api/docker/images/pull → 拉取映像

GET  /api/users              → 使用者列表
POST /api/users              → 建立使用者
DEL  /api/users/{username}   → 刪除使用者
PUT  /api/users/{username}/password → 改密碼
GET  /api/users/groups       → 群組列表
POST /api/users/groups       → 建立群組
DEL  /api/users/groups/{name}→ 刪除群組
```

## 安全性

- **認證方式**：JWT Bearer Token (HS256)
- **Token 有效期**：24 小時（可配置）
- **敏感操作**：所有 API 需要有效 token（除了 /api/auth/login）
- **系統權限**：後端需以 root 或有 sudo 權限的使用者執行（操作 mount/useradd/smb.conf）
- **生產建議**：使用 nginx reverse proxy + HTTPS

## 部署架構

```
[Nginx]  ← HTTPS (port 443)
   │
   ├── /          → frontend/dist/ (static)
   └── /api/*     → uvicorn (port 8000)
```

## 開發環境

- Python 3.10+
- Node.js 20.x
- Debian 12 / Ubuntu 22.04+
- Docker 24+

## 目標硬體

- Intel N100 (4C/4T, 6W TDP)
- 16GB DDR4
- 256GB NVMe (系統)
- 2-4x HDD (資料 RAID)
- 2.5GbE x2

## 未來規劃 (Post-MVP)

- [ ] BTRFS 快照管理
- [ ] 定時備份任務
- [ ] 媒體伺服器整合 (Jellyfin)
- [ ] AI 照片辨識
- [ ] 行動 APP
- [ ] 系統通知 (Email / Telegram)
- [ ] 多語言 (i18n)
- [ ] 2FA 雙因子認證
