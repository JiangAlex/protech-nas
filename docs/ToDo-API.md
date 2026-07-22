# Backend — 尚未實作 API 端點（詳細規格）

> 更新日期：2026-07-20
>
> Router 層：對外 HTTP 端點。
> 每個端點包含：Request Body/Params、Response 結構、權限等級、錯誤碼、依賴 Service、注意事項。

---

## 1. 儲存管理 (`/api/storage/*`)

---

### `POST /api/storage/format` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 格式化磁碟 |
| Request Body | `{"device": "/dev/sdb1", "fs_type": "ext4"}` |
| Response 200 | `{"success": true, "message": "Formatted /dev/sdb1 as ext4"}` |
| 權限 | admin（JWT required） |
| 錯誤碼 | 400: device 不存在/仍掛載中<br>403: 權限不足<br>422: 參數驗證失敗 |
| 依賴 Service | `storage_service.format_disk()` |
| 注意事項 | ⚠️ 不可逆操作；前端需二次確認對話框；禁止格式化系統碟 |

---

### `GET /api/storage/smart/{device}` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 讀取 S.M.A.R.T. 健康資訊 |
| Path Param | `device` — URL encode (e.g. `%2Fdev%2Fsda`) |
| Response 200 | `{"success": true, "smart_status": "PASSED", "temperature": 38, "power_on_hours": 12500, "attributes": [...]}` |
| 權限 | admin |
| 錯誤碼 | 400: 裝置不支援 SMART<br>404: 裝置不存在 |
| 依賴 Service | `storage_service.get_smart_info()` |
| 注意事項 | device 含 `/`，需 URL encode 或改用 query param |

---

### `POST /api/storage/smart/{device}/test` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 執行 S.M.A.R.T. 自檢 |
| Path Param | `device` |
| Request Body | `{"test_type": "short"}` |
| Response 200 | `{"success": true, "message": "Short test started", "estimated_minutes": 2}` |
| 權限 | admin |
| 錯誤碼 | 400: 已有測試在進行<br>422: test_type 無效 |
| 依賴 Service | `storage_service.run_smart_test()` |
| 注意事項 | 非同步操作，回傳後需輪詢取得結果 |

---

### `POST /api/storage/partition` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 建立分割區 |
| Request Body | `{"device": "/dev/sdb", "size": "100G", "part_type": "primary"}` |
| Response 200 | `{"success": true, "partition": "/dev/sdb1"}` |
| 權限 | admin |
| 錯誤碼 | 400: 無可用空間/裝置不存在<br>422: 參數錯誤 |
| 依賴 Service | `storage_service.create_partition()` |
| 注意事項 | 系統碟黑名單保護 |

---

### `DELETE /api/storage/partition/{device}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 刪除分割區 |
| Path Param | `device` — e.g. `sdb1` |
| Response 200 | `{"success": true, "message": "Partition deleted"}` |
| 權限 | admin |
| 錯誤碼 | 400: 仍在掛載中<br>404: 不存在 |
| 依賴 Service | `storage_service.delete_partition()` |
| 注意事項 | ⚠️ 不可逆；需前端確認 |

---

### `POST /api/storage/raid/create` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 建立 RAID 陣列 |
| Request Body | `{"name": "md0", "level": 1, "devices": ["/dev/sdb", "/dev/sdc"], "spare": ["/dev/sdd"]}` |
| Response 200 | `{"success": true, "device": "/dev/md0"}` |
| 權限 | admin |
| 錯誤碼 | 400: 裝置數不足/已屬其他 RAID<br>422: level 不支援 |
| 依賴 Service | `storage_service.create_raid()` |
| 注意事項 | ⚠️ 成員碟資料清除；需多重確認 |

---

### `DELETE /api/storage/raid/{name}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 移除 RAID 陣列 |
| Path Param | `name` — e.g. `md0` |
| Response 200 | `{"success": true, "message": "RAID md0 removed"}` |
| 權限 | admin |
| 錯誤碼 | 400: 仍在掛載<br>404: 不存在 |
| 依賴 Service | `storage_service.remove_raid()` |
| 注意事項 | ⚠️ 不可逆 |

---

### `POST /api/storage/raid/{name}/add` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 向 RAID 加入磁碟 |
| Request Body | `{"device": "/dev/sde"}` |
| Response 200 | `{"success": true, "message": "Disk added, rebuilding"}` |
| 權限 | admin |
| 錯誤碼 | 400: 容量太小/裝置已在使用 |
| 依賴 Service | `storage_service.add_raid_disk()` |

---

### `GET /api/storage/fstab` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 讀取自動掛載設定 |
| Response 200 | `{"success": true, "entries": [{"device": "/dev/sda1", "mount": "/", "fs": "ext4", "options": "defaults", "dump": 0, "pass": 1}]}` |
| 權限 | admin |
| 依賴 Service | `storage_service.get_fstab()` |

---

### `POST /api/storage/fstab` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 新增自動掛載項目 |
| Request Body | `{"device": "/dev/sdb1", "mount": "/data", "fs": "ext4", "options": "defaults,noatime"}` |
| Response 200 | `{"success": true, "message": "fstab entry added"}` |
| 權限 | admin |
| 錯誤碼 | 400: 重複掛載點<br>422: 裝置不存在 |
| 依賴 Service | `storage_service.add_fstab_entry()` |
| 注意事項 | 錯誤設定可能導致開機失敗；建議用 `mount -a --fake` 驗證 |

---

### `DELETE /api/storage/fstab` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 移除自動掛載項目 |
| Query Param | `mount=/data` |
| Response 200 | `{"success": true, "message": "fstab entry removed"}` |
| 權限 | admin |
| 錯誤碼 | 400: 禁止移除系統掛載<br>404: 不存在 |
| 依賴 Service | `storage_service.remove_fstab_entry()` |

---

