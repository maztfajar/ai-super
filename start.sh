#!/bin/bash

# ── WARNA ─────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo "🚀 Memulai AI-SUPER (Mode Lokal)..."

# Pindah ke folder script
cd "$(dirname "$0")"

# ── Deteksi first-run: buat .env dari template jika belum ada ─
FIRST_RUN=false
if [ ! -f ".env" ]; then
    FIRST_RUN=true
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}[✓]${NC} .env dibuat dari template (instalasi pertama)"

        # Auto-generate SECRET_KEY yang aman
        if command -v python3 &>/dev/null; then
            NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
            sed -i "s|^SECRET_KEY=.*|SECRET_KEY=\"$NEW_SECRET\"|" .env
        fi
    else
        echo "⚠️ .env tidak ditemukan! Salin dari template: cp .env.example .env"
        exit 1
    fi
fi

cd backend
if [ ! -d "venv" ]; then
    echo "⚠️ venv tidak ditemukan. Silakan jalankan ./update.sh terlebih dahulu untuk menginstall dependensi."
    exit 1
fi
source venv/bin/activate

# Matikan instance lama jika ada
if [ -f "backend.pid" ]; then
    kill -9 $(cat backend.pid) 2>/dev/null
    rm backend.pid
fi

# Jalankan uvicorn di background
nohup uvicorn main:app --host 0.0.0.0 --port 7860 > backend.log 2>&1 &
echo $! > backend.pid

echo -e "${GREEN}✅ AI-SUPER berjalan di http://localhost:7860${NC}"
echo "Log dapat dilihat di: backend/backend.log"

# Tampilkan kredensial default saat first-run
if [ "$FIRST_RUN" = true ]; then
    echo ""
    echo -e " ${CYAN}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e " ${CYAN}║  ${BOLD}INSTALASI PERTAMA — Kredensial Default Login${NC}    ${CYAN}║${NC}"
    echo -e " ${CYAN}╠═══════════════════════════════════════════════════╣${NC}"
    echo -e " ${CYAN}║${NC}  Username : ${YELLOW}${BOLD}admin${NC}                                ${CYAN}║${NC}"
    echo -e " ${CYAN}║${NC}  Password : ${YELLOW}${BOLD}12345678${NC}                             ${CYAN}║${NC}"
    echo -e " ${CYAN}╠═══════════════════════════════════════════════════╣${NC}"
    echo -e " ${CYAN}║${NC}  ${YELLOW}⚠  Ganti password setelah login via Profile!${NC}     ${CYAN}║${NC}"
    echo -e " ${CYAN}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e " Untuk mengganti kredensial secara manual:"
    echo -e "   ${YELLOW}nano .env${NC}  → ubah ADMIN_USERNAME dan ADMIN_PASSWORD"
    echo -e "   kemudian restart: ${YELLOW}./stop.sh && ./start.sh${NC}"
    echo ""
fi
