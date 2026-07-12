#!/bin/bash
# ========================================================
# AI ORCHESTRATOR - DOCKER INSTALLER (LINUX/MACOS)
# ========================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================================${NC}"
echo -e "${CYAN}       AI ORCHESTRATOR - DOCKER INSTALLER               ${NC}"
echo -e "${CYAN}========================================================${NC}"
echo ""

# Pengecekan Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker tidak ditemukan!${NC}"
    echo "Silakan install Docker terlebih dahulu:"
    echo "https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}[ERROR] Docker Compose tidak ditemukan!${NC}"
    echo "Pastikan docker-compose plugin terinstall."
    exit 1
fi

echo -e "${GREEN}[OK] Docker dan Docker Compose tersedia.${NC}"

# Setup .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${GREEN}[OK] Membuat file konfigurasi .env...${NC}"
        cp .env.example .env
    else
        echo -e "${YELLOW}[WARNING] File .env.example tidak ditemukan. Melewati pembuatan .env.${NC}"
    fi
else
    echo -e "${CYAN}[INFO] File .env sudah ada, tidak akan ditimpa.${NC}"
fi

# Setup Volumes
echo -e "${GREEN}[OK] Membuat direktori penyimpanan data (volumes)...${NC}"
mkdir -p data/logs data/uploads data/chroma_db rag_documents
# Berikan permission yang longgar agar container docker dapat menulis ke dalamnya
chmod -R 777 data rag_documents 2>/dev/null || true

echo ""
echo -e "${CYAN}========================================================${NC}"
echo "Menjalankan aplikasi AI Orchestrator..."
echo -e "${CYAN}========================================================${NC}"
echo "Ini mungkin memakan waktu beberapa menit saat pertama kali dijalankan karena mengunduh image."
echo ""

# Menjalankan Docker Compose
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo ""
echo -e "${GREEN}========================================================${NC}"
echo -e "${GREEN}🎉 INSTALASI SELESAI 🎉${NC}"
echo -e "${GREEN}========================================================${NC}"
echo "Aplikasi berjalan di belakang layar."
echo -e "Silakan buka browser Anda di: ${CYAN}http://localhost:7860${NC}"
echo ""
echo -e "Untuk melihat log, ketik: ${YELLOW}docker-compose logs -f${NC}"
echo -e "Untuk menghentikan, ketik: ${YELLOW}docker-compose down${NC}"
echo -e "${GREEN}========================================================${NC}"
