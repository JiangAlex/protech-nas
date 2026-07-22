# Hermes Agent 自動執行方案

> 更新日期：2026-07-20
>
> 用 systemd 保持背景運行，自動依序餵 plan 給 hermes 執行。

---

## 架構

```
┌─────────────────────────────────────────┐
│  systemd service / tmux session         │
│                                         │
│  scripts/task-runner.sh (loop)          │
│    ├── 讀取 .hermes/plans/queue/ 下一個  │
│    ├── hermes --execute plan.md         │
│    ├── 檢查結果（exit code / git diff）  │
│    ├── 成功 → 移到 done/               │
│    └── 失敗 → 移到 failed/ + 通知      │
│                                         │
└─────────────────────────────────────────┘
```

## 目錄結構

```
.hermes/
└── plans/
    ├── queue/       ← 待執行的 plan（按檔名排序依序執行）
    ├── done/        ← 執行成功
    └── failed/      ← 執行失敗（需人工檢查）
```

---

## Task Runner 腳本

**檔案：** `scripts/task-runner.sh`

```bash
#!/bin/bash
# task-runner.sh — 自動餵 plan 給 hermes 執行

set -euo pipefail

WORK_DIR="/home/alex_chiang/projects/protech-nas"
QUEUE_DIR="$WORK_DIR/.hermes/plans/queue"
DONE_DIR="$WORK_DIR/.hermes/plans/done"
FAILED_DIR="$WORK_DIR/.hermes/plans/failed"
LOG_FILE="$WORK_DIR/.hermes/runner.log"

mkdir -p "$QUEUE_DIR" "$DONE_DIR" "$FAILED_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cd "$WORK_DIR"

while true; do
  # 取下一個待執行的 plan（按檔名排序）
  PLAN=$(ls "$QUEUE_DIR"/*.md 2>/dev/null | sort | head -1)

  if [ -z "$PLAN" ]; then
    log "No tasks in queue. Sleeping 60s..."
    sleep 60
    continue
  fi

  PLAN_NAME=$(basename "$PLAN")
  log "▶ Executing: $PLAN_NAME"

  # 建立 feature branch（可選）
  BRANCH="hermes/$(echo "$PLAN_NAME" | sed 's/.md$//' | tr ' ' '-')"
  git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH" 2>/dev/null || true

  # 餵給 hermes 執行（非互動模式）
  # ⚠️ 需確認 hermes 實際支援的 CLI flag（見下方注意事項）
  if hermes --no-interactive --execute "$PLAN" 2>&1 | tee -a "$LOG_FILE"; then
    EXIT_CODE=0
  else
    EXIT_CODE=$?
  fi

  if [ $EXIT_CODE -eq 0 ]; then
    log "✅ Success: $PLAN_NAME"
    mv "$PLAN" "$DONE_DIR/"
  else
    log "❌ Failed: $PLAN_NAME (exit $EXIT_CODE)"
    mv "$PLAN" "$FAILED_DIR/"

    # 可選：發送失敗通知
    # Telegram
    # curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    #   -d "chat_id=${TELEGRAM_CHAT_ID}&text=❌ Hermes plan failed: $PLAN_NAME"

    # 回到 main branch
    git checkout main 2>/dev/null || true
  fi

  # 間隔避免 API rate limit
  sleep 10
done
```

---

## systemd Service

**檔案：** `/etc/systemd/system/hermes-runner.service`

```ini
[Unit]
Description=Hermes Agent Auto Task Runner
After=network.target

[Service]
Type=simple
User=alex_chiang
Group=alex_chiang
WorkingDirectory=/home/alex_chiang/projects/protech-nas
ExecStart=/home/alex_chiang/projects/protech-nas/scripts/task-runner.sh
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# 環境變數（API Key 等）
EnvironmentFile=/home/alex_chiang/projects/protech-nas/.hermes/.env

[Install]
WantedBy=multi-user.target
```

### 啟用

```bash
# 安裝 service
sudo cp hermes-runner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hermes-runner
sudo systemctl start hermes-runner

# 查看狀態
sudo systemctl status hermes-runner

# 查看日誌
journalctl -u hermes-runner -f
```

---

## 環境變數

**檔案：** `.hermes/.env`

```bash
# LLM API Key（依你使用的 provider）
ANTHROPIC_API_KEY=sk-xxx
# 或
OPENAI_API_KEY=sk-xxx

# 可選：通知
TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx
```

---

## Plan 檔案命名規則

使用排序友好的命名，確保依序執行：

```
.hermes/plans/queue/
├── 001-file-service.md
├── 002-files-router.md
├── 003-files-vue.md
├── 004-smart-service.md
├── 005-smart-router.md
└── ...
```

---

## 注意事項

| 項目 | 說明 |
|------|------|
| **hermes CLI flag** | 需先確認 hermes 支援的非互動模式 flag（執行 `hermes --help` 查看）。可能是 `--no-interactive`、`--headless`、`--batch` 或其他名稱 |
| **API Key** | 確保 `.hermes/.env` 有正確的 API key |
| **Git 策略** | 每個 plan 跑在獨立 branch → 成功後手動 review → merge to main |
| **速率控制** | sleep 間隔避免 token 爆量；可依 plan 大小調整 |
| **失敗處理** | 失敗的 plan **不自動重試**（避免無限迴圈燒 token） |
| **成本監控** | 建議設定 API 帳號的月度上限 |
| **磁碟空間** | 日誌檔案定期 rotate（加入 logrotate 或 truncate） |
| **併行限制** | 此方案為單 worker 序列執行；如需併行需額外設計 |

---

## 測試步驟

在正式啟用前，先手動測試：

```bash
# 1. 建立目錄結構
mkdir -p .hermes/plans/{queue,done,failed}

# 2. 放入一個簡單的測試 plan
cat > .hermes/plans/queue/000-test.md << 'EOF'
# Test Plan

> **Goal:** Verify hermes auto-execution works

### Task 1: Create test file

**Files:**
- Create: `test-hermes-runner.txt`

**Step 1:** Create a file with content "Hello from Hermes"

```bash
echo "Hello from Hermes" > test-hermes-runner.txt
```

**Step 2:** Verify

```bash
cat test-hermes-runner.txt
```

Expected: "Hello from Hermes"

**Step 3:** Commit

```bash
git add test-hermes-runner.txt
git commit -m "test: verify hermes auto-runner"
```
EOF

# 3. 手動執行一次 runner（Ctrl+C 中斷）
bash scripts/task-runner.sh

# 4. 確認結果
ls .hermes/plans/done/    # 應該看到 000-test.md
cat test-hermes-runner.txt  # 應該看到 "Hello from Hermes"

# 5. 清理測試
rm test-hermes-runner.txt
git checkout -- .
```

---

## 後續

- [ ] 確認 hermes CLI 非互動模式的正確 flag
- [ ] 建立 Phase 1 的 plan 文件放入 queue/
- [ ] 手動測試單個 plan 執行成功
- [ ] 啟用 systemd service 進行持續執行
- [ ] 設定 Telegram 通知（成功/失敗）
