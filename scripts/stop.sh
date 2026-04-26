#!/bin/bash
[ -f /tmp/ai-orchestrator-api.pid ] && kill $(cat /tmp/ai-orchestrator-api.pid) 2>/dev/null && rm /tmp/ai-orchestrator-api.pid
pkill -f "uvicorn main:app" 2>/dev/null || true
echo "AI ORCHESTRATOR stopped."
