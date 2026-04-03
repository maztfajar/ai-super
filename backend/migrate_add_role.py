"""
Migration: tambah kolom 'role' ke tabel users
Jalankan sekali: python migrate_add_role.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "ai-super-assistant.db"

if not DB_PATH.exists():
    print(f"Database tidak ditemukan di {DB_PATH}")
    exit(1)

conn = sqlite3.connect(str(DB_PATH))
cur  = conn.cursor()

# Cek apakah kolom role sudah ada
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]

if 'role' in cols:
    print("✓ Kolom 'role' sudah ada, tidak perlu migrasi")
else:
    cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'admin'")
    # Set role berdasarkan is_admin
    cur.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")
    cur.execute("UPDATE users SET role = 'subadmin' WHERE is_admin = 0")
    conn.commit()
    print("✓ Kolom 'role' berhasil ditambahkan dan diisi")

conn.close()
print("✓ Migrasi selesai")
