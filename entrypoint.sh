#!/bin/bash
# ============================================================
# AI ORCHESTRATOR — Docker Entrypoint
# Auto-generates .env with safe defaults if not mounted by user
# ============================================================

ENV_FILE="/app/.env"
ENV_DEFAULT="/app/.env.default"

# ── Auto-generate .env if not mounted / empty ──────────────
if [ ! -s "$ENV_FILE" ] || grep -q "GANTI-INI" "$ENV_FILE" 2>/dev/null; then
    echo "============================================================"
    echo "  AI ORCHESTRATOR — First-run setup"
    echo "============================================================"

    # Generate a random SECRET_KEY
    GENERATED_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # Copy default template and inject the generated secret
    cp "$ENV_DEFAULT" "$ENV_FILE"
    sed -i "s|SECRET_KEY=__AUTO_GENERATED__|SECRET_KEY=${GENERATED_SECRET}|g" "$ENV_FILE"

    echo ""
    echo "  ✅ File .env berhasil dibuat secara otomatis."
    echo ""
fi

# ── Baca kredensial aktif dari .env yang berlaku ───────────
ACTIVE_USER=$(grep -m1 "^ADMIN_USERNAME=" "$ENV_FILE" | cut -d= -f2 | tr -d '"' | tr -d "'")
ACTIVE_PASS=$(grep -m1 "^ADMIN_PASSWORD=" "$ENV_FILE" | cut -d= -f2 | tr -d '"' | tr -d "'")
ACTIVE_USER="${ACTIVE_USER:-admin}"
ACTIVE_PASS="${ACTIVE_PASS:-admin123}"

echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │         KREDENSIAL LOGIN DEFAULT         │"
echo "  │                                          │"
printf "  │  Username : %-28s│\n" "$ACTIVE_USER"
printf "  │  Password : %-28s│\n" "$ACTIVE_PASS"
echo "  │                                          │"
echo "  │  ⚠️  Ganti password setelah login!       │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  Buka browser: http://localhost:7860"
echo "  (Password di-sync otomatis dari .env setiap restart)"
echo "============================================================"

# ── Run the application ─────────────────────────────────────
exec python backend/main.pyc
