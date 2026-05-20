# 🎤 Voice-to-Voice Reply Feature

## Overview

Fitur **Voice-to-Voice Reply** memungkinkan pengguna berinteraksi dengan AI Orchestrator melalui pesan suara di Telegram. Bot akan:

1. **Menerima** pesan suara dari pengguna
2. **Mentranskrip** suara ke teks menggunakan Whisper
3. **Memproses** dengan AI (menggunakan model dari AI Role Mapping)
4. **Mengonversi** jawaban AI ke suara menggunakan edge-tts
5. **Mengirim** balasan dalam bentuk voice note + caption teks

## Flow Diagram

```
User (🎤 Voice Message)
    ↓
Bot download audio file
    ↓
Whisper transcribe → Text
(contoh: "Hei, hari ini cuaca gimana ya?")
    ↓
Text → AI (via Orchestrator)
AI jawab dalam teks
(contoh: "Wah, aku nggak punya akses cuaca real-time nih...")
    ↓
Text → edge-tts → Audio (MP3)
    ↓
Bot reply dengan 🎤 Voice Note + Caption
```

## Konfigurasi

### 1. Aktifkan di `.env`

```bash
# Aktifkan voice reply
VOICE_REPLY_ENABLED=true

# Pilih bahasa voice (default: id)
VOICE_REPLY_LANGUAGE=id
```

### 2. Bahasa yang Didukung

| Kode | Bahasa | Voice Model |
|------|--------|-------------|
| `id` | Indonesia | id-ID-ArdiNeural (Male) |
| `en` | English | en-US-GuyNeural (Male) |
| `ar` | Arabic | ar-SA-HamedNeural (Male) |
| `jp` | Japanese | ja-JP-KeitaNeural (Male) |
| `jv` | Jawa | id-ID-ArdiNeural (fallback) |

### 3. AI Role Mapping (Opsional)

Anda bisa mengatur model AI khusus untuk voice processing di menu **Integrations → AI Roles Mapping**:

- **`multimodal`** - untuk speech-to-text (Gemini/Whisper)
  - **Rekomendasi:** `gemini-2.5-flash` (gratis, cepat, akurat)
  - Alternatif: `gpt-4o`, `groq-whisper-large-v3`
- **`audio_gen`** - untuk text-to-speech (edge-tts)
  - Tidak perlu API key, 100% gratis
- **`general`** atau **`chat`** - untuk pemrosesan teks utama
  - Contoh: `claude-sonnet-4`, `gemini-2.5-flash`

#### Cara Setting Gemini untuk Transcription:

1. Buka **Dashboard → Integrations → AI Roles Mapping**
2. Pada field **`multimodal`**, pilih: `gemini/gemini-2.5-flash`
3. Klik **Save**
4. Selesai! Sekarang voice transcription akan menggunakan Gemini

**Catatan:** Jika tidak diatur, sistem akan menggunakan **Auto-Routing** atau fallback ke OpenAI Whisper (jika tersedia).

## Cara Penggunaan

### Di Telegram

1. Buka chat dengan bot Telegram Anda
2. Tekan tombol **🎤 Record** di Telegram
3. Bicara (contoh: "Halo, siapa kamu?")
4. Kirim voice message
5. Bot akan membalas dengan:
   - **Caption teks** berisi transkripsi + jawaban AI
   - **Voice note** berisi jawaban AI dalam bentuk suara

### Contoh Interaksi

**User (Voice):** "Hei, buatkan saya script Python untuk scraping website"

**Bot Reply:**
```
🎤 Kamu: Hei, buatkan saya script Python untuk scraping website

🤖 Jawaban:
Baik, saya akan buatkan script Python untuk web scraping...
(Lihat voice note untuk jawaban lengkap)

[🎤 Voice Note: 45 detik]
```

## Batasan & Catatan

- **Panjang voice reply:** Maksimal ~1000 karakter (~1 menit audio)
- **Fallback:** Jika TTS gagal, bot akan kirim jawaban dalam bentuk teks
- **Biaya:** 
  - **Gemini 2.5 Flash transcription:** Gratis (dalam free tier Google AI)
  - Whisper (OpenAI): $0.006/menit
  - Groq Whisper: Gratis
  - edge-tts: **100% Gratis, unlimited**
- **Latency:** ~5-15 detik (tergantung panjang audio dan kecepatan AI)

## Troubleshooting

### Voice reply tidak muncul

1. Cek `.env`:
   ```bash
   VOICE_REPLY_ENABLED=true
   ```

2. Restart container:
   ```bash
   docker compose restart backend
   ```

### Audio tidak terdengar

- Pastikan `edge-tts` terinstall:
  ```bash
  pip install edge-tts
  ```

### Transcription gagal

1. **Jika menggunakan Gemini:**
   - Pastikan `GOOGLE_API_KEY` sudah diisi di Integrations
   - Set `AI_ROLE_MULTIMODAL=gemini/gemini-2.5-flash` di AI Roles Mapping
   - Cek log: `docker compose logs backend | grep -i gemini`

2. **Jika menggunakan Whisper:**
   - Pastikan OpenAI API key tersedia
   - Atau gunakan Groq (gratis): set `AI_ROLE_MULTIMODAL=groq/whisper-large-v3`

3. **Cek log umum:**
   ```bash
   docker compose logs backend | grep transcribe
   ```

## Integrasi dengan AI Role Mapping

Sistem ini **otomatis terintegrasi** dengan AI Role Mapping yang sudah ada:

```python
# Di backend/agents/agent_registry.py
def resolve_model_for_agent(agent_type: str) -> str:
    # Priority 1: Manual user setting (AI_ROLE_<TYPE>)
    manual = os.getenv(f"AI_ROLE_{agent_type.upper()}")
    if manual:
        return manual
    
    # Priority 2: Auto-routing (performance cache)
    # Priority 3: Capability map
    # Priority 4: Available models
    # Priority 5: Default model
```

Jadi jika Anda set `AI_ROLE_MULTIMODAL=gpt-4o` di Integrations, maka Whisper akan menggunakan GPT-4o untuk transcription.

## Keamanan & Privacy

- ✅ Audio file **tidak disimpan** di server (langsung diproses dan dihapus)
- ✅ Transkripsi disimpan di database (sama seperti chat teks biasa)
- ✅ Voice reply di-generate on-the-fly (tidak di-cache)
- ✅ Semua komunikasi melalui Telegram API (encrypted)

## Roadmap

- [ ] Support multiple voice models (female, child, etc)
- [ ] Voice emotion detection
- [ ] Real-time streaming TTS
- [ ] Voice cloning (user's own voice)
- [ ] Multi-language auto-detection

---

**Built with ❤️ for AI ORCHESTRATOR v4.1**
