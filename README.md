# 🧠 AI ORCHESTRATOR

Platform AI Self-Hosted dengan **VISION_GATE Engine**, multi-model orchestration, knowledge base RAG, workflow otomatis, integrasi Telegram/WhatsApp, dan keamanan 2FA.

> **Stack:** FastAPI · React · Vite · ChromaDB · Celery · Redis

---

## ✨ Fitur Utama

### 🤖 AI Orchestrator Engine
- **Multi-Model Intelligence** — Otomatis routing ke model terbaik berdasarkan jenis tugas
- **VISION_GATE Engine** — Analisis gambar: objek, aktivitas, situasi, dan konteks
- **Multimodal Chat** — Chat dengan gambar + teks secara bersamaan
- **Smart Routing** — Auto-pilih model untuk coding, analysis, vision, audio, dll.

### 📸 Vision & Image Analysis
- Upload gambar dan dapatkan analisis detail
- Deteksi objek, aktivitas, situasi, dan konteks dalam foto
- OCR (Optical Character Recognition) untuk teks dalam gambar
- Screenshot analysis untuk debugging error

### 🗄️ RAG (Retrieval Augmented Generation)
- Knowledge base dengan vector search (ChromaDB)
- Upload dokumen PDF, DOC, TXT untuk augmentasi AI
- Context-aware responses dengan sumber referensi
- Auto-indexing dan semantic search

### 🔄 Workflow Automation
- Buat workflow otomatis dengan trigger & actions
- Integrasi dengan berbagai platform via webhook
- Scheduled tasks dan background processing (Celery)
- Visual workflow builder

### 📁 Project Management System
- **Smart Project Location** — Auto-deteksi saat pembuatan aplikasi
- **Persistent Storage** — Lokasi proyek tersimpan per session
- **File Browser** — Popup untuk memilih folder penyimpanan
- **Auto-Organization** — Semua file aplikasi tersimpan di lokasi yang sama
- **Security Validation** — Hanya mengizinkan lokasi di user home directory
- **Relative Path Support** — Path relatif otomatis di-resolve ke lokasi proyek

### 📱 Multi-Channel Integration
- **Telegram Bot** — Chat AI langsung di Telegram
- **WhatsApp Integration** — Coming soon
- **Web Interface** — Full-featured web app
- **API Endpoints** — RESTful API untuk integrasi eksternal

### 🔒 Enterprise Security
- Two-Factor Authentication (TOTP + Telegram OTP)
- JWT tokens dengan expiry management
- Brute force protection (5x gagal → kunci 5 menit)
- Multi-level user roles & permissions
- Encrypted data storage

### 📊 Analytics & Monitoring
- Real-time system monitoring
- Usage analytics dan performance metrics
- Agent performance tracking
- System health dashboard
- Log management & rotation

### 🎵 Text-to-Speech (TTS)
- High-quality voice synthesis
- Multiple voice options
- Audio file generation & download

---

## 🆕 Recent Updates (v2.5)

- ✅ **Project Management System** — Auto-deteksi lokasi proyek untuk aplikasi
- ✅ **Enhanced Session Reliability** — Timeout improvements dengan partial responses
- ✅ **Fixed Model Management** — Mencegah deleted models muncul di monitoring
- ✅ **Better Error Recovery** — Increased iterations dan timeout handling
- ✅ **Smart File Organization** — Path relatif otomatis ke lokasi proyek
- ✅ **Improved Code Styling** — Code block background sesuai tema aplikasi

---

## ⚡ Instalasi Cepat

```bash
git clone https://github.com/maztfajar/ai-super.git
cd ai-super
bash install.sh
```

Buka: **http://localhost:7860**

> ⚠️ Saat instalasi, wizard akan meminta username dan password. **Jangan gunakan password lemah.** `SECRET_KEY` akan di-generate otomatis.

---

## 📋 System Requirements

|           | Minimum        | Rekomendasi              |
|-----------|----------------|--------------------------|
| OS        | Ubuntu 20.04+  | Ubuntu 22.04 LTS         |
| RAM       | 2 GB           | 8 GB+ (untuk vision models) |
| CPU       | 2 cores        | 4+ cores                 |
| Storage   | 5 GB           | 20 GB+ (untuk knowledge base) |
| Python    | 3.10+          | 3.11                     |
| Node.js   | 18+            | 20 LTS                   |

---

## 🗂️ Struktur Folder

```
ai-super/
├── backend/                  # FastAPI Python backend
│   ├── api/                  # REST API endpoints
│   │   ├── chat.py           # Chat & multimodal endpoints
│   │   ├── media.py          # Image upload & analysis
│   │   ├── rag.py            # Knowledge base management
│   │   ├── workflow.py       # Workflow automation
│   │   └── tts.py            # Text-to-speech
│   ├── core/                 # Core services
│   │   ├── orchestrator.py   # AI orchestration engine
│   │   ├── model_manager.py  # Multi-model management
│   │   ├── request_preprocessor.py # Intent classification
│   │   └── vision_gate.py    # Image analysis engine
│   ├── db/                   # Database models & migrations
│   └── integrations/         # External integrations
├── frontend/                 # React + Vite frontend
│   └── src/
│       ├── pages/            # Main application pages
│       ├── components/       # Reusable UI components
│       └── hooks/            # React hooks & API calls
├── scripts/                  # Utility scripts
├── data/                     # Static data & configurations
├── .env.example              # Configuration template
├── install.sh                # Script instalasi
├── deploy.sh                 # Script deploy
└── update_and_restart.sh     # Script update & restart
```

