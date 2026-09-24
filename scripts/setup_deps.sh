#!/bin/bash
# ProTech NAS — Project Dependencies Setup
set -e

# ─── Guard: must NOT run as root/sudo ────────────────────────────────────────
# Running this under sudo makes the Python venv and the frontend build output
# (frontend/dist, incl. the PWA service worker sw.js) owned by root. A later
# non-root `npm run build` / deploy then fails with EACCES when trying to
# overwrite those files. venv creation and frontend build must run as the
# normal user; only copying artifacts into system paths (handled by deploy.sh)
# needs sudo.
if [ "$(id -u)" -eq 0 ]; then
    echo "✗ Do NOT run setup_deps.sh as root/sudo." >&2
    echo "  It would make .venv and frontend/dist root-owned and break later builds." >&2
    echo "  Run it as your normal user:  ./scripts/setup_deps.sh" >&2
    exit 1
fi

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== ProTech NAS — Setting Up Project Dependencies ==="

# Backend
echo "[1/3] Setting up Python backend..."
cd "$PROJECT_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
echo "  Backend OK."

# Frontend
echo "[2/3] Setting up Vue.js frontend..."
cd "$PROJECT_DIR/frontend"
npm install
echo "  Frontend OK."

# Build frontend
echo "[3/3] Building frontend for production..."
npm run build
echo "  Frontend built to dist/."

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start development:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn src.main:app --reload --port 8000"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "For production:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port 8000"
echo "  Frontend: Serve frontend/dist/ with nginx or similar"
