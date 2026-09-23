#!/bin/bash
# ProTech NAS — Backend service-only deployment
# 只安裝並啟用 backend 的 systemd service（開機自動啟動），不含前端/Nginx。
# 路徑自適應：從專案內任意位置的 scripts/ 執行，會以該專案路徑部署，
# 因此同一份腳本在 ~/projects/protech-nas 或 ~/Documents/protech-nas 皆適用。
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
SERVICE_USER="${NAS_USER:-$(whoami)}"
SERVICE_TEMPLATE="$SCRIPT_DIR/protech-nas.service"

echo "╔══════════════════════════════════════════════╗"
echo "║   ProTech NAS — Backend Service Deployment   ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Project:  $PROJECT_DIR"
echo "║  User:     $SERVICE_USER"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Pre-flight checks ───────────────────────────────────────────────────────
echo "[0/3] Pre-flight checks..."

if [ ! -f "$SERVICE_TEMPLATE" ]; then
    echo "  ✗ Service template not found: $SERVICE_TEMPLATE"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
    echo "  ✗ Backend venv not found at $BACKEND_DIR/.venv"
    echo "    Run scripts/setup_deps.sh first (creates venv + installs deps)."
    exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "  ⚠ Backend .env not found. Creating from .env.example..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "  ⚠ Please edit $BACKEND_DIR/.env and set SECRET_KEY!"
fi

echo "  ✓ Checks passed."
echo ""

# ─── Step 1: Generate systemd unit with correct user/paths ───────────────────
echo "[1/3] Installing systemd service..."
sed -e "s|User=alex_chiang|User=$SERVICE_USER|g" \
    -e "s|Group=alex_chiang|Group=$SERVICE_USER|g" \
    -e "s|/home/alex_chiang/projects/protech-nas|$PROJECT_DIR|g" \
    "$SERVICE_TEMPLATE" | sudo tee /etc/systemd/system/protech-nas.service > /dev/null
echo "  ✓ Unit written to /etc/systemd/system/protech-nas.service"
echo ""

# ─── Step 2: Enable on boot + start now ──────────────────────────────────────
echo "[2/3] Enabling on boot and starting..."
sudo systemctl daemon-reload
sudo systemctl enable protech-nas
sudo systemctl restart protech-nas
echo "  ✓ Service enabled (starts on boot) and started."
echo ""

# ─── Step 3: Verify ──────────────────────────────────────────────────────────
echo "[3/3] Verifying..."
sleep 1
ENABLED="$(systemctl is-enabled protech-nas 2>/dev/null || true)"
ACTIVE="$(systemctl is-active protech-nas 2>/dev/null || true)"
echo "  is-enabled: $ENABLED"
echo "  is-active:  $ACTIVE"
echo ""

if [ "$ENABLED" = "enabled" ] && [ "$ACTIVE" = "active" ]; then
    echo "╔══════════════════════════════════════════════╗"
    echo "║          ✓ Service deployed & enabled        ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    echo "  API:   http://$(hostname -I | awk '{print $1}'):8000"
    echo "  Docs:  http://$(hostname -I | awk '{print $1}'):8000/docs"
    echo ""
    echo "  Useful commands:"
    echo "    systemctl status protech-nas"
    echo "    journalctl -u protech-nas -f"
    echo "    sudo systemctl restart protech-nas"
    echo "    sudo systemctl disable protech-nas   # 取消開機自啟"
else
    echo "  ⚠ Service did not reach enabled+active state."
    echo "    Inspect logs:  journalctl -u protech-nas -n 50 --no-pager"
    exit 1
fi
