#!/bin/bash
# ============================================================
# AI ORCHESTRATOR — Secure Docker Installer
# Usage: curl -fsSL <url> | bash
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}🚀 AI ORCHESTRATOR — Secure Docker Installer${NC}"
echo -e "${WHITE}Memulai proses instalasi terproteksi...${NC}\n"

# 1. Cek Docker
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}[!] Docker tidak ditemukan. Menginstall Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "${GREEN}[✓] Docker berhasil diinstall.${NC}"
else
    echo -e "${GREEN}[✓] Docker sudah terpasang.${NC}"
fi

# 2. Cek Docker Compose
if ! docker compose version &>/dev/null; then
    echo -e "${YELLOW}[!] Docker Compose tidak ditemukan. Menginstall...${NC}"
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# 3. Persiapkan Direktori
INSTALL_DIR="ai-orchestrator"
mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/rag_documents"
cd "$INSTALL_DIR"

# 4. Unduh Konfigurasi (dari repo publik)
echo -e "${CYAN}[*] Mengunduh file konfigurasi...${NC}"
# Note: Ganti URL di bawah dengan URL mentah (raw) dari file di repo publik Anda
REPO_URL="https://raw.githubusercontent.com/maztfajar/ai-super/main"

curl -sSL "$REPO_URL/docker-compose.yml" -o docker-compose.yml
curl -sSL "$REPO_URL/.env.example" -o .env

# 5. Konfigurasi Awal
if [ ! -f ".env" ]; then
    echo -e "${RED}[✗] Gagal mengunduh .env.example${NC}"
    exit 1
fi

# Generate SECRET_KEY otomatis
NEW_SECRET=$(LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 64 | head -n 1)
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=\"$NEW_SECRET\"|" .env

echo -e "${GREEN}[✓] Konfigurasi dasar siap.${NC}"
echo -e "${YELLOW}[!] PENTING: Silakan edit file .env untuk memasukkan API Key Anda.${NC}"
echo -e "    Gunakan: nano .env\n"

# 6. Jalankan Container
echo -e "${CYAN}[*] Menarik Image dan menjalankan container...${NC}"
docker compose pull
docker compose up -d

echo -e "\n${GREEN}${BOLD}╔═════════════════════════════════════════════════╗"
echo -e "║   AI ORCHESTRATOR Berhasil Terpasang! 🎉        ║"
echo -e "╚═════════════════════════════════════════════════╝${NC}"
echo -e "Akses Dashboard di: ${BOLD}http://$(curl -s ifconfig.me):7860${NC}"
echo -e "Username default  : admin"
echo -e "Password default  : (cek .env)${NC}"
echo -e "\n${CYAN}Gunakan 'docker compose logs -f' untuk melihat log.${NC}"
