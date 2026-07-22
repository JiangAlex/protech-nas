# Frontend — 尚未實作功能清單（詳細規格）

> 更新日期：2026-07-20
>
> 前端（Vue.js 3 + Element Plus）尚未實作的頁面、元件與功能。
> 每項包含：元件結構、依賴 API、狀態管理、UX 細節、驗證規則。

---

## 1. 儲存管理頁面增強

---

### 格式化操作 UI 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<FormatDiskDialog>` — 嵌入 `Storage.vue` |
| 結構 | el-dialog → el-steps（選碟 → 選 FS → 確認） |
| 依賴 API | `GET /api/storage/disks`（列出可格式化裝置）<br>`POST /api/storage/format` |
| 狀態管理 | 本地 reactive state（selectedDevice, fsType, step） |
| UX 細節 | ① 僅顯示未掛載的裝置<br>② 系統碟灰色不可選<br>③ 最終確認需輸入裝置名稱（防誤操作）<br>④ 格式化中顯示 loading + 禁止關閉 |
| 驗證規則 | device 必選；fsType 必選 (`ext4`/`xfs`/`btrfs`) |
| 注意事項 | ⚠️ 不可逆操作紅色警告文字 |

---

### S.M.A.R.T. 健康面板 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<SmartPanel>` — Storage.vue 新 Tab |
| 結構 | el-table 磁碟列表 + 展開行顯示 attributes + el-tag 狀態標記 |
| 依賴 API | `GET /api/storage/smart/{device}`<br>`POST /api/storage/smart/{device}/test` |
| 狀態管理 | `ref(smartData)` per device |
| UX 細節 | ① PASSED = 綠色 tag，FAILED = 紅色<br>② 溫度用 progress bar 帶色彩閾值<br>③ 「執行自檢」按鈕 + 預估時間提示<br>④ 自動每 60 秒刷新溫度 |
| 驗證規則 | 無（唯讀顯示） |

---

### 掛載/卸載按鈕 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `Storage.vue` 掛載 Tab |
| 結構 | 每列增加「卸載」按鈕；工具列增加「掛載」按鈕 + dialog |
| 依賴 API | `POST /api/storage/mount`<br>`POST /api/storage/unmount` |
| UX 細節 | 卸載前確認 `ElMessageBox.confirm`；成功後刷新列表 |
| 驗證規則 | mount: device + mount_point 必填；fs_type 預設 ext4 |

---

### 分割區管理 UI 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<PartitionManager>` — Storage.vue 新 Tab |
| 結構 | 磁碟選擇 → 視覺化分割區 bar → 建立/刪除按鈕 |
| 依賴 API | `POST /api/storage/partition`<br>`DELETE /api/storage/partition/{device}` |
| UX 細節 | 用 stacked bar 圖示現有分割區佔比 |
| 驗證規則 | size 必填且不超過可用空間 |

---

### RAID 建立精靈 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<RaidWizardDialog>` |
| 結構 | el-steps：選 level → 選碟 → 設定 spare → 確認 |
| 依賴 API | `POST /api/storage/raid/create` |
| UX 細節 | 依 level 顯示最少碟數提示；勾選碟自動計算可用容量 |
| 驗證規則 | level 必選；devices 數 >= level 需求；至少 2 碟 |

---

### fstab 管理頁面 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<FstabManager>` — Storage.vue 新 Tab |
| 依賴 API | `GET /api/storage/fstab`<br>`POST /api/storage/fstab`<br>`DELETE /api/storage/fstab` |
| UX 細節 | 表格列出 entries；新增用 dialog；刪除需確認；系統掛載點標記為「不可刪」 |

---

### 磁碟使用量圖表 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<DiskUsageChart>` |
| 結構 | ECharts 折線圖（日期 x 軸，使用率 y 軸） |
| 依賴 API | `GET /api/storage/usage/history` |
| 依賴套件 | `echarts` + `vue-echarts` |
| UX 細節 | 切換時間範圍（7d/30d/90d）；hover 顯示數值 |

---

## 2. 檔案共享頁面增強

---

### SMB 共享編輯 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `Shares.vue` SMB table + `<EditSMBDialog>` |
| 結構 | 每列新增「編輯」按鈕 → 彈出 dialog 填入現有值 |
| 依賴 API | `PUT /api/shares/smb/{name}` |
| 狀態管理 | 複製 row 資料到 editForm reactive |
| UX 細節 | 編輯時顯示目前值；儲存後刷新列表 |
| 驗證規則 | name 唯讀不可改；path 必填 |

