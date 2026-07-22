# Backend — 尚未實作 Service 函式（詳細規格）

> 更新日期：2026-07-20
>
> Service 層：商業邏輯函式（系統指令呼叫 / SDK 操作）。
> 每個函式包含：參數型別、回傳格式、權限、安全驗證、風險、前置條件、錯誤情境、測試策略。

---

## 1. 儲存管理 (`services/storage_service.py`)

---

### `format_disk(device: str, fs_type: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `device: str` — 裝置路徑 (e.g. `/dev/sdb1`)<br>`fs_type: str` — 檔案系統 (`ext4` / `xfs` / `btrfs`) |
| 回傳 | `{"success": bool, "message": str, "error": str}` |
| 底層工具 | `mkfs.ext4` / `mkfs.xfs` / `mkfs.btrfs` |
| 權限 | root（需 sudo） |
| 前置條件 | device 必須已 unmount；不可為系統碟 |
| 安全驗證 | device 白名單 `/dev/sd[a-z]*` 或 `/dev/nvme*`；禁止 `/dev/sda`（系統碟）；fs_type 限 enum |
| 風險 | ⚠️ **不可逆** — 資料全部清除 |
| 錯誤情境 | 裝置不存在、仍在掛載中、fs_type 不支援、權限不足 |
| 測試策略 | loop device (`losetup --find --show`) 模擬磁碟 |

---

### `get_smart_info(device: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `device: str` — 裝置路徑 (e.g. `/dev/sda`) |
| 回傳 | `{"success": bool, "smart_status": str, "temperature": int, "power_on_hours": int, "attributes": list[dict]}` |
| 底層工具 | `smartctl -a --json=c {device}` |
| 權限 | root |
| 前置條件 | smartmontools 已安裝；裝置支援 SMART |
| 安全驗證 | device 路徑白名單驗證 |
| 風險 | 唯讀操作，無風險 |
| 錯誤情境 | smartctl 未安裝、裝置不支援 SMART、裝置不存在 |
| 測試策略 | mock subprocess output；或使用 `/dev/sda` 實機測試 |

---

### `run_smart_test(device: str, test_type: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `device: str`<br>`test_type: str` — `short` / `long` / `conveyance` |
| 回傳 | `{"success": bool, "message": str, "estimated_minutes": int}` |
| 底層工具 | `smartctl -t {test_type} {device}` |
| 權限 | root |
| 前置條件 | 裝置支援 SMART；無其他測試正在執行 |
| 安全驗證 | test_type 限 enum；device 白名單 |
| 風險 | 低 — 測試期間磁碟效能略降 |
| 錯誤情境 | 已有測試在進行、裝置不支援該測試類型 |
| 測試策略 | mock subprocess；短測試實機驗證 |

---

### `create_partition(device: str, size: str, part_type: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `device: str` — 整顆磁碟 (e.g. `/dev/sdb`)<br>`size: str` — 如 `100G` 或 `100%`<br>`part_type: str` — `primary` / `logical` |
| 回傳 | `{"success": bool, "partition": str, "message": str}` |
| 底層工具 | `parted -s {device} mkpart {part_type} 0% {size}` |
| 權限 | root |
| 前置條件 | 磁碟有可用空間；無分割區正在使用中 |
| 安全驗證 | device 白名單；禁止系統碟 |
| 風險 | ⚠️ 中 — 可能影響既有分割區表 |
| 錯誤情境 | 無可用空間、GPT/MBR 不相容、device 不存在 |
| 測試策略 | loop device + parted |

---

### `delete_partition(device: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `device: str` — 分割區路徑 (e.g. `/dev/sdb1`) |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `parted -s {disk} rm {part_number}` |
| 權限 | root |
| 前置條件 | 分割區已 unmount |
| 安全驗證 | 禁止刪除系統分割區 `/`、`/boot` |
| 風險 | ⚠️ **不可逆** — 分割區資料遺失 |
| 錯誤情境 | 仍在掛載中、分割區不存在 |
| 測試策略 | loop device |

---

### `create_raid(name: str, level: int, devices: list[str], spare: list[str]) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str` — 陣列名稱 (e.g. `md0`)<br>`level: int` — 0/1/5/6/10<br>`devices: list[str]` — 成員裝置<br>`spare: list[str]` — 備用碟 |
| 回傳 | `{"success": bool, "device": str, "message": str}` |
| 底層工具 | `mdadm --create /dev/{name} --level={level} --raid-devices={n} {devices}` |
| 權限 | root |
| 前置條件 | 所有 devices 已 unmount 且無資料（或使用者確認） |
| 安全驗證 | devices 白名單；level 限 enum；至少 2 顆碟 |
| 風險 | ⚠️ **高** — 成員碟資料清除 |
| 錯誤情境 | 裝置數不足、裝置已屬其他 RAID、mdadm 未安裝 |
| 測試策略 | loop device 模擬多碟 RAID |

---

### `remove_raid(name: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str` — e.g. `md0` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `mdadm --stop /dev/{name}` + `mdadm --remove /dev/{name}` |
| 權限 | root |
| 前置條件 | 陣列已 unmount |
| 安全驗證 | name 格式驗證 `md[0-9]+` |
| 風險 | ⚠️ **不可逆** — RAID 資料不可存取 |
| 錯誤情境 | 陣列仍在掛載、陣列不存在 |
| 測試策略 | loop device RAID 建立後移除 |

---

### `add_raid_disk(name: str, device: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str`<br>`device: str` — 新增碟 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `mdadm --add /dev/{name} {device}` |
| 權限 | root |
| 前置條件 | 新碟已 unmount；容量 >= 現有成員 |
| 安全驗證 | device 白名單 |
| 風險 | 低 — 會觸發 rebuild |
| 錯誤情境 | 碟容量太小、陣列 degraded 中 |
| 測試策略 | loop device RAID + 新增碟 |

---

### `get_fstab() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "entries": list[{"device": str, "mount": str, "fs": str, "options": str, "dump": int, "pass": int}]}` |
| 底層工具 | 解析 `/etc/fstab` |
| 權限 | 一般使用者可讀 |
| 安全驗證 | 無（唯讀） |
| 風險 | 無 |
| 錯誤情境 | 檔案格式異常 |
| 測試策略 | 使用 fixture fstab 檔案 |

---

### `add_fstab_entry(device: str, mount: str, fs: str, options: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `device: str`<br>`mount: str` — 掛載點<br>`fs: str` — 檔案系統<br>`options: str` — e.g. `defaults,noatime` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | append 到 `/etc/fstab` |
| 權限 | root |
| 前置條件 | device 存在；mount 目錄已建立 |
| 安全驗證 | 禁止覆蓋既有掛載點；device 白名單 |
| 風險 | 中 — 錯誤設定可能導致開機失敗 |
| 錯誤情境 | 重複掛載點、device 不存在 |
| 測試策略 | 使用暫存 fstab 檔案；`mount -a --fake` 驗證 |

---

