#!/bin/bash
echo "🔄 Memulai proses instalasi / update AI-SUPER..."

cd "$(dirname "$0")"

# ── WARNA ─────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

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
            echo -e "${GREEN}[✓]${NC} SECRET_KEY di-generate otomatis"
        fi
    else
        echo "⚠️ .env.example tidak ditemukan! Salin manual: cp .env.example .env"
        exit 1
    fi
fi

echo "[1/4] Mengambil pembaruan repository..."
git pull 2>/dev/null || echo "Bukan direktori git, melewati git pull..."

echo "[2/4] Menyiapkan Frontend..."
cd frontend
npm install
npm run build
cd ..

echo "[3/4] Menyiapkan Backend..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements-minimal.txt
cd ..

echo "[4/4] Memuat ulang aplikasi..."
./stop.sh
./start.sh

echo ""
echo -e "${GREEN}${BOLD}✅ Pembaruan selesai! Aplikasi siap digunakan.${NC}"
echo ""

# Tampilkan kredensial default saat first-run
if [ "$FIRST_RUN" = true ]; then
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

echo -e " Akses dashboard: ${YELLOW}http://localhost:7860${NC}"
echo ""
