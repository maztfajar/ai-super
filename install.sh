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

# ── Interactive Wizard ───────────────────────────────────────
step "Interactive Configuration Wizard"

echo -e "${CYAN}Tekan ENTER untuk menggunakan nilai [Default].${NC}\n"

read -p "1. Nama Aplikasi [Default: AL FATIH]: " WZ_APP_NAME
WZ_APP_NAME=${WZ_APP_NAME:-"AL FATIH"}

echo -e "\n2. Konfigurasi Database (dijalankan otomatis oleh sistem)"
echo "   [1] SQLite (Ringan, Tanpa Konfigurasi Ekstra)"
echo "   [2] PostgreSQL (Disarankan untuk Server/Production)"
read -p "   Pilih tipe database [1/2, Default: 1]: " WZ_DB_TYPE
WZ_DB_TYPE=${WZ_DB_TYPE:-1}

if [ "$WZ_DB_TYPE" = "2" ]; then
    read -p "   Nama User DB [Default: pitakonku]: " WZ_DB_USER
    WZ_DB_USER=${WZ_DB_USER:-pitakonku}
    
    read -p "   Nama Database [Default: pitakonku_db]: " WZ_DB_NAME
    WZ_DB_NAME=${WZ_DB_NAME:-pitakonku_db}
    
    read -p "   Password DB [Default: admin]: " WZ_DB_PASS
    WZ_DB_PASS=${WZ_DB_PASS:-admin}
else
    WZ_DB_USER="-"
    WZ_DB_NAME="-"
    WZ_DB_PASS="-"
fi

echo -e "\n3. Kredensial Login Aplikasi AI"
read -p "   Username Login [Default: admin]: " WZ_ADMIN_USER
WZ_ADMIN_USER=${WZ_ADMIN_USER:-admin}
read -p "   Password Login [Default: admin]: " WZ_ADMIN_PASS
WZ_ADMIN_PASS=${WZ_ADMIN_PASS:-admin}

echo -e "\n4. Integrasi & Model AI (Tekan ENTER untuk melewati)"
read -p "   OpenAI API Key: " WZ_OPENAI
read -p "   Anthropic API Key: " WZ_ANTHROPIC
read -p "   Telegram Bot Token: " WZ_TELEGRAM
read -p "   WhatsApp Access Token: " WZ_WHATSAPP

# Copy env.example
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    log ".env dibuat dari template .env.example"
else
    log ".env sudah ada. Akan disesuaikan dengan isian wizard..."
fi

# Update .env
if [ -f "$APP_DIR/.env" ]; then
    sed -i -e "s/^APP_NAME=.*/APP_NAME=\"$WZ_APP_NAME\"/" "$APP_DIR/.env"
    sed -i -e "s/^ADMIN_USERNAME=.*/ADMIN_USERNAME=\"$WZ_ADMIN_USER\"/" "$APP_DIR/.env"
    sed -i -e "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=\"$WZ_ADMIN_PASS\"/" "$APP_DIR/.env"

    if [ -n "$WZ_OPENAI" ]; then sed -i -e "s/^OPENAI_API_KEY=.*/OPENAI_API_KEY=\"$WZ_OPENAI\"/" "$APP_DIR/.env"; fi
    if [ -n "$WZ_ANTHROPIC" ]; then sed -i -e "s/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=\"$WZ_ANTHROPIC\"/" "$APP_DIR/.env"; fi
    if [ -n "$WZ_TELEGRAM" ]; then sed -i -e "s/^TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=\"$WZ_TELEGRAM\"/" "$APP_DIR/.env"; fi
    if [ -n "$WZ_WHATSAPP" ]; then sed -i -e "s/^WHATSAPP_ACCESS_TOKEN=.*/WHATSAPP_ACCESS_TOKEN=\"$WZ_WHATSAPP\"/" "$APP_DIR/.env"; fi

    if [ "$WZ_DB_TYPE" = "2" ]; then
        # PostgreSQL
        DB_URL="postgresql+asyncpg:\/\/$WZ_DB_USER:$WZ_DB_PASS@localhost\/$WZ_DB_NAME"
        sed -i -e "s/^DATABASE_URL=.*/DATABASE_URL=$DB_URL/" "$APP_DIR/.env"
    else
        # SQLite
        DB_URL="sqlite+aiosqlite:\/\/\/.\/data\/ai-super-assistant.db"
        sed -i -e "s/^DATABASE_URL=.*/DATABASE_URL=$DB_URL/" "$APP_DIR/.env"
    fi
fi

# ── System dependencies (TANPA nodejs/npm dari apt) ──────────
step "Installing System Dependencies"
if [ "$PKG" = "apt" ]; then
    sudo apt-get update -qq
    sudo apt-get install -y curl wget git \
        python3 python3-pip python3-venv python3-full \
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
if [ "$WZ_DB_TYPE" = "2" ]; then
    step "Setting Up PostgreSQL"
    sudo systemctl enable postgresql 2>/dev/null || true
    sudo systemctl start postgresql 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER $WZ_DB_USER WITH PASSWORD '$WZ_DB_PASS';" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE DATABASE $WZ_DB_NAME OWNER $WZ_DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $WZ_DB_NAME TO $WZ_DB_USER;" 2>/dev/null || true
    log "PostgreSQL ready (db: $WZ_DB_NAME, user: $WZ_DB_USER)"
else
    step "Setting Up PostgreSQL"
    log "Menggunakan SQLite, melewati instalasi PostgreSQL setup."
fi

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
    "asyncpg>=0.29.0"
    "psycopg2-binary>=2.9.9"
    "pandas>=2.0.0"
    "tabulate>=0.9.0"
    "pdfplumber>=0.11.0"
    "docx2txt>=0.8"
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

# ── Init Database & Admin ─────────────────────────────────────
step "Initializing Database & Admin User"
cd "$APP_DIR/backend"
source "$APP_DIR/backend/venv/bin/activate"
mkdir -p data/logs data/uploads data/chroma_db

if [ -f "$APP_DIR/.env" ]; then
    set -a
    source "$APP_DIR/.env"
    set +a
fi

python3 - << 'PYEOF'
import asyncio, sys, os
sys.path.insert(0, '.')

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
npm install --silent
log "Building React app..."
npm run build
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
Environment=PATH=$APP_DIR/backend/venv/bin:/usr/bin
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
echo -e "  4. Login                   : ${YELLOW}$WZ_ADMIN_USER / $WZ_ADMIN_PASS${NC}"
echo -e "\n  ${CYAN}RAG/LangChain (opsional):${NC}"
echo -e "  bash $APP_DIR/scripts/install-rag.sh"
echo ""
