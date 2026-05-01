#!/bin/bash
# AI ORCHESTRATOR — Production Start

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

echo -e "${CYAN}${BOLD}Starting AI ORCHESTRATOR...${NC}"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

sudo systemctl start redis-server 2>/dev/null || sudo systemctl start redis 2>/dev/null || true
sudo systemctl start postgresql 2>/dev/null || true

cd "$DIR/backend"
source venv/bin/activate
[ -f "$DIR/.env" ] && { set -a; source "$DIR/.env"; set +a; }
mkdir -p data/logs data/uploads data/chroma_db

uvicorn main:app --host 0.0.0.0 --port 7860 --workers 2 &
echo $! > /tmp/ai-orchestrator-api.pid

sleep 2
echo -e "${GREEN}${BOLD}AI ORCHESTRATOR berjalan!${NC}"
echo -e "  🌐 http://localhost:7860"
echo -e "  🔑 admin / admin"
echo -e "\n  Ctrl+C untuk stop\n"
wait $(cat /tmp/ai-orchestrator-api.pid)
