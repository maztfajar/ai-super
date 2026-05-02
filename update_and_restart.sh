#!/bin/bash

# ============================================================
# AI ORCHESTRATOR — Update & Restart Script
# Usage: bash update_and_restart.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}\n"; }

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$APP_DIR/backend"
VENV_PYTHON="$BACKEND_DIR/venv/bin/python3"
VENV_PIP="$BACKEND_DIR/venv/bin/pip"
VENV_UVICORN="$BACKEND_DIR/venv/bin/uvicorn"
PID_FILE="$APP_DIR/data/uvicorn.pid"
LOG_FILE="$APP_DIR/data/logs/ai_orchestrator.log"

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
╔══════════════════════════════════════════════╗
║    AI ORCHESTRATOR — Update & Restart     ║
╚══════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ── Validasi ─────────────────────────────────────────────────
step "1. Validasi Environment"

[ -d "$BACKEND_DIR" ]         || err "Folder backend tidak ditemukan."
[ -f "$VENV_PYTHON" ]         || err "Virtual environment tidak ditemukan. Jalankan install.sh terlebih dahulu."
[ -f "$APP_DIR/.env" ]        || err "File .env tidak ditemukan."
[ -f "$BACKEND_DIR/main.py" ] || err "File backend/main.py tidak ditemukan."

mkdir -p "$APP_DIR/data/logs"
log "Semua validasi lolos"

# ── Cek SECRET_KEY ────────────────────────────────────────────
step "2. Cek Keamanan .env"

