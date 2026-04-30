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

SERVICE_NAME="ai-orchestrator-api.service"
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    echo "⚙️ Menggunakan systemd untuk restart..."
    sudo systemctl daemon-reload
    sudo systemctl restart "$SERVICE_NAME"
else
    echo "⚠️ Unit $SERVICE_NAME tidak ditemukan."
    echo "🔧 Mencoba restart manual (fallback)..."
    
    # Cari PID uvicorn yang jalan di port 7860
    PID=$(lsof -t -i:7860)
    if [ -n "$PID" ]; then
        echo "🔪 Menghentikan proses lama (PID: $PID)..."
        kill -9 $PID
    fi
    
    echo "🚀 Menjalankan backend di background..."
    cd "$APP_DIR/backend"
    nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 7860 > "$APP_DIR/data/logs/manual_restart.log" 2>&1 &
    
    echo "📝 Log manual restart: $APP_DIR/data/logs/manual_restart.log"
fi

# 4. Health Check
echo "----------------------------------------"
echo "⏳ Menunggu service untuk online..."
max_retries=20
counter=0
until curl -s http://localhost:7860/api/health > /dev/null; do
    sleep 2
    counter=$((counter+1))
    if [ $counter -ge $max_retries ]; then
        echo "❌ Service gagal online dalam 40 detik."
        if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
            echo "Gunakan perintah ini untuk cek log: sudo journalctl -u $SERVICE_NAME -n 50 --no-pager"
        else
            echo "Cek log manual di: $APP_DIR/data/logs/manual_restart.log"
        fi
        exit 1
    fi
done

echo "----------------------------------------"
echo "🎉 AI ORCHESTRATOR Berhasil Diupdate dan Berjalan Normal!"