---

### NFS 匯出編輯 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `Shares.vue` NFS table + `<EditNFSDialog>` |
| 依賴 API | `PUT /api/shares/nfs/{path}` |
| UX 細節 | clients 提供格式提示 placeholder |
| 驗證規則 | clients 必填；格式提示 `IP/CIDR(options)` |

---

### ACL 權限設定面板 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<AclPanel>` — Shares.vue 每個共享的展開面板 |
| 結構 | el-table（使用者/群組 + 權限 checkbox rwx） + 新增/移除按鈕 |
| 依賴 API | `GET /api/shares/smb/{name}/acl`<br>`PUT /api/shares/smb/{name}/acl` |
| UX 細節 | checkbox 群組（讀/寫/執行）；使用者下拉從系統用戶列表選取 |
| 驗證規則 | 至少選一個權限 |

---

### 服務狀態顯示 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | Shares.vue 頂部 status bar |
| 依賴 API | `GET /api/shares/smb/status`<br>`GET /api/shares/nfs/status` |
| UX 細節 | 綠點/紅點指示運行狀態 + 目前連線數 badge |

---

## 3. 檔案管理器 🆕

---

### 主頁面 `views/Files.vue` 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `views/Files.vue` + 子元件群 |
| 結構 | 上方工具列 + 麵包屑<br>左側資料夾樹（可選）<br>中間檔案列表（表格/網格切換）<br>右側詳情面板（可選） |
| 路由 | `/files` — 加入 router + AppLayout sidebar |
| 狀態管理 | `stores/files.js`（Pinia）<br>`currentPath`, `items`, `selected`, `loading`, `viewMode` |
| 依賴 API | `GET /api/files/list` |
| UX 細節 | ① 雙擊資料夾進入<br>② 單擊選取（Ctrl 多選、Shift 範圍選）<br>③ 排序（名稱/大小/日期）<br>④ 空目錄顯示提示圖 |

---

### 麵包屑導航 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<FileBreadcrumb>` |
| 結構 | el-breadcrumb，每段路徑可點擊跳轉 |
| UX 細節 | 路徑過長時省略中間段（`/data/.../deep/folder`） |

---

### 檔案上傳 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<FileUploader>` |
| 結構 | el-upload（drag） + 自訂 progress 列表 |
| 依賴 API | `POST /api/files/upload` |
| UX 細節 | ① 拖拽上傳區域<br>② 多檔並行上傳（限 3 並行）<br>③ 每檔獨立 progress bar<br>④ 失敗可重試<br>⑤ 上傳完成自動刷新列表 |
| 驗證規則 | 單檔上限 2GB；可設定禁止副檔名 |

---

### 檔案下載 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | 工具列按鈕 + 右鍵選單 |
| 依賴 API | `GET /api/files/download?path=...` |
| UX 細節 | 單檔直接下載；多選時考慮打包（需 compress API） |

---

### 建立資料夾 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<NewFolderDialog>` 或 inline 編輯 |
| 依賴 API | `POST /api/files/mkdir` |
| 驗證規則 | 名稱非空；禁止 `/`、`\`、特殊字元；長度 <= 255 |

---

### 刪除確認 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `ElMessageBox.confirm` |
| 依賴 API | `DELETE /api/files/delete` |
| UX 細節 | 顯示即將刪除的檔案列表 + 數量；⚠️ 紅色警告文字 |

---

### 搬移/重新命名 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<MoveDialog>` / inline 重命名 |
| 依賴 API | `POST /api/files/move` |
| UX 細節 | 重命名: inline input 直接編輯；搬移: 彈出目錄選擇器 |
| 驗證規則 | 新名稱非空；不可與同目錄既有檔案重名 |

---

### 複製/貼上 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 工具列「複製」「貼上」按鈕 |
| 依賴 API | `POST /api/files/copy` |
| 狀態管理 | `clipboard: {action: "copy", paths: []}` in Pinia store |
| UX 細節 | 複製後 toolbar 亮起「貼上」按鈕；跨目錄可貼 |

---

### 檔案預覽 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<FilePreview>` drawer |
| 結構 | 依 MIME type 切換：<br>圖片 → `<img>` / lightbox<br>文字/程式碼 → code block<br>PDF → `<iframe>` / pdf.js<br>影片 → `<video>`<br>其他 → 顯示 info |
| 依賴 API | `GET /api/files/download`（串流預覽） |
| UX 細節 | 快速鍵 Space 開關預覽；上下鍵切換檔案 |

