#!/bin/bash
# ══════════════════════════════════════════════════════════════
# AI SUPER ASSISTANT — Security Patch Installer
# Jalankan dari root direktori project: bash apply_security_patches.sh
# ══════════════════════════════════════════════════════════════

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
BACKEND="./backend"

echo -e "${YELLOW}🔧 Applying security patches...${NC}\n"

# ── Cek apakah di direktori yang benar ───────────────────────
if [ ! -f "$BACKEND/main.py" ]; then
    echo -e "${RED}❌ Error: Jalankan script ini dari root direktori project (yang berisi folder 'backend/')${NC}"
    exit 1
fi

# ── Backup dulu ───────────────────────────────────────────────
BACKUP_DIR=".backup_$(date +%Y%m%d_%H%M%S)"
echo "📦 Membuat backup ke $BACKUP_DIR ..."
mkdir -p "$BACKUP_DIR"
cp "$BACKEND/core/config.py"    "$BACKUP_DIR/"
cp "$BACKEND/api/auth.py"       "$BACKUP_DIR/"
cp "$BACKEND/api/security.py"   "$BACKUP_DIR/"
cp "$BACKEND/db/models.py"      "$BACKUP_DIR/"
cp "$BACKEND/main.py"           "$BACKUP_DIR/"
echo -e "${GREEN}✅ Backup selesai di $BACKUP_DIR${NC}\n"

# ── PATCH 6: Fix datetime.utcnow() deprecated ────────────────
echo "🔧 Patch 6: Memperbaiki datetime.utcnow() yang deprecated..."
for f in "$BACKEND/db/models.py" "$BACKEND/memory/manager.py"; do
    if [ -f "$f" ]; then
        # Tambahkan timezone ke import jika belum ada
        sed -i 's/from datetime import datetime$/from datetime import datetime, timezone/g' "$f"
        # Ganti datetime.utcnow() ke datetime.now(timezone.utc).replace(tzinfo=None)
        sed -i 's/default_factory=datetime\.utcnow/default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)/g' "$f"
        echo "  ✅ $f"
    fi
done

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Semua patch berhasil diaplikasikan!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📋 Langkah selanjutnya:${NC}"
echo "1. Edit file .env dan ganti SECRET_KEY & ADMIN_PASSWORD"
echo "2. Jalankan migrasi database: bash scripts/migrate-db.sh"
echo "3. Restart aplikasi: bash scripts/restart.sh"
echo ""
echo -e "${RED}⚠️  PENTING: Jangan lupa mengganti nilai di .env sebelum restart!${NC}"
