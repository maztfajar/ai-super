#!/bin/bash
# ============================================================
#  AI SUPER ASSISTANT — Install Script
#  Usage: bash install.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
cat << 'EOF'
   █████╗ ██╗  ███████╗██╗   ██╗██████╗ ███████╗██████╗ 
  ██╔══██╗██║  ██╔════╝██║   ██║██╔══██╗██╔════╝██╔══██╗
  ███████║██║  ███████╗██║   ██║██████╔╝█████╗  ██████╔╝
  ██╔══██║██║  ╚════██║██║   ██║██╔═══╝ ██╔══╝  ██╔══██╗
  ██║  ██║██║  ███████║╚██████╔╝██║     ███████╗██║  ██║
  ╚═╝  ╚═╝╚═╝  ╚══════╝ ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═╝
                A S S I S T A N T
EOF
echo -e "${NC}"

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}\n"; }

# ── Detect OS ────────────────────────────────────────────────
step "Detecting System"
if command -v apt-get &>/dev/null; then
    PKG="apt"; log "Ubuntu/Debian detected"
elif command -v pacman &>/dev/null; then
    PKG="pacman"; log "Arch Linux detected"
elif command -v dnf &>/dev/null; then
    PKG="dnf"; log "Fedora/RHEL detected"
else
    err "Unsupported OS."
fi

# ── System dependencies (TANPA nodejs/npm dari apt) ──────────
step "Installing System Dependencies"
if [ "$PKG" = "apt" ]; then
    sudo apt-get update -qq
    sudo apt-get install -y curl wget git \
        python3 python3-pip python3-venv \
        redis-server postgresql postgresql-contrib \
        build-essential libpq-dev libssl-dev libffi-dev \
        python3-dev gcc g++ make 2>/dev/null \
        || warn "Some packages may already be installed"
elif [ "$PKG" = "pacman" ]; then
    sudo pacman -Syu --noconfirm python python-pip nodejs npm redis postgresql \
        base-devel openssl libffi 2>/dev/null || true
elif [ "$PKG" = "dnf" ]; then
    sudo dnf install -y python3 python3-pip redis postgresql-server \
        gcc gcc-c++ make openssl-devel libffi-devel python3-devel \
        curl wget git 2>/dev/null || true
fi
log "System dependencies installed"

# ── Node.js via nvm (hindari konflik apt nodejs/npm) ─────────
step "Installing Node.js via nvm"
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    log "Installing nvm..."
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && source "$NVM_DIR/bash_completion"

NODE_VER=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_VER" ] || [ "$NODE_VER" -lt 18 ]; then
    log "Installing Node.js 20 LTS..."
    nvm install 20 && nvm use 20 && nvm alias default 20
else
    log "Node.js $(node --version) sudah tersedia"
fi

# Tambahkan nvm ke shell configs
NVM_INIT='
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"'
for RC in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    [ -f "$RC" ] && ! grep -q "NVM_DIR" "$RC" && echo "$NVM_INIT" >> "$RC"
done
log "Node.js $(node --version) ready"
log "npm $(npm --version) ready"

# ── Redis ─────────────────────────────────────────────────────
step "Setting Up Redis"
sudo systemctl enable redis-server 2>/dev/null || sudo systemctl enable redis 2>/dev/null || true
sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null || true
log "Redis started"

# ── PostgreSQL ────────────────────────────────────────────────
step "Setting Up PostgreSQL"
sudo systemctl enable postgresql 2>/dev/null || true
sudo systemctl start postgresql 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER ai-super-assistant WITH PASSWORD 'ai-super-assistant2024';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE ai_super_assistant_db OWNER ai-super-assistant;" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ai_super_assistant_db TO ai-super-assistant;" 2>/dev/null || true
log "PostgreSQL ready (db: ai_super_assistant_db, user: ai-super-assistant)"

# ── Python Backend ────────────────────────────────────────────
step "Setting Up Python Backend"
cd "$APP_DIR/backend"

VENV_DIR="$APP_DIR/backend/venv"

# Selalu hapus dan buat ulang venv agar tidak pakai path lama/rusak
if [ -d "$VENV_DIR" ]; then
    warn "Hapus venv lama..."
    rm -rf "$VENV_DIR"
fi

log "Membuat venv baru di: $VENV_DIR"
python3 -m venv "$VENV_DIR"

if [ ! -f "$VENV_DIR/bin/pip" ]; then
    err "Gagal membuat venv! Coba: sudo apt install python3-venv python3-full"
fi