---

## ⚙️ Konfigurasi (.env)

Salin `.env.example` ke `.env` lalu sesuaikan:

```bash
cp .env.example .env
nano .env
```

Variabel penting yang **wajib** diisi:

```env
# Nama aplikasi
APP_NAME="AI ORCHESTRATOR"

# WAJIB diganti — generate otomatis oleh install.sh
SECRET_KEY="..."

# Kredensial admin — WAJIB diganti dari default
ADMIN_USERNAME=admin
ADMIN_PASSWORD=password-kuat-anda

# Isi minimal satu AI provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
OLLAMA_HOST=http://localhost:11434  # Gratis, lokal
```

Lihat `.env.example` untuk daftar lengkap semua variabel.

---

## 🚀 Panduan Penggunaan

### 💬 Multimodal Chat dengan Vision
1. Klik tombol **📷 Kamera** untuk upload gambar
2. Ketik pertanyaan tentang gambar tersebut
3. Sistem akan mengaktifkan **VISION_GATE Engine**
4. Dapatkan analisis detail: objek, aktivitas, situasi, konteks

### 📚 Knowledge Base RAG
1. Upload dokumen ke menu **RAG**
2. Sistem akan auto-index dokumen
3. AI akan menggunakan knowledge base untuk jawaban yang lebih akurat
4. Lihat sumber referensi pada setiap jawaban

### 🔄 Workflow Automation
1. Buat workflow baru di menu **Workflow**
2. Set trigger (schedule, webhook, manual)
3. Tambah actions (send message, API call, file operations)
4. Jalankan atau schedule workflow

### 📁 Project Management System
1. Saat minta AI buat aplikasi, sistem otomatis meminta lokasi proyek
2. Popup muncul untuk memilih folder (Desktop, Home, atau custom)
3. Lokasi tersimpan per session chat
4. Semua file aplikasi otomatis tersimpan di lokasi yang sama

### 🤖 Telegram Integration
1. Setup bot token di menu **Integrations**
2. Chat dengan AI langsung di Telegram
3. Support untuk gambar dan dokumen
4. 2FA verification via Telegram

---

## 🛠️ Script Utility

```bash
# Instalasi & Setup
bash install.sh                   # Install semua dependencies
bash scripts/install-rag.sh       # Setup RAG dengan ChromaDB
bash scripts/setup-cloudflare.sh  # Setup Cloudflare tunnel

# Deployment
bash deploy.sh                    # Deploy ke server
bash update_and_restart.sh        # Update kode + restart server

# Service Management
bash scripts/start.sh             # Jalankan aplikasi lengkap
bash scripts/stop.sh              # Hentikan semua services
bash scripts/dev.sh               # Development mode

# Database & Data
bash scripts/migrate-db.sh        # Migrasi database
bash scripts/reindex-rag.sh       # Re-index RAG documents
bash scripts/reset-password.sh    # Reset password darurat

# Maintenance
bash scripts/backup.sh            # Backup data & konfigurasi
bash scripts/cleanup.sh           # Cleanup temporary files
```

---

## 🔧 Troubleshooting

**Gambar tidak bisa diupload**
- Pastikan file < 10MB
- Format yang didukung: JPG, PNG, GIF, WebP
- Cek logs: `tail -f data/logs/ai-orchestrator.log`

**Vision analysis tidak berfungsi**
- Pastikan model vision tersedia (GPT-4o, Gemini, dll)
- Cek API keys di menu **Integrations**
- Lihat status model di dashboard **Monitoring**

**RAG tidak menggunakan knowledge base**
- Pastikan dokumen sudah ter-index
- Cek ChromaDB: `bash scripts/check-rag.sh`
- Re-index jika perlu: `bash scripts/reindex-rag.sh`

**Telegram bot tidak merespon**
- Verify bot token di @BotFather
- Cek webhook URL di menu **Integrations**
- Lihat logs: `tail -f data/logs/ai-orchestrator.log`

Lihat **TROUBLESHOOTING.md** untuk panduan lengkap.

---

## 🔐 Keamanan

- **Brute Force Protection** — 5x gagal login → akun dikunci 5 menit
- **Two-Factor Authentication** — TOTP (Google Authenticator) + Telegram OTP
- **JWT Security** — Token expiry 7 hari dengan refresh mechanism
- **Password Recovery** — via Email / Telegram OTP / Recovery Token
- **Audit Logging** — Semua aktivitas tercatat untuk compliance
- **Role-Based Access** — Multi-level permissions system

---

## 🤝 Contributing

1. Fork repository
2. Buat feature branch: `git checkout -b feature/nama-fitur`
3. Commit changes: `git commit -am 'feat: deskripsi singkat'`
4. Push ke branch: `git push origin feature/nama-fitur`
5. Buat Pull Request

---

## 🆘 Support

- **Issues** — Buat issue di GitHub repository
- **Dokumentasi** — Lihat `TROUBLESHOOTING.md`

---

## 📄 License

Copyright (c) 2026 maztfajarwahyudi. All rights reserved.

Source code ini dilisensikan untuk keperluan **viewing only**.  
Anda **tidak diizinkan** untuk menggunakan, menyalin, memodifikasi, mendistribusikan, atau menjual kode ini tanpa izin tertulis dari pemilik.

---

*AI ORCHESTRATOR v2.5 — Self-Hosted AI Platform with Vision & Multimodal Intelligence*  
*Built with ❤️ using FastAPI, React, and cutting-edge AI models*