---

### 檔案詳細資訊面板 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<FileInfoDrawer>` 右側 drawer |
| 依賴 API | `GET /api/files/info` |
| UX 細節 | 顯示：名稱、類型、大小、建立/修改時間、權限、擁有者 |

---

### 壓縮/解壓縮 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<CompressDialog>` |
| 依賴 API | `POST /api/files/compress`<br>`POST /api/files/extract` |
| UX 細節 | 選擇格式（zip/tar.gz）；解壓目標目錄選擇 |

---

### 分享連結產生 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<ShareLinkDialog>` |
| 依賴 API | `POST /api/files/share` |
| UX 細節 | 設定有效期 + 可選密碼 → 產生連結 → 一鍵複製 |
| 驗證規則 | expires_hours > 0；password 可選 |

---

### 批次操作工具列 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | 工具列條件渲染（有選取時顯示） |
| UX 細節 | 顯示「已選 N 項」+ 批次刪除/搬移/下載按鈕 |

---

## 4. Docker 頁面增強

---

### 建立容器精靈 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<CreateContainerDialog>` |
| 結構 | el-steps：映像選擇 → 基本設定 → 埠對應 → Volume → 環境變數 → 確認 |
| 依賴 API | `GET /api/docker/images`<br>`POST /api/docker/containers/create` |
| 狀態管理 | 本地 reactive `containerForm` |
| UX 細節 | ① 映像可搜尋/下拉選擇<br>② 埠對應動態增減行<br>③ Volume 動態增減 + host path 瀏覽器<br>④ env 用 key=value 對增減 |
| 驗證規則 | image 必填；port 為數字 1-65535；name 英數+hyphen |

---

### 重啟按鈕 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `Docker.vue` 操作欄 |
| 依賴 API | `POST /api/docker/containers/{id}/restart` |
| UX 細節 | 在「停止」按鈕旁新增「重啟」；loading 狀態 |

---

### 刪除映像按鈕 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `Docker.vue` 映像表格 |
| 依賴 API | `DELETE /api/docker/images/{id}` |
| UX 細節 | 每列增加「刪除」按鈕；確認對話框顯示 tag |

---

### 容器資源監控 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<ContainerStats>` — 容器詳情頁子元件 |
| 依賴 API | `GET /api/docker/containers/{id}/stats` |
| 結構 | CPU gauge + Memory gauge + 網路流量數字 |
| UX 細節 | 每 5 秒自動刷新；或 WebSocket 串流 |
| 依賴套件 | `echarts`（gauge chart） |

---

### 容器詳情頁 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<ContainerDetail>` drawer 或新頁面 |
| 依賴 API | `GET /api/docker/containers/{id}/inspect` |
| 結構 | Tabs：概覽 / 環境變數 / 掛載 / 網路 / 日誌 |
| UX 細節 | JSON 格式化顯示 inspect 資料 |

---

### 映像搜尋/拉取 UI 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<PullImageDialog>` |
| 依賴 API | `POST /api/docker/images/pull` |
| UX 細節 | 輸入 image:tag → 拉取 → progress 顯示（需 WebSocket 或輪詢） |
| 驗證規則 | image 非空；tag 預設 latest |

---

### 網路管理 Tab 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | Docker.vue 新增 `<NetworkTab>` |
| 依賴 API | `GET /api/docker/networks`<br>`POST /api/docker/networks`<br>`DELETE /api/docker/networks/{id}` |
| UX 細節 | 表格列出；建立 dialog（name + driver）；刪除確認；預設網路不可刪 |

---

### Volume 管理 Tab 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | Docker.vue 新增 `<VolumeTab>` |
| 依賴 API | `GET /api/docker/volumes`<br>`POST /api/docker/volumes`<br>`DELETE /api/docker/volumes/{name}` |
| UX 細節 | 表格列出；建立 dialog；刪除確認 + ⚠️ 資料遺失警告 |

---

### 映像清理按鈕 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | Docker.vue 映像區工具列按鈕 |
| 依賴 API | `POST /api/docker/images/prune` |
| UX 細節 | 確認對話框顯示「清理無用映像」；完成後顯示回收空間 |

---