### `remove_fstab_entry(mount: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `mount: str` — 掛載點路徑 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 編輯 `/etc/fstab` 移除指定行 |
| 權限 | root |
| 安全驗證 | 禁止移除 `/`、`/boot`、`swap` |
| 風險 | 中 |
| 錯誤情境 | 掛載點不存在於 fstab |
| 測試策略 | fixture fstab |

---

### `get_disk_temperature(device: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `device: str` |
| 回傳 | `{"success": bool, "device": str, "temperature_c": int}` |
| 底層工具 | `smartctl -A {device}` 取 Temperature 欄位 |
| 權限 | root |
| 安全驗證 | device 白名單 |
| 風險 | 無（唯讀） |
| 錯誤情境 | SMART 不支援、smartctl 未安裝 |
| 測試策略 | mock output |

---

### `get_usage_history() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `days: int = 30` |
| 回傳 | `{"success": bool, "history": list[{"timestamp": str, "device": str, "used_gb": float, "percent": float}]}` |
| 底層工具 | SQLite 查詢（需定期採集 job） |
| 權限 | 一般使用者 |
| 前置條件 | 背景採集任務已啟動、DB 已建立 |
| 安全驗證 | days 限 1-365 |
| 風險 | 無 |
| 錯誤情境 | DB 不存在、無資料 |
| 測試策略 | fixture DB |

---

## 2. 檔案共享 (`services/samba_service.py`, `services/nfs_service.py`)

---

### `update_smb_share(name: str, config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `name: str` — 共享名稱<br>`config: dict` — `{path, comment, read_only, guest_ok, valid_users}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 找到 `smb.conf` 中 `[name]` section → 替換內容 → `systemctl restart smbd` |
| 權限 | root |
| 前置條件 | 該共享已存在 |
| 安全驗證 | name 禁止 `global`/`homes`/`printers`；path 限制在安全目錄 |
| 風險 | 低 — 修改設定檔可 rollback |
| 錯誤情境 | 共享不存在、smb.conf 語法錯誤、smbd restart 失敗 |
| 測試策略 | 使用暫存 smb.conf；`testparm -s` 驗證語法 |

---

### `update_nfs_export(path: str, clients: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `path: str` — 匯出路徑<br>`clients: str` — 新的客戶端規則 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 修改 `/etc/exports` 中對應行 → `exportfs -ra` |
| 權限 | root |
| 前置條件 | 該 export 已存在 |
| 安全驗證 | path 必須存在且為目錄；clients 格式驗證 (IP/CIDR + options) |
| 風險 | 低 |
| 錯誤情境 | 路徑不存在於 exports、clients 格式錯誤 |
| 測試策略 | fixture exports 檔案 |

---

### `get_share_acl(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `path: str` — 共享資料夾路徑 |
| 回傳 | `{"success": bool, "owner": str, "group": str, "permissions": str, "acl": list[{"user/group": str, "perms": str}]}` |
| 底層工具 | `getfacl {path}` |
| 權限 | root（或目錄擁有者） |
| 安全驗證 | path 限制在共享根目錄內 |
| 風險 | 無（唯讀） |
| 錯誤情境 | 路徑不存在、ACL 未啟用 |
| 測試策略 | 建立暫存目錄 + setfacl 設定後驗證 |

---

### `set_share_acl(path: str, acl: list[dict]) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `path: str`<br>`acl: list[dict]` — `[{"type": "user"/"group", "name": str, "perms": "rwx"}]` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `setfacl -m u:{name}:{perms} {path}` |
| 權限 | root |
| 前置條件 | 檔案系統支援 ACL（mount option `acl`） |
| 安全驗證 | path 白名單；name 必須是有效使用者/群組；perms 限 `[rwx-]` |
| 風險 | 低 — 可 `setfacl -b` 復原 |
| 錯誤情境 | 使用者不存在、FS 不支援 ACL |
| 測試策略 | tmpfs + setfacl |

---

### `get_smb_status() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "service_running": bool, "connections": list[{"user": str, "ip": str, "share": str}]}` |
| 底層工具 | `smbstatus --json` 或 `smbstatus -b` 解析 |
| 權限 | root |
| 風險 | 無 |
| 錯誤情境 | smbd 未運行 |
| 測試策略 | mock output |

---

### `get_nfs_status() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "service_running": bool, "clients": list[{"ip": str, "mount": str}]}` |
| 底層工具 | `showmount -a` + `systemctl is-active nfs-server` |
| 權限 | root |
| 風險 | 無 |
| 錯誤情境 | NFS 未安裝 |
| 測試策略 | mock output |

---

## 3. 檔案管理器 (`services/file_service.py`) 🆕

---

### `list_directory(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `path: str` — 目錄路徑 |
| 回傳 | `{"success": bool, "path": str, "items": list[{"name": str, "type": "file"/"dir", "size": int, "modified": str, "permissions": str}]}` |
| 底層工具 | `os.scandir` + `os.stat` |
| 權限 | 依使用者權限（需傳入 current_user） |
| 前置條件 | 路徑存在且為目錄 |
| 安全驗證 | **路徑穿越防護** — 解析後必須在允許的根目錄內（`realpath` 檢查）；禁止 `..`、symlink 逃脫 |
| 風險 | 無（唯讀） |
| 錯誤情境 | 路徑不存在、無權限讀取、非目錄 |
| 測試策略 | 暫存目錄結構 |

---

### `save_upload(file: UploadFile, dest: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `file: UploadFile` — FastAPI 上傳物件<br>`dest: str` — 目標目錄 |
| 回傳 | `{"success": bool, "path": str, "size": int}` |
| 底層工具 | `aiofiles` 串流寫入 |
| 權限 | 依使用者對目標目錄的寫入權限 |
| 前置條件 | dest 存在且可寫 |
| 安全驗證 | 路徑穿越防護；檔名消毒（移除特殊字元）；檔案大小限制（config 設定） |
| 風險 | 低 — 新增檔案，不覆蓋（同名加序號） |
| 錯誤情境 | 磁碟空間不足、目標不可寫、檔案過大 |
| 測試策略 | 暫存目錄 + 模擬 UploadFile |
| 依賴套件 | `aiofiles` |

---

### `get_download_path(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `path: str` — 檔案路徑 |
| 回傳 | `{"success": bool, "absolute_path": str, "filename": str, "size": int}` |
| 底層工具 | `pathlib.Path` |
| 權限 | 依使用者對檔案的讀取權限 |
| 安全驗證 | 路徑穿越防護；必須是檔案非目錄 |
| 風險 | 無 |
| 錯誤情境 | 檔案不存在、無讀取權限 |
| 測試策略 | 暫存檔案 |

---

### `make_directory(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `path: str` — 新資料夾完整路徑 |
| 回傳 | `{"success": bool, "path": str}` |
| 底層工具 | `os.makedirs(path, exist_ok=False)` |
| 權限 | 依使用者對父目錄的寫入權限 |
| 安全驗證 | 路徑穿越防護；禁止系統目錄 |
| 風險 | 無 |
| 錯誤情境 | 已存在、父目錄不可寫 |
| 測試策略 | 暫存目錄 |

---

