#!/bin/bash
echo "🔄 Memulai proses instalasi / update AI-SUPER..."

cd "$(dirname "$0")"

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

echo "✅ Pembaruan selesai! Aplikasi siap digunakan."
