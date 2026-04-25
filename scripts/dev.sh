#!/bin/bash
# AI SUPER ASSISTANT — Dev/Quick Start
# Usage: bash scripts/dev.sh

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

echo -e "${CYAN}${BOLD}  🧠 AI SUPER ASSISTANT — Starting...${NC}\n"

# ── Load nvm ─────────────────────────────────────────────────
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

# ── Cek venv ─────────────────────────────────────────────────
step "Cek Python Environment"
VENV="$DIR/backend/venv"
if [ ! -f "$VENV/bin/activate" ]; then
    err "venv tidak ditemukan! Jalankan dulu: bash install.sh"
fi
source "$VENV/bin/activate"
log "venv aktif: $(python3 --version)"

# ── Build frontend ───────────────────────────────────────────
step "Build Frontend"
if ! command -v node &>/dev/null; then
    warn "Node.js tidak ditemukan. Install: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs"
else
    cd "$DIR/frontend"
    # Install node_modules jika belum ada
    if [ ! -d "node_modules" ]; then
        log "Menginstall npm packages..."
        npm install --silent 2>&1 | tail -2
    fi
    # Cek apakah dist sudah ada
    if [ ! -d "dist" ] || [[ "$*" == *"--build"* ]]; then
        log "Build frontend (mohon tunggu ~30 detik)..."
        npm run build 2>&1 | tail -5
        if [ $? -eq 0 ]; then
            log "Frontend berhasil di-build"
        else
            warn "Build frontend gagal! Cek error di atas."
            warn "Coba manual: cd frontend && npm run build"
        fi
    else
        warn "Frontend 'dist' sudah ada. Melewati build otomatis."
        warn "Gunakan 'bash scripts/dev.sh --build' jika ada perubahan kode UI."
    fi
fi

# ── Load env ─────────────────────────────────────────────────
step "Load Konfigurasi"
cd "$DIR/backend"
[ -f "$DIR/.env" ] && { set -a; source "$DIR/.env"; set +a; log ".env loaded"; }
# Biarkan mengikuti konfigurasi dari .env

# ── Buat direktori data ───────────────────────────────────────
mkdir -p data/logs data/uploads data/chroma_db

# ── Init DB & admin ───────────────────────────────────────────
step "Inisialisasi Database"
python3 - << 'PYEOF'
import asyncio, sys, os
sys.path.insert(0, '.')
# config.py akan otomatis memuat .env

async def main():
    try:
        from db.database import init_db, AsyncSessionLocal
        from core.auth import ensure_admin_exists
        from core.config import settings
        await init_db()
        async with AsyncSessionLocal() as db:
            await ensure_admin_exists(db)
        print(f"  \033[32m✓\033[0m Database OK — admin: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
    except Exception as e:
        print(f"  \033[33m!\033[0m {e}")

asyncio.run(main())
PYEOF

# ── Start server ──────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════╗"
echo -e "║  AI SUPER ASSISTANT berjalan!                         ║"
echo -e "║  → http://localhost:7860                     ║"
echo -e "║  Login: admin / admin                                   ║"
echo -e "╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  API Docs : http://localhost:7860/docs"
echo -e "  Stop     : Ctrl+C"
echo ""

uvicorn main:app \
    --host 0.0.0.0 \
    --port 7860 \
    --reload \
    --reload-include .env \
    --reload-include .custom_models.json \
    --log-level info
