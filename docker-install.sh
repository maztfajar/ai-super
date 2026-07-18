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

echo -e "${CYAN}========================================================"
echo -e "       AI ORCHESTRATOR - DOCKER INSTALLER               "
echo -e "========================================================${NC}"
echo ""

# Pengecekan Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker tidak ditemukan!${NC}"
    echo "Silakan install Docker terlebih dahulu:"
    echo "https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}[ERROR] Docker Compose tidak ditemukan!${NC}"
    echo "Pastikan docker-compose plugin terinstall."
    exit 1
fi

echo -e "${GREEN}[OK] Docker dan Docker Compose tersedia.${NC}"

# Setup Volumes
echo -e "${GREEN}[OK] Membuat direktori penyimpanan data...${NC}"
mkdir -p data/logs data/uploads data/chroma_db rag_documents
chmod -R 777 data rag_documents 2>/dev/null || true

echo ""
echo -e "${CYAN}========================================================"
echo "  Menjalankan AI Orchestrator..."
echo -e "========================================================${NC}"
echo "  Mengunduh image dari DockerHub (mungkin butuh beberapa menit)"
echo ""

# Menjalankan Docker Compose
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

echo ""
echo -e "${GREEN}========================================================"
echo -e "  🎉 INSTALASI SELESAI! 🎉"
echo -e "========================================================${NC}"
echo ""
echo -e "  Buka browser: ${CYAN}http://localhost:7860${NC}"
echo ""
echo -e "  ┌─────────────────────────────────────────────────┐"
echo -e "  │           KREDENSIAL LOGIN DEFAULT               │"
echo -e "  │                                                   │"
echo -e "  │   Username : ${YELLOW}admin${NC}                              │"
echo -e "  │   Password : ${YELLOW}admin123${NC}                           │"
echo -e "  │                                                   │"
echo -e "  │   ⚠️  Segera ganti password setelah login!       │"
echo -e "  └─────────────────────────────────────────────────┘"
echo ""
echo -e "  💡 Untuk menambahkan API key (OpenAI, Gemini, dll):"
echo -e "     Login → Settings → API Keys"
echo ""
echo -e "  Perintah berguna:"
echo -e "  ${YELLOW}docker compose logs -f${NC}     → Lihat log"
echo -e "  ${YELLOW}docker compose down${NC}         → Hentikan aplikasi"
echo -e "  ${YELLOW}docker compose pull && docker compose up -d${NC} → Update"
echo -e "${GREEN}========================================================${NC}"

