#!/bin/bash
[ -f /tmp/ai-super-assistant-api.pid ] && kill $(cat /tmp/ai-super-assistant-api.pid) 2>/dev/null && rm /tmp/ai-super-assistant-api.pid
pkill -f "uvicorn main:app" 2>/dev/null || true
echo "AI SUPER ASSISTANT stopped."