### `GET /api/storage/usage/history` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 磁碟使用量歷史資料 |
| Query Param | `days=30` |
| Response 200 | `{"success": true, "history": [{"timestamp": "...", "device": "...", "used_gb": 120.5, "percent": 65.2}]}` |
| 權限 | admin |
| 依賴 Service | `storage_service.get_usage_history()` |
| 注意事項 | 需背景採集任務已啟動 |

---

## 2. 檔案共享 (`/api/shares/*`)

---

### `PUT /api/shares/smb/{name}` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 編輯現有 SMB 共享設定 |
| Path Param | `name` — 共享名稱 |
| Request Body | `{"path": "/data/share1", "comment": "Updated", "read_only": true, "guest_ok": false, "valid_users": "user1,user2"}` |
| Response 200 | `{"success": true, "message": "Share [name] updated"}` |
| 權限 | admin |
| 錯誤碼 | 404: 共享不存在<br>400: smbd restart 失敗 |
| 依賴 Service | `samba_service.update_smb_share()` |
| 注意事項 | 修改後自動重啟 smbd |

---

### `PUT /api/shares/nfs/{path}` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 編輯現有 NFS 匯出設定 |
| Query Param | `path=/data/nfs1`（因 path 含 `/`） |
| Request Body | `{"clients": "192.168.1.0/24(rw,sync,no_subtree_check)"}` |
| Response 200 | `{"success": true, "message": "Export updated"}` |
| 權限 | admin |
| 錯誤碼 | 404: export 不存在<br>400: clients 格式錯誤 |
| 依賴 Service | `nfs_service.update_nfs_export()` |

---

### `GET /api/shares/smb/{name}/acl` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 取得共享資料夾 ACL 權限 |
| Response 200 | `{"success": true, "owner": "root", "group": "data", "permissions": "rwxrwxr-x", "acl": [{"type": "user", "name": "alex", "perms": "rwx"}]}` |
| 權限 | admin |
| 錯誤碼 | 404: 共享不存在 |
| 依賴 Service | `samba_service.get_share_acl()` |

---

### `PUT /api/shares/smb/{name}/acl` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 設定共享資料夾存取權限 |
| Request Body | `{"acl": [{"type": "user", "name": "alex", "perms": "rwx"}, {"type": "group", "name": "dev", "perms": "rx"}]}` |
| Response 200 | `{"success": true, "message": "ACL updated"}` |
| 權限 | admin |
| 錯誤碼 | 400: 使用者/群組不存在<br>422: perms 格式錯誤 |
| 依賴 Service | `samba_service.set_share_acl()` |

---

### `GET /api/shares/smb/status` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | Samba 服務狀態與連線數 |
| Response 200 | `{"success": true, "service_running": true, "connections": [{"user": "alex", "ip": "192.168.1.10", "share": "data"}]}` |
| 權限 | admin |
| 依賴 Service | `samba_service.get_smb_status()` |

---

### `GET /api/shares/nfs/status` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | NFS 服務狀態與客戶端連線 |
| Response 200 | `{"success": true, "service_running": true, "clients": [{"ip": "192.168.1.20", "mount": "/data"}]}` |
| 權限 | admin |
| 依賴 Service | `nfs_service.get_nfs_status()` |

---

## 3. 檔案管理器 (`/api/files/*`) 🆕

---

### `GET /api/files/list` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 列出指定目錄的檔案與資料夾 |
| Query Param | `path=/data/documents&sort=name&order=asc` |
| Response 200 | `{"success": true, "path": "/data/documents", "items": [{"name": "file.txt", "type": "file", "size": 1024, "modified": "2026-07-20T10:00:00", "permissions": "rw-r--r--"}]}` |
| 權限 | authenticated（依使用者對目錄的讀取權限） |
| 錯誤碼 | 403: 無權限<br>404: 路徑不存在<br>400: 非目錄 |
| 依賴 Service | `file_service.list_directory()` |
| 注意事項 | 路徑穿越防護（realpath 驗證） |

---

### `POST /api/files/upload` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 上傳檔案 |
| Content-Type | `multipart/form-data` |
| Form Fields | `file: UploadFile`<br>`dest: str` — 目標目錄路徑 |
| Response 200 | `{"success": true, "path": "/data/documents/file.txt", "size": 1024}` |
| 權限 | authenticated（依使用者對目標目錄的寫入權限） |
| 錯誤碼 | 403: 無寫入權限<br>400: 空間不足<br>413: 檔案過大 |
| 依賴 Service | `file_service.save_upload()` |
| 注意事項 | 限制上傳大小（預設 2GB）；同名檔案自動加序號 |

---

### `GET /api/files/download` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 下載檔案 |
| Query Param | `path=/data/documents/file.txt` |
| Response 200 | `FileResponse`（binary stream + Content-Disposition） |
| 權限 | authenticated（依使用者對檔案的讀取權限） |
| 錯誤碼 | 403: 無權限<br>404: 檔案不存在<br>400: 是目錄而非檔案 |
| 依賴 Service | `file_service.get_download_path()` |
| 注意事項 | 使用 `StreamingResponse` 支援大檔案；設定正確 MIME type |

---

### `POST /api/files/mkdir` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 建立資料夾 |
| Request Body | `{"path": "/data/documents/new-folder"}` |
| Response 200 | `{"success": true, "path": "/data/documents/new-folder"}` |
| 權限 | authenticated（依父目錄寫入權限） |
| 錯誤碼 | 400: 已存在<br>403: 無權限 |
| 依賴 Service | `file_service.make_directory()` |

---

### `DELETE /api/files/delete` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 刪除檔案或資料夾 |
| Request Body | `{"path": "/data/documents/old-file.txt"}` |
| Response 200 | `{"success": true, "message": "Deleted"}` |
| 權限 | authenticated（依寫入權限） |
| 錯誤碼 | 403: 無權限<br>404: 不存在<br>400: 禁止刪除根目錄 |
| 依賴 Service | `file_service.delete_item()` |
| 注意事項 | ⚠️ 不可逆；建議可選移至回收站 |

---