### Compose 部署頁面 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<ComposeManager>` — Docker.vue 新 Tab |
| 依賴 API | `POST /api/docker/compose/deploy`<br>`GET /api/docker/compose/projects`<br>`DELETE /api/docker/compose/projects/{name}` |
| UX 細節 | 上傳 yaml 或線上編輯器（CodeMirror）；專案列表 + 停止/刪除 |
| 依賴套件 | `codemirror`（可選） |

---

### 應用商店 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<AppStore>` |
| 結構 | 卡片列表（Nextcloud, Jellyfin, Pi-hole, ...）→ 一鍵部署 |
| UX 細節 | 每個 App 卡片含 logo、描述、「安裝」按鈕 → 跳轉 Compose 部署 |
| 注意事項 | 範本資料可存為 JSON/YAML 靜態檔 |

---

## 5. 使用者管理頁面增強

---

### 編輯使用者 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<EditUserDialog>` |
| 依賴 API | `PUT /api/users/{username}` |
| UX 細節 | 點擊使用者列「編輯」→ 彈出 dialog 帶入現有值（shell、群組） |
| 驗證規則 | shell 從下拉選單選取（`/bin/bash`, `/bin/sh`, `/usr/sbin/nologin`） |

---

### 修改密碼 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<ChangePasswordDialog>` |
| 依賴 API | `PUT /api/users/{username}/password` |
| UX 細節 | 管理員免輸入舊密碼；顯示密碼強度指示 |
| 驗證規則 | 新密碼 >= 8 字元；確認密碼需一致 |

---

### 群組管理 Tab 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | Users.vue 新增 Tab「群組」 |
| 依賴 API | `GET /api/users/groups`<br>`POST /api/users/groups`<br>`DELETE /api/users/groups/{name}`<br>`PUT /api/users/groups/{name}/members` |
| UX 細節 | 群組表格 + 展開顯示成員清單 + 新增/移除成員按鈕 |

---

### 停用/啟用切換 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 使用者表格新增 el-switch 欄位 |
| 依賴 API | `PUT /api/users/{username}/status` |
| UX 細節 | 停用時灰色標記 + switch off；啟用確認 |

---

### 磁碟配額設定 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<QuotaDialog>` |
| 依賴 API | `GET /api/users/{username}/quota`<br>`PUT /api/users/{username}/quota` |
| UX 細節 | 顯示目前使用量 progress bar + 設定 soft/hard limit |
| 驗證規則 | soft <= hard；數值正整數 |

---

### 稽核日誌頁面 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `views/AuditLog.vue` 或 Users.vue 子頁 |
| 依賴 API | `GET /api/users/audit` |
| UX 細節 | 表格 + 時間/使用者/動作過濾器；分頁 |

---

### 2FA 設定 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<TwoFactorSetup>` |
| 依賴 API | `POST /api/users/{username}/2fa/setup`<br>`POST /api/users/{username}/2fa/verify` |
| UX 細節 | 顯示 QR code（qrcode.js）→ 輸入驗證碼確認綁定 |
| 依賴套件 | `qrcode`（前端 QR 產生） |

---

### 個人設定頁面 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `views/Profile.vue` |
| 路由 | `/profile` |
| 依賴 API | `PUT /api/users/{username}/password`<br>`GET /api/users/{username}/quota` |
| UX 細節 | 修改自己的密碼 + 查看配額使用量 + 語言偏好 |

---

## 6. 系統管理 🆕

---

### 主頁面 `views/System.vue` 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `views/System.vue` |
| 結構 | el-tabs：日誌 / 服務 / 電源 / 設定 / 硬體 / 更新 |
| 路由 | `/system` — 加入 router + sidebar |
| 依賴 API | 多個 `/api/system/*` |

---

### 系統日誌查看 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<SystemLogs>` Tab |
| 依賴 API | `GET /api/system/logs` |
| 結構 | 上方過濾列（unit 下拉 + lines 輸入 + since 日期選擇）<br>下方 monospace 日誌面板 + 自動捲動 |
| UX 細節 | ① 即時模式（WebSocket 或 5 秒輪詢）<br>② 依 priority 上色（error=紅, warn=黃）<br>③ 可搜尋/過濾文字 |

---

### 電源管理 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<PowerControl>` Tab |
| 依賴 API | `POST /api/system/power/shutdown`<br>`POST /api/system/power/reboot` |
| UX 細節 | ① 大按鈕 + ⚠️ 紅色警告<br>② 點擊後 ElMessageBox 二次確認 + 輸入「SHUTDOWN」或「REBOOT」<br>③ 確認後顯示倒數計時<br>④ 重啟後前端自動偵測恢復（ping /api/health） |

