#!/bin/bash

# ============================================================
# AI ORCHESTRATOR — Reset Admin Login Script
# Gunakan skrip ini jika Anda terkunci dari halaman login atau
# lupa password admin. Skrip ini akan:
# 1. Menghapus rate limit (blokir) di Redis
# 2. Mereset password admin menjadi "123456"
# 3. Menghapus status "terkunci" di database
# ============================================================

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$APP_DIR/backend/venv/bin/python3"

echo "Mereset akses login admin..."

"$VENV_PYTHON" -c "
import sqlite3, bcrypt, redis
import os

# 1. Hapus Blokir Rate Limit dari Redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.delete('login:count:user:admin', 'login:lockout:user:admin')
    print('✅ Blokir Rate Limit berhasil dihapus dari Redis.')
except Exception as e:
    print('⚠️ Gagal koneksi ke Redis (Abaikan jika Redis tidak dipakai):', e)

# 2. Reset Password & Buka Blokir di Database Utama
db_path = '$APP_DIR/data/ai-orchestrator.db'

if not os.path.exists(db_path):
    print(f'❌ Database tidak ditemukan di: {db_path}')
    exit(1)

try:
    db = sqlite3.connect(db_path)
    c = db.cursor()
    salt = bcrypt.gensalt()
    # Hash password default: 123456
    hashed = bcrypt.hashpw('123456'.encode('utf-8'), salt).decode('utf-8')
    
    c.execute('UPDATE users SET failed_attempts = 0, locked_until = NULL, totp_enabled = 0, hashed_password = ? WHERE username = ?', (hashed, 'admin'))
    
    if c.rowcount == 0:
        print('⚠️ User admin tidak ditemukan di database!')
    else:
        db.commit()
        print('✅ Password admin berhasil direset menjadi: 123456')
        
    db.close()
except Exception as e:
    print('❌ Gagal update database:', e)
"

echo "============================================================"
echo "Selesai! Silakan login dengan username: admin | password: 123456"
echo "============================================================"
