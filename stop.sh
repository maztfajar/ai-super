#!/bin/bash
echo "🛑 Mematikan AI-SUPER..."

cd "$(dirname "$0")/backend"
if [ -f "backend.pid" ]; then
    PID=$(cat backend.pid)
    kill -9 $PID 2>/dev/null
    rm backend.pid
fi

# Bunuh semua child process atau worker uvicorn yang tertinggal
pkill -f "uvicorn main:app" 2>/dev/null

# Terakhir, pastikan port 7860 benar-benar bebas
fuser -k 7860/tcp 2>/dev/null

echo "✅ Aplikasi berhasil dihentikan sepenuhnya."