### `POST /api/files/move` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 搬移或重新命名 |
| Request Body | `{"src": "/data/a.txt", "dst": "/data/backup/a.txt"}` |
| Response 200 | `{"success": true, "new_path": "/data/backup/a.txt"}` |
| 權限 | authenticated（src 寫入 + dst 父目錄寫入） |
| 錯誤碼 | 404: src 不存在<br>400: dst 已存在<br>403: 無權限 |
| 依賴 Service | `file_service.move_item()` |

---

### `POST /api/files/copy` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 複製檔案或資料夾 |
| Request Body | `{"src": "/data/a.txt", "dst": "/data/backup/a.txt"}` |
| Response 200 | `{"success": true, "new_path": "/data/backup/a.txt"}` |
| 權限 | authenticated（src 讀取 + dst 寫入） |
| 錯誤碼 | 404: src 不存在<br>400: 空間不足 |
| 依賴 Service | `file_service.copy_item()` |

---

### `GET /api/files/info` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 檔案詳細資訊 |
| Query Param | `path=/data/file.txt` |
| Response 200 | `{"success": true, "name": "file.txt", "type": "file", "size": 1024, "mime": "text/plain", "created": "...", "modified": "...", "permissions": "rw-r--r--", "owner": "alex"}` |
| 權限 | authenticated |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `file_service.get_file_info()` |

---

### `POST /api/files/compress` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 壓縮檔案 |
| Request Body | `{"paths": ["/data/a.txt", "/data/folder/"], "format": "zip", "dest": "/data/archive.zip"}` |
| Response 200 | `{"success": true, "archive_path": "/data/archive.zip", "size": 5120}` |
| 權限 | authenticated |
| 錯誤碼 | 400: 空間不足<br>404: paths 不存在 |
| 依賴 Service | `file_service.compress()` |
| 注意事項 | 大檔案為非同步任務，回傳 task_id |

---

### `POST /api/files/extract` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 解壓縮 |
| Request Body | `{"archive": "/data/archive.zip", "dest": "/data/extracted/"}` |
| Response 200 | `{"success": true, "extracted_path": "/data/extracted/", "file_count": 12}` |
| 權限 | authenticated |
| 錯誤碼 | 400: 格式不支援/檔案損壞<br>404: archive 不存在 |
| 依賴 Service | `file_service.extract()` |
| 注意事項 | Zip Slip 防護 |

---

### `POST /api/files/share` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 產生公開分享連結 |
| Request Body | `{"path": "/data/file.pdf", "expires_hours": 72, "password": "optional"}` |
| Response 200 | `{"success": true, "link_id": "abc123", "url": "/api/files/shared/abc123", "expires_at": "2026-07-23T17:00:00"}` |
| 權限 | authenticated |
| 錯誤碼 | 404: 檔案不存在 |
| 依賴 Service | `file_service.create_share_link()` |
| 注意事項 | 另需一個 `GET /api/files/shared/{link_id}` 公開端點供下載 |

---

## 4. Docker 容器化 (`/api/docker/*`)

---

### `POST /api/docker/containers/create` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 建立新容器 |
| Request Body | `{"image": "nginx:latest", "name": "my-nginx", "ports": {"80/tcp": 8080}, "volumes": {"/data/web": {"bind": "/usr/share/nginx/html", "mode": "ro"}}, "environment": {"TZ": "Asia/Taipei"}, "restart_policy": "always"}` |
| Response 200 | `{"success": true, "container_id": "abc123", "name": "my-nginx"}` |
| 權限 | admin |
| 錯誤碼 | 400: port 佔用/name 重複<br>404: 映像不存在<br>500: Docker 不可用 |
| 依賴 Service | `docker_service.create_container()` |
| 注意事項 | volumes host path 限制在安全目錄；不允許 `--privileged` |

---

### `POST /api/docker/containers/{id}/restart` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 重啟容器 |
| Path Param | `id` — container ID 或 name |
| Response 200 | `{"success": true, "message": "Container restarted"}` |
| 權限 | admin |
| 錯誤碼 | 404: 容器不存在 |
| 依賴 Service | `docker_service.restart_container()` |

---

### `DELETE /api/docker/images/{id}` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 刪除映像 |
| Path Param | `id` — image ID 或 tag |
| Query Param | `force=false` |
| Response 200 | `{"success": true, "message": "Image removed"}` |
| 權限 | admin |
| 錯誤碼 | 400: 映像被容器使用中<br>404: 不存在 |
| 依賴 Service | `docker_service.remove_image()` |

---

### `GET /api/docker/containers/{id}/stats` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 容器即時資源使用 |
| Response 200 | `{"success": true, "cpu_percent": 15.2, "memory_mb": 256.0, "memory_limit_mb": 1024.0, "memory_percent": 25.0, "network_rx_mb": 10.5, "network_tx_mb": 3.2}` |
| 權限 | admin |
| 錯誤碼 | 400: 容器未運行<br>404: 不存在 |
| 依賴 Service | `docker_service.get_container_stats()` |

---

### `GET /api/docker/containers/{id}/inspect` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 容器完整設定資訊 |
| Response 200 | `{"success": true, "config": { ... full docker inspect output ... }}` |
| 權限 | admin |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `docker_service.inspect_container()` |

---

### `POST /api/docker/images/prune` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 清理無用映像 |
| Response 200 | `{"success": true, "deleted_count": 5, "space_reclaimed_mb": 1200.5}` |
| 權限 | admin |
| 依賴 Service | `docker_service.prune_images()` |
| 注意事項 | 不可逆；僅清理 dangling images |

---

### `GET /api/docker/networks` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 列出 Docker 網路 |
| Response 200 | `{"success": true, "networks": [{"id": "...", "name": "bridge", "driver": "bridge", "scope": "local"}]}` |
| 權限 | admin |
| 依賴 Service | `docker_service.list_networks()` |

---