CURRENT_SECRET=$(grep -E '^SECRET_KEY=' "$APP_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '"' || echo "")

if [[ -z "$CURRENT_SECRET" || "$CURRENT_SECRET" == *"ganti"* || "$CURRENT_SECRET" == *"random"* || "$CURRENT_SECRET" == *"pitakonku-secret"* || "$CURRENT_SECRET" == *"al-fatih"* ]]; then
    warn "SECRET_KEY masih default/kosong. Membuat yang baru..."
    NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    if grep -q '^SECRET_KEY=' "$APP_DIR/.env"; then
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=\"$NEW_SECRET\"|" "$APP_DIR/.env"
    else
        echo "SECRET_KEY=\"$NEW_SECRET\"" >> "$APP_DIR/.env"
    fi
    log "SECRET_KEY baru berhasil di-generate dan disimpan ke .env"
else
    log "SECRET_KEY sudah aman"
fi

# ── Stop proses lama ──────────────────────────────────────────
step "3. Menghentikan Proses Lama"

# Cek apakah berjalan sebagai systemd service
if systemctl list-unit-files | grep -q "ai-orchestrator-api.service"; then
    if systemctl is-active --quiet ai-orchestrator-api; then
        sudo systemctl stop ai-orchestrator-api
        log "Systemd service ai-orchestrator-api dihentikan"
    fi
fi

# Stop uvicorn (server utama) — HANYA proses app ini, bukan semua Python
if pgrep -f "uvicorn" > /dev/null 2>&1; then
    pkill -f "uvicorn"
    log "Uvicorn berhasil dihentikan"
else
    log "Tidak ada proses uvicorn mandiri yang berjalan"
fi

# Stop celery worker (jika ada — untuk workflow automation)
if pgrep -f "celery worker" > /dev/null 2>&1; then
    pkill -f "celery worker"
    log "Celery worker berhasil dihentikan"
else
    log "Tidak ada proses celery yang berjalan"
fi

# Tunggu port benar-benar bebas
sleep 2

# Paksa bebaskan port jika masih terpakai
PORT_NUM="${PORT:-7860}"
if command -v fuser > /dev/null 2>&1; then
    if fuser "$PORT_NUM/tcp" > /dev/null 2>&1; then
        warn "Port $PORT_NUM masih terpakai, paksa kill (fuser)..."
        fuser -k -9 "$PORT_NUM/tcp" > /dev/null 2>&1 || true
        sleep 2
    fi
fi
if lsof -ti ":$PORT_NUM" > /dev/null 2>&1; then
    warn "Port $PORT_NUM masih terpakai, paksa kill (lsof)..."
    lsof -ti ":$PORT_NUM" | xargs kill -9 2>/dev/null || true
    sleep 2
fi
log "Port $PORT_NUM bebas"

# ── Pull update dari Git ──────────────────────────────────────
step "4. Mengambil Update dari Git"

cd "$APP_DIR"

log "Update dari Git dinonaktifkan sementara untuk melindungi perubahan lokal Anda."
# Simpan perubahan lokal jika ada agar tidak hilang
# if ! git diff --quiet 2>/dev/null; then
#     warn "Ada perubahan lokal, menyimpan ke git stash..."
#     git stash push -m "auto-stash sebelum update $(date '+%Y-%m-%d %H:%M:%S')"
# fi
#
# git fetch origin main || err "Gagal fetch dari remote. Cek koneksi internet."
# git reset --hard origin/main
# log "Kode berhasil diperbarui ke versi terbaru"

# ── Update Python dependencies ────────────────────────────────
step "5. Update Python Dependencies"

cd "$BACKEND_DIR"

if [ -f "requirements.txt" ]; then
    "$VENV_PIP" install -r requirements.txt --quiet \
        && log "Dependencies Python berhasil diperbarui" \
        || warn "Beberapa package gagal diupdate, server tetap akan dijalankan"
else
    warn "requirements.txt tidak ditemukan, melewati update dependencies"
fi

# ── Migrasi database (jika ada) ───────────────────────────────
step "6. Migrasi Database"

cd "$BACKEND_DIR"

if [ -f "migrate.py" ]; then
    "$VENV_PYTHON" migrate.py \
        && log "Migrasi database selesai" \
        || warn "Migrasi gagal, periksa log"
elif [ -f "$APP_DIR/scripts/migrate-db.sh" ]; then
    bash "$APP_DIR/scripts/migrate-db.sh" \
        && log "Migrasi database selesai" \
        || warn "Migrasi gagal, periksa log"
else
    log "Tidak ada script migrasi, melewati langkah ini"
fi

# ── Build Frontend ────────────────────────────────────────────
step "6.5. Build Frontend"

cd "$APP_DIR/frontend"
if ! command -v npm &>/dev/null; then
    warn "npm tidak ditemukan, melewati build frontend."
else
    log "Menginstall npm packages..."
    npm install --silent 2>&1 | tail -2
    log "Membangun ulang frontend UI..."
    npm run build 2>&1 | tail -5
    if [ $? -eq 0 ]; then
        log "Frontend berhasil di-build"
    else
        warn "Build frontend gagal! Cek error npm di atas."
    fi
fi

# ── Jalankan ulang Uvicorn ────────────────────────────────────
step "7. Menjalankan Server"

cd "$BACKEND_DIR"

# Load variabel dari .env
set -a
source "$APP_DIR/.env"
set +a

if systemctl list-unit-files | grep -q "ai-orchestrator-api.service"; then
    log "Ditemukan systemd service. Menjalankan via systemctl..."
    sudo systemctl daemon-reload
    sudo systemctl start ai-orchestrator-api
    
    if systemctl is-active --quiet ai-orchestrator-api; then
        log "Server berhasil dijalankan via systemd (ai-orchestrator-api.service)"
    else
        err "Server gagal dijalankan via systemd. Cek log: sudo journalctl -u ai-orchestrator-api -f"
    fi
else
    log "Systemd service tidak ditemukan. Menjalankan via nohup..."
    nohup "$VENV_UVICORN" main:app \
        --host 0.0.0.0 \
        --port "${PORT:-7860}" \
        --workers "${UVICORN_WORKERS:-2}" \
        >> "$LOG_FILE" 2>&1 &

    UVICORN_PID=$!
    sleep 3

    # Verifikasi server benar-benar jalan
    if kill -0 "$UVICORN_PID" 2>/dev/null; then
        echo "$UVICORN_PID" > "$PID_FILE"
        log "Server berhasil dijalankan (PID: $UVICORN_PID)"
    else
        err "Server gagal dijalankan.\n\n=== LOG ERROR TERAKHIR ===\n$(tail -n 20 $LOG_FILE)\n==========================\n\nCek log lengkap: tail -f $LOG_FILE"
    fi
fi

# ── Jalankan ulang Celery (jika Redis tersedia) ───────────────
step "8. Menjalankan Celery Worker"

if command -v redis-cli > /dev/null 2>&1 && redis-cli ping > /dev/null 2>&1; then
    cd "$BACKEND_DIR"
    nohup "$VENV_PYTHON" -m celery -A core.celery_app worker \
        --loglevel=info \
        >> "$APP_DIR/data/logs/celery.log" 2>&1 &
    CELERY_PID=$!
    sleep 1
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        log "Celery worker berhasil dijalankan (PID: $CELERY_PID)"
        echo "$CELERY_PID" > "$APP_DIR/data/celery.pid"
    else
        warn "Celery worker gagal dijalankan (tidak wajib, server tetap jalan)"
    fi
else
    warn "Redis tidak tersedia, Celery worker tidak dijalankan (fitur workflow tidak aktif)"
fi

# ── Selesai ───────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}"
cat << 'EOF'
╔══════════════════════════════════════════════╗
║   Update & Restart Selesai! 🚀               ║
╚══════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo -e " ${CYAN}Akses aplikasi :${NC}  ${YELLOW}http://localhost:${PORT:-7860}${NC}"
echo -e " ${CYAN}Log server     :${NC}  ${YELLOW}tail -f $LOG_FILE${NC}"
echo -e " ${CYAN}Log celery     :${NC}  ${YELLOW}tail -f $APP_DIR/data/logs/celery.log${NC}"
echo -e " ${CYAN}Hentikan server:${NC}  ${YELLOW}pkill -f 'uvicorn main:app'${NC}"
echo ""
