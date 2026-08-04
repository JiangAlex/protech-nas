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

## 系統需求

- OS：Debian 12 / Ubuntu 22.04+
- Hardware：Intel N100 Mini-ITX / 16GB RAM
- 必要套件：python3, nodejs 18+, nginx, docker.io, samba, nfs-kernel-server, smartmontools
- 選用套件：lm-sensors, traceroute, dnsutils, wireguard, certbot, exfatprogs, btrfs-progs
