#!/bin/bash
# AI ORCHESTRATOR — Database Migration Script
# Usage: bash scripts/migrate-db.sh

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="$DIR/backend/data/ai-orchestrator.db"

echo "📂 Folder: $DIR"
echo "🗄️  Database: $DB"

if [ ! -f "$DB" ]; then
  echo "❌ Database tidak ditemukan: $DB"
  exit 1
fi

echo "🔧 Menjalankan migrasi..."

cd "$DIR/backend"
source venv/bin/activate 2>/dev/null || true

python3 << PYEOF
import sqlite3, os

db_path = "$DB"
conn = sqlite3.connect(db_path)
cur  = conn.cursor()

cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]
print("  Kolom saat ini: " + ", ".join(cols))

added = []
migrations = [
    ("role",             "TEXT DEFAULT 'admin'"),
    ("totp_secret",      "TEXT"),
    ("totp_enabled",     "INTEGER DEFAULT 0"),
    ("telegram_chat_id", "TEXT"),
]

for col, defval in migrations:
    if col not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN " + col + " " + defval)
        added.append(col)
        print("  + Kolom '" + col + "' ditambahkan")

cur.execute("UPDATE users SET role='admin'    WHERE is_admin=1 AND (role IS NULL OR role='')")
cur.execute("UPDATE users SET role='subadmin' WHERE is_admin=0 AND (role IS NULL OR role='')")
conn.commit()
conn.close()

if added:
    print("")
    print("Selesai: " + ", ".join(added) + " ditambahkan")
else:
    print("")
    print("Semua kolom sudah ada, tidak ada perubahan")
PYEOF