---

### 溫度監控 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<TemperaturePanel>` — 可嵌入 Dashboard 或 System |
| 依賴 API | `GET /api/system/temperature` |
| 結構 | CPU 溫度 gauge + 各磁碟溫度列表 |
| UX 細節 | 閾值警告色（< 50 綠, 50-70 黃, > 70 紅）；每 30 秒刷新 |

---

### 服務管理 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<ServiceManager>` Tab |
| 依賴 API | `GET /api/system/services`<br>`POST /api/system/services/{name}/start|stop|restart` |
| UX 細節 | 表格：服務名 + 狀態 tag + enabled switch + 操作按鈕（啟/停/重啟） |

---

### 系統設定 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<SystemSettings>` Tab |
| 依賴 API | `PUT /api/system/settings` |
| 結構 | el-form：hostname 輸入 + timezone 下拉 + NTP switch |
| 驗證規則 | hostname 英數+hyphen，1-63 字；timezone 從列表選取 |

---

### 硬體資訊頁 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<HardwareInfo>` Tab |
| 依賴 API | `GET /api/system/hardware` |
| UX 細節 | 分區塊顯示 CPU、RAM、PCI 裝置；el-descriptions 格式 |

---

### 系統更新 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<SystemUpdate>` Tab |
| 依賴 API | `GET /api/system/updates`<br>`POST /api/system/updates/apply` |
| UX 細節 | ① 「檢查更新」按鈕 → 顯示可更新套件列表<br>② 「全部更新」按鈕 + 確認<br>③ 更新中 loading + 日誌輸出 |

---

### 排程任務管理 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<CronManager>` Tab |
| 依賴 API | `GET /api/system/cron`<br>`POST /api/system/cron`<br>`DELETE /api/system/cron/{id}` |
| UX 細節 | 表格 + 新增 dialog（cron 表達式提供視覺化選擇器） |
| 依賴套件 | `cron-expression-input`（可選） |

---

### 歷史監控圖表 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<MetricsChart>` — Dashboard 或 System |
| 依賴 API | `GET /api/dashboard/history` |
| 結構 | ECharts 多折線圖（CPU/RAM/Temp） |
| 依賴套件 | `echarts` + `vue-echarts` |

---

## 7. 網路管理 🆕

---

### 主頁面 `views/Network.vue` 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `views/Network.vue` |
| 結構 | el-tabs：介面 / 防火牆 / 速率 / 診斷 / WOL |
| 路由 | `/network` — 加入 router + sidebar |

---

### 網路介面列表 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<InterfaceList>` Tab |
| 依賴 API | `GET /api/network/interfaces` |
| 結構 | el-table：名稱, IP, MAC, 狀態 tag, 速率 |
| UX 細節 | up = 綠色 tag；down = 灰色；點擊列可編輯 |

---

### 介面設定表單 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<InterfaceConfigDialog>` |
| 依賴 API | `PUT /api/network/interfaces/{name}` |
| 結構 | el-form：method radio(DHCP/Static) → Static 顯示 IP/netmask/gateway/DNS |
| UX 細節 | ⚠️ 修改警告：「錯誤設定可能導致無法連線」；30 秒確認機制建議 |
| 驗證規則 | IP/netmask/gateway 格式驗證（IPv4）；DNS 每行一個 |

---

### 防火牆管理 Tab 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<FirewallManager>` Tab |
| 依賴 API | `GET /api/network/firewall/rules`<br>`POST /api/network/firewall/rules`<br>`DELETE /api/network/firewall/rules/{id}` |
| 結構 | 規則表格 + 新增 dialog（chain/protocol/port/source/target） |
| UX 細節 | SSH (port 22) 規則標記為「保護」不可刪；新增規則即時生效 |
| 驗證規則 | port 1-65535；source 為有效 IP/CIDR |

---

### 即時速率圖表 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<NetworkStatsChart>` Tab |
| 依賴 API | `GET /api/network/stats`（輪詢）或 WebSocket |
| 結構 | 每介面獨立折線圖（rx/tx），最近 60 秒 |
| 依賴套件 | `echarts` |
| UX 細節 | 自動捲動時間軸；hover 顯示數值 |

---

