#!/bin/bash
pkill -f python3
git fetch origin main
git reset --hard origin/main

# Masuk ke folder backend dan update library
cd /root/ai-super/backend
./venv/bin/pip install -r requirements.txt

# Jalankan uvicorn
./venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 7860 --workers 2 &
echo "AL FATIH AI Orchestrator Berhasil Diupdate dan Library Diperbarui!"
