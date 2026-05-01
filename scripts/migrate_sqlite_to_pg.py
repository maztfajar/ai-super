import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, inspect
from pathlib import Path

# Fix: Resolve absolute path ke SQLite secara manual
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
SQLITE_PATH = BACKEND_DIR / "data" / "ai-orchestrator.db"

def migrate():
    # 1. Konfigurasi Database (Driver SYNCHRONOUS)
    if not SQLITE_PATH.exists():
        print(f"❌ File SQLite tidak ditemukan di: {SQLITE_PATH}")
        sys.exit(1)
        
    sqlite_url = f"sqlite:///{SQLITE_PATH}"
    pg_url = "postgresql://ai_orchestrator:admin@localhost/ai_orchestrator_db"
    
    print(f"🔄 Memulai migrasi data...")
    print(f"📥 Source: {sqlite_url}")
    print(f"📤 Target: {pg_url}")
    
    try:
        sqlite_engine = create_engine(sqlite_url)
        pg_engine = create_engine(pg_url)
        pg_inspector = inspect(pg_engine)
        
        # 2. Ambil daftar tabel
        metadata = MetaData()
        metadata.reflect(bind=sqlite_engine)
        tables = list(metadata.tables.keys())
        
        if not tables:
            print("⚠️ Tidak ada tabel yang ditemukan di database SQLite.")
            return

        print(f"📋 Ditemukan {len(tables)} tabel: {', '.join(tables)}")
        
        # 3. Migrasi tabel demi tabel
        for table_name in tables:
            print(f"⏳ Migrasi tabel: {table_name}...")
            
            try:
                # Baca data dari SQLite
                df = pd.read_sql_table(table_name, sqlite_engine)
                
                if df.empty:
                    print(f"   ℹ️  Tabel {table_name} kosong, melewati.")
                    continue
                
                # Bersihkan atau siapkan tabel target
                with pg_engine.connect() as conn:
                    # FIX: Gunakan inspect(engine).has_table() untuk SQLAlchemy 2.0+
                    if pg_inspector.has_table(table_name):
                        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE;"))
                        conn.commit()
                
                # Tulis ke PostgreSQL
                df.to_sql(table_name, pg_engine, if_exists='append', index=False)
                print(f"   ✅ Berhasil memindahkan {len(df)} baris.")
            except Exception as table_err:
                print(f"   ❌ Gagal memindahkan tabel {table_name}: {table_err}")
            
        print("\n🎉 Migrasi data SELESAI dengan sukses!")
        print("🚀 Sekarang Anda bisa merestart aplikasi: ./update_and_restart.sh")
        
    except Exception as e:
        print(f"❌ Error sistem saat migrasi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