### `delete_item(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `path: str` — 檔案或資料夾路徑 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `os.unlink`（檔案）/ `shutil.rmtree`（目錄） |
| 權限 | 依使用者對該路徑的寫入權限 |
| 安全驗證 | 路徑穿越防護；禁止刪除根目錄 `/`、系統目錄；可考慮移至回收站 |
| 風險 | ⚠️ **不可逆**（除非有回收站） |
| 錯誤情境 | 路徑不存在、無權限、目錄非空但無 recursive flag |
| 測試策略 | 暫存目錄 |

---

### `move_item(src: str, dst: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `src: str` — 來源<br>`dst: str` — 目標 |
| 回傳 | `{"success": bool, "new_path": str}` |
| 底層工具 | `shutil.move` |
| 權限 | 對 src 有寫入、對 dst 父目錄有寫入 |
| 安全驗證 | 雙路徑穿越防護；不可將父目錄移入子目錄 |
| 風險 | 中 — 原位置檔案消失 |
| 錯誤情境 | src 不存在、dst 已存在、跨掛載點（改用 copy+delete） |
| 測試策略 | 暫存目錄結構 |

---

### `copy_item(src: str, dst: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `src: str`<br>`dst: str` |
| 回傳 | `{"success": bool, "new_path": str}` |
| 底層工具 | `shutil.copy2`（檔案）/ `shutil.copytree`（目錄） |
| 權限 | 對 src 有讀取、對 dst 有寫入 |
| 安全驗證 | 雙路徑穿越防護 |
| 風險 | 低 — 不影響原檔案 |
| 錯誤情境 | src 不存在、磁碟空間不足 |
| 測試策略 | 暫存目錄 |

---

### `get_file_info(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `path: str` |
| 回傳 | `{"success": bool, "name": str, "type": "file"/"dir", "size": int, "mime": str, "created": str, "modified": str, "permissions": str, "owner": str}` |
| 底層工具 | `os.stat` + `mimetypes.guess_type` + `pwd.getpwuid` |
| 權限 | 一般使用者 |
| 安全驗證 | 路徑穿越防護 |
| 風險 | 無 |
| 錯誤情境 | 路徑不存在 |
| 測試策略 | 暫存檔案 |

---

### `compress(paths: list[str], format: str, dest: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `paths: list[str]` — 要壓縮的檔案/目錄<br>`format: str` — `zip` / `tar.gz`<br>`dest: str` — 輸出路徑 |
| 回傳 | `{"success": bool, "archive_path": str, "size": int}` |
| 底層工具 | `zipfile` / `tarfile` |
| 權限 | 對 paths 有讀取、對 dest 有寫入 |
| 安全驗證 | 路徑穿越防護；format 限 enum；限制壓縮大小上限 |
| 風險 | 低 |
| 錯誤情境 | 路徑不存在、磁碟空間不足 |
| 測試策略 | 暫存檔案壓縮後驗證 |

---

### `extract(archive: str, dest: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `archive: str` — 壓縮檔路徑<br>`dest: str` — 解壓目標 |
| 回傳 | `{"success": bool, "extracted_path": str, "file_count": int}` |
| 底層工具 | `zipfile` / `tarfile` |
| 權限 | 對 archive 有讀取、對 dest 有寫入 |
| 安全驗證 | **Zip Slip 防護** — 驗證解壓路徑不超出 dest；限制檔案數量/大小 |
| 風險 | 中 — Zip Slip 可能覆蓋系統檔案 |
| 錯誤情境 | 格式不支援、檔案損壞、空間不足 |
| 測試策略 | 包含惡意路徑的 zip 驗證防護有效 |

---

### `create_share_link(path: str, expires_hours: int, password: str | None) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `path: str`<br>`expires_hours: int` — 過期時間<br>`password: str | None` — 可選密碼 |
| 回傳 | `{"success": bool, "link_id": str, "url": str, "expires_at": str}` |
| 底層工具 | 產生 UUID token → 存入 DB |
| 權限 | 對該檔案有讀取權限 |
| 前置條件 | DB 已建立（share_links table） |
| 安全驗證 | 路徑穿越防護；password 若有則 hash 儲存 |
| 風險 | 低 |
| 錯誤情境 | 檔案不存在 |
| 測試策略 | DB fixture + 產生連結後下載驗證 |
| 依賴套件 | SQLAlchemy（DB）、`passlib`（password hash） |

---

## 4. Docker 容器化 (`services/docker_service.py`)

---

### `create_container(config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `config: dict` — `{image, name, ports: {"8080/tcp": 8080}, volumes: {"/host": {"bind": "/container", "mode": "rw"}}, environment: {"KEY": "VAL"}, restart_policy: {"Name": "always"}}` |
| 回傳 | `{"success": bool, "container_id": str, "name": str}` |
| 底層工具 | `client.containers.run(detach=True, **config)` |
| 權限 | Docker group 成員（或 root） |
| 前置條件 | 映像已存在（或自動 pull） |
| 安全驗證 | image 名稱格式驗證；ports 數字範圍 1-65535；volumes host path 限制在允許目錄 |
| 風險 | 中 — 不當 volume 掛載可能暴露主機檔案 |
| 錯誤情境 | 映像不存在、port 已佔用、name 重複 |
| 測試策略 | 使用 `alpine` 映像建立後移除 |

---

### `restart_container(container_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `container_id: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `container.restart(timeout=10)` |
| 權限 | Docker group |
| 安全驗證 | container_id 格式驗證 |
| 風險 | 低 — 短暫服務中斷 |
| 錯誤情境 | 容器不存在 |
| 測試策略 | 建立 alpine 容器 → restart → 驗證 running |

---

### `remove_image(image_id: str, force: bool) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `image_id: str`<br>`force: bool = False` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `client.images.remove(image_id, force=force)` |
| 權限 | Docker group |
| 安全驗證 | image_id 格式驗證 |
| 風險 | 中 — force=True 會移除正在使用的映像 |
| 錯誤情境 | 映像被容器使用中（非 force）、映像不存在 |
| 測試策略 | pull alpine → remove → 驗證不在 list |

---

### `get_container_stats(container_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `container_id: str` |
| 回傳 | `{"success": bool, "cpu_percent": float, "memory_mb": float, "memory_limit_mb": float, "memory_percent": float, "network_rx_mb": float, "network_tx_mb": float}` |
| 底層工具 | `container.stats(stream=False)` → 計算百分比 |
| 權限 | Docker group |
| 前置條件 | 容器必須 running |
| 風險 | 無（唯讀） |
| 錯誤情境 | 容器未運行、容器不存在 |
| 測試策略 | 運行中容器取 stats |

---

### `inspect_container(container_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `container_id: str` |
| 回傳 | `{"success": bool, "config": dict}` — 完整 container.attrs |
| 底層工具 | `container.attrs` |
| 權限 | Docker group |
| 風險 | 無 |
| 錯誤情境 | 容器不存在 |
| 測試策略 | 建立容器 → inspect |

---

### `prune_images() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "deleted_count": int, "space_reclaimed_mb": float}` |
| 底層工具 | `client.images.prune()` |
| 權限 | Docker group |
| 風險 | 中 — 無法復原已刪除的 dangling 映像 |
| 錯誤情境 | Docker 不可用 |
| 測試策略 | pull 映像 → untag → prune → 驗證 |

