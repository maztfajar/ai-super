# 🚀 Quick Start: Voice-to-Voice dengan Gemini

## Setup dalam 3 Langkah

### 1. Aktifkan Voice Reply di `.env`

```bash
VOICE_REPLY_ENABLED=true
VOICE_REPLY_LANGUAGE=id
```

### 2. Set Gemini untuk Transcription

**Via UI (Recommended):**

1. Buka **Dashboard → Integrations**
2. Pastikan `GOOGLE_API_KEY` sudah terisi
3. Klik tab **AI Roles Mapping**
4. Pada field **`multimodal`**, pilih: `gemini/gemini-2.5-flash`
5. Klik **Save**

**Via `.env` (Alternative):**

```bash
AI_ROLE_MULTIMODAL=gemini/gemini-2.5-flash
```

### 3. Restart Backend

```bash
docker compose restart backend
```

---

## Test di Telegram

1. Buka chat dengan bot Telegram
2. Tekan tombol 🎤 Record
3. Bicara: "Halo, siapa kamu?"
4. Kirim voice message
5. Bot akan balas dengan voice note + caption

---

## Kenapa Gemini?

✅ **Gratis** - Dalam free tier Google AI  
✅ **Cepat** - Latency ~2-5 detik  
✅ **Akurat** - Mendukung 100+ bahasa  
✅ **Multimodal** - Bisa handle audio, video, image  
✅ **No Whisper API** - Tidak perlu OpenAI/Groq  

---

## Troubleshooting

### "Transcription failed"

```bash
# Cek log
docker compose logs backend | grep -i transcribe

# Pastikan Google API Key valid
docker compose logs backend | grep -i google
```

### "Model not found"

Pastikan format model benar:
- ✅ `gemini/gemini-2.5-flash`
- ✅ `gemini-2.5-flash`
- ❌ `gemini-flash` (salah)

### Voice reply tidak muncul

```bash
# Cek setting
docker compose exec backend cat /app/.env | grep VOICE_REPLY

# Restart
docker compose restart backend
```

---

## Flow Lengkap

```
User 🎤 Voice
    ↓
Telegram Bot download audio
    ↓
AI_ROLE_MULTIMODAL = gemini/gemini-2.5-flash
    ↓
Gemini transcribe → Text
    ↓
AI_ROLE_GENERAL/CHAT process text
    ↓
edge-tts → Voice
    ↓
Bot reply 🎤 Voice + Caption
```

---

**Selesai! Sekarang bot Anda bisa voice-to-voice tanpa Whisper API** 🎉
