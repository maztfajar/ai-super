#!/bin/bash
# AI SUPER ASSISTANT — Install Cloudflare Tunnel (cloudflared)

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

echo -e "${CYAN}${BOLD}Install Cloudflare Tunnel (cloudflared)${NC}"

if command -v cloudflared &>/dev/null; then
    log "cloudflared sudah terinstall: $(cloudflared --version)"
    exit 0
fi

step "Download cloudflared"
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
elif [ "$ARCH" = "aarch64" ]; then
    URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
else
    URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
fi

sudo curl -fsSL "$URL" -o /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

if command -v cloudflared &>/dev/null; then
    log "cloudflared berhasil diinstall: $(cloudflared --version)"
else
    echo "Gagal install otomatis. Coba manual:"
    echo "  wget $URL -O cloudflared && sudo mv cloudflared /usr/local/bin/ && sudo chmod +x /usr/local/bin/cloudflared"
fi

echo ""
echo -e "${GREEN}${BOLD}Cara pakai Cloudflare Tunnel:${NC}"
echo ""
echo -e "  ${CYAN}Mode Cepat (tanpa akun):${NC}"
echo -e "  Klik tombol 'Start Tunnel' di AI SUPER ASSISTANT Settings"
echo -e "  URL publik otomatis akan muncul (*.trycloudflare.com)"
echo ""
echo -e "  ${CYAN}Mode Permanen (pakai domain sendiri):${NC}"
echo -e "  1. Login: cloudflared tunnel login"
echo -e "  2. Buat tunnel: cloudflared tunnel create ai-super-assistant"
echo -e "  3. Copy token → tempel di AI SUPER ASSISTANT Settings"
echo -e "  4. Set domain di Cloudflare DNS"
