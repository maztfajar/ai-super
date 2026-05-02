#!/bin/bash

# ============================================================
# AI ORCHESTRATOR — Install Script
# Usage: bash install.sh
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GOLD='\033[0;33m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m'

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

clear
echo -e "${CYAN}${BOLD}"
echo "   ___  ___        ____  ____   ____"
echo "  / _ \|_ _|      / __ \|  _ \ / ___|"
echo " / /_\ \| |      | |  | | |_) | |"
echo " |  _  || |      | |  | |  _ < | |"
echo " | | | || |_     | |__| | | \ \| |____"
echo " |_| |_|_____|    \____/|_|  \_\\_____|"
echo -e "${NC}"
echo -e "${WHITE}${BOLD}  [ ORCHESTRATOR - ONE STOP SOLUTION ]${NC}"
echo -e "${GOLD}           BY FAJAR WAHYUDI${NC}"
echo -e "${WHITE}  ──────────────────────────────────────${NC}"
echo ""
echo -e "  [*] Loading AI Orchestrator Core..."

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
    err "Unsupported OS. Hanya mendukung Ubuntu/Debian, Arch, atau Fedora/RHEL."
fi

# ── Interactive Wizard ───────────────────────────────────────
step "Interactive Configuration Wizard"

echo -e "${CYAN}Tekan ENTER untuk menggunakan nilai [Default].${NC}\n"

read -p "1. Nama Aplikasi [Default: AI ORCHESTRATOR]: " WZ_APP_NAME
WZ_APP_NAME=${WZ_APP_NAME:-"AI ORCHESTRATOR"}

echo -e "\n2. Konfigurasi Database"
echo "   [1] SQLite    (Ringan, cocok untuk personal/development)"
echo "   [2] PostgreSQL (Disarankan untuk production/server)"
read -p "   Pilih tipe database [1/2, Default: 1]: " WZ_DB_TYPE
WZ_DB_TYPE=${WZ_DB_TYPE:-1}

