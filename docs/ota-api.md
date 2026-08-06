# OTA API 規格

NAS 設備主動連回 Server 檢查更新、取得下載資訊、回報更新結果。

## 流程概覽

```
┌─────────────┐                          ┌──────────────────┐
│  NAS 設備    │                          │  Server (:8060)  │
└──────┬──────┘                          └────────┬─────────┘
       │                                          │
       │  1. POST /api/ota/check                  │
       │  {device_id, current_version}            │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：是否有新版本                        │
       │←─────────────────────────────────────────│
       │                                          │
       │  2. GET /api/ota/download/{device_id}    │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：git repo / branch / 執行指令       │
       │←─────────────────────────────────────────│
       │                                          │
       │  3. GET /api/ota/artifacts/{version}/     │
       │     frontend.tar.gz                      │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：預建好的 frontend dist 壓縮檔      │
       │←─────────────────────────────────────────│
       │                                          │
       │  (NAS 執行更新...)                        │
       │                                          │
       │  4. POST /api/ota/report                 │
       │  {device_id, to_version, status}         │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：確認收到                            │
       │←─────────────────────────────────────────│
```

### 建置流程（Server 端 / CI）

```
開發者 git push
       │
       ▼
┌──────────────────────────────┐
│  CI / Server Build Pipeline   │
│                              │
│  1. npm ci                   │
│  2. npm run build            │
│  3. tar -czf frontend.tar.gz dist/  │
│  4. 上傳至 OTA Server artifacts     │
└──────────────────────────────┘
```

NAS 設備**不需要安裝 Node.js**，只需下載預建好的 `frontend.tar.gz` 解壓即可。

---

## API Endpoints

### 1. 檢查更新

**`POST /api/ota/check`**

NAS 設備傳送目前版本資訊，Server 比對最新版本回應是否需要更新。

#### Request Body

```json
{
  "device_id": 1,
  "current_version": "1.0.0",
  "current_git_hash": "abc1234d",
  "device_type": "nas",
  "deploy_mode": "systemd"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| device_id | int | ✅ | 設備 ID |
| current_version | string | 選填 | 目前版本號 |
| current_git_hash | string | 選填 | 目前 git commit hash |
| device_type | string | 選填 | 設備類型（device_id 未註冊時的 fallback） |
| deploy_mode | string | 選填 | 部署模式：`systemd` / `docker`（預設 `systemd`） |

#### Response（有更新）

```json
{
  "update_available": true,
  "current_version": "1.0.0",
  "latest_version": "1.1.0",
  "latest_git_hash": "def5678e",
  "changelog": "修正 XXX 問題，新增 YYY 功能",
  "download_url": "/api/ota/download/1",
  "frontend_artifact_url": "/api/ota/artifacts/1.1.0/frontend.tar.gz",
  "released_at": "2026-08-05T10:00:00Z"
}
```

#### Response（無更新）

```json
{
  "update_available": false,
  "current_version": "1.1.0",
  "latest_version": "1.1.0"
}
```

#### 副作用

- 更新設備的 `last_seen_at`、`status = "online"`
- 更新設備的 `current_version`、`current_git_hash`

---

### 2. 取得更新資訊

**`GET /api/ota/download/{device_id}`**

取得更新的詳細下載/執行資訊。Server 根據設備的 `deploy_mode` 回傳對應的 `instructions`。

#### Response（Systemd 部署）

```json
{
  "version": "1.1.0",
  "git_hash": "def5678e",
  "git_repo_url": "https://github.com/JiangAlex/protech-nas.git",
  "git_branch": "main",
  "deploy_mode": "systemd",
  "frontend_artifact_url": "/api/ota/artifacts/1.1.0/frontend.tar.gz",
  "frontend_checksum": "sha256:abc123...",
  "instructions": "cd /opt/protech-nas && git fetch origin main && git checkout def5678e && cd backend && source .venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart protech-nas"
}
```

#### Response（Docker 部署）

```json
{
  "version": "1.1.0",
  "git_hash": "def5678e",
  "git_repo_url": "https://github.com/JiangAlex/protech-nas.git",
  "git_branch": "main",
  "deploy_mode": "docker",
  "frontend_artifact_url": null,
  "frontend_checksum": null,
  "instructions": "cd /opt/protech-nas && git fetch origin main && git checkout def5678e && docker compose up -d --build"
}
```

> **注意：** Docker 部署時 frontend 包含在 image 內（Dockerfile 內建 build stage），不需要額外下載 artifact。

#### 欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| version | string | 目標版本號 |
| git_hash | string | 目標 git commit |
| git_repo_url | string | Git repository URL |
| git_branch | string | Git branch |
| deploy_mode | string | 部署模式：`systemd` / `docker` |
| frontend_artifact_url | string\|null | 預建 frontend 壓縮檔下載路徑 |
| frontend_checksum | string\|null | frontend.tar.gz 的 SHA256 校驗碼 |
| instructions | string | NAS 端執行的 shell 指令（僅 backend） |

#### Error Response

```json
{
  "detail": "No update available for this device"
}
```
Status: `404`

---

### 3. 下載 Frontend Artifact

**`GET /api/ota/artifacts/{version}/frontend.tar.gz`**

下載 Server 端預先建置好的 frontend 靜態檔壓縮包。

#### Response

- Content-Type: `application/gzip`
- Body: `frontend.tar.gz`（解壓後為 `dist/` 目錄）

#### 壓縮包結構

```
frontend.tar.gz
└── dist/
    ├── index.html
    ├── assets/
    │   ├── index-xxxxx.js
    │   ├── index-xxxxx.css
    │   └── ...
    └── favicon.ico
