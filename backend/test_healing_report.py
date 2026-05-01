import asyncio
import sys
from pathlib import Path

# Tambahkan path backend ke sys.path agar import berhasil
sys.path.insert(0, str(Path(__file__).parent))

from core.self_healing import self_healing_engine, HealingEvent

async def test():
    print("Memulai tes pengiriman laporan Telegram...")
    
    # Cek konfigurasi
    token, chat_id = await self_healing_engine._get_telegram_config()
    if not token or not chat_id:
        print("❌ Gagal: Token Telegram atau Chat ID belum dikonfigurasi!")
        return
    
    print(f"✅ Konfigurasi ditemukan (Chat ID: {chat_id})")

    # Buat dummy event untuk uji coba
    dummy_event = HealingEvent(
        issue_type="permission",
        description="Ini adalah pengujian (Test Notification)",
        action_taken="Sistem berhasil terhubung dengan bot Telegram",
        success=True,
        details="Jika Anda menerima pesan ini, fitur notifikasi berfungsi dengan baik!"
    )
    
    print("Mengirim pesan...")
    # Paksa reset rate limiter (jaga-jaga)
    self_healing_engine._last_report_time = 0.0
    await self_healing_engine._send_report([dummy_event])
    print("✅ Pesan uji coba berhasil dikirim. Silakan cek Telegram Anda!")

if __name__ == "__main__":
    asyncio.run(test())