### `POST /api/docker/networks` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 建立 Docker 網路 |
| Request Body | `{"name": "my-network", "driver": "bridge"}` |
| Response 200 | `{"success": true, "network_id": "..."}` |
| 權限 | admin |
| 錯誤碼 | 400: name 重複 |
| 依賴 Service | `docker_service.create_network()` |

---

### `DELETE /api/docker/networks/{id}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 刪除 Docker 網路 |
| Response 200 | `{"success": true, "message": "Network removed"}` |
| 權限 | admin |
| 錯誤碼 | 400: 有容器連接中/預設網路<br>404: 不存在 |
| 依賴 Service | `docker_service.remove_network()` |

---

### `GET /api/docker/volumes` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 列出 Docker Volume |
| Response 200 | `{"success": true, "volumes": [{"name": "data-vol", "driver": "local", "mountpoint": "/var/lib/docker/volumes/data-vol/_data"}]}` |
| 權限 | admin |
| 依賴 Service | `docker_service.list_volumes()` |

---

### `POST /api/docker/volumes` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 建立 Volume |
| Request Body | `{"name": "data-vol", "driver": "local"}` |
| Response 200 | `{"success": true, "name": "data-vol"}` |
| 權限 | admin |
| 錯誤碼 | 400: name 重複 |
| 依賴 Service | `docker_service.create_volume()` |

---

### `DELETE /api/docker/volumes/{name}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 刪除 Volume |
| Response 200 | `{"success": true, "message": "Volume removed"}` |
| 權限 | admin |
| 錯誤碼 | 400: 正被使用<br>404: 不存在 |
| 依賴 Service | `docker_service.remove_volume()` |
| 注意事項 | ⚠️ 不可逆，資料遺失 |

---

### `POST /api/docker/compose/deploy` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 上傳 docker-compose.yml 並部署 |
| Content-Type | `multipart/form-data` |
| Form Fields | `file: UploadFile`<br>`project_name: str` |
| Response 200 | `{"success": true, "services": ["web", "db"], "message": "Deployed"}` |
| 權限 | admin |
| 錯誤碼 | 400: YAML 語法錯誤/映像拉取失敗<br>422: 缺少 project_name |
| 依賴 Service | `docker_service.deploy_compose()` |
| 注意事項 | 安全檢查 YAML 內容（禁止 privileged） |

---

### `GET /api/docker/compose/projects` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 列出 Compose 專案 |
| Response 200 | `{"success": true, "projects": [{"name": "myapp", "status": "running", "services": 3}]}` |
| 權限 | admin |
| 依賴 Service | `docker_service.list_compose_projects()` |

---

### `DELETE /api/docker/compose/projects/{name}` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 停止並移除 Compose 專案 |
| Query Param | `remove_volumes=false` |
| Response 200 | `{"success": true, "message": "Project removed"}` |
| 權限 | admin |
| 依賴 Service | `docker_service.remove_compose_project()` |
| 注意事項 | `remove_volumes=true` 會刪除 named volumes |

---

## 5. 使用者 & 權限 (`/api/users/*`)

---

### `PUT /api/users/{username}` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 編輯使用者資訊 |
| Request Body | `{"shell": "/bin/bash", "groups": "docker,data"}` |
| Response 200 | `{"success": true, "message": "User updated"}` |
| 權限 | admin |
| 錯誤碼 | 404: 使用者不存在<br>400: 無效 shell/群組不存在 |
| 依賴 Service | `user_service.update_user()` |

---

### `PUT /api/users/{username}/status` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 停用或啟用使用者 |
| Request Body | `{"enabled": false}` |
| Response 200 | `{"success": true, "message": "User disabled"}` |
| 權限 | admin |
| 錯誤碼 | 400: 不可停用唯一管理員<br>404: 不存在 |
| 依賴 Service | `user_service.disable_user()` / `enable_user()` |

---

### `PUT /api/users/groups/{name}/members` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 群組成員管理 |
| Request Body | `{"add": ["user1", "user2"], "remove": ["user3"]}` |
| Response 200 | `{"success": true, "added": ["user1", "user2"], "removed": ["user3"]}` |
| 權限 | admin |
| 錯誤碼 | 404: 群組不存在<br>400: 使用者不存在 |
| 依賴 Service | `user_service.update_group_members()` |

---

### `GET /api/users/{username}/quota` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 取得使用者磁碟配額 |
| Response 200 | `{"success": true, "username": "alex", "used_mb": 5120, "soft_limit_mb": 10240, "hard_limit_mb": 12288}` |
| 權限 | admin 或本人 |
| 錯誤碼 | 404: 不存在<br>400: quota 未啟用 |
| 依賴 Service | `user_service.get_quota()` |

---

### `PUT /api/users/{username}/quota` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 設定磁碟配額 |
| Request Body | `{"soft_mb": 10240, "hard_mb": 12288}` |
| Response 200 | `{"success": true, "message": "Quota set"}` |
| 權限 | admin |
| 錯誤碼 | 400: quota 未啟用/soft > hard<br>404: 不存在 |
| 依賴 Service | `user_service.set_quota()` |

---

### `GET /api/users/audit` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 使用者操作稽核日誌 |
| Query Param | `username=alex&action=login&since=2026-07-01&limit=50` |
| Response 200 | `{"success": true, "logs": [{"timestamp": "...", "username": "alex", "action": "login", "ip": "192.168.1.5"}]}` |
| 權限 | admin |
| 依賴 Service | `user_service.get_audit_log()` |

---

### `POST /api/users/{username}/2fa/setup` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 設定 TOTP 兩步驟驗證 |
| Response 200 | `{"success": true, "secret": "JBSWY3DPEHPK3PXP", "qr_uri": "otpauth://totp/ProTech:alex?secret=..."}` |
| 權限 | 本人或 admin |
| 依賴 Service | `user_service.setup_totp()` |
| 注意事項 | 回傳 secret 僅此一次，需前端顯示 QR code |

---