### 網路診斷工具 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<NetworkDiag>` Tab |
| 依賴 API | `POST /api/network/diag/ping`<br>`POST /api/network/diag/traceroute`<br>`POST /api/network/diag/dns` |
| 結構 | 三個子面板（Ping / Traceroute / DNS）各有輸入框 + 執行按鈕 + 結果面板 |
| UX 細節 | 結果用 monospace pre 顯示；Ping 逐行輸出 |
| 驗證規則 | host/domain 非空 |

---

### Wake-on-LAN 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<WolPanel>` Tab |
| 依賴 API | `POST /api/network/wol` |
| 結構 | el-input MAC 位址 + 「發送」按鈕 + 常用裝置收藏列表 |
| UX 細節 | MAC 輸入自動格式化（加冒號）；收藏存 localStorage |
| 驗證規則 | MAC 格式 `XX:XX:XX:XX:XX:XX` |

---

## 8. 備份 & 同步 🆕

---

### 主頁面 `views/Backup.vue` 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `views/Backup.vue` |
| 結構 | 任務列表 + 工具列（建立任務）+ 快照 Tab |
| 路由 | `/backup` |

---

### 備份任務列表 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<BackupTaskList>` |
| 依賴 API | `GET /api/backup/tasks` |
| 結構 | el-table：名稱, 來源, 目的地, 排程, 上次狀態 tag, 操作按鈕 |
| UX 細節 | success = 綠 tag；failed = 紅 tag；running = 藍 + 旋轉 icon |

---

### 建立備份任務精靈 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | `<CreateBackupDialog>` |
| 依賴 API | `POST /api/backup/tasks` |
| 結構 | el-steps：來源路徑 → 目的地 → 排程（cron 視覺化）→ 保留策略 → 備份方法 |
| 驗證規則 | source 必填存在；destination 必填；schedule 有效 cron；retention > 0 |

---

### 立即執行按鈕 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 任務列操作欄 |
| 依賴 API | `POST /api/backup/tasks/{id}/run` |
| UX 細節 | 執行中禁止重複按；完成後顯示結果（耗時、檔案數、大小） |

---

### 執行歷史 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<BackupHistory>` drawer（點擊任務展開） |
| 依賴 API | `GET /api/backup/tasks/{id}/history` |
| UX 細節 | 表格：時間、狀態、耗時、大小、錯誤訊息 |

---

### 還原操作 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<RestoreDialog>` |
| 依賴 API | `POST /api/backup/restore` |
| UX 細節 | 從歷史選擇版本 → 選擇還原目標路徑 → 確認（⚠️ 可能覆蓋） |

---

### 快照管理 Tab 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<SnapshotTab>` |
| 依賴 API | `GET/POST/DELETE /api/backup/snapshots` |
| UX 細節 | 表格 + 建立按鈕 + 刪除確認 |

---

## 9. 遠端存取 🆕

---

### 主頁面 `views/Remote.vue` 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `views/Remote.vue` |
| 結構 | el-tabs：DDNS / SSL / VPN |
| 路由 | `/remote` |

---

### DDNS 設定表單 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<DdnsSettings>` Tab |
| 依賴 API | `GET /api/remote/ddns`<br>`PUT /api/remote/ddns` |
| 結構 | el-form：provider 下拉 + domain 輸入 + token 密碼輸入 + enabled switch |
| UX 細節 | 顯示目前 IP + 上次更新時間 |
| 驗證規則 | provider 必選；domain 非空；token 非空 |

---

### SSL 憑證狀態 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<SslStatus>` Tab |
| 依賴 API | `GET /api/remote/ssl`<br>`POST /api/remote/ssl/issue` |
| UX 細節 | 顯示憑證到期日 + 剩餘天數 progress bar；「申請/續期」按鈕 |

---

### VPN 狀態面板 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | `<VpnPanel>` Tab |
| 依賴 API | `GET /api/remote/vpn/status`<br>`PUT /api/remote/vpn/config` |
| UX 細節 | 運行狀態指示 + listen port + public key + Peer 列表表格 |

---

### VPN Peer 管理 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<VpnPeerManager>` 子元件 |
| 依賴 API | `POST /api/remote/vpn/peers`<br>`DELETE /api/remote/vpn/peers/{id}` |
| UX 細節 | 新增 Peer dialog + 產生 client config 下載（QR code） |

---

### 反向代理管理 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<ReverseProxyManager>` |
| 依賴 API | `GET /api/remote/reverse-proxy`<br>`POST /api/remote/reverse-proxy` |
| UX 細節 | 表格：domain → upstream + SSL badge；新增 dialog |

