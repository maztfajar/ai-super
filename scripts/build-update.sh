#!/bin/bash
# scripts/build-update.sh
# Creates an OTA update package for AI ORCHESTRATOR (Master Server action)
# Auto-increments APP_BUILD setiap kali dijalankan.

cd "$(dirname "$0")/.." || exit

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'; BOLD='\033[1m'

echo -e "${CYAN}${BOLD}📦 AI ORCHESTRATOR — Build Update Package${NC}\n"

# ── 1. Auto-increment APP_BUILD ──────────────────────────────

ENV_FILE=".env"
CONFIG_FILE="backend/core/config.py"

# Baca APP_BUILD saat ini dari .env
CURRENT_BUILD=$(grep -oP 'APP_BUILD=\K[0-9]+' "$ENV_FILE" 2>/dev/null || echo "0")
NEW_BUILD=$((CURRENT_BUILD + 1))

# Baca APP_VERSION dari .env
CURRENT_VERSION=$(grep -oP 'APP_VERSION="\K[^"]+' "$ENV_FILE" 2>/dev/null || echo "1.0.0")

echo -e "${CYAN}[1/3]${NC} Auto-increment build number"
echo -e "      Versi    : ${BOLD}${CURRENT_VERSION}${NC}"
echo -e "      Build    : ${YELLOW}${CURRENT_BUILD}${NC} → ${GREEN}${NEW_BUILD}${NC}"

# Update APP_BUILD di .env
if grep -q "^APP_BUILD=" "$ENV_FILE"; then
    sed -i "s/^APP_BUILD=.*/APP_BUILD=${NEW_BUILD}/" "$ENV_FILE"
else
    # Tambahkan setelah APP_VERSION jika belum ada
    sed -i "/^APP_VERSION=/a APP_BUILD=${NEW_BUILD}" "$ENV_FILE"
fi

# Update APP_BUILD di config.py
if grep -q "APP_BUILD" "$CONFIG_FILE"; then
    sed -i "s/APP_BUILD: int = .*/APP_BUILD: int = ${NEW_BUILD}/" "$CONFIG_FILE"
else
    sed -i "/APP_VERSION/a\\    APP_BUILD: int = ${NEW_BUILD}" "$CONFIG_FILE"
fi

echo -e "${GREEN}[✓]${NC} Build number updated to ${NEW_BUILD}"

# ── 2. Build zip package ─────────────────────────────────────

echo -e "\n${CYAN}[2/3]${NC} Building update zip..."

SERVE_DIR="$(pwd)/backend/data/updates"
mkdir -p "$SERVE_DIR"
ZIP_DEST="$SERVE_DIR/ai-orchestrator_update.zip"
rm -f "$ZIP_DEST"

# Juga copy ke /tmp untuk backward compatibility
TMP_DEST="/tmp/ai-orchestrator_update.zip"

# Zip the contents, excluding sensitive and cache directories
zip -r "$ZIP_DEST" . \
  -x "*.git*" \
  -x "backend/db/*" \
  -x "backend/data/*" \
  -x "backend/__pycache__/*" \
  -x "backend/venv/*" \
  -x "frontend/node_modules/*" \
  -x "frontend/dist/*" \
  -x ".env" \
  -x ".domains.json" \
  -x "*/.custom_models.json" \
  -x "*/__pycache__/*" \
  -x "*.DS_Store" \
  -x "scripts/venv/*" \
  > /dev/null 2>&1

cp "$ZIP_DEST" "$TMP_DEST" 2>/dev/null || true

ZIP_SIZE=$(du -h "$ZIP_DEST" | cut -f1)
echo -e "${GREEN}[✓]${NC} Zip created (${ZIP_SIZE})"

# ── 3. Summary ───────────────────────────────────────────────

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║  ✅ Update Package Ready!                    ║${NC}"
echo -e "${GREEN}${BOLD}╠══════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}${BOLD}║${NC}  Versi  : ${BOLD}${CURRENT_VERSION}${NC}"
echo -e "${GREEN}${BOLD}║${NC}  Build  : ${BOLD}${NEW_BUILD}${NC}"
echo -e "${GREEN}${BOLD}║${NC}  File   : ${ZIP_DEST}"
echo -e "${GREEN}${BOLD}║${NC}  Size   : ${ZIP_SIZE}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📌 Note:${NC} Restart server agar build baru aktif:"
echo -e "   ${CYAN}bash scripts/dev.sh${NC}"
echo ""
echo -e "Client akan otomatis mendeteksi update ini."
echo ""