### `POST /api/users/{username}/2fa/verify` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 驗證 TOTP code |
| Request Body | `{"code": "123456"}` |
| Response 200 | `{"success": true, "valid": true}` |
| 權限 | 本人 |
| 錯誤碼 | 400: 未設定 2FA<br>401: code 無效 |
| 依賴 Service | `user_service.verify_totp()` |
| 注意事項 | 限制嘗試次數，5 次失敗鎖定 5 分鐘 |

---

### `GET /api/auth/sessions` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 目前活躍 session 列表 |
| Response 200 | `{"success": true, "sessions": [{"id": "...", "username": "admin", "ip": "192.168.1.5", "created_at": "...", "last_active": "..."}]}` |
| 權限 | admin |
| 依賴 Service | `user_service.list_sessions()` |

---

### `DELETE /api/auth/sessions/{id}` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 踢出指定 session |
| Response 200 | `{"success": true, "message": "Session revoked"}` |
| 權限 | admin |
| 錯誤碼 | 404: session 不存在 |
| 依賴 Service | `user_service.revoke_session()` |
| 注意事項 | 該使用者下次請求會收到 401 |

---

## 6. 系統管理 (`/api/system/*`) 🆕

---

### `GET /api/system/logs` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 系統日誌 |
| Query Param | `unit=nginx&lines=200&since=1+hour+ago` |
| Response 200 | `{"success": true, "logs": [{"timestamp": "...", "unit": "nginx", "priority": "info", "message": "..."}]}` |
| 權限 | admin |
| 錯誤碼 | 400: unit 不存在 |
| 依賴 Service | `system_service.get_system_logs()` |

---

### `POST /api/system/power/shutdown` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 關機 |
| Request Body | `{"delay_seconds": 0}` (可選) |
| Response 200 | `{"success": true, "message": "Shutting down"}` |
| 權限 | admin |
| 依賴 Service | `system_service.power_action("shutdown")` |
| 注意事項 | ⚠️ 不可逆；前端需二次確認+倒數 |

---

### `POST /api/system/power/reboot` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 重啟 |
| Response 200 | `{"success": true, "message": "Rebooting"}` |
| 權限 | admin |
| 依賴 Service | `system_service.power_action("reboot")` |
| 注意事項 | 前端顯示重啟倒數 + 自動重新連線檢測 |

---

### `GET /api/system/temperature` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | CPU/HDD 溫度 |
| Response 200 | `{"success": true, "cpu_temp_c": 55.0, "disks": [{"device": "/dev/sda", "temp_c": 38}]}` |
| 權限 | admin |
| 錯誤碼 | 500: sensors 未安裝 |
| 依賴 Service | `system_service.get_temperatures()` |

---

### `GET /api/system/services` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 列出系統服務狀態 |
| Response 200 | `{"success": true, "services": [{"name": "smbd", "status": "running", "enabled": true, "description": "Samba SMB Daemon"}]}` |
| 權限 | admin |
| 依賴 Service | `system_service.list_services()` |

---

### `POST /api/system/services/{name}/start` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 啟動服務 |
| Response 200 | `{"success": true, "message": "Service started"}` |
| 權限 | admin |
| 錯誤碼 | 404: 服務不存在<br>400: 啟動失敗 |
| 依賴 Service | `system_service.control_service(name, "start")` |

---

### `POST /api/system/services/{name}/stop` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 停止服務 |
| Response 200 | `{"success": true, "message": "Service stopped"}` |
| 權限 | admin |
| 錯誤碼 | 404: 不存在<br>400: 停止失敗 |
| 依賴 Service | `system_service.control_service(name, "stop")` |
| 注意事項 | 停止 smbd/nfs-server 會中斷共享連線 |

---

### `POST /api/system/services/{name}/restart` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 重啟服務 |
| Response 200 | `{"success": true, "message": "Service restarted"}` |
| 權限 | admin |
| 依賴 Service | `system_service.control_service(name, "restart")` |

---

### `PUT /api/system/settings` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 修改系統設定 |
| Request Body | `{"hostname": "protech-nas", "timezone": "Asia/Taipei", "ntp_enabled": true}` |
| Response 200 | `{"success": true, "message": "Settings updated"}` |
| 權限 | admin |
| 錯誤碼 | 400: timezone 無效/hostname 格式錯誤 |
| 依賴 Service | `system_service.update_system_settings()` |

---

### `GET /api/system/hardware` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 詳細硬體資訊 |
| Response 200 | `{"success": true, "cpu": {"model": "Intel N100", "cores": 4, "threads": 4}, "memory": {"total_gb": 16, "slots": [...]}, "pci_devices": [...]}` |
| 權限 | admin |
| 依賴 Service | `system_service.get_hardware_info()` |

---

### `GET /api/system/updates` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 檢查可用更新 |
| Response 200 | `{"success": true, "upgradable_count": 12, "packages": [{"name": "nginx", "current": "1.24.0", "available": "1.26.0"}]}` |
| 權限 | admin |
| 依賴 Service | `system_service.check_updates()` |

---

### `POST /api/system/updates/apply` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 套用系統更新 |
| Request Body | `{"packages": ["nginx", "openssl"]}` 或 `{}` 全部更新 |
| Response 200 | `{"success": true, "updated_count": 12, "message": "Updates applied"}` |
| 權限 | admin |
| 錯誤碼 | 400: apt lock/空間不足 |
| 依賴 Service | `system_service.apply_updates()` |
| 注意事項 | 非同步長時間操作；可能需要重啟 |

---

### `GET /api/system/cron` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 列出排程任務 |
| Response 200 | `{"success": true, "jobs": [{"id": 1, "schedule": "0 2 * * *", "command": "/usr/local/bin/backup.sh", "user": "root"}]}` |
| 權限 | admin |
| 依賴 Service | `system_service.list_cron_jobs()` |

---

### `POST /api/system/cron` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 新增排程任務 |
| Request Body | `{"schedule": "0 2 * * *", "command": "/usr/local/bin/backup.sh", "user": "root"}` |
| Response 200 | `{"success": true, "message": "Cron job added"}` |
| 權限 | admin |
| 錯誤碼 | 422: schedule 格式錯誤 |
| 依賴 Service | `system_service.add_cron_job()` |

