#!/bin/bash
# ============================================================
#  PostgreSQL Setup for AI ORCHESTRATOR
#  Usage: bash scripts/setup_pg.sh
# ============================================================

set -e

# Configuration (sesuai implementation plan)
DB_NAME="ai_orchestrator_db"
DB_USER="ai_orchestrator"
DB_PASS="admin"

echo "🐘 Menyiapkan PostgreSQL untuk AI Orchestrator..."

# 1. Pastikan service berjalan
if command -v systemctl &>/dev/null; then
    echo "⚙️ Memastikan PostgreSQL service aktif..."
    sudo systemctl start postgresql || true
    sudo systemctl enable postgresql || true
fi

# 2. Setup User dan Database
# Kami menggunakan sudo -u postgres untuk menjalankan psql
echo "🔑 Membuat user dan database (memerlukan izin sudo)..."

sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || echo "⚠️ User $DB_USER mungkin sudah ada."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "⚠️ Database $DB_NAME mungkin sudah ada."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "✅ PostgreSQL Setup selesai!"
echo "📍 DB Name: $DB_NAME"
echo "👤 DB User: $DB_USER"
echo "============================================================"
