#!/bin/bash
# ============================================================
#  AI ORCHESTRATOR — Installer Otomatis
#  Mendukung: Ubuntu 20.04/22.04/24.04, Debian, Linux Mint
# ============================================================
set -e

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'
info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo -e "${CYAN}${BOLD}"
echo "  ╔══════════════════════════════╗"
echo "  ║   AI ORCHESTRATOR — Installer      ║"
echo "  ║   AI Orchestrator         ║"
echo "  ╚══════════════════════════════╝"
echo -e "${NC}"

# ── System Requirements ─────────────────────────────────────
info "Mengecek system requirements..."

OS=$(cat /etc/os-release | grep ^ID= | cut -d= -f2 | tr -d '"')
ARCH=$(uname -m)
RAM_MB=$(free -m | awk '/^Mem:/{print $2}')

echo "  OS: $OS | Arch: $ARCH | RAM: ${RAM_MB}MB"

if [ $RAM_MB -lt 1024 ]; then
    warn "RAM < 1GB. Disarankan minimal 2GB untuk performa optimal."
fi

# ── Dependencies ─────────────────────────────────────────────
info "Menginstall system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3 python3-pip python3-venv \
    nodejs npm \
    redis-server sqlite3 \
    curl wget git build-essential \
    libssl-dev libffi-dev python3-dev 2>/dev/null || warn "Beberapa paket mungkin tidak terinstall"

# ── Node.js version check ────────────────────────────────────
NODE_VER=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_VER" ] || [ "$NODE_VER" -lt 18 ]; then
    info "Menginstall Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
    sudo apt-get install -y nodejs 2>/dev/null
fi
success "Node.js $(node --version) OK"

# ── Python venv ──────────────────────────────────────────────
info "Membuat Python virtual environment..."
cd "$DIR/backend"
python3 -m venv venv
source venv/bin/activate

info "Menginstall Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ── Database migration ───────────────────────────────────────
mkdir -p data/logs data/uploads data/chroma_db
info "Menjalankan database migration..."
bash "$DIR/scripts/migrate-db.sh" 2>/dev/null || true

# ── Frontend ─────────────────────────────────────────────────
info "Menginstall Node.js dependencies..."
cd "$DIR/frontend"
npm install -q

info "Build frontend..."
npm run build

# ── Env file ─────────────────────────────────────────────────
if [ ! -f "$DIR/.env" ]; then
    info "Membuat file .env dari template..."
    cp "$DIR/.env.example" "$DIR/.env"
    # Generate random SECRET_KEY
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/ai-orchestrator-secret-key-ganti-ini-dengan-random-string-panjang/$SECRET/" "$DIR/.env"
    success ".env dibuat dengan SECRET_KEY random"
fi

# ── Redis ────────────────────────────────────────────────────
sudo systemctl enable redis-server 2>/dev/null || true
sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null || warn "Redis tidak bisa distart otomatis"

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   ✅ INSTALASI SELESAI!              ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  Jalankan aplikasi:"
echo -e "  ${CYAN}bash scripts/start.sh${NC}"
echo ""
echo -e "  Buka browser: ${CYAN}http://localhost:7860${NC}"
echo -e "  Login default: ${YELLOW}admin / admin${NC}"
echo -e "  ${RED}⚠ Segera ganti password default!${NC}"
echo ""