---

### `DELETE /api/system/cron/{id}` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 刪除排程任務 |
| Response 200 | `{"success": true, "message": "Cron job removed"}` |
| 權限 | admin |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `system_service.remove_cron_job()` |

---

### `GET /api/dashboard/history` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 歷史監控資料 |
| Query Param | `hours=24` |
| Response 200 | `{"success": true, "data": [{"timestamp": "...", "cpu_percent": 25.0, "memory_percent": 60.0, "temperature": 55.0}]}` |
| 權限 | admin |
| 依賴 Service | `system_service.get_metrics_history()` |
| 注意事項 | 需背景採集任務 |

---

## 7. 網路管理 (`/api/network/*`) 🆕

---

### `GET /api/network/interfaces` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 列出網路介面 |
| Response 200 | `{"success": true, "interfaces": [{"name": "eth0", "mac": "00:11:22:33:44:55", "ipv4": "192.168.1.100", "ipv6": "fe80::1", "status": "up", "speed_mbps": 1000, "mtu": 1500}]}` |
| 權限 | admin |
| 依賴 Service | `network_service.list_interfaces()` |

---

### `PUT /api/network/interfaces/{name}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 設定網路介面 |
| Request Body | `{"method": "static", "ip": "192.168.1.100", "netmask": "255.255.255.0", "gateway": "192.168.1.1", "dns": ["8.8.8.8", "1.1.1.1"]}` |
| Response 200 | `{"success": true, "message": "Interface configured"}` |
| 權限 | admin |
| 錯誤碼 | 400: IP 格式錯誤/gateway 不可達<br>404: 介面不存在 |
| 依賴 Service | `network_service.configure_interface()` |
| 注意事項 | ⚠️ 錯誤設定可能導致遠端斷線；建議套用前驗證 + 30 秒回復機制 |

---

### `GET /api/network/firewall/rules` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 列出防火牆規則 |
| Response 200 | `{"success": true, "backend": "iptables", "rules": [{"id": 1, "chain": "INPUT", "target": "ACCEPT", "protocol": "tcp", "port": "22", "source": "0.0.0.0/0"}]}` |
| 權限 | admin |
| 依賴 Service | `network_service.list_firewall_rules()` |

---

### `POST /api/network/firewall/rules` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 新增防火牆規則 |
| Request Body | `{"chain": "INPUT", "protocol": "tcp", "port": 443, "source": "0.0.0.0/0", "target": "ACCEPT"}` |
| Response 200 | `{"success": true, "message": "Rule added"}` |
| 權限 | admin |
| 錯誤碼 | 422: 參數格式錯誤 |
| 依賴 Service | `network_service.add_firewall_rule()` |
| 注意事項 | 確保 SSH (port 22) 規則永遠存在，避免鎖死 |

---

### `DELETE /api/network/firewall/rules/{id}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 刪除防火牆規則 |
| Query Param | `chain=INPUT` |
| Response 200 | `{"success": true, "message": "Rule deleted"}` |
| 權限 | admin |
| 錯誤碼 | 400: 禁止刪除 SSH 保護規則<br>404: 規則不存在 |
| 依賴 Service | `network_service.delete_firewall_rule()` |

---

### `GET /api/network/stats` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 即時網路速率 |
| Response 200 | `{"success": true, "interfaces": [{"name": "eth0", "rx_bytes_per_sec": 102400, "tx_bytes_per_sec": 51200}]}` |
| 權限 | admin |
| 依賴 Service | `network_service.get_realtime_stats()` |
| 注意事項 | 取樣需 ~1 秒延遲；考慮改用 WebSocket 推送 |

---

### `POST /api/network/diag/ping` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | Ping 測試 |
| Request Body | `{"host": "8.8.8.8", "count": 4}` |
| Response 200 | `{"success": true, "host": "8.8.8.8", "packets_sent": 4, "packets_received": 4, "avg_ms": 12.5, "output": "..."}` |
| 權限 | admin |
| 錯誤碼 | 400: host 不可達 |
| 依賴 Service | `network_service.ping()` |
| 注意事項 | 設定 timeout，避免長時間掛起 |

---

### `POST /api/network/diag/traceroute` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | Traceroute 測試 |
| Request Body | `{"host": "google.com"}` |
| Response 200 | `{"success": true, "hops": [{"hop": 1, "ip": "192.168.1.1", "rtt_ms": 1.2}], "output": "..."}` |
| 權限 | admin |
| 依賴 Service | `network_service.traceroute()` |
| 注意事項 | 可能耗時較長（最多 20 hops） |

---

### `POST /api/network/diag/dns` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | DNS 查詢 |
| Request Body | `{"domain": "example.com", "record_type": "A"}` |
| Response 200 | `{"success": true, "domain": "example.com", "records": ["93.184.216.34"], "server": "8.8.8.8"}` |
| 權限 | admin |
| 依賴 Service | `network_service.dns_lookup()` |

---

### `POST /api/network/wol` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 發送 Wake-on-LAN 封包 |
| Request Body | `{"mac": "AA:BB:CC:DD:EE:FF"}` |
| Response 200 | `{"success": true, "message": "WOL packet sent"}` |
| 權限 | admin |
| 錯誤碼 | 422: MAC 格式錯誤 |
| 依賴 Service | `network_service.send_wol()` |

---

## 8. 備份 & 同步 (`/api/backup/*`) 🆕

---

### `GET /api/backup/tasks` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 列出所有備份任務 |
| Response 200 | `{"success": true, "tasks": [{"id": "...", "name": "Daily Backup", "source": "/data", "destination": "/backup", "schedule": "0 2 * * *", "last_run": "...", "last_status": "success"}]}` |
| 權限 | admin |
| 依賴 Service | `backup_service.list_backup_tasks()` |

---

