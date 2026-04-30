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
SERVICE_NAME="ai-orchestrator-api.service"
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
else
    echo "⚠️ Unit $SERVICE_NAME not found. Restarting manually..."
    PID=$(lsof -t -i:7860)
    [ -n "$PID" ] && kill -9 $PID
    cd "$APP_DIR/backend"
    nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 7860 > "$APP_DIR/data/logs/manual_restart.log" 2>&1 &
fi

echo "Waiting for service to become healthy..."
max_retries=20
counter=0
until curl -s http://localhost:7860/api/health > /dev/null; do
    sleep 2
    counter=$((counter+1))
    if [ $counter -ge $max_retries ]; then
        echo "❌ Service did not become healthy within 40 seconds."
        [ -f "$APP_DIR/data/logs/manual_restart.log" ] && echo "Check logs: $APP_DIR/data/logs/manual_restart.log"
        exit 1
    fi
done

echo "✅ AI ORCHESTRATOR Berhasil Diupdate dan Berjalan Normal!"