```

---

### 4. 回報更新結果

**`POST /api/ota/report`**

NAS 設備完成更新（或失敗）後回報結果。

#### Request Body

```json
{
  "device_id": 1,
  "from_version": "1.0.0",
  "to_version": "1.1.0",
  "to_git_hash": "def5678e",
  "status": "completed",
  "error_message": null
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| device_id | int | ✅ | 設備 ID |
| from_version | string | 選填 | 更新前版本 |
| to_version | string | ✅ | 目標版本 |
| to_git_hash | string | 選填 | 目標 git hash |
| status | string | ✅ | `completed` / `failed` / `rolled_back` |
| error_message | string | 選填 | 失敗時的錯誤訊息 |

#### Response

```json
{
  "success": true,
  "message": "Update report recorded: completed"
}
```

#### 副作用

- 更新設備的 `last_seen_at`、`status = "online"`
- 若 status = `completed`：更新 `current_version`、`current_git_hash`、`last_update_at`
- 建立一筆 `update_logs` 記錄

---

## NAS 端實作範例

### Part 1: Systemd 部署

適用於直接在 Linux 上以 systemd service 運行的 NAS（推薦用於 Atom D2550 / 4GB RAM）。

**更新流程：** git pull → pip install → restart service → 下載預建 frontend → 解壓部署

NAS 設備**不需要安裝 Node.js**。

```bash
#!/bin/bash
# NAS 系統更新腳本 — Systemd 部署
# 前置需求：curl, jq, tar, git, python3-venv

SERVER_URL="http://your-server:8060"
DEVICE_ID=1
APP_DIR="/opt/protech-nas"
WEB_DIR="/var/www/protech-nas"
CURRENT_VERSION=$(cat "$APP_DIR/VERSION" 2>/dev/null || echo "unknown")
CURRENT_HASH=$(cd "$APP_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# 1. 檢查更新
RESPONSE=$(curl -s -X POST "$SERVER_URL/api/ota/check" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"current_version\": \"$CURRENT_VERSION\",
    \"current_git_hash\": \"$CURRENT_HASH\",
    \"deploy_mode\": \"systemd\"
  }")

UPDATE_AVAILABLE=$(echo "$RESPONSE" | jq -r '.update_available')

if [ "$UPDATE_AVAILABLE" != "true" ]; then
  echo "已是最新版本"
  exit 0
fi

LATEST_VERSION=$(echo "$RESPONSE" | jq -r '.latest_version')
echo "發現新版本: $LATEST_VERSION"

# 2. 取得更新資訊
DOWNLOAD_INFO=$(curl -s "$SERVER_URL/api/ota/download/$DEVICE_ID")
TARGET_HASH=$(echo "$DOWNLOAD_INFO" | jq -r '.git_hash')
FRONTEND_URL=$(echo "$DOWNLOAD_INFO" | jq -r '.frontend_artifact_url')
FRONTEND_CHECKSUM=$(echo "$DOWNLOAD_INFO" | jq -r '.frontend_checksum')

# 3. 備份目前版本（方便回滾）
OLD_HASH=$(cd "$APP_DIR" && git rev-parse HEAD)
sudo cp -r "$WEB_DIR" "${WEB_DIR}.bak"

# 4. 更新 Backend
echo "更新 Backend..."
cd "$APP_DIR"

git fetch origin main && git checkout "$TARGET_HASH" || { STATUS="failed"; ERROR="git checkout failed"; }

if [ -z "$STATUS" ]; then
  cd backend
  source .venv/bin/activate
  pip install -r requirements.txt -q || { STATUS="failed"; ERROR="pip install failed"; }
  cd ..
fi

if [ -z "$STATUS" ]; then
  sudo systemctl restart protech-nas || { STATUS="failed"; ERROR="systemctl restart failed"; }
fi

# 5. 更新 Frontend（下載預建 artifact）
if [ -z "$STATUS" ]; then
  echo "下載 Frontend artifact..."
  TMPFILE=$(mktemp /tmp/frontend-XXXXXX.tar.gz)

  curl -sf "$SERVER_URL$FRONTEND_URL" -o "$TMPFILE" || { STATUS="failed"; ERROR="frontend download failed"; }

  # 校驗 checksum
  if [ -z "$STATUS" ] && [ "$FRONTEND_CHECKSUM" != "null" ]; then
    EXPECTED=$(echo "$FRONTEND_CHECKSUM" | sed 's/sha256://')
    ACTUAL=$(sha256sum "$TMPFILE" | awk '{print $1}')
    if [ "$EXPECTED" != "$ACTUAL" ]; then
      STATUS="failed"
      ERROR="frontend checksum mismatch"
    fi
  fi

  # 解壓部署
  if [ -z "$STATUS" ]; then
    sudo rm -rf "$WEB_DIR"
    sudo mkdir -p "$WEB_DIR"
    sudo tar -xzf "$TMPFILE" -C "$WEB_DIR" --strip-components=1
  fi

  rm -f "$TMPFILE"
fi

# 6. 健康檢查
if [ -z "$STATUS" ]; then
  sleep 3
  if curl -sf http://localhost:8000/api/health > /dev/null; then
    STATUS="completed"
    ERROR=""
    echo "$LATEST_VERSION" > "$APP_DIR/VERSION"
  else
    STATUS="failed"
    ERROR="Health check failed after update"
  fi
fi

# 7. 若失敗則回滾
if [ "$STATUS" = "failed" ] || [ "$STATUS" = "" ]; then
  echo "更新失敗，回滾中..."
  cd "$APP_DIR"
  git checkout "$OLD_HASH"
  cd backend && source .venv/bin/activate && pip install -r requirements.txt -q
  sudo systemctl restart protech-nas
  sudo rm -rf "$WEB_DIR"
  sudo mv "${WEB_DIR}.bak" "$WEB_DIR"
  STATUS="rolled_back"
fi

# 清理備份
sudo rm -rf "${WEB_DIR}.bak" 2>/dev/null

# 8. 回報結果
curl -s -X POST "$SERVER_URL/api/ota/report" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"from_version\": \"$CURRENT_VERSION\",
    \"to_version\": \"$LATEST_VERSION\",
    \"to_git_hash\": \"$TARGET_HASH\",
    \"status\": \"$STATUS\",
    \"error_message\": \"$ERROR\"
  }"

echo "更新結果: $STATUS"
```

---

### Part 2: Docker 部署

適用於以 Docker Compose 運行的 NAS（適合資源充足的設備，或需要環境隔離的場景）。

**更新流程：** git pull → docker compose build（含 frontend multi-stage build）→ docker compose up

Frontend 由 Dockerfile 的 build stage 處理，不需要額外下載 artifact。

```bash
#!/bin/bash
# NAS 系統更新腳本 — Docker 部署
# 前置需求：curl, jq, git, docker

SERVER_URL="http://your-server:8060"
DEVICE_ID=1
APP_DIR="/opt/protech-nas"
CURRENT_VERSION=$(cat "$APP_DIR/VERSION" 2>/dev/null || echo "unknown")
CURRENT_HASH=$(cd "$APP_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# 1. 檢查更新
RESPONSE=$(curl -s -X POST "$SERVER_URL/api/ota/check" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"current_version\": \"$CURRENT_VERSION\",
    \"current_git_hash\": \"$CURRENT_HASH\",
    \"deploy_mode\": \"docker\"
  }")

UPDATE_AVAILABLE=$(echo "$RESPONSE" | jq -r '.update_available')

if [ "$UPDATE_AVAILABLE" != "true" ]; then
  echo "已是最新版本"
  exit 0
fi

LATEST_VERSION=$(echo "$RESPONSE" | jq -r '.latest_version')
echo "發現新版本: $LATEST_VERSION"

# 2. 取得更新指令
DOWNLOAD_INFO=$(curl -s "$SERVER_URL/api/ota/download/$DEVICE_ID")
TARGET_HASH=$(echo "$DOWNLOAD_INFO" | jq -r '.git_hash')

# 3. 記錄目前版本（方便回滾）
OLD_HASH=$(cd "$APP_DIR" && git rev-parse HEAD)

# 4. 執行更新
echo "執行更新..."
cd "$APP_DIR"

# 拉取新版本
git fetch origin main && git checkout "$TARGET_HASH" || {
  curl -s -X POST "$SERVER_URL/api/ota/report" \
    -H "Content-Type: application/json" \
    -d "{\"device_id\":$DEVICE_ID,\"to_version\":\"$LATEST_VERSION\",\"status\":\"failed\",\"error_message\":\"git checkout failed\"}"
  exit 1
}

# 重建並啟動容器（Dockerfile 內 multi-stage 會 build frontend）
if docker compose up -d --build; then
  sleep 5

  # 健康檢查
  if curl -sf http://localhost:8000/api/health > /dev/null; then
    STATUS="completed"
    ERROR=""
    echo "$LATEST_VERSION" > "$APP_DIR/VERSION"
  else
    STATUS="failed"
    ERROR="Health check failed after container restart"
  fi
else
  STATUS="failed"
  ERROR="docker compose up failed"
fi

# 5. 若失敗則回滾
if [ "$STATUS" = "failed" ]; then
  echo "更新失敗，回滾中..."
  cd "$APP_DIR"
  git checkout "$OLD_HASH"
  docker compose up -d --build
  sleep 5
  STATUS="rolled_back"
fi

# 6. 回報結果
curl -s -X POST "$SERVER_URL/api/ota/report" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"from_version\": \"$CURRENT_VERSION\",
    \"to_version\": \"$LATEST_VERSION\",
    \"to_git_hash\": \"$TARGET_HASH\",
    \"status\": \"$STATUS\",
    \"error_message\": \"$ERROR\"
  }"

echo "更新結果: $STATUS"
```

---

## 部署模式比較

| 面向 | Systemd | Docker |
|------|---------|--------|
| Frontend 更新 | 下載預建 `frontend.tar.gz` 解壓 | Dockerfile multi-stage build |
| NAS 需要 Node.js | ❌ 不需要 | ❌ 不需要（容器內建） |
| 更新原子性 | 分步驟，可能中途失敗 | image 替換，較原子 |
| 回滾速度 | git checkout + pip + restart + 還原備份 | git checkout + docker compose up |
| 資源開銷 | 低（直接運行） | 高（Docker daemon ~100-200MB） |
| 系統整合 | 直接存取 smartctl/mdadm/iptables | 需 privileged + volume mount |
| 適用硬體 | Atom D2550 / 4GB RAM ✅ | 建議 8GB+ RAM |
| 環境隔離 | 依賴 .venv | 完全隔離 |

---

## 注意事項

1. **Server 端需先建立版本記錄**：透過管理介面或 API 建立 `firmware_versions` 記錄，標記 `is_latest=true` 和 `is_stable=true`
2. **Server 端需預建 Frontend**：CI/CD 或手動執行 `npm run build`，將 `dist/` 打包為 `frontend.tar.gz` 上傳至 OTA Server
3. **Device 需先註冊**：透過管理介面或 API 建立設備記錄，取得 `device_id`，並設定 `deploy_mode`
4. **網路可達性**：NAS 設備必須能連到 Server 的 port 8060
5. **VERSION 檔案**：在 repo 根目錄放置 `VERSION` 檔案，NAS 端讀取回報 `current_version`
6. **NAS 不需要 Node.js**：Systemd 模式下載預建檔；Docker 模式由容器內 build
7. **未來規劃**：加入 `X-Device-Token` header 認證，避免未授權設備呼叫 API

---

## 實作重點記錄

### OTA Server API 路徑

Server 的 NAS OTA 路由前綴為 `/api/ota/nas/`（非 `/api/ota/`）：

| 用途 | 路徑 |
|------|------|
| 檢查更新 | `POST /api/ota/nas/check` |
| 取得更新資訊 | `GET /api/ota/nas/download/{device_id}` |
| 下載 Frontend Artifact | `GET /api/ota/nas/artifacts/{version}/frontend.tar.gz` |
| 上傳 Frontend Artifact | `POST /api/ota/nas/artifacts/{version}/upload` |
| 回報更新結果 | `POST /api/ota/nas/report` |

### 版本比對邏輯

Server 判定是否有更新時，比對 **version + git hash**：
- version 相同 **且** git hash 相同 → 無更新
- version 相同但 git hash 不同 → 有更新（支援 downgrade / hotfix）
- version 不同 → 有更新

以 Server 端的版本記錄為唯一真相來源，NAS 必須對齊 Server 指定的 git hash，不管是升級還是降級。

### Systemd 模式的 Self-Restart 問題

Backend 是 systemd service，`apply_updates()` 裡不能直接 `systemctl restart protech-nas`（會殺死自己，導致前端收不到回應）。

**解決方案：** 使用 `systemd-run --on-active=2s` 延遲重啟：

```python
# 延遲 2 秒重啟，讓 API 先回應前端
_sudo_run(["systemd-run", "--on-active=2s", "systemctl", "restart", "protech-nas"])
```

流程：
1. git checkout + pip install + deploy frontend → 完成
2. 更新 VERSION 檔案 + 回報 OTA Server
3. **先回傳成功給前端**（「系統已更新，服務即將重啟...」）
4. 延遲 2 秒後 systemd restart → 新 code 生效

Docker 模式不受此限制（backend 在容器內，restart container 不會影響 API process）。

### Frontend Artifact 上傳

OTA Server 需要預先上傳每個版本的 `frontend.tar.gz`：

```bash
# 在開發機 / CI 上
cd frontend && npm run build
tar -czf frontend.tar.gz dist/

# 上傳到 OTA Server
curl -X POST http://blog.softsnail.com:8060/api/ota/nas/artifacts/{version}/upload \
  -F "file=@frontend.tar.gz"
```

若 artifact 未上傳，NAS 更新時會因為下載 404 而失敗並回滾。

### OTA Server 資料準備步驟

1. **建立 Device Type**：`POST /api/device-types` → `{"name": "nas", "display_name": "ProTech NAS", "update_method": "git_pull"}`
2. **註冊 Device**：`POST /api/devices` → `{"device_type_id": 1, "name": "...", "ip_address": "..."}`
3. **建立 Firmware Version**：`POST /api/firmware` → `{"device_type_id": 1, "version": "1.0.0", "git_hash": "...", "is_latest": true, "is_stable": true}`
4. **上傳 Frontend Artifact**：`POST /api/ota/nas/artifacts/1.0.0/upload`

### NAS 端環境變數

```env
OTA_SERVER_URL=http://blog.softsnail.com:8060
OTA_DEVICE_ID=1
OTA_DEPLOY_MODE=systemd
OTA_APP_DIR=/home/alex_chiang/projects/protech-nas
OTA_WEB_DIR=/var/www/protech-nas
```

---

## 正式出貨規劃（方案 B：純 Artifact 部署）

目前實驗階段使用 git clone（方案 A），正式 DUT 出貨將改為純 artifact 下載（方案 B）。

### 差異

| | 實驗階段（方案 A） | 正式出貨（方案 B） |
|---|---|---|
| DUT 上有 .git | ✅ | ❌ |
| 更新方式 | git fetch + checkout | 下載 backend.tar.gz + frontend.tar.gz |
| 需要連 GitHub | ✅ | ❌（只需連 OTA Server） |
| 下載量 | 差異（小） | 全量（數 MB） |
| 回滾方式 | git checkout old_hash | 保留前一版 tar 備份 |

### 方案 B 的 OTA Server 需要額外存放

```
data/artifacts/{version}/
├── backend.tar.gz      ← 完整 backend source + requirements
└── frontend.tar.gz     ← 預建 dist
```

### 方案 B 的 DUT 更新流程

1. 下載 `backend.tar.gz` → 解壓覆蓋 `/opt/protech-nas/backend/`
2. 下載 `frontend.tar.gz` → 解壓到 `/var/www/protech-nas/`
3. `pip install -r requirements.txt`
4. `systemd-run --on-active=2s systemctl restart protech-nas`
5. 回報結果

### 方案 B 的 CI 需要

- 打包 `backend.tar.gz`（排除 .venv、__pycache__、.git）
- 打包 `frontend.tar.gz`（npm run build 後的 dist/）
- 上傳兩個 artifact 到 OTA Server

### 切換時間點

當第一台正式 DUT 出貨時，實作方案 B 的 `apply_updates()` 邏輯（下載 + 解壓 + 覆蓋）。

---

## 目前實驗狀態記錄（2026-08-06）

### 環境

| 項目 | 資訊 |
|------|------|
| NAS (DUT) | 192.168.131.150 |
| OTA Server | blog.softsnail.com:8060 |
| GitHub Repo | https://github.com/JiangAlex/protech-nas.git |
| Device ID | 1 |
| Device Type | nas (id=1) |
| Deploy Mode | systemd |
| 目前版本 | 1.0.0 |

### 已完成

- [x] NAS 端 `check_updates()` 呼叫 OTA Server `/api/ota/nas/check`
- [x] NAS 端 `apply_updates()` 完整 OTA 流程（git fetch → checkout → pip install → 下載 frontend → restart）
- [x] 延遲 restart（`systemd-run --on-active=2s`）避免殺死自己
- [x] 回滾機制（失敗自動 rollback）
- [x] NAS 回報 MAC address
- [x] 前端「系統更新」頁面顯示版本 + git hash + changelog
- [x] Dashboard 顯示系統版本 + Git Hash
- [x] `/api/health` 回傳動態 version + git_hash
- [x] GitHub Actions CI 自動 build frontend + 上傳 artifact 到 OTA Server
- [x] OTA Server 版本比對：version + git hash（支援 upgrade / downgrade）
- [x] OTA Server 群發 API（`/api/ota/batch/push`）
- [x] Device model 加入 SKU / customer_id / mac_address

### 已知問題

- CI 上傳 artifact 後，firmware 記錄的 `frontend_checksum` 需要同步更新（目前由 artifact_service 動態計算）
- `--workers 2` 時 APScheduler 可能只在 parent process 跑，metrics 記錄可能不正常
- 正式 DUT 不會有 `.git`，需要切方案 B（artifact 全量下載）

### 測試步驟

```bash
# 1. 退版測試（模擬 DUT 落後）
cd /home/alex_chiang/projects/protech-nas
git checkout <old_hash>
sudo systemctl restart protech-nas

# 2. 到 Web UI「系統更新」→「檢查更新」→ 顯示有新版
# 3. 「套用更新」→ 成功訊息 → 服務重啟 → 前端 + 後端更新

# 4. 驗證
curl -s http://192.168.131.150/api/health
# 應顯示新的 version + git_hash

# 5. 切回 main
git checkout main
sudo systemctl restart protech-nas
```

---

## 設計建議與規劃

### Artifact 存放策略

Server 端需要一個目錄存放各版本的預建 frontend：

```
/data/artifacts/
├── 1.0.0/
│   └── frontend.tar.gz
├── 1.1.0/
│   └── frontend.tar.gz
└── 1.2.0/
    └── frontend.tar.gz
```

- 上傳 artifact 時自動計算 SHA256 checksum，存入 `firmware_versions.file_checksum`
- 可設定保留最近 N 個版本，自動清理舊版

### 更新鎖機制

避免 user 連按多次「系統更新」導致同時執行多個更新程序：

```bash
LOCK_FILE="/tmp/protech-nas-update.lock"

if [ -f "$LOCK_FILE" ]; then
  echo "更新進行中，請稍後再試"
  exit 1
fi

trap "rm -f $LOCK_FILE" EXIT
touch "$LOCK_FILE"

# ... 執行更新 ...
```

Server 端也可在 `devices` 表加上 `update_status` 欄位：
- `idle` — 無更新進行中
- `updating` — 更新中（check 時若偵測到此狀態，拒絕新的更新請求）

### Rollback 策略

| 策略 | 說明 | 磁碟需求 |
|------|------|----------|
| 保留前一版備份 | `${WEB_DIR}.bak` + 記錄 `OLD_HASH` | 低（約 frontend 大小） |
| 保留前 N 版 | `/var/www/protech-nas-v1.0.0/` 多版本目錄 | 中 |
| Symlink 切換 | `/var/www/current → /var/www/v1.1.0/` | 中（但切換瞬間完成） |

**建議**：對 4GB RAM / 有限磁碟的 NAS，使用 symlink 切換 + 只保留前一版：

```bash
# 部署新版
sudo tar -xzf frontend.tar.gz -C /var/www/protech-nas-v1.1.0/

# 切換（原子操作）
sudo ln -sfn /var/www/protech-nas-v1.1.0 /var/www/protech-nas-current

# 清除舊版（保留前一版）
sudo rm -rf /var/www/protech-nas-v0.9.0/
```

### 漸進式更新（Canary Deploy）

設備數量多時，避免一次全部更新導致大規模故障：

```
階段 1: 更新 1-2 台測試設備 → 等待 10 分鐘
       ↓ 健康檢查通過
階段 2: 更新 30% 設備 → 等待 30 分鐘
       ↓ 無異常通知
階段 3: 更新剩餘所有設備
```

可在 `firmware_versions` 表加上 rollout 欄位：
- `rollout_percentage`: 0-100（目前開放更新的比例）
- `rollout_stage`: `canary` / `partial` / `full`

設備 check 更新時，Server 根據 rollout 狀態決定是否回傳 `update_available: true`。

### 安全認證（未來）

加入 `X-Device-Token` header 認證，每台設備有獨立的 token：

```
POST /api/ota/check
X-Device-Token: <device-specific-token>
```

- Token 在設備註冊時產生，存於 `devices.config` JSON
- Server 驗證 token 對應的 device_id 一致
- 防止未授權設備呼叫 OTA API
