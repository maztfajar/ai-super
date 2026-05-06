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

echo -e "\n${CYAN}${BOLD}--- Konfigurasi .env ---${NC}"
echo -e "${WHITE}Mari kita atur konfigurasi penting agar aplikasi siap digunakan.${NC}"

# Admin Password
read -p "Masukkan ADMIN_PASSWORD (kosongkan untuk generate otomatis): " admin_pwd </dev/tty
if [ -z "$admin_pwd" ]; then
    admin_pwd=$(LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | fold -w 12 | head -n 1)
    echo -e "${GREEN}Password admin otomatis: ${admin_pwd}${NC}"
fi
sed -i "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=\"$admin_pwd\"|" .env

# API Keys
read -p "Masukkan OPENAI_API_KEY (opsional, tekan Enter untuk lewati): " openai_key </dev/tty
if [ -n "$openai_key" ]; then
    sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=\"$openai_key\"|" .env
fi

read -p "Masukkan ANTHROPIC_API_KEY (opsional, tekan Enter untuk lewati): " anthropic_key </dev/tty
if [ -n "$anthropic_key" ]; then
    sed -i "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=\"$anthropic_key\"|" .env
fi

echo -e "\n${GREEN}[✓] Konfigurasi dasar telah disimpan ke .env${NC}"

# Konfirmasi edit manual
read -p "Apakah Anda ingin membuka file .env dengan nano untuk konfigurasi lainnya? (y/N): " edit_env </dev/tty
if [[ "$edit_env" =~ ^[Yy]$ ]]; then
    nano .env </dev/tty >/dev/tty
fi


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
