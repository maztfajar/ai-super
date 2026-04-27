#!/bin/bash
# Detect the project directory dynamically
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Memulai proses update dan restart AI Orchestrator..."

# 1. Update Frontend
echo "----------------------------------------"
echo "📦 Building Frontend..."
cd "$APP_DIR/frontend"
npm run build
if [ $? -eq 0 ]; then
    echo "✅ Frontend berhasil di-build!"
else
    echo "❌ Frontend build gagal!"
    exit 1
fi

# 2. Update Backend
echo "----------------------------------------"
echo "⚙️ Memperbarui dependensi Backend..."
cd "$APP_DIR/backend"
./venv/bin/pip install -r requirements.txt

# 3. Restart Service
echo "----------------------------------------"
echo "🔄 Merestart AI ORCHESTRATOR service..."
sudo systemctl restart ai-super-assistant-api.service

# 4. Health Check
echo "----------------------------------------"
echo "⏳ Menunggu service untuk online..."
max_retries=15
counter=0
until curl -s http://localhost:7860/api/health > /dev/null; do
    sleep 2
    counter=$((counter+1))
    if [ $counter -ge $max_retries ]; then
        echo "❌ Service gagal online dalam 30 detik."
        echo "Gunakan perintah ini untuk cek log: sudo journalctl -u ai-super-assistant-api.service -n 50 --no-pager"
        exit 1
    fi
done

echo "----------------------------------------"
echo "🎉 AI ORCHESTRATOR Berhasil Diupdate dan Berjalan Normal!"