---

## 10. 通知中心 🆕

---

### Header 通知圖示 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `AppLayout.vue` header |
| 依賴 API | `GET /api/notifications?unread_only=true` |
| 結構 | el-badge（未讀數）+ el-popover 下拉列表 |
| UX 細節 | 每 30 秒輪詢未讀數；點擊通知跳轉相關頁面 |

---

### 通知設定頁面 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | System.vue 或獨立 `/settings/notifications` |
| 依賴 API | `GET /api/notifications/settings`<br>`PUT /api/notifications/settings`<br>`POST /api/notifications/test` |
| 結構 | 三區塊：Email / Telegram / Webhook 各有 enabled switch + 設定表單 + 「測試」按鈕 |
| 驗證規則 | Email: smtp_host 非空, port 數字；Telegram: bot_token + chat_id 非空 |

---

### 通知歷史頁面 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `views/Notifications.vue` |
| 依賴 API | `GET /api/notifications`<br>`PUT /api/notifications/{id}/read` |
| UX 細節 | 表格 + 未讀粗體 + 「全部標記已讀」按鈕；分頁 |

---

## 11. Dashboard 增強

---

### 自動刷新 🔴 高

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `Dashboard.vue` |
| 實作 | `setInterval` 每 5 秒呼叫 `/api/dashboard` 或升級為 WebSocket |
| UX 細節 | 右上角顯示「即時」指示燈 + 手動暫停按鈕 |

---

### 即時網路速率 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 修改 Dashboard 網路卡片 |
| 依賴 API | `GET /api/network/stats` |
| UX 細節 | 顯示 KB/s 或 MB/s（自動切換單位）而非累計值 |

---

### 磁碟溫度卡片 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | Dashboard 新增溫度卡片 |
| 依賴 API | `GET /api/system/temperature` |
| UX 細節 | 各碟溫度 + 色彩閾值 |

---

### 服務狀態概覽 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | Dashboard 新增服務狀態區 |
| 依賴 API | `GET /api/system/services`（過濾關鍵服務） |
| UX 細節 | SMB/NFS/Docker/SSH 小圓點指示（綠=running） |

---

### 歷史圖表 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | Dashboard 底部折線圖 |
| 依賴 API | `GET /api/dashboard/history` |
| 依賴套件 | `echarts` |

---

### 自訂 Widget 🟢 低

| 項目 | 內容 |
|------|------|
| 元件 | `<DashboardGrid>` 可拖拽佈局 |
| UX 細節 | 使用者可拖拽排列卡片順序；偏好存 localStorage |
| 依賴套件 | `vue-grid-layout` |

---

## 12. 全域 / 跨模組功能

---

### 表單驗證 🔴 高

| 項目 | 內容 |
|------|------|
| 實作 | 所有 `<el-form>` 加入 `:rules` prop |
| 範圍 | Login, 新增使用者, SMB, NFS, Docker 建立, 系統設定 |
| 方式 | Element Plus 內建 async-validator rules |
| 常見規則 | required, min/max length, pattern (IP/MAC/email), custom validator |

---

### 錯誤處理 🔴 高

| 項目 | 內容 |
|------|------|
| 實作 | `api/index.js` response interceptor 統一處理 |
| 行為 | 4xx → `ElMessage.error(detail)`<br>5xx → `ElMessage.error("伺服器錯誤")`<br>timeout → `ElMessage.error("連線逾時")` |
| 範圍 | 全域（所有 API 呼叫） |

---

### Loading 狀態 🔴 高

| 項目 | 內容 |
|------|------|
| 實作 | 每個頁面增加 `loading` ref + `v-loading` directive |
| 範圍 | 所有 data-fetching 頁面 |
| UX 細節 | 首次載入用 el-skeleton；後續刷新用 overlay loading |

---

### i18n 國際化 🟡 中

| 項目 | 內容 |
|------|------|
| 實作 | 安裝 `vue-i18n`；建立 `locales/zh-TW.json` + `locales/en.json` |
| 結構 | main.js 掛載 i18n；所有模板文字改用 `{{ $t('key') }}` |
| UX 細節 | Header 語言切換下拉；偏好存 localStorage |
| 工作量 | 約 200+ 翻譯 key |
| 依賴套件 | `vue-i18n` |

---

### 深色模式 🟡 中