---

### `list_networks() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "networks": list[{"id": str, "name": str, "driver": str, "scope": str, "containers": list}]}` |
| 底層工具 | `client.networks.list()` |
| 權限 | Docker group |
| 風險 | 無 |
| 測試策略 | 直接呼叫驗證格式 |

---

### `create_network(name: str, driver: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str`<br>`driver: str` — `bridge` / `overlay` / `host` |
| 回傳 | `{"success": bool, "network_id": str}` |
| 底層工具 | `client.networks.create(name, driver=driver)` |
| 權限 | Docker group |
| 安全驗證 | name 格式驗證；driver 限 enum |
| 風險 | 低 |
| 錯誤情境 | name 重複 |
| 測試策略 | 建立 → 驗證存在 → 移除 |

---

### `remove_network(network_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `network_id: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `network.remove()` |
| 權限 | Docker group |
| 安全驗證 | 禁止刪除 `bridge`、`host`、`none` 預設網路 |
| 風險 | 中 — 連接中的容器會斷網 |
| 錯誤情境 | 網路有容器連接中 |
| 測試策略 | 建立 → 移除 |

---

### `list_volumes() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "volumes": list[{"name": str, "driver": str, "mountpoint": str, "created": str}]}` |
| 底層工具 | `client.volumes.list()` |
| 權限 | Docker group |
| 風險 | 無 |
| 測試策略 | 直接呼叫 |

---

### `create_volume(name: str, driver: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str`<br>`driver: str = "local"` |
| 回傳 | `{"success": bool, "name": str}` |
| 底層工具 | `client.volumes.create(name, driver=driver)` |
| 權限 | Docker group |
| 安全驗證 | name 格式驗證 |
| 風險 | 無 |
| 錯誤情境 | name 重複 |
| 測試策略 | 建立 → 列表驗證 → 移除 |

---

### `remove_volume(name: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `volume.remove(force=False)` |
| 權限 | Docker group |
| 風險 | ⚠️ **不可逆** — 資料遺失 |
| 錯誤情境 | volume 正被容器使用 |
| 測試策略 | 建立 → 移除 |

---

### `deploy_compose(yaml_content: str, project_name: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `yaml_content: str` — docker-compose.yml 內容<br>`project_name: str` |
| 回傳 | `{"success": bool, "services": list[str], "message": str}` |
| 底層工具 | 寫入暫存 yaml → `docker compose -p {project_name} -f {file} up -d` |
| 權限 | Docker group + root（docker compose） |
| 前置條件 | docker compose CLI 已安裝 |
| 安全驗證 | YAML 解析驗證；禁止 `privileged: true`；volumes 路徑限制 |
| 風險 | 中 — 不當設定可能暴露主機 |
| 錯誤情境 | YAML 語法錯誤、映像拉取失敗、port 衝突 |
| 測試策略 | 簡單 nginx compose 部署後移除 |
| 依賴套件 | `pyyaml`（驗證 YAML） |

---

### `list_compose_projects() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "projects": list[{"name": str, "status": str, "services": int}]}` |
| 底層工具 | `docker compose ls --format json` |
| 權限 | Docker group |
| 風險 | 無 |
| 測試策略 | mock output |

---

### `remove_compose_project(name: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `name: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `docker compose -p {name} down --volumes` |
| 權限 | Docker group |
| 風險 | ⚠️ 含 `--volumes` 會刪除 named volumes |
| 錯誤情境 | project 不存在 |
| 測試策略 | 部署 → 移除 → 驗證 |

---

## 5. 使用者 & 權限 (`services/user_service.py`)

---

### `update_user(username: str, config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `username: str`<br>`config: dict` — `{shell: str, groups: str, home: str}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `usermod -s {shell} -G {groups} {username}` |
| 權限 | root |
| 安全驗證 | username 不可為 root/admin（自我鎖定防護）；shell 限已安裝的 shells (`/etc/shells`) |
| 風險 | 低 |
| 錯誤情境 | 使用者不存在、無效 shell、群組不存在 |
| 測試策略 | 建立暫存使用者 → 修改 → 驗證 → 刪除 |

---

### `disable_user(username: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `username: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `usermod -L {username}` + `smbpasswd -d {username}` |
| 權限 | root |
| 安全驗證 | 禁止停用最後一個管理員帳號 |
| 風險 | 低 — 可用 enable_user 復原 |
| 錯誤情境 | 使用者不存在、是唯一管理員 |
| 測試策略 | 建立使用者 → disable → 驗證無法登入 → enable |

---

### `enable_user(username: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `username: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `usermod -U {username}` + `smbpasswd -e {username}` |
| 權限 | root |
| 風險 | 無 |
| 錯誤情境 | 使用者不存在 |
| 測試策略 | 同 disable |

---

### `update_group_members(name: str, add: list[str], remove: list[str]) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str` — 群組名<br>`add: list[str]` — 要加入的使用者<br>`remove: list[str]` — 要移除的使用者 |
| 回傳 | `{"success": bool, "added": list, "removed": list, "errors": list}` |
| 底層工具 | `gpasswd -a {user} {group}` / `gpasswd -d {user} {group}` |
| 權限 | root |
| 安全驗證 | 群組與使用者必須存在 |
| 風險 | 低 |
| 錯誤情境 | 群組不存在、使用者不存在 |
| 測試策略 | 建立群組+使用者 → 加入/移除 → 驗證 |

---

### `get_quota(username: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `username: str` |
| 回傳 | `{"success": bool, "username": str, "used_mb": float, "soft_limit_mb": float, "hard_limit_mb": float}` |
| 底層工具 | `quota -u {username} --output=csv` 或 `repquota` |
| 權限 | root |
| 前置條件 | 檔案系統啟用 quota（`usrquota` mount option） |
| 風險 | 無（唯讀） |
| 錯誤情境 | quota 未啟用、使用者不存在 |
| 測試策略 | mock output（quota 需特殊 FS 設定） |

---

### `set_quota(username: str, soft_mb: int, hard_mb: int) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `username: str`<br>`soft_mb: int`<br>`hard_mb: int` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `setquota -u {username} {soft} {hard} 0 0 {filesystem}` |
| 權限 | root |
| 前置條件 | quota 已啟用 |
| 安全驗證 | soft <= hard；數值正整數 |
| 風險 | 低 |
| 錯誤情境 | quota 未啟用、數值不合理 |
| 測試策略 | mock |

---

### `get_audit_log(filters: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `filters: dict` — `{username: str, action: str, since: str, limit: int}` |
| 回傳 | `{"success": bool, "logs": list[{"timestamp": str, "username": str, "action": str, "detail": str, "ip": str}]}` |
| 底層工具 | 自建 audit_log table（SQLite）或解析 `/var/log/auth.log` |
| 權限 | admin |
| 安全驗證 | limit 上限 1000 |
| 風險 | 無 |
| 錯誤情境 | DB 不存在 |
| 測試策略 | fixture DB |
| 依賴套件 | SQLAlchemy |

---

