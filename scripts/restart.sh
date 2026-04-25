#!/bin/bash
# AI SUPER ASSISTANT — Restart & Rebuild
# Build frontend and restart backend services

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

echo -e "${CYAN}${BOLD}🔄 Memulai ulang AI SUPER ASSISTANT...${NC}\n"

# 1. Rebuild Frontend
bash "$DIR/scripts/rebuild-frontend.sh"

# 2. Stop Server
echo -e "\n${CYAN}[→]${NC} Menghentikan server lama..."
bash "$DIR/scripts/stop.sh"
sleep 1

# 3. Start Server
echo -e "${CYAN}[→]${NC} Memulai server baru..."
# Kita jalankan uvicorn secara langsung agar output start.sh tidak keburu tertutup atau gunakan background
bash "$DIR/scripts/start.sh" &
START_PID=$!

sleep 3
echo -e "\n${GREEN}${BOLD}✅ Proses restart & build selesai!${NC}"
echo -e "Server kembali berjalan. Akses di: ${CYAN}http://localhost:7860${NC}\n"

wait $START_PID