source "$VENV_DIR/bin/activate"
log "venv aktif: $(which python3)"
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -q

log "Installing Python packages (estimasi 3-5 menit)..."
PACKAGES=(
    "fastapi==0.111.0"
    "uvicorn[standard]==0.29.0"
    "python-multipart==0.0.9"
    "websockets==12.0"
    "sqlmodel==0.0.19"
    "aiosqlite==0.20.0"
    "python-jose[cryptography]==3.3.0"
    "bcrypt>=4.0.0"
    "python-dotenv==1.0.1"
    "pydantic-settings>=2.3.0"
    "structlog>=24.2.0"
    "aiofiles>=23.2.1"
    "tenacity>=8.4.1"
    "httpx>=0.27.0"
    "aiohttp>=3.9.0"
    "requests>=2.32.0"
    "pypdf>=4.2.0"
    "python-docx>=1.1.2"
    "beautifulsoup4>=4.12.0"
    "openai>=1.35.0"
    "anthropic>=0.28.0"
    "ollama>=0.2.1"
    "litellm>=1.40.0"
    "celery>=5.4.0"
    "redis>=5.0.0"
    "fpdf2>=2.7.0"
    "openpyxl>=3.1.0"
    "markdown>=3.6.0"
    "edge-tts>=6.1.12"
    "gTTS>=2.5.1"
    "psutil>=5.9.0"
    "python-pptx>=0.6.23"
)

TOTAL=${#PACKAGES[@]}
COUNT=0
FAILED=()
for pkg in "${PACKAGES[@]}"; do
    COUNT=$((COUNT + 1))
    printf "  [%2d/%d] %-45s" "$COUNT" "$TOTAL" "$pkg"
    if "$VENV_DIR/bin/pip" install --prefer-binary --quiet "$pkg" 2>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
    else
        echo -e " ${RED}✗${NC}"
        FAILED+=("$pkg")
    fi
done

[ ${#FAILED[@]} -gt 0 ] && warn "Gagal: ${FAILED[*]}" || log "Semua package terinstall!"

# ── Env file ─────────────────────────────────────────────────
step "Creating Environment Config"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    log ".env dibuat — edit untuk tambah API key"
else
    log ".env sudah ada"
fi

# ── Init Database & Admin ─────────────────────────────────────
step "Initializing Database & Admin User"
cd "$APP_DIR/backend"
source "$APP_DIR/backend/venv/bin/activate"
export DATABASE_URL="sqlite+aiosqlite:///./data/ai-super-assistant.db"
mkdir -p data/logs data/uploads data/chroma_db

python3 - << 'PYEOF'
import asyncio, sys, os
sys.path.insert(0, '.')
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./data/ai-super-assistant.db'

async def main():
    from db.database import init_db, AsyncSessionLocal
    from core.auth import ensure_admin_exists
    from core.config import settings
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_admin_exists(db)
    print(f"  Admin siap: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")

asyncio.run(main())
PYEOF
log "Database & admin user siap"

# ── Frontend ──────────────────────────────────────────────────
step "Building Frontend"
cd "$APP_DIR/frontend"
log "Installing npm packages..."
npm install 2>&1 | tail -3
log "Building React app..."
npm run build 2>&1 | tail -3
log "Frontend built"

# ── Systemd services ─────────────────────────────────────────
step "Installing System Services"
cat > /tmp/ai-super-assistant-api.service << EOF
[Unit]
Description=AI SUPER ASSISTANT API Server
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/.env
Environment=DATABASE_URL=sqlite+aiosqlite:///./data/ai-super-assistant.db
ExecStart=$APP_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 7860 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/ai-super-assistant-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-super-assistant-api 2>/dev/null || true
log "Systemd service installed"

# ── Done ──────────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}"
cat << 'EOF'
  ╔═════════════════════════════════════════════════╗
  ║    AI SUPER ASSISTANT Installation Complete! 🎉 ║
  ╚═════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo -e "  ${CYAN}Langkah berikutnya:${NC}"
echo -e "  1. Edit API key (opsional) : ${YELLOW}nano $APP_DIR/.env${NC}"
echo -e "  2. Jalankan server         : ${YELLOW}bash $APP_DIR/scripts/dev.sh${NC}"
echo -e "  3. Buka browser            : ${YELLOW}http://localhost:7860${NC}"
echo -e "  4. Login                   : ${YELLOW}admin / ai-super-assistant2024${NC}"
echo -e "\n  ${CYAN}RAG/LangChain (opsional):${NC}"
echo -e "  bash $APP_DIR/scripts/install-rag.sh"
echo ""