### `setup_totp(username: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `username: str` |
| 回傳 | `{"success": bool, "secret": str, "qr_uri": str}` |
| 底層工具 | `pyotp.random_base32()` + `pyotp.totp.TOTP(secret).provisioning_uri()` |
| 權限 | 本人或 admin |
| 安全驗證 | secret 加密儲存於 DB |
| 風險 | 低 |
| 錯誤情境 | 使用者不存在 |
| 測試策略 | 產生 → verify 驗證 |
| 依賴套件 | `pyotp`, `qrcode` |

---

### `verify_totp(username: str, code: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `username: str`<br>`code: str` — 6 位數 TOTP code |
| 回傳 | `{"success": bool, "valid": bool}` |
| 底層工具 | `pyotp.TOTP(secret).verify(code)` |
| 權限 | 本人 |
| 安全驗證 | 限制嘗試次數（防暴力破解） |
| 風險 | 無 |
| 錯誤情境 | 使用者未設定 2FA、code 過期 |
| 測試策略 | setup → 用 pyotp 產生 code → verify |

---

### `list_sessions() -> dict` / `revoke_session(session_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `list`: 無<br>`revoke`: `session_id: str` |
| 回傳 | list: `{"sessions": list[{"id": str, "username": str, "ip": str, "created_at": str, "last_active": str}]}`<br>revoke: `{"success": bool}` |
| 底層工具 | JWT blacklist table（DB）或 Redis SET |
| 權限 | admin |
| 安全驗證 | 禁止踢掉自己唯一 session |
| 風險 | 低 |
| 依賴套件 | SQLAlchemy 或 Redis |
| 測試策略 | 登入多 session → list → revoke → 驗證失效 |

---

## 6. 系統管理 (`services/system_service.py`) — 擴充

---

### `get_system_logs(unit: str | None, lines: int, since: str | None) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `unit: str | None` — systemd unit 過濾<br>`lines: int = 100`<br>`since: str | None` — e.g. `"1 hour ago"` |
| 回傳 | `{"success": bool, "logs": list[{"timestamp": str, "unit": str, "priority": str, "message": str}]}` |
| 底層工具 | `journalctl --output=json -n {lines} [-u {unit}] [--since={since}]` |
| 權限 | root 或 `systemd-journal` group |
| 安全驗證 | lines 限 1-5000；unit 格式驗證（英數+hyphen）；since 格式驗證 |
| 風險 | 無（唯讀） |
| 錯誤情境 | unit 不存在、journalctl 不可用 |
| 測試策略 | mock subprocess output |

---

### `power_action(action: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `action: str` — `shutdown` / `reboot` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `shutdown -h now` / `reboot` |
| 權限 | root |
| 安全驗證 | action 限 enum；建議前端二次確認 |
| 風險 | ⚠️ **高** — 系統立即關機/重啟，所有連線中斷 |
| 錯誤情境 | 權限不足 |
| 測試策略 | mock（不可實際執行） |

---

### `get_temperatures() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "cpu_temp_c": float, "disks": list[{"device": str, "temp_c": int}]}` |
| 底層工具 | `sensors --json`（CPU）+ `smartctl`（磁碟） |
| 權限 | root |
| 前置條件 | `lm-sensors` 已安裝並設定 |
| 安全驗證 | 無 |
| 風險 | 無 |
| 錯誤情境 | sensors 未安裝、SMART 不支援 |
| 測試策略 | mock output |
| 依賴套件 | 系統 `lm-sensors`、`smartmontools` |

---

### `list_services() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "services": list[{"name": str, "status": str, "enabled": bool, "description": str}]}` |
| 底層工具 | `systemctl list-units --type=service --all --output=json` |
| 權限 | 一般使用者可讀 |
| 風險 | 無 |
| 錯誤情境 | systemd 不可用（非 systemd 系統） |
| 測試策略 | 直接呼叫；mock for CI |

---

### `control_service(name: str, action: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str` — 服務名稱<br>`action: str` — `start` / `stop` / `restart` / `enable` / `disable` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `systemctl {action} {name}` |
| 權限 | root |
| 安全驗證 | name 白名單或格式驗證（禁止 injection）；action 限 enum |
| 風險 | 中 — 停止關鍵服務可能斷網/斷存取 |
| 錯誤情境 | 服務不存在、依賴服務衝突 |
| 測試策略 | 使用非關鍵服務測試（如 `cron`） |

---

### `update_system_settings(config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `config: dict` — `{hostname: str, timezone: str, ntp_enabled: bool}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `hostnamectl set-hostname`、`timedatectl set-timezone`、`timedatectl set-ntp` |
| 權限 | root |
| 安全驗證 | hostname 限英數+hyphen，長度 1-63；timezone 須存在於 `timedatectl list-timezones` |
| 風險 | 低 |
| 錯誤情境 | timezone 無效 |
| 測試策略 | mock（避免改變實際系統） |

---

### `get_hardware_info() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "cpu": {"model": str, "cores": int, "threads": int}, "memory": {"slots": list, "total_gb": float}, "pci_devices": list[str]}` |
| 底層工具 | `lscpu --json`、`dmidecode -t memory`、`lspci` |
| 權限 | root（dmidecode 需要） |
| 風險 | 無 |
| 測試策略 | mock output |

---

### `check_updates() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "upgradable_count": int, "packages": list[{"name": str, "current": str, "available": str}]}` |
| 底層工具 | `apt update -qq` → `apt list --upgradable` |
| 權限 | root（apt update） |
| 風險 | 無（只檢查不安裝） |
| 錯誤情境 | 無網路、apt lock |
| 測試策略 | mock output |

---

### `apply_updates() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `packages: list[str] | None` — None 表示全部更新 |
| 回傳 | `{"success": bool, "updated_count": int, "message": str}` |
| 底層工具 | `apt upgrade -y` 或 `apt install --only-upgrade {packages}` |
| 權限 | root |
| 風險 | ⚠️ 中 — 可能需要重啟；更新失敗可能影響系統穩定 |
| 錯誤情境 | apt lock、空間不足、套件相依衝突 |
| 測試策略 | mock（不可在 CI 實際更新） |

---

### `list_cron_jobs() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "jobs": list[{"id": int, "schedule": str, "command": str, "user": str}]}` |
| 底層工具 | `crontab -l` 解析（root + 各使用者） |
| 權限 | root |
| 風險 | 無 |
| 測試策略 | mock output |

---

### `add_cron_job(schedule: str, command: str, user: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `schedule: str` — cron 表達式 (e.g. `0 2 * * *`)<br>`command: str`<br>`user: str = "root"` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 讀取 crontab → 追加 → 寫回 `crontab -u {user} -` |
| 權限 | root |
| 安全驗證 | schedule 格式驗證（5 欄位）；command 禁止 `rm -rf /` 等危險指令 |
| 風險 | 低 — 可用 remove 復原 |
| 錯誤情境 | schedule 格式錯誤 |
| 測試策略 | 新增 → list 驗證 → 移除 |

---

### `remove_cron_job(job_id: int, user: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `job_id: int` — 行號<br>`user: str = "root"` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 讀取 crontab → 移除行 → 寫回 |
| 權限 | root |
| 風險 | 低 |
| 測試策略 | 同 add |

