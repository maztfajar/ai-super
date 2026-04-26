#!/bin/bash
# Detect the project directory dynamically
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Deploying application from $APP_DIR..."

# Safely kill only the specific uvicorn instance for this app
pkill -f "uvicorn main:app --host 0.0.0.0 --port 7860" || true

git fetch origin main
git reset --hard origin/main

# Masuk ke folder backend dan update library
cd "$APP_DIR/backend"
./venv/bin/pip install -r requirements.txt

# Jalankan uvicorn
./venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 7860 --workers 2 &
echo "AI Orchestrator Berhasil Diupdate dan Library Diperbarui!"
