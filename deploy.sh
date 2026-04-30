#!/bin/bash
# Detect the project directory dynamically
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Deploying application from $APP_DIR..."

git fetch origin main
git reset --hard origin/main

# Masuk ke folder backend dan update library
cd "$APP_DIR/backend"
./venv/bin/pip install -r requirements.txt

echo "Restarting AI ORCHESTRATOR service..."
sudo systemctl restart ai-orchestrator-api.service

echo "Waiting for service to become healthy..."
max_retries=15
counter=0
until curl -s http://localhost:7860/api/health > /dev/null; do
    sleep 2
    counter=$((counter+1))
    if [ $counter -ge $max_retries ]; then
        echo "❌ Service did not become healthy within 30 seconds. Check logs with: sudo journalctl -u ai-orchestrator-api.service -n 50 --no-pager"
        exit 1
    fi
done

echo "✅ AI ORCHESTRATOR Berhasil Diupdate dan Berjalan Normal!"