---

### `record_metrics() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | 無（由排程呼叫） |
| 回傳 | `{"success": bool, "recorded_at": str}` |
| 底層工具 | `psutil` 採集 → INSERT INTO SQLite |
| 權限 | 系統服務帳號 |
| 前置條件 | DB schema 已建立 |
| 風險 | 無 |
| 測試策略 | 呼叫 → 查詢 DB 驗證寫入 |

---

### `get_metrics_history(hours: int) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `hours: int = 24` |
| 回傳 | `{"success": bool, "data": list[{"timestamp": str, "cpu_percent": float, "memory_percent": float, "temperature": float}]}` |
| 底層工具 | SQLite SELECT WHERE timestamp > now - hours |
| 權限 | 一般使用者 |
| 安全驗證 | hours 限 1-720 |
| 風險 | 無 |
| 測試策略 | fixture DB + 查詢 |

---

## 7. 網路管理 (`services/network_service.py`) 🆕

---

### `list_interfaces() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "interfaces": list[{"name": str, "mac": str, "ipv4": str, "ipv6": str, "status": "up"/"down", "speed_mbps": int, "mtu": int}]}` |
| 底層工具 | `ip -j addr show` |
| 權限 | 一般使用者可讀 |
| 風險 | 無 |
| 錯誤情境 | `ip` 指令不可用（極少見） |
| 測試策略 | 直接呼叫；mock for CI |

---

### `configure_interface(name: str, config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `name: str` — 介面名稱 (e.g. `eth0`)<br>`config: dict` — `{method: "dhcp"/"static", ip: str, netmask: str, gateway: str, dns: list[str]}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | Netplan: 寫入 `/etc/netplan/*.yaml` → `netplan apply`<br>ifupdown: 寫入 `/etc/network/interfaces` → `ifup/ifdown` |
| 權限 | root |
| 前置條件 | 偵測系統使用 Netplan 或 ifupdown |
| 安全驗證 | IP/netmask 格式驗證（`ipaddress` 模組）；name 必須存在於 `list_interfaces()` |
| 風險 | ⚠️ **高** — 錯誤設定可能導致網路中斷、遠端連線失效 |
| 錯誤情境 | IP 衝突、gateway 不可達、DNS 格式錯誤 |
| 測試策略 | mock（不可在 CI 實際修改網路）；可用 network namespace 隔離測試 |

---

### `list_firewall_rules() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "backend": "iptables"/"nftables", "rules": list[{"id": int, "chain": str, "target": str, "protocol": str, "source": str, "destination": str, "port": str}]}` |
| 底層工具 | `iptables -L -n --line-numbers` 或 `nft -j list ruleset` |
| 權限 | root |
| 風險 | 無（唯讀） |
| 測試策略 | mock output |

---

### `add_firewall_rule(rule: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `rule: dict` — `{chain: "INPUT"/"OUTPUT", protocol: "tcp"/"udp", port: int, source: str, target: "ACCEPT"/"DROP"}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `iptables -A {chain} -p {protocol} --dport {port} -s {source} -j {target}` |
| 權限 | root |
| 安全驗證 | chain/protocol/target 限 enum；port 1-65535；source 為有效 IP/CIDR |
| 風險 | ⚠️ 中 — 錯誤規則可能鎖定自己（建議先加 ACCEPT 22） |
| 錯誤情境 | 語法錯誤、規則衝突 |
| 測試策略 | network namespace 隔離 |

---

### `delete_firewall_rule(rule_id: int, chain: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `rule_id: int`<br>`chain: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `iptables -D {chain} {rule_id}` |
| 權限 | root |
| 安全驗證 | 禁止刪除保護 SSH 的規則（除非明確確認） |
| 風險 | 中 |
| 測試策略 | 新增 → 刪除 → 驗證 |

---

### `get_realtime_stats() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `interval: float = 1.0` — 取樣間隔秒數 |
| 回傳 | `{"success": bool, "interfaces": list[{"name": str, "rx_bytes_per_sec": int, "tx_bytes_per_sec": int}]}` |
| 底層工具 | 讀取 `/sys/class/net/{name}/statistics/rx_bytes` 兩次取差值 |
| 權限 | 一般使用者 |
| 風險 | 無 |
| 錯誤情境 | 介面消失（拔除 USB 網卡） |
| 測試策略 | 直接呼叫驗證格式 |

---

### `ping(host: str, count: int) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `host: str`<br>`count: int = 4` |
| 回傳 | `{"success": bool, "host": str, "packets_sent": int, "packets_received": int, "avg_ms": float, "output": str}` |
| 底層工具 | `ping -c {count} -W 3 {host}` |
| 權限 | 一般使用者 |
| 安全驗證 | host 禁止 shell metachar；count 限 1-20 |
| 風險 | 無 |
| 錯誤情境 | host 不可達、DNS 解析失敗 |
| 測試策略 | ping localhost |

---

### `traceroute(host: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `host: str` |
| 回傳 | `{"success": bool, "hops": list[{"hop": int, "ip": str, "rtt_ms": float}], "output": str}` |
| 底層工具 | `traceroute -n -m 20 {host}` |
| 權限 | root（某些系統需要） |
| 安全驗證 | host 禁止 shell metachar |
| 風險 | 無 |
| 錯誤情境 | traceroute 未安裝 |
| 測試策略 | traceroute localhost |
| 依賴套件 | 系統 `traceroute` |

---

### `dns_lookup(domain: str, record_type: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `domain: str`<br>`record_type: str` — `A` / `AAAA` / `MX` / `CNAME` / `TXT` |
| 回傳 | `{"success": bool, "domain": str, "records": list[str], "server": str}` |
| 底層工具 | `dig +short {domain} {record_type}` |
| 權限 | 一般使用者 |
| 安全驗證 | domain 格式驗證；record_type 限 enum |
| 風險 | 無 |
| 錯誤情境 | dig 未安裝、domain 不存在 |
| 測試策略 | dig localhost A |
| 依賴套件 | 系統 `dnsutils` |

---

### `send_wol(mac: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `mac: str` — MAC 位址 (e.g. `AA:BB:CC:DD:EE:FF`) |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `wakeonlan {mac}` 或手動構造 UDP magic packet (port 9) |
| 權限 | 一般使用者（UDP broadcast） |
| 安全驗證 | MAC 格式驗證 `^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$` |
| 風險 | 無 |
| 錯誤情境 | 目標裝置不支援 WOL、不在同一子網 |
| 測試策略 | 驗證封包發送（不保證喚醒） |

---

## 8. 備份 & 同步 (`services/backup_service.py`) 🆕

---

### `list_backup_tasks() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "tasks": list[{"id": str, "name": str, "source": str, "destination": str, "schedule": str, "retention": int, "last_run": str, "last_status": str}]}` |
| 底層工具 | SQLite SELECT |
| 權限 | admin |
| 前置條件 | DB schema 已建立 |
| 風險 | 無 |
| 測試策略 | fixture DB |
| 依賴套件 | SQLAlchemy |

