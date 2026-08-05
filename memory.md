# ProTech NAS — 開發筆記

## 專案概況

- 自建 NAS 管理系統，仿 fnOS，基於 FastAPI + Vue.js 3 + Element Plus
- 專案路徑：`/home/alex_chiang/projects/protech-nas`
- Backend：Python 3.11+ / FastAPI / Uvicorn，入口 `src.main:app`，port 8000
- Frontend：Vue.js 3 / Vite / Element Plus / Pinia / vue-i18n，dev port 5173
- 92 個 API endpoints，12 個 routers，12 個 service modules

## 生產部署（開機自動啟動）

已建立以下部署檔案（2026-08-04）：

| 檔案 | 用途 |
|------|------|
| `scripts/protech-nas.service` | systemd service，Uvicorn --workers 2，開機自動啟動 backend |
| `scripts/protech-nas-nginx.conf` | Nginx 設定：前端 SPA 託管 + `/api` 反向代理到 backend + gzip + 10G 上傳限制 |
| `scripts/deploy.sh` | 一鍵部署腳本（build frontend → 部署 → systemd → nginx → sudoers） |

### 部署指令

```bash
# 前置：安裝系統依賴與專案依賴
bash scripts/install.sh
bash scripts/setup_deps.sh

# 一鍵部署（需 sudo）
sudo bash scripts/deploy.sh
```

### 管理指令

```bash
systemctl status protech-nas        # 查看狀態
journalctl -u protech-nas -f        # 即時 log
sudo systemctl restart protech-nas  # 重啟 backend
sudo systemctl reload nginx         # 重載前端設定
```

### 部署架構

```
Browser → Nginx(:80)
            ├── / → /var/www/protech-nas/ (Vue SPA)
            └── /api/* → proxy → Uvicorn(:8000) (FastAPI backend)
```

## 重要設定

- `.env` 需設定 `SECRET_KEY`（生產環境必改）
- 預設帳號：admin / admin123（生產環境必改）
- sudoers 設定：`/etc/sudoers.d/protech-nas`（免密碼執行特權指令）
- Backend service 以 `alex_chiang` 使用者執行（deploy.sh 會自動替換）

## RAID 1 HA（高可用開機鏡像）

- 2 顆 HDD → 自動偵測，建議設定 RAID 1 資料碟鏡像
- 1 顆 HDD → 跳過，單碟模式
- 腳本：`scripts/setup-raid1-ha.sh`（資料碟 RAID 1 設定）
- 腳本：`scripts/migrate-to-raid1.sh`（說明線上遷移風險，建議重裝）
- deploy.sh 會自動偵測磁碟數量並提示是否需要設定 RAID

### RAID 1 管理指令

```bash
cat /proc/mdstat               # 查看 RAID 狀態
mdadm --detail /dev/md0        # 陣列詳情
mdadm --add /dev/md0 /dev/sdX1 # 加入新碟重建鏡像
```

## 硬體規格（已修正）

- CPU：Intel Atom D2550 @ 1.86GHz（2C/4T, 32nm, TDP 10W）
- RAM：~4GB DDR3
- 資源有限，不適合跑 Docker daemon 來包裝 NAS 系統本身
- Docker 適合讓使用者部署自己的容器（Jellyfin、Nextcloud 等）

## 系統需求

- OS：Debian 12 / Ubuntu 22.04+
- Hardware：Intel Atom D2550 / 4GB RAM
- 必要套件：python3, nginx, samba, nfs-kernel-server, smartmontools
- 選用套件：lm-sensors, traceroute, dnsutils, wireguard, certbot, exfatprogs, btrfs-progs, docker.io
- **NAS 不需要安裝 Node.js**（frontend 由 OTA Server / CI 預建）

## 系統更新功能（OTA — 已實作 2026-08-05）

### 設計決策

- **不是 apt 套件更新**，是 ProTech NAS 應用程式自身的 OTA 更新
- **不用 .bin 韌體**，用 git-based code deployment + service restart
- **NAS 不需要 Node.js**：frontend 由 Server 端 / CI 預先 build，NAS 只下載 `frontend.tar.gz` 解壓
- 支援 Systemd 和 Docker 兩種部署模式

### OTA Server

- 獨立 Server 運行在 port 8060
- API 規格：`docs/ota-api.md`
- NAS 主動向 Server 檢查更新（pull model）

### OTA 流程

```
NAS → POST /api/ota/check → 有新版本？
NAS → GET /api/ota/download/{device_id} → 取得 git hash + instructions
NAS → GET /api/ota/artifacts/{version}/frontend.tar.gz → 下載預建 frontend
NAS → 執行更新（git checkout → pip install → deploy frontend → restart）
NAS → 健康檢查 → 失敗自動回滾
NAS → POST /api/ota/report → 回報結果
```

### 實作檔案

| 檔案 | 說明 |
|------|------|
| `VERSION` | 目前版本號（根目錄） |
| `docs/ota-api.md` | OTA API 完整規格（含 Systemd / Docker 兩種模式） |
| `backend/src/config.py` | `OTA_SERVER_URL`, `OTA_DEVICE_ID`, `OTA_DEPLOY_MODE`, `OTA_APP_DIR`, `OTA_WEB_DIR` |
| `backend/src/services/system_service.py` | `check_updates()` → 呼叫 OTA Server；`apply_updates()` → 完整 OTA 流程含回滾 |
| `backend/src/routers/system.py` | `GET /api/system/updates`、`POST /api/system/updates/apply` |
| `scripts/ota-update.sh` | 獨立 bash 腳本，可由 cron 或手動觸發 |

### 環境變數（.env）

```
OTA_SERVER_URL=http://your-server:8060
OTA_DEVICE_ID=1
OTA_DEPLOY_MODE=systemd        # systemd / docker
OTA_APP_DIR=/opt/protech-nas
OTA_WEB_DIR=/var/www/protech-nas
```

### 依賴

- `httpx`（已在 requirements.txt）— NAS 端呼叫 OTA Server API

### Cron 自動檢查（建議）

```bash
# 每天凌晨 3 點自動檢查並更新
0 3 * * * /opt/protech-nas/scripts/ota-update.sh >> /var/log/protech-nas-update.log 2>&1
```