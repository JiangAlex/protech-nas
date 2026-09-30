# 在 protech-nas 上以 Docker 部署 Redmine

於 NAS（EWS4606-02）以 Docker 部署自架 Redmine，連線至同機既有的 PostgreSQL 17
容器（`PG17`，`pgvector/pgvector:pg17`），使用**獨立的 `redmine` database**，與
ProBiz-CompanySim 的 `company_sim` 完全隔離。

## 最終可用的部署方式（docker run）

實務上 protech-nas 的 Docker Compose UI 部署踩到多個坑（見下），最終以
`docker run` 直接部署最可靠：

```bash
docker run -d --name redmine --restart unless-stopped \
  -p 3000:3000 \
  -e REDMINE_DB_POSTGRES=172.17.0.1 \
  -e REDMINE_DB_PORT=5432 \
  -e REDMINE_DB_DATABASE=redmine \
  -e REDMINE_DB_USERNAME=redmine \
  -e REDMINE_DB_PASSWORD=<redmine_db_password> \
  -e REDMINE_SECRET_KEY_BASE=<openssl rand -hex 64> \
  -v redmine-files:/usr/src/redmine/files \
  redmine:6
```

- 存取：`http://<NAS_IP>:3000`，預設 `admin` / `admin`（首次登入強制改密碼）。
- 資料：schema 在 PG17 的 `redmine` db；附件在 named volume `redmine-files`。

## 前置：在 PG17 建立 redmine 帳號與獨立 database

```bash
# 超級用戶為 user（POSTGRES_USER），入口 db 用既有的 company_sim（僅作連線入口，不會寫入）
docker exec -it PG17 psql -U user -d company_sim -c "ALTER USER redmine WITH PASSWORD '<redmine_db_password>';"
docker exec -it PG17 psql -U user -d company_sim -c "SELECT datname FROM pg_database WHERE datname='redmine';"
# 若沒有 redmine db 才建：
# docker exec -it PG17 psql -U user -d company_sim -c "CREATE DATABASE redmine OWNER redmine ENCODING 'UTF8';"

# 驗證 redmine 帳號能經 TCP 連上（模擬容器連法）
docker exec -it PG17 env PGPASSWORD='<redmine_db_password>' \
  psql -h 172.17.0.1 -U redmine -d redmine -c "SELECT 1;"
```

## 連線關鍵：為何用 172.17.0.1

- PG17 在 **預設 bridge 網路**，並將 5432 映射到 host（`0.0.0.0:5432`，由 docker-proxy 提供）。
- Redmine 容器（bridge）連 host 上的 PG17，最穩定的位址是 **docker bridge 閘道 IP**：
  ```bash
  docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'   # 通常 172.17.0.1
  ```
- **不要用 `network_mode: host` + `127.0.0.1`**：實測會 `Connection refused`（host-network
  容器連 docker-proxy 的 loopback 行為不一致）。
- PG17 的 `pg_hba.conf` 需放行 docker 網段（本環境已通；若不通加
  `host all all 172.16.0.0/12 scram-sha-256` 後 `SELECT pg_reload_conf();`）。

## 與 company_sim 的隔離

- Redmine 只用 `redmine` database + `redmine` 帳號；PostgreSQL database 層級完全隔離。
- 全程只 `CREATE`/`ALTER` redmine 專屬物件，**未碰 company_sim / cs_system**。
- 共用同一個 PG17 實例（共享 CPU/RAM/連線、同生共死），但資料互不影響。Redmine 為輕量
  工單系統，影響很小。

## 部署過程踩過的坑（時序）

| # | 現象 | 根因 | 解法 |
|---|------|------|------|
| 1 | UI 部署 422「參數錯誤：[object Object],[object Object]」 | 前端送 `name`/`yaml`，後端要 `project_name`/`yaml_content` | 修前端欄位名 + api 攔截器格式化（commit 7fb0895） |
| 2 | `docker compose: unknown command` | NAS 只有 docker-compose v1，protech-nas 寫死 v2 | 後端 `_compose_cmd()` v1/v2 偵測（commit b85f452） |
| 3 | UI 修正不生效 | nginx serve `/var/www/protech-nas` 舊前端；且 dist 被 root 擁有 build 失敗 | `sudo rm -rf dist && npm run build`，再同步到 `/var/www/protech-nas` |
| 4 | `password authentication failed for user redmine` | redmine 帳號密碼與 compose 不一致 | `ALTER USER redmine WITH PASSWORD ...` 並用 PGPASSWORD 實測一致 |
| 5 | `127.0.0.1:5432 Connection refused` | `network_mode: host` 連 docker-proxy loopback 失敗 | 改 bridge + `172.17.0.1` |
| 6 | 網頁 `ERR_CONNECTION_REFUSED`（3000） | 容器只 EXPOSE 3000，未 `-p` 發布到 host | `docker run -p 3000:3000` |
| 7 | UI Compose 移除失敗 | 現有 redmine 容器非 compose 建（無 compose label） | 用 `docker rm -f redmine` 直接管理；清 `~/.protech-nas/compose/redmine` |
| 8 | `Top level object ... not <class 'str'>` | 貼上的 YAML 縮排遺失被當字串 | 後端部署前先 pyyaml 驗證，回清楚錯誤（commit 9a03fd5） |

## 附帶修復（同時期，protech-nas 本體）

- `fb8776d` — system_service 缺 `datetime` import，metrics recorder 每分鐘 NameError。
- `524fc24` — SQLAlchemy 2.0.36 → 2.0.54（Python 3.14 相容，否則 app 啟動失敗）。

## 前端改動後的部署提醒

protech-nas 前端是 Vite build 的靜態檔，改前端後需：
```bash
cd frontend && npm run build            # 勿用 sudo，避免 dist 變 root 擁有
sudo rsync -a --delete dist/ /var/www/protech-nas/
sudo systemctl reload nginx
```

## 安全備註

- `admin` 預設密碼、redmine DB 弱密碼（部署當下用了 `000000`）應盡快改強密碼。
- PG17 的 5432 對外開放（`0.0.0.0`），弱密碼風險較高，建議輪換。
