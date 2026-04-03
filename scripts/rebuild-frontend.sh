#!/bin/bash
# AI SUPER ASSISTANT — Rebuild Frontend
# Jalankan ini setelah update file dari zip baru
# Usage: bash scripts/rebuild-frontend.sh

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

echo -e "${CYAN}${BOLD}🔨 Rebuild Frontend AI SUPER ASSISTANT...${NC}\n"

# Cek node
if ! command -v node &>/dev/null; then
    echo -e "${RED}[✗] Node.js tidak ditemukan!${NC}"
    echo "Install: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs"
    exit 1
fi
echo -e "${GREEN}[✓]${NC} Node.js $(node --version)"

cd "$DIR/frontend"

# Install packages jika perlu
if [ ! -d "node_modules" ]; then
    echo -e "${CYAN}[→]${NC} Menginstall npm packages..."
    npm install
fi

# Build
echo -e "${CYAN}[→]${NC} Building... (mohon tunggu)"
npm run build

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║  ✅ Frontend berhasil build! ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════╝${NC}"
    echo ""
    echo -e "Sekarang jalankan: ${CYAN}bash scripts/dev.sh${NC}"
else
    echo -e "${RED}[✗] Build gagal! Lihat error di atas.${NC}"
    exit 1
fi