| 項目 | 內容 |
|------|------|
| 實作 | Element Plus dark theme（`document.documentElement.classList.add('dark')`） |
| UX 細節 | Header 切換按鈕（太陽/月亮 icon）；偏好存 localStorage；跟隨系統自動切換 |

---

### 響應式布局 🟡 中

| 項目 | 內容 |
|------|------|
| 實作 | el-row/el-col 響應式 span；sidebar 手機下收合為 hamburger |
| 測試 | 確認 375px / 768px / 1024px 寬度下正常 |

---

### 麵包屑導航 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `AppLayout.vue` header 區 |
| 結構 | el-breadcrumb 根據 route.matched 自動產生 |

---

### 側邊欄收合 🟡 中

| 項目 | 內容 |
|------|------|
| 元件 | 修改 `AppLayout.vue` |
| UX 細節 | collapse 按鈕；收合後只顯示 icon；偏好存 localStorage |

---

### 確認刪除統一 🟡 中

| 項目 | 內容 |
|------|------|
| 實作 | 抽出 `utils/confirm.js` 封裝 `ElMessageBox.confirm` |
| 行為 | 所有刪除操作統一呼叫：紅色標題 + 不可逆警告 |

---

### 鍵盤快捷鍵 🟢 低

| 項目 | 內容 |
|------|------|
| 實作 | `@vueuse/core` 的 `useKeyboard` 或自訂 |
| 功能 | Ctrl+K: 全域搜尋；Delete: 刪除選取；Ctrl+U: 上傳 |
| 依賴套件 | `@vueuse/core` |

---

### PWA 支援 🟢 低

| 項目 | 內容 |
|------|------|
| 實作 | Vite PWA plugin + manifest.json + service worker |
| 依賴套件 | `vite-plugin-pwa` |
| UX 細節 | 可安裝到桌面；離線顯示「無法連線」頁面 |

---

### 頁面過渡動畫 🟢 低

| 項目 | 內容 |
|------|------|
| 實作 | `<router-view>` 外包 `<transition>` |
| UX 細節 | 淡入淡出 / 左右滑動 |

---

## 優先順序統計

| 優先級 | 數量 | 說明 |
|--------|------|------|
| 🔴 高 | 33 | 核心使用體驗、基本操作 |
| 🟡 中 | 40 | 進階功能、管理介面 |
| 🟢 低 | 26 | 加值體驗、企業需求 |
| **總計** | **99** | |

---

## 建議開發順序

### Phase 1 — 核心體驗（🔴 高）
1. 全域錯誤處理 + Loading + 表單驗證（跨模組基礎）
2. 檔案管理器 `Files.vue`（瀏覽/上傳/下載/刪除）
3. Dashboard 自動刷新
4. 儲存管理格式化 Dialog + SMART 面板
5. Docker 建立容器精靈 + 重啟 + 映像刪除
6. 系統管理 `System.vue`（日誌/電源/溫度）
7. 網路介面列表 `Network.vue`
8. 備份管理 `Backup.vue`（任務列表 + 建立精靈）
9. 使用者編輯 + 修改密碼

### Phase 2 — 完善管理（🟡 中）
1. i18n 國際化（越早做越少改）
2. 共享編輯 + ACL 面板
3. 使用者群組管理 + 停用 + 配額
4. 網路設定 + 防火牆 + 速率圖表
5. Docker 網路/Volume/Stats
6. 通知中心（Header badge + 設定頁）
7. 遠端存取（DDNS/SSL/VPN）
8. 深色模式 + 響應式 + 側邊欄收合
9. 系統服務管理 + 更新

### Phase 3 — 進階功能（🟢 低）
1. Docker Compose / 應用商店
2. VPN Peer / 反向代理管理
3. 2FA 設定 + 稽核日誌
4. 歷史圖表 + 自訂 Widget
5. 壓縮/快照/分享連結
6. PWA + 鍵盤快捷鍵 + 過渡動畫

---

## 新增依賴套件總覽

| 套件 | 用途 | Phase |
|------|------|-------|
| `echarts` + `vue-echarts` | 圖表（溫度/速率/歷史） | 1 |
| `vue-i18n` | 國際化 | 2 |
| `@vueuse/core` | 工具函式（keyboard, resize） | 2-3 |
| `qrcode` | 2FA QR code 產生 | 3 |
| `vite-plugin-pwa` | PWA 支援 | 3 |
| `vue-grid-layout` | Dashboard 拖拽佈局 | 3 |
| `codemirror` | Compose YAML 編輯器 | 3 |