### `POST /api/backup/tasks` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 建立備份任務 |
| Request Body | `{"name": "Daily Backup", "source": "/data", "destination": "/backup", "schedule": "0 2 * * *", "retention_days": 30, "method": "rsync"}` |
| Response 200 | `{"success": true, "task_id": "..."}` |
| 權限 | admin |
| 錯誤碼 | 400: source 不存在<br>422: schedule 格式錯誤 |
| 依賴 Service | `backup_service.create_backup_task()` |

---

### `POST /api/backup/tasks/{id}/run` 🔴 高

| 項目 | 內容 |
|------|------|
| 說明 | 立即執行備份 |
| Response 200 | `{"success": true, "duration_sec": 120.5, "files_transferred": 450, "size_mb": 2048.0}` |
| 權限 | admin |
| 錯誤碼 | 400: 任務正在執行中<br>404: task 不存在 |
| 依賴 Service | `backup_service.run_backup()` |
| 注意事項 | 長時間操作；考慮非同步 + WebSocket 進度回報 |

---

### `PUT /api/backup/tasks/{id}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 編輯備份任務 |
| Request Body | 同 POST（部分更新） |
| Response 200 | `{"success": true, "message": "Task updated"}` |
| 權限 | admin |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `backup_service.update_backup_task()` |

---

### `DELETE /api/backup/tasks/{id}` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 刪除備份任務 |
| Response 200 | `{"success": true, "message": "Task deleted"}` |
| 權限 | admin |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `backup_service.delete_backup_task()` |
| 注意事項 | 僅刪除排程，不刪除已備份資料 |

---

### `GET /api/backup/tasks/{id}/history` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 備份執行歷史 |
| Query Param | `limit=20` |
| Response 200 | `{"success": true, "history": [{"run_id": "...", "timestamp": "...", "status": "success", "duration_sec": 120.5, "size_mb": 2048.0}]}` |
| 權限 | admin |
| 依賴 Service | `backup_service.get_backup_history()` |

---

### `POST /api/backup/restore` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 還原指定版本 |
| Request Body | `{"task_id": "...", "version": "2026-07-20T02:00:00", "target_path": "/data/restored"}` |
| Response 200 | `{"success": true, "restored_to": "/data/restored", "files_count": 450}` |
| 權限 | admin |
| 錯誤碼 | 404: version 不存在<br>400: 空間不足 |
| 依賴 Service | `backup_service.restore_backup()` |
| 注意事項 | ⚠️ 可能覆蓋現有檔案 |

---

### `GET /api/backup/snapshots` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 列出檔案系統快照 |
| Response 200 | `{"success": true, "snapshots": [{"path": "/snapshots/2026-07-20", "created": "...", "size": "2.5G"}]}` |
| 權限 | admin |
| 依賴 Service | `backup_service.list_snapshots()` |

---

### `POST /api/backup/snapshots` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 建立快照 |
| Request Body | `{"subvol": "/data"}` |
| Response 200 | `{"success": true, "snapshot_path": "/snapshots/2026-07-20-170000"}` |
| 權限 | admin |
| 錯誤碼 | 400: 非 Btrfs |
| 依賴 Service | `backup_service.create_snapshot()` |

---

### `DELETE /api/backup/snapshots/{id}` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 刪除快照 |
| Response 200 | `{"success": true, "message": "Snapshot deleted"}` |
| 權限 | admin |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `backup_service.delete_snapshot()` |
| 注意事項 | ⚠️ 不可逆 |

---

## 9. 遠端存取 (`/api/remote/*`) 🆕

---

### `GET /api/remote/ddns` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | DDNS 設定狀態 |
| Response 200 | `{"success": true, "enabled": true, "provider": "cloudflare", "domain": "nas.example.com", "last_update": "2026-07-20T10:00:00", "current_ip": "1.2.3.4"}` |
| 權限 | admin |
| 依賴 Service | `remote_service.get_ddns_config()` |

---

### `PUT /api/remote/ddns` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 設定 DDNS |
| Request Body | `{"provider": "cloudflare", "domain": "nas.example.com", "token": "xxx", "enabled": true}` |
| Response 200 | `{"success": true, "message": "DDNS configured"}` |
| 權限 | admin |
| 錯誤碼 | 400: token 驗證失敗<br>422: provider 不支援 |
| 依賴 Service | `remote_service.update_ddns_config()` |

---

### `GET /api/remote/ssl` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | SSL 憑證狀態 |
| Response 200 | `{"success": true, "certs": [{"domain": "nas.example.com", "expires": "2026-10-20", "days_remaining": 92}]}` |
| 權限 | admin |
| 依賴 Service | `remote_service.get_ssl_status()` |

---

### `POST /api/remote/ssl/issue` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 申請 Let's Encrypt 憑證 |
| Request Body | `{"domain": "nas.example.com", "email": "admin@example.com"}` |
| Response 200 | `{"success": true, "cert_path": "/etc/letsencrypt/live/...", "expires": "2026-10-20"}` |
| 權限 | admin |
| 錯誤碼 | 400: DNS 未指向本機/port 80 佔用 |
| 依賴 Service | `remote_service.issue_ssl_cert()` |
| 注意事項 | Let's Encrypt 有頻率限制（5 次/週/域名） |

---

### `GET /api/remote/vpn/status` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | VPN 連線狀態 |
| Response 200 | `{"success": true, "interface": "wg0", "running": true, "public_key": "...", "listen_port": 51820, "peers": [{"public_key": "...", "endpoint": "1.2.3.4:51820", "last_handshake": "...", "transfer_rx": 1024000, "transfer_tx": 512000}]}` |
| 權限 | admin |
| 錯誤碼 | 400: WireGuard 未安裝 |
| 依賴 Service | `remote_service.get_vpn_status()` |

---