---

### `create_backup_task(config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `config: dict` — `{name, source, destination, schedule, retention_days, method: "rsync"/"borg"/"restic"}` |
| 回傳 | `{"success": bool, "task_id": str}` |
| 底層工具 | INSERT INTO DB + 註冊 APScheduler job |
| 權限 | admin |
| 安全驗證 | source/destination 路徑驗證；schedule 為有效 cron 表達式 |
| 風險 | 無（建立不執行） |
| 錯誤情境 | source 不存在、schedule 格式錯誤 |
| 測試策略 | 建立 → 列表驗證 |
| 依賴套件 | SQLAlchemy, APScheduler, `croniter`（驗證 cron） |

---

### `run_backup(task_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🔴 高 |
| 參數 | `task_id: str` |
| 回傳 | `{"success": bool, "duration_sec": float, "files_transferred": int, "size_mb": float}` |
| 底層工具 | 依 method：<br>`rsync -avz --delete {source} {destination}`<br>`borg create {repo}::{archive} {source}`<br>`restic -r {repo} backup {source}` |
| 權限 | root（跨使用者目錄存取） |
| 前置條件 | task 已建立；destination 可存取 |
| 安全驗證 | task_id 存在於 DB；防止並行執行同一任務（lock） |
| 風險 | 低 — 目的地寫入不影響來源 |
| 錯誤情境 | source 不存在、destination 空間不足、網路中斷（遠端備份） |
| 測試策略 | 暫存目錄 rsync 測試 |
| 依賴套件 | 系統 `rsync` / `borg` / `restic` |

---

### `update_backup_task(task_id: str, config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `task_id: str`<br>`config: dict` — 同 create，部分更新 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | UPDATE DB + 重新註冊 scheduler |
| 權限 | admin |
| 風險 | 無 |
| 測試策略 | 建立 → 修改 → 驗證 |

---

### `delete_backup_task(task_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `task_id: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | DELETE FROM DB + 移除 scheduler job |
| 權限 | admin |
| 安全驗證 | 不刪除備份資料本身（只移除排程） |
| 風險 | 低 |
| 測試策略 | 建立 → 刪除 → 驗證不在列表 |

---

### `get_backup_history(task_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `task_id: str` |
| 回傳 | `{"success": bool, "history": list[{"run_id": str, "timestamp": str, "status": str, "duration_sec": float, "size_mb": float, "error": str | None}]}` |
| 底層工具 | SQLite SELECT WHERE task_id |
| 權限 | admin |
| 風險 | 無 |
| 測試策略 | fixture DB |

---

### `restore_backup(task_id: str, version: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `task_id: str`<br>`version: str` — 備份版本/archive 名稱 |
| 回傳 | `{"success": bool, "restored_to": str, "files_count": int}` |
| 底層工具 | `borg extract {repo}::{version}` / `restic restore {version} --target {path}` |
| 權限 | root |
| 安全驗證 | version 必須存在；還原目標路徑驗證 |
| 風險 | ⚠️ **中** — 可能覆蓋現有檔案 |
| 錯誤情境 | version 不存在、空間不足 |
| 測試策略 | 備份 → 修改來源 → 還原 → 驗證內容回復 |

---

### `schedule_backup(task_id: str, cron_expr: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `task_id: str`<br>`cron_expr: str` — e.g. `0 2 * * *` |
| 回傳 | `{"success": bool, "next_run": str}` |
| 底層工具 | APScheduler `add_job` with CronTrigger |
| 權限 | admin |
| 安全驗證 | cron_expr 格式驗證 |
| 風險 | 無 |
| 測試策略 | 驗證 next_run 計算正確 |
| 依賴套件 | APScheduler, croniter |

---

### `list_snapshots() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "snapshots": list[{"path": str, "created": str, "size": str}]}` |
| 底層工具 | `btrfs subvolume list {mount}` |
| 權限 | root |
| 前置條件 | 使用 Btrfs 檔案系統 |
| 風險 | 無 |
| 錯誤情境 | 非 Btrfs FS |
| 測試策略 | mock output |

---

### `create_snapshot(subvol: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `subvol: str` — 來源 subvolume 路徑 |
| 回傳 | `{"success": bool, "snapshot_path": str}` |
| 底層工具 | `btrfs subvolume snapshot -r {subvol} {dest}` |
| 權限 | root |
| 安全驗證 | subvol 路徑驗證 |
| 風險 | 無（唯讀快照不影響原資料） |
| 測試策略 | 需 Btrfs 環境 |

---

### `delete_snapshot(path: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `path: str` — 快照路徑 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | `btrfs subvolume delete {path}` |
| 權限 | root |
| 安全驗證 | path 必須是 snapshot（驗證 subvolume info） |
| 風險 | ⚠️ 不可逆 |
| 測試策略 | 建立 → 刪除 → 驗證 |

---

## 9. 遠端存取 (`services/remote_service.py`) 🆕

---

### `get_ddns_config() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "enabled": bool, "provider": str, "domain": str, "last_update": str, "current_ip": str}` |
| 底層工具 | 讀取設定檔（DB 或 JSON） |
| 權限 | admin |
| 風險 | 無 |
| 測試策略 | fixture config |

---

### `update_ddns_config(provider: str, domain: str, token: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `provider: str` — `cloudflare` / `duckdns` / `noip`<br>`domain: str`<br>`token: str` — API token |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 寫入設定檔 + 註冊定時更新 job |
| 權限 | admin |
| 安全驗證 | token 加密儲存；provider 限 enum |
| 風險 | 低 |
| 錯誤情境 | token 無效（呼叫 API 驗證） |
| 測試策略 | mock API call |

---

### `ddns_update_ip() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "ip": str, "message": str}` |
| 底層工具 | 取得公網 IP（`httpx.get("https://api.ipify.org")`）→ 呼叫 provider API 更新 |
| 權限 | admin |
| 前置條件 | DDNS 已設定 |
| 風險 | 無 |
| 錯誤情境 | 無法取得公網 IP、provider API 回傳錯誤 |
| 測試策略 | mock httpx |
| 依賴套件 | `httpx` |

---

### `issue_ssl_cert(domain: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `domain: str` |
| 回傳 | `{"success": bool, "cert_path": str, "expires": str}` |
| 底層工具 | `certbot certonly --standalone -d {domain} --non-interactive --agree-tos -m {email}` |
| 權限 | root |
| 前置條件 | port 80 未被佔用（standalone mode）；domain DNS 已指向本機 |
| 安全驗證 | domain 格式驗證 |
| 風險 | 低 — Let's Encrypt 有頻率限制 |
| 錯誤情境 | DNS 未指向本機、port 80 佔用、頻率超限 |
| 測試策略 | staging 環境 `--staging` flag |
| 依賴套件 | 系統 `certbot` |

---

### `get_ssl_status() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "certs": list[{"domain": str, "expires": str, "days_remaining": int}]}` |
| 底層工具 | 解析 `/etc/letsencrypt/live/*/cert.pem` |
| 權限 | root |
| 風險 | 無 |
| 測試策略 | mock cert 檔案 |

---