if [ "$WZ_DB_TYPE" = "2" ]; then
    read -p "   Nama User DB [Default: ai_orchestrator_user]: " WZ_DB_USER
    WZ_DB_USER=${WZ_DB_USER:-ai_orchestrator_user}
    read -p "   Nama Database [Default: ai_orchestrator_db]: " WZ_DB_NAME
    WZ_DB_NAME=${WZ_DB_NAME:-ai_orchestrator_db}

    # Password DB wajib diisi, tidak boleh kosong
    while true; do
        read -s -p "   Password DB (wajib diisi, min 8 karakter): " WZ_DB_PASS
        echo ""
        if [ ${#WZ_DB_PASS} -ge 8 ]; then
            break
        else
            warn "Password DB minimal 8 karakter. Coba lagi."
        fi
    done
else
    WZ_DB_USER="-"
    WZ_DB_NAME="-"
    WZ_DB_PASS="-"
fi

echo -e "\n3. Kredensial Login Aplikasi AI"
read -p "   Username Login [Default: admin]: " WZ_ADMIN_USER
WZ_ADMIN_USER=${WZ_ADMIN_USER:-admin}

# Password admin wajib diisi dan tidak boleh "admin"
while true; do
    read -s -p "   Password Login (wajib diisi, min 8 karakter, bukan 'admin'): " WZ_ADMIN_PASS
    echo ""
    if [ ${#WZ_ADMIN_PASS} -lt 8 ]; then
        warn "Password minimal 8 karakter. Coba lagi."
    elif [ "$WZ_ADMIN_PASS" = "admin" ] || [ "$WZ_ADMIN_PASS" = "password" ] || [ "$WZ_ADMIN_PASS" = "123456" ]; then
        warn "Password terlalu lemah. Gunakan password yang lebih kuat."
    else
        break
    fi
done

echo -e "\n4. Integrasi & Model AI (Tekan ENTER untuk melewati)"
read -p "   OpenAI API Key    : " WZ_OPENAI
read -p "   Anthropic API Key : " WZ_ANTHROPIC
read -p "   Telegram Bot Token: " WZ_TELEGRAM
read -p "   WhatsApp Token    : " WZ_WHATSAPP

# ── Buat .env dari template ───────────────────────────────────
echo ""
step "Menyiapkan File Konfigurasi .env"

if [ ! -f "$APP_DIR/.env.example" ]; then
    err ".env.example tidak ditemukan. Pastikan file ini ada di root project."
fi

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    log ".env dibuat dari template .env.example"
else
    warn ".env sudah ada. Nilai dari wizard akan diterapkan..."
fi

# Auto-generate SECRET_KEY yang aman (32 byte hex = 64 karakter)
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
if grep -q '^SECRET_KEY=' "$APP_DIR/.env"; then
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=\"$NEW_SECRET\"|" "$APP_DIR/.env"
else
    echo "SECRET_KEY=\"$NEW_SECRET\"" >> "$APP_DIR/.env"
fi
log "SECRET_KEY baru di-generate secara otomatis"

# Update nilai dari wizard ke .env
sed -i "s|^APP_NAME=.*|APP_NAME=\"$WZ_APP_NAME\"|" "$APP_DIR/.env"
sed -i "s|^ADMIN_USERNAME=.*|ADMIN_USERNAME=\"$WZ_ADMIN_USER\"|" "$APP_DIR/.env"
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=\"$WZ_ADMIN_PASS\"|" "$APP_DIR/.env"

[ -n "$WZ_OPENAI" ]    && sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=\"$WZ_OPENAI\"|" "$APP_DIR/.env"
[ -n "$WZ_ANTHROPIC" ] && sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=\"$WZ_ANTHROPIC\"|" "$APP_DIR/.env"
[ -n "$WZ_TELEGRAM" ]  && sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=\"$WZ_TELEGRAM\"|" "$APP_DIR/.env"
[ -n "$WZ_WHATSAPP" ]  && sed -i "s|^WHATSAPP_ACCESS_TOKEN=.*|WHATSAPP_ACCESS_TOKEN=\"$WZ_WHATSAPP\"|" "$APP_DIR/.env"

if [ "$WZ_DB_TYPE" = "2" ]; then
    DB_URL="postgresql+asyncpg://$WZ_DB_USER:$WZ_DB_PASS@localhost/$WZ_DB_NAME"
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" "$APP_DIR/.env"
    log "Database: PostgreSQL ($WZ_DB_NAME)"
else
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=sqlite+aiosqlite:///./data/ai-orchestrator.db|" "$APP_DIR/.env"
    log "Database: SQLite"
fi

log ".env berhasil dikonfigurasi"

# ── System dependencies ───────────────────────────────────────
step "Installing System Dependencies"

if [ "$PKG" = "apt" ]; then
    sudo apt-get update -qq

    # Paket dasar — selalu diinstall
    sudo apt-get install -y \
        curl wget git \
        python3 python3-pip python3-venv python3-full \
        redis-server \
        build-essential libssl-dev libffi-dev \
        python3-dev gcc g++ make 2>/dev/null \
        || warn "Beberapa paket mungkin sudah terinstall"

    # PostgreSQL — HANYA jika user memilih PostgreSQL
    if [ "$WZ_DB_TYPE" = "2" ]; then
        sudo apt-get install -y postgresql postgresql-contrib libpq-dev 2>/dev/null \
            || warn "PostgreSQL mungkin sudah terinstall"
        log "PostgreSQL diinstall"
    else
        log "SQLite dipilih — PostgreSQL tidak diinstall"
    fi

elif [ "$PKG" = "pacman" ]; then
    sudo pacman -Syu --noconfirm python python-pip redis \
        base-devel openssl libffi 2>/dev/null || true
    if [ "$WZ_DB_TYPE" = "2" ]; then
        sudo pacman -S --noconfirm postgresql 2>/dev/null || true
    fi

elif [ "$PKG" = "dnf" ]; then
    sudo dnf install -y python3 python3-pip redis \
        gcc gcc-c++ make openssl-devel libffi-devel python3-devel \
        curl wget git 2>/dev/null || true
    if [ "$WZ_DB_TYPE" = "2" ]; then
        sudo dnf install -y postgresql-server postgresql-devel 2>/dev/null || true
    fi
fi

log "System dependencies installed"

# ── Node.js via nvm ───────────────────────────────────────────
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

# ── PostgreSQL (hanya jika dipilih) ──────────────────────────
if [ "$WZ_DB_TYPE" = "2" ]; then
    step "Setting Up PostgreSQL"

    sudo systemctl enable postgresql 2>/dev/null || true
    sudo systemctl start postgresql 2>/dev/null || true

    # Tunggu PostgreSQL benar-benar siap menerima koneksi (maks 30 detik)
    log "Menunggu PostgreSQL siap..."
    PG_READY=0
    for i in $(seq 1 15); do
        if sudo -u postgres psql -c "SELECT 1;" > /dev/null 2>&1; then
            PG_READY=1
            break
        fi
        sleep 2
    done

    if [ "$PG_READY" -eq 0 ]; then
        err "PostgreSQL tidak siap setelah 30 detik. Coba: sudo systemctl status postgresql"
    fi

    sudo -u postgres psql -c "CREATE USER $WZ_DB_USER WITH PASSWORD '$WZ_DB_PASS';" 2>/dev/null \
        && log "User DB '$WZ_DB_USER' dibuat" \
        || warn "User '$WZ_DB_USER' sudah ada, lanjut..."

    sudo -u postgres psql -c "CREATE DATABASE $WZ_DB_NAME OWNER $WZ_DB_USER;" 2>/dev/null \
        && log "Database '$WZ_DB_NAME' dibuat" \
        || warn "Database '$WZ_DB_NAME' sudah ada, lanjut..."

    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $WZ_DB_NAME TO $WZ_DB_USER;" 2>/dev/null || true

    log "PostgreSQL ready (db: $WZ_DB_NAME, user: $WZ_DB_USER)"
fi

# ── Python Backend ────────────────────────────────────────────
step "Setting Up Python Backend"

VENV_DIR="$APP_DIR/backend/venv"

if [ -d "$VENV_DIR" ]; then
    warn "Menghapus venv lama dan membuat ulang..."
    rm -rf "$VENV_DIR"
fi

log "Membuat venv baru di: $VENV_DIR"
python3 -m venv "$VENV_DIR"

[ -f "$VENV_DIR/bin/pip" ] || err "Gagal membuat venv! Coba: sudo apt install python3-venv python3-full"

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
    "pandas>=2.0.0"
    "tabulate>=0.9.0"
    "pdfplumber>=0.11.0"
    "docx2txt>=0.8"
)

# Tambah asyncpg & psycopg2 hanya jika pakai PostgreSQL
if [ "$WZ_DB_TYPE" = "2" ]; then
    PACKAGES+=("asyncpg>=0.29.0" "psycopg2-binary>=2.9.9")
fi

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

[ ${#FAILED[@]} -gt 0 ] && warn "Gagal install: ${FAILED[*]}" || log "Semua package berhasil diinstall!"

# ── Init Database & Admin ─────────────────────────────────────
step "Initializing Database & Admin User"

cd "$APP_DIR/backend"
mkdir -p "$APP_DIR/backend/data/logs" \
         "$APP_DIR/backend/data/uploads" \
         "$APP_DIR/backend/data/chroma_db"

# Load .env ke environment shell dulu
set -a
source "$APP_DIR/.env"
set +a

# Tulis script Python ke file sementara agar variabel shell bisa di-expand
# (heredoc dengan 'PYEOF' tidak expand variabel — ini root cause bug login gagal)
INIT_SCRIPT="$APP_DIR/backend/_init_admin_tmp.py"

cat > "$INIT_SCRIPT" << PYEOF
import asyncio, sys, os

# Pastikan working directory benar dan .env terbaca
os.chdir("$APP_DIR/backend")
sys.path.insert(0, "$APP_DIR/backend")

# Load .env secara eksplisit dari path absolut
from dotenv import load_dotenv
load_dotenv("$APP_DIR/.env", override=True)

async def main():
    try:
        from db.database import init_db, AsyncSessionLocal
        from core.auth import ensure_admin_exists
        from core.config import settings

        print(f"  [DB] Membuat tabel database...")
        await init_db()

        print(f"  [DB] Membuat admin user: {settings.ADMIN_USERNAME}")
        async with AsyncSessionLocal() as db:
            await ensure_admin_exists(db)

        print(f"  [OK] Admin '{settings.ADMIN_USERNAME}' berhasil dibuat")
        print(f"  [OK] Database siap di: {settings.DATABASE_URL}")

    except Exception as e:
        print(f"  [ERROR] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

asyncio.run(main())
PYEOF

# Jalankan script init
"$VENV_DIR/bin/python3" "$INIT_SCRIPT"
INIT_STATUS=$?

# Hapus script sementara
rm -f "$INIT_SCRIPT"

if [ $INIT_STATUS -ne 0 ]; then
    err "Gagal inisialisasi database/admin. Cek error di atas."
fi

log "Database & admin user siap"

# ── Frontend ──────────────────────────────────────────────────
step "Building Frontend"

cd "$APP_DIR/frontend"
log "Installing npm packages..."
npm install --silent
log "Building React app..."
npm run build
log "Frontend built"

# ── Systemd service ───────────────────────────────────────────
step "Installing Systemd Service"

cat > /tmp/ai-orchestrator-api.service << EOF
[Unit]
Description=AI ORCHESTRATOR API Server
After=network.target redis.service

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

sudo cp /tmp/ai-orchestrator-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-orchestrator-api 2>/dev/null || true
log "Systemd service installed"

# ── Selesai ───────────────────────────────────────────────────
echo -e "\n${GREEN}${BOLD}"
cat << 'EOF'
╔═════════════════════════════════════════════════╗
║   AI ORCHESTRATOR Installation Complete! 🎉  ║
╚═════════════════════════════════════════════════╝
EOF
echo -e "${NC}"
echo -e " ${CYAN}Langkah berikutnya:${NC}"
echo -e "  1. Tambahkan API key (opsional) : ${YELLOW}nano $APP_DIR/.env${NC}"
echo -e "  2. Jalankan server              : ${YELLOW}bash $APP_DIR/scripts/dev.sh${NC}"
echo -e "     atau update & restart        : ${YELLOW}bash $APP_DIR/update_and_restart.sh${NC}"
echo -e "  3. Buka browser                 : ${YELLOW}http://localhost:7860${NC}"
echo -e "  4. Login dengan username        : ${YELLOW}$WZ_ADMIN_USER${NC}"
echo -e "\n ${CYAN}RAG/LangChain (opsional):${NC}"
echo -e "  bash $APP_DIR/scripts/install-rag.sh"
echo ""