### `PUT /api/remote/vpn/config` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | VPN 設定 |
| Request Body | `{"address": "10.0.0.1/24", "listen_port": 51820, "private_key": "...", "dns": "1.1.1.1"}` |
| Response 200 | `{"success": true, "message": "VPN configured"}` |
| 權限 | admin |
| 錯誤碼 | 400: 設定格式錯誤<br>422: port 佔用 |
| 依賴 Service | `remote_service.update_vpn_config()` |
| 注意事項 | 修改後自動重啟 wg0 介面 |

---

### `GET /api/remote/vpn/peers` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | VPN Peer 列表 |
| Response 200 | `{"success": true, "peers": [{"public_key": "...", "allowed_ips": "10.0.0.2/32", "endpoint": "..."}]}` |
| 權限 | admin |
| 依賴 Service | `remote_service.get_vpn_status()` (subset) |

---

### `POST /api/remote/vpn/peers` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 新增 Peer |
| Request Body | `{"public_key": "...", "allowed_ips": "10.0.0.2/32", "endpoint": "1.2.3.4:51820"}` |
| Response 200 | `{"success": true, "message": "Peer added"}` |
| 權限 | admin |
| 錯誤碼 | 400: public_key 格式錯誤 |
| 依賴 Service | `remote_service.add_vpn_peer()` |

---

### `DELETE /api/remote/vpn/peers/{id}` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 刪除 Peer |
| Path Param | `id` — public_key (URL-safe base64) |
| Response 200 | `{"success": true, "message": "Peer removed"}` |
| 權限 | admin |
| 依賴 Service | `remote_service.remove_vpn_peer()` |

---

### `GET /api/remote/reverse-proxy` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 反向代理規則列表 |
| Response 200 | `{"success": true, "rules": [{"domain": "app.nas.com", "upstream": "localhost:3000", "ssl": true}]}` |
| 權限 | admin |
| 依賴 Service | `remote_service.manage_reverse_proxy()` (read) |

---

### `POST /api/remote/reverse-proxy` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 新增反向代理規則 |
| Request Body | `{"domain": "app.nas.com", "upstream": "localhost:3000", "ssl": true}` |
| Response 200 | `{"success": true, "message": "Proxy rule added"}` |
| 權限 | admin |
| 錯誤碼 | 400: Nginx config 語法錯誤 |
| 依賴 Service | `remote_service.manage_reverse_proxy()` |
| 注意事項 | 新增前用 `nginx -t` 驗證 |

---

## 10. 通知系統 (`/api/notifications/*`) 🆕

---

### `GET /api/notifications` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 通知列表 |
| Query Param | `unread_only=true&limit=20` |
| Response 200 | `{"success": true, "notifications": [{"id": "...", "title": "磁碟溫度過高", "body": "/dev/sda 溫度 65°C", "level": "warning", "read": false, "created_at": "..."}]}` |
| 權限 | authenticated（僅看自己的） |
| 依賴 Service | `notification_service.list_notifications()` |

---

### `GET /api/notifications/settings` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 通知管道設定 |
| Response 200 | `{"success": true, "email": {"enabled": true, "smtp_host": "smtp.gmail.com", "from": "nas@example.com"}, "telegram": {"enabled": false}, "webhook": {"enabled": false}}` |
| 權限 | admin |
| 依賴 Service | `notification_service.get_notification_settings()` |
| 注意事項 | 敏感欄位（password/token）回傳遮罩 |

---

### `PUT /api/notifications/settings` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 設定通知管道 |
| Request Body | `{"email": {"enabled": true, "smtp_host": "smtp.gmail.com", "smtp_port": 587, "username": "...", "password": "...", "from": "nas@example.com"}, "telegram": {"enabled": true, "bot_token": "...", "chat_id": "..."}}` |
| Response 200 | `{"success": true, "message": "Settings updated"}` |
| 權限 | admin |
| 錯誤碼 | 422: 設定格式錯誤 |
| 依賴 Service | `notification_service.update_notification_settings()` |

---

### `POST /api/notifications/test` 🟡 中

| 項目 | 內容 |
|------|------|
| 說明 | 發送測試通知 |
| Request Body | `{"channel": "email"}` |
| Response 200 | `{"success": true, "message": "Test notification sent"}` |
| 權限 | admin |
| 錯誤碼 | 400: 管道未設定/發送失敗 |
| 依賴 Service | `notification_service.send_notification()` |

---

### `PUT /api/notifications/{id}/read` 🟢 低

| 項目 | 內容 |
|------|------|
| 說明 | 標記已讀 |
| Response 200 | `{"success": true}` |
| 權限 | 本人 |
| 錯誤碼 | 404: 不存在 |
| 依賴 Service | `notification_service.mark_read()` |

---

## 優先順序統計

| 優先級 | 數量 | 說明 |
|--------|------|------|
| 🔴 高 | 26 | NAS 核心功能、使用者最常操作 |
| 🟡 中 | 46 | 進階管理功能、日常維運 |
| 🟢 低 | 34 | 加值功能、企業級需求 |
| **總計** | **106** | |

---

## 建議開發順序

### Phase 1 — 核心體驗（🔴 高）
1. 檔案管理器 API（list/upload/download/mkdir/delete）
2. 儲存格式化 + SMART API
3. 系統電源 + 溫度 + 日誌 API
4. Docker 建立容器 + 重啟 + 刪映像 API
5. 使用者編輯 API
6. 網路介面列表 API
7. 備份任務 CRUD + 執行 API

### Phase 2 — 完善管理（🟡 中）
1. 共享編輯 + ACL API
2. 網路設定 + 防火牆 API
3. Docker networks/volumes API
4. 使用者停用 + 配額 + 群組管理 API
5. 系統服務管理 + 設定 + 更新 API
6. 遠端存取（DDNS/SSL/VPN）API
7. 通知系統 API

### Phase 3 — 進階功能（🟢 低）
1. Docker Compose API
2. VPN Peer / 反向代理 API
3. 2FA / Session / 稽核 API
4. 壓縮/解壓/分享連結 API
5. 排程任務 + 歷史監控 API
6. 快照管理 API
