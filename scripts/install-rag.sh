#!/bin/bash
# AI SUPER ASSISTANT — Install RAG (Opsional)
# Jalankan setelah server berjalan normal
# Estimasi: 10-20 menit, ~500MB

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

echo -e "${CYAN}${BOLD}AI SUPER ASSISTANT — Install RAG & Vector DB${NC}"
echo ""
echo "Package: chromadb, langchain, sentence-transformers"
echo "Estimasi: 10-20 menit"
echo ""
read -p "Lanjutkan? (y/N): " confirm
[[ "$confirm" != "y" && "$confirm" != "Y" ]] && echo "Dibatalkan." && exit 0

cd "$DIR/backend"
[ ! -f "venv/bin/activate" ] && { echo "venv tidak ada — jalankan install.sh dulu"; exit 1; }
source venv/bin/activate

step "Install ChromaDB + LangChain"
pip install --prefer-binary --no-cache-dir \
    "chromadb>=0.5.0" \
    "langchain>=0.2.6" \
    "langchain-community>=0.2.6" \
    "langchain-openai>=0.1.13" \
    "langchain-anthropic>=0.1.15" \
    2>&1 | grep -E "^(Collecting|Installing|Successfully|ERROR)" || true

step "Install Sentence Transformers"
warn "Model embedding ~90MB akan didownload saat pertama digunakan..."
pip install --prefer-binary --no-cache-dir \
    "sentence-transformers>=3.0.0" \
    "langchain-huggingface>=0.0.3" \
    2>&1 | grep -E "^(Collecting|Installing|Successfully|ERROR)" || true

step "Verifikasi"
python3 -c "
import chromadb, langchain
print(f'chromadb {chromadb.__version__} ✓')
print(f'langchain {langchain.__version__} ✓')
print('RAG siap!')
" && log "RAG berhasil diinstall!" || warn "Ada yang gagal, cek di atas"

echo ""
echo -e "${GREEN}Restart server untuk aktifkan RAG:${NC}"
echo -e "  bash $DIR/scripts/dev.sh"
