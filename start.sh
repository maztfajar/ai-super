#!/bin/bash
echo "🚀 Memulai AI-SUPER (Mode Lokal)..."

# Pindah ke folder script
cd "$(dirname "$0")"

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

echo "✅ AI-SUPER berjalan di http://localhost:7860"
echo "Log dapat dilihat di: backend/backend.log"