### `get_vpn_status() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "interface": str, "running": bool, "public_key": str, "listen_port": int, "peers": list[{"public_key": str, "endpoint": str, "last_handshake": str, "transfer_rx": int, "transfer_tx": int}]}` |
| 底層工具 | `wg show wg0 dump` 解析 |
| 權限 | root |
| 前置條件 | WireGuard 已安裝、wg0 已設定 |
| 風險 | 無 |
| 錯誤情境 | WireGuard 未安裝/未啟動 |
| 測試策略 | mock output |

---

### `update_vpn_config(config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `config: dict` — `{address, listen_port, private_key, dns}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 寫入 `/etc/wireguard/wg0.conf` → `wg-quick down wg0 && wg-quick up wg0` |
| 權限 | root |
| 安全驗證 | private_key 格式驗證（base64, 44 chars）；port 1-65535 |
| 風險 | ⚠️ 中 — 錯誤設定可能中斷 VPN |
| 錯誤情境 | config 格式錯誤、port 佔用 |
| 測試策略 | mock（或 network namespace） |

---

### `add_vpn_peer(peer_config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `peer_config: dict` — `{public_key, allowed_ips, endpoint, persistent_keepalive}` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 追加 `[Peer]` section 到 wg0.conf → `wg syncconf wg0 <(wg-quick strip wg0)` |
| 權限 | root |
| 安全驗證 | public_key 格式；allowed_ips 為有效 CIDR |
| 風險 | 低 |
| 測試策略 | mock |

---

### `remove_vpn_peer(public_key: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `public_key: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 移除 wg0.conf 中對應 Peer section → sync |
| 權限 | root |
| 風險 | 低 — 該 peer 立即斷線 |
| 測試策略 | 新增 → 移除 → 驗證 |

---

### `manage_reverse_proxy(rules: list[dict]) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `rules: list[dict]` — `[{domain, upstream, ssl: bool}]` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 產生 Nginx server block 或 Caddy Caddyfile → `nginx -t && systemctl reload nginx` |
| 權限 | root |
| 安全驗證 | domain 格式驗證；upstream 為 `host:port` 格式 |
| 風險 | 中 — 語法錯誤可能導致 Nginx 無法 reload |
| 錯誤情境 | 語法錯誤、upstream 不可達 |
| 測試策略 | `nginx -t` 語法檢查 |

---

## 10. 通知系統 (`services/notification_service.py`) 🆕

---

### `send_notification(channel: str, title: str, body: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `channel: str` — `email` / `telegram` / `webhook`<br>`title: str`<br>`body: str` |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | Email: `smtplib`<br>Telegram: `httpx.post("https://api.telegram.org/bot{token}/sendMessage")`<br>Webhook: `httpx.post(url, json=payload)` |
| 權限 | 系統（由事件觸發）或 admin（手動測試） |
| 安全驗證 | token/密碼加密儲存；webhook URL 格式驗證 |
| 風險 | 無 |
| 錯誤情境 | SMTP 連線失敗、Telegram token 無效、webhook 逾時 |
| 測試策略 | mock HTTP；Email 使用 `aiosmtpd` 假 server |
| 依賴套件 | `httpx` |

---

### `get_notification_settings() -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | 無 |
| 回傳 | `{"success": bool, "email": {"enabled": bool, "smtp_host": str, "smtp_port": int, "from": str}, "telegram": {"enabled": bool, "chat_id": str}, "webhook": {"enabled": bool, "url": str}}` |
| 底層工具 | DB/JSON 讀取 |
| 權限 | admin |
| 安全驗證 | token/password 回傳時遮罩（`***`） |
| 風險 | 無 |
| 測試策略 | fixture config |

---

### `update_notification_settings(config: dict) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `config: dict` — 同 get 回傳結構 |
| 回傳 | `{"success": bool, "message": str}` |
| 底層工具 | 寫入 DB/JSON |
| 權限 | admin |
| 安全驗證 | smtp_port 1-65535；URL 格式驗證 |
| 風險 | 無 |
| 測試策略 | 更新 → get 驗證 |

---

### `list_notifications(user: str, unread_only: bool) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟡 中 |
| 參數 | `user: str`<br>`unread_only: bool = False` |
| 回傳 | `{"success": bool, "notifications": list[{"id": str, "title": str, "body": str, "level": str, "read": bool, "created_at": str}]}` |
| 底層工具 | SQLite SELECT |
| 權限 | 本人或 admin |
| 安全驗證 | 僅能查看自己的通知（除非 admin） |
| 風險 | 無 |
| 測試策略 | fixture DB |

---

### `mark_read(notification_id: str) -> dict`

| 項目 | 內容 |
|------|------|
| 優先級 | 🟢 低 |
| 參數 | `notification_id: str` |
| 回傳 | `{"success": bool}` |
| 底層工具 | UPDATE notifications SET read=true WHERE id |
| 權限 | 本人 |
| 風險 | 無 |
| 測試策略 | 建立通知 → mark → 驗證 |

---

## 基礎設施待建

| 優先級 | 元件 | 說明 | 依賴套件 |
|--------|------|------|----------|
| 🔴 高 | 資料庫層 | SQLite + SQLAlchemy async，models + migrations | `sqlalchemy[asyncio]`, `aiosqlite`, `alembic` |
| 🔴 高 | 日誌框架 | structlog 結構化 logging，統一格式 | `structlog` |
| 🟡 中 | 背景任務 | APScheduler，備份排程 + 監控採集 + DDNS | `apscheduler` |
| 🟡 中 | WebSocket | FastAPI WebSocket，容器日誌串流 + 速率推送 | 內建 |
| 🟡 中 | 速率限制 | slowapi，防暴力登入（5 次/分鐘） | `slowapi` |
| 🟡 中 | 設定持久化 | 系統設定存入 DB（取代只讀 .env） | SQLAlchemy |
| 🟢 低 | 測試覆蓋 | pytest + httpx TestClient + coverage | `pytest`, `pytest-asyncio`, `httpx`, `coverage` |
| 🟢 低 | API 版本管理 | `/api/v1/` prefix，向下相容 | — |

---

## 優先順序統計

| 優先級 | 函式數 | 說明 |
|--------|--------|------|
| 🔴 高 | 24 | 核心操作函式 |
| 🟡 中 | 53 | 進階管理邏輯 |
| 🟢 低 | 30 | 加值/企業功能 |
| **總計** | **107** | |

### 建議開發順序

1. **Phase 1 — 基礎 + 核心**
   - 建立 DB 層 + 日誌框架
   - file_service（檔案管理器）
   - storage（format + SMART）
   - system（logs + power + temperature）
   - docker（create + restart + remove_image）

2. **Phase 2 — 管理完善**
   - 共享編輯 + ACL
   - 網路介面 + 防火牆
   - 備份任務 CRUD + 執行
   - APScheduler 整合
   - 通知系統
   - WebSocket 即時推送

3. **Phase 3 — 進階功能**
   - Docker Compose
   - VPN / DDNS / SSL
   - 2FA / Session / 稽核
   - 快照 / 歷史圖表
   - 測試覆蓋 80%+
