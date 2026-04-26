#!/bin/bash
# ============================================================
#  AI ORCHESTRATOR — Setup Cloudflare Tunnel sebagai System Service
#  Tunnel otomatis berjalan saat server boot
# ============================================================

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'
log()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; }
step() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

TOKEN="${1:-}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${CYAN}${BOLD}AI ORCHESTRATOR — Cloudflare Tunnel Service Setup${NC}\n"

# ── 1. Cek / install cloudflared ─────────────────────────────
step "1. Cek cloudflared"
if ! command -v cloudflared &>/dev/null; then
    warn "cloudflared tidak ditemukan, install dulu..."
    bash "$DIR/scripts/install-cloudflare.sh"
fi
log "cloudflared: $(cloudflared --version 2>&1 | head -1)"

# ── 2. Ambil token ────────────────────────────────────────────
step "2. Token"
if [ -z "$TOKEN" ]; then
    # Coba baca dari .env
    if [ -f "$DIR/.env" ]; then
        TOKEN=$(grep "^CLOUDFLARE_TUNNEL_TOKEN=" "$DIR/.env" | cut -d= -f2-)
    fi
fi

if [ -z "$TOKEN" ]; then
    err "Token tidak ditemukan!"
    echo "Cara pakai:"
    echo "  bash scripts/setup-cloudflare-service.sh <TOKEN>"
    echo ""
    echo "Atau set dulu di AI ORCHESTRATOR Settings → Cloudflare Tunnel → Simpan"
    echo "Lalu jalankan script ini tanpa argumen."
    exit 1
fi
log "Token ditemukan (${#TOKEN} karakter)"

# ── 3. Install sebagai service ────────────────────────────────
step "3. Install cloudflared service"
sudo cloudflared service install "$TOKEN"
if [ $? -ne 0 ]; then
    err "Gagal install service. Coba manual:"
    echo "  sudo cloudflared service install $TOKEN"
    exit 1
fi
log "Service berhasil diinstall"

# ── 4. Start & enable service ─────────────────────────────────
step "4. Start service"
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sleep 3

STATUS=$(sudo systemctl is-active cloudflared 2>/dev/null)
if [ "$STATUS" = "active" ]; then
    log "cloudflared service: AKTIF"
else
    warn "Status: $STATUS"
    echo "Cek log: sudo journalctl -u cloudflared -n 20"
fi

# ── 5. Simpan token ke .env ───────────────────────────────────
step "5. Simpan ke .env"
if [ -f "$DIR/.env" ]; then
    if grep -q "^CLOUDFLARE_TUNNEL_TOKEN=" "$DIR/.env"; then
        sed -i "s|^CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=$TOKEN|" "$DIR/.env"
    else
        echo "CLOUDFLARE_TUNNEL_TOKEN=$TOKEN" >> "$DIR/.env"
    fi
    sed -i 's|^TUNNEL_ENABLED=.*|TUNNEL_ENABLED=true|' "$DIR/.env" 2>/dev/null || \
        echo "TUNNEL_ENABLED=true" >> "$DIR/.env"
    log "Token disimpan ke .env"
fi

# ── Done ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗"
echo -e "║  Cloudflare Tunnel Service berhasil disetup!     ║"
echo -e "╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Status   : ${CYAN}sudo systemctl status cloudflared${NC}"
echo -e "  Log live : ${CYAN}sudo journalctl -u cloudflared -f${NC}"
echo -e "  Stop     : ${CYAN}sudo systemctl stop cloudflared${NC}"
echo -e "  Uninstall: ${CYAN}sudo cloudflared service uninstall${NC}"
echo ""
echo -e "  ${YELLOW}Langkah berikutnya di Cloudflare Dashboard:${NC}"
echo -e "  1. Buka tunnel → tab 'Hostname routes'"
echo -e "  2. Add route: subdomain=eai-orchestrator, domain=kapanewonpengasih.my.id"
echo -e "  3. Path: kosongkan | Type: HTTP | URL: localhost:7860"
echo -e "  4. Save hostname"
echo ""
