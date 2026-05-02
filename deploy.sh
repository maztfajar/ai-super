#!/bin/bash

# ============================================================
# AI SUPER ASSISTANT — Deploy Script
# Usage: bash deploy.sh
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

# ── Validasi ─────────────────────────────────────────────────
step "Validasi Environment"

[ -d "$BACKEND_DIR" ]       || err "Folder backend tidak ditemukan di: $BACKEND_DIR"
[ -f "$VENV_PYTHON" ]       || err "Virtual environment tidak ditemukan. Jalankan install.sh terlebih dahulu."
[ -f "$APP_DIR/.env" ]      || err "File .env tidak ditemukan. Salin dari .env.example lalu isi konfigurasi."
[ -f "$BACKEND_DIR/main.py" ] || err "File backend/main.py tidak ditemukan."

log "Semua validasi lolos"

# ── Cek & Generate SECRET_KEY jika masih default ─────────────
step "Cek Keamanan .env"

CURRENT_SECRET=$(grep -E '^SECRET_KEY=' "$APP_DIR/.env" | cut -d= -f2- | tr -d '"')

if [[ -z "$CURRENT_SECRET" || "$CURRENT_SECRET" == *"ganti"* || "$CURRENT_SECRET" == *"random"* || "$CURRENT_SECRET" == *"pitakonku-secret"* ]]; then
    warn "SECRET_KEY masih default/kosong. Membuat SECRET_KEY baru secara otomatis..."
    NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    # Ganti atau tambahkan SECRET_KEY di .env
    if grep -q '^SECRET_KEY=' "$APP_DIR/.env"; then
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=\"$NEW_SECRET\"|" "$APP_DIR/.env"
    else
        echo "SECRET_KEY=\"$NEW_SECRET\"" >> "$APP_DIR/.env"
    fi
    log "SECRET_KEY baru telah di-generate dan disimpan ke .env"
else
    log "SECRET_KEY sudah diset dengan benar"
fi

# ── Stop proses lama (AMAN: hanya matikan uvicorn app ini) ────
step "Menghentikan Proses Lama"

# Hanya matikan proses uvicorn yang menjalankan app ini,
# BUKAN semua proses python3 di server
if pgrep -f "uvicorn main:app" > /dev/null 2>&1; then
    pkill -f "uvicorn main:app"
    sleep 2
    log "Proses uvicorn lama berhasil dihentikan"
else
    log "Tidak ada proses uvicorn yang berjalan sebelumnya"
fi

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

# ── Pull update dari Git ──────────────────────────────────────
step "Mengambil Update dari Git"

cd "$APP_DIR"

# Simpan perubahan lokal sebelum reset (jika ada)
if ! git diff --quiet 2>/dev/null; then
    warn "Ada perubahan lokal yang belum di-commit. Menyimpan ke git stash..."
    git stash push -m "auto-stash sebelum deploy $(date '+%Y-%m-%d %H:%M:%S')"
fi

git fetch origin main || err "Gagal fetch dari remote. Cek koneksi internet atau akses repo."
git reset --hard origin/main
log "Kode berhasil diperbarui ke versi terbaru"

# ── Update Python dependencies ────────────────────────────────
step "Update Python Dependencies"

cd "$BACKEND_DIR"

if [ -f "requirements.txt" ]; then
    "$VENV_PIP" install -r requirements.txt --quiet \
        && log "Dependencies Python berhasil diperbarui" \
        || warn "Beberapa package gagal diupdate. Cek log di atas."
else
    warn "requirements.txt tidak ditemukan, lewati update dependencies"
fi

# ── Jalankan migrasi database (jika ada) ─────────────────────
step "Migrasi Database"

cd "$BACKEND_DIR"
source "$APP_DIR/.env" 2>/dev/null || true

if [ -f "migrate.py" ]; then
    "$VENV_PYTHON" migrate.py && log "Migrasi database selesai" || warn "Migrasi gagal, periksa log"
elif [ -f "../scripts/migrate-db.sh" ]; then
    bash "$APP_DIR/scripts/migrate-db.sh" && log "Migrasi database selesai" || warn "Migrasi gagal"
else
    log "Tidak ada script migrasi ditemukan, melewati langkah ini"
fi

# ── Jalankan Uvicorn ──────────────────────────────────────────
step "Menjalankan Server"

cd "$BACKEND_DIR"

# Load .env agar variabel tersedia untuk uvicorn
set -a
source "$APP_DIR/.env"
set +a

nohup "$VENV_UVICORN" main:app \
    --host 0.0.0.0 \
    --port "${PORT:-7860}" \
    --workers "${UVICORN_WORKERS:-2}" \
    >> "$APP_DIR/data/logs/ai_orchestrator.log" 2>&1 &

UVICORN_PID=$!
sleep 3

# Verifikasi server berhasil jalan
if kill -0 "$UVICORN_PID" 2>/dev/null; then
    log "Server berhasil dijalankan (PID: $UVICORN_PID)"
    echo "$UVICORN_PID" > "$APP_DIR/data/uvicorn.pid"
else
    err "Server gagal dijalankan.\n\n=== LOG ERROR TERAKHIR ===\n$(tail -n 20 $APP_DIR/data/logs/ai_orchestrator.log)\n==========================\n\nCek log lengkap: tail -f $APP_DIR/data/logs/ai_orchestrator.log"
fi

# ── Selesai ───────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}"
cat << 'EOF'
╔══════════════════════════════════════════════╗
║   Deploy Selesai! Server sedang berjalan 🚀  ║
╚══════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo -e " ${CYAN}Akses aplikasi:${NC}   ${YELLOW}http://localhost:${PORT:-7860}${NC}"
echo -e " ${CYAN}Lihat log:${NC}        ${YELLOW}tail -f $APP_DIR/data/logs/ai_orchestrator.log${NC}"
echo -e " ${CYAN}Hentikan server:${NC}  ${YELLOW}pkill -f 'uvicorn main:app'${NC}"
echo ""
