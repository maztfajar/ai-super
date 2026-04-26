#!/bin/bash
# AI ORCHESTRATOR — Update & Rebuild Script
# Jalankan ini setelah extract zip baru
# Usage: bash scripts/update.sh

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

echo -e "${CYAN}${BOLD}🔄 AI ORCHESTRATOR — Update & Rebuild${NC}\n"

# ── 1. Migrate DB ─────────────────────────────────────────────
echo -e "${CYAN}[1/3]${NC} Migrasi database..."
bash "$DIR/scripts/migrate-db.sh"

# ── 2. Rebuild Frontend ───────────────────────────────────────
echo -e "\n${CYAN}[2/3]${NC} Rebuild frontend..."
if ! command -v node &>/dev/null; then
    echo -e "${RED}Node.js tidak ditemukan!${NC}"
    echo "Install: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
    exit 1
fi

cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install --silent
fi

npm run build
if [ $? -ne 0 ]; then
    echo -e "${RED}[✗] Build gagal! Lihat error di atas.${NC}"
    exit 1
fi
echo -e "${GREEN}[✓]${NC} Frontend berhasil di-build"

# ── 3. Restart server ─────────────────────────────────────────
echo -e "\n${CYAN}[3/3]${NC} Restart server..."

# Stop server lama jika ada
if [ -f /tmp/ai-orchestrator-api.pid ]; then
    PID=$(cat /tmp/ai-orchestrator-api.pid)
    kill $PID 2>/dev/null && echo "Server lama dihentikan (PID $PID)"
    rm -f /tmp/ai-orchestrator-api.pid
fi
# Coba pkill sebagai fallback
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 1

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  ✅ Update selesai!                  ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "Sekarang jalankan: ${CYAN}bash scripts/dev.sh${NC}"
echo ""
