# 🧠 AI ORCHESTRATOR — AI ORCHESTRATOR

Platform AI Self-Hosted dengan **VISION_GATE Engine**, multi-model orchestration, knowledge base RAG, workflow otomatis, integrasi Telegram/WhatsApp, dan keamanan 2FA.

---

## ✨ Fitur Utama

### 🤖 **AI ORCHESTRATOR Engine**
- **Multi-Model Intelligence**: Otomatis routing ke model terbaik berdasarkan tugas
- **VISION_GATE Engine**: Analisis gambar lengkap - objek, aktivitas, situasi, konteks
- **Multimodal Chat**: Chat dengan gambar + teks secara bersamaan
- **Smart Routing**: Auto-pilih model untuk coding, analysis, vision, audio, dll.

### 📸 **Vision & Image Analysis**
- Upload gambar dan dapatkan analisis detail
- Deteksi objek, aktivitas, situasi, dan konteks dalam foto
- OCR (Optical Character Recognition) untuk teks dalam gambar
- Screenshot analysis untuk debugging error

### 🗄️ **RAG (Retrieval Augmented Generation)**
- Knowledge base dengan vector search
- Upload dokumen PDF, DOC, TXT untuk augmentasi AI
- Context-aware responses dengan sumber referensi
- Auto-indexing dan semantic search

### 🔄 **Workflow Automation**
- Buat workflow otomatis dengan trigger & actions
- Integrasi dengan berbagai platform
- Scheduled tasks dan background processing
- Visual workflow builder

### � **Project Management System**
- **Smart Project Location**: Auto-deteksi saat pembuatan aplikasi
- **Persistent Storage**: Lokasi proyek tersimpan per session
- **File Browser**: Popup untuk memilih folder penyimpanan
- **Auto-Organization**: Semua file aplikasi tersimpan di lokasi yang sama
- **Security Validation**: Hanya允许 lokasi di user home directory
- **Relative Path Support**: Path relatif otomatis di-resolve ke lokasi proyek

### � **Multi-Channel Integration**
- **Telegram Bot**: Chat AI langsung di Telegram
- **WhatsApp Integration**: Coming soon
- **Web Interface**: Full-featured web app
- **API Endpoints**: RESTful API untuk integrasi

### 🔒 **Enterprise Security**
- Two-Factor Authentication (TOTP + Telegram OTP)
- JWT tokens dengan expiry management
- Brute force protection
- Multi-level user roles & permissions
- Encrypted data storage

### 📊 **Analytics & Monitoring**
- Real-time system monitoring
- Usage analytics dan performance metrics
- Agent performance tracking
- System health dashboard
- Log management & rotation
- **Enhanced Session Management**: Persistent session dengan project location
- **Improved Error Recovery**: Better timeout handling dengan partial responses
- **Model Management**: Fixed deleted model appearing in monitoring

### 🎵 **Text-to-Speech (TTS)**
- High-quality voice synthesis
- Multiple voice options
- Audio file generation & download

---

## ⚡ Instalasi Cepat

```bash
cd ai-orchestrator
bash scripts/install.sh
bash scripts/start.sh
```

Buka: **http://localhost:7860**  
Login default: `admin` / `admin`

> ⚠️ Segera ganti password default setelah login pertama!

---

## 📋 System Requirements

| | Minimum | Rekomendasi |
|---|---|---|
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| RAM | 2 GB | 8 GB+ (untuk vision models) |
| CPU | 2 cores | 4+ cores |
| Storage | 5 GB | 20 GB+ (untuk knowledge base) |
| Python | 3.10+ | 3.11 |
| Node.js | 18+ | 20 LTS |

---

## 🗂️ Struktur Folder

```
ai-orchestrator/
├── backend/          # FastAPI Python backend
│   ├── api/          # REST API endpoints
│   │   ├── chat.py           # Chat & multimodal endpoints
│   │   ├── media.py          # Image upload & analysis
│   │   ├── rag.py            # Knowledge base management
│   │   ├── workflow.py       # Workflow automation
│   │   ├── tts.py            # Text-to-speech
│   │   └── ...
│   ├── core/         # Core services
│   │   ├── orchestrator.py   # AI orchestration engine
│   │   ├── model_manager.py  # Multi-model management
│   │   ├── request_preprocessor.py # Intent classification
│   │   └── vision_gate.py    # Image analysis engine
│   ├── db/           # Database models & migrations
│   ├── data/         # Persistent data (auto-created)
│   │   ├── chroma_db/        # Vector database
│   │   └── uploads/          # User uploads
│   └── integrations/ # External integrations
├── frontend/         # React + Vite frontend
│   ├── src/
│   │   ├── pages/    # Main application pages
│   │   │   ├── Chat.jsx      # Multimodal chat interface
│   │   │   └── ...
│   │   ├── components/       # Reusable UI components
│   │   └── hooks/            # React hooks & API calls
│   └── public/
├── scripts/          # Utility scripts
│   ├── install.sh            # Full installation
│   ├── start.sh              # Start all services
│   ├── stop.sh               # Stop all services
│   ├── migrate-db.sh         # Database migrations
│   ├── reset-password.sh     # Emergency password reset
│   └── ...
├── data/             # Static data & configurations
│   ├── ai_core_prompt.md     # AI orchestrator personality
│   ├── capability_map.json   # Model capabilities mapping
│   └── ...
├── .env.example      # Configuration template
└── README.md
```

---

## ⚙️ Konfigurasi (.env)

```env
# Basic Configuration
APP_NAME=AI ORCHESTRATOR    # Nama tampil di sidebar
SECRET_KEY=random-32-chars    # WAJIB diganti untuk keamanan
ADMIN_USERNAME=admin
ADMIN_PASSWORD=passwordbaru

# AI Providers (isi minimal satu)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
SUMOPOD_API_KEY=sk-...
OLLAMA_HOST=http://localhost:11434

# Vision Models (untuk VISION_GATE)
VISION_MODEL=gpt-4o            # OpenAI GPT-4 Vision
# VISION_MODEL=gemini-2.5-flash # Google Gemini Vision
# VISION_MODEL=sumopod/mimo-v2-omni # Sumopod Vision

# Database
DATABASE_URL=sqlite:///./data/app.db

# SMTP untuk reset password via email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=email@gmail.com
SMTP_PASS=app-password

# Telegram Bot (untuk 2FA & notifications)
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=123456789

# RAG Configuration
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
RAG_EMBEDDING_MODEL=text-embedding-3-small

# Workflow
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## 🚀 Panduan Penggunaan

### 💬 **Multimodal Chat dengan Vision**
1. Klik tombol **📷 Kamera** untuk upload gambar
2. Ketik pertanyaan tentang gambar tersebut
3. Sistem akan mengaktifkan **VISION_GATE Engine**
4. Dapatkan analisis detail: objek, aktivitas, situasi, konteks

### 📚 **Knowledge Base RAG**
1. Upload dokumen ke **RAG** menu
2. Sistem akan auto-index dokumen
3. AI akan menggunakan knowledge base untuk jawaban yang lebih akurat
4. Lihat sumber referensi pada setiap jawaban

### 🔄 **Workflow Automation**
1. Buat workflow baru di menu **Workflow**
2. Set trigger (schedule, webhook, manual)
3. Tambah actions (send message, API call, file operations)
4. Jalankan atau schedule workflow

### 📁 **Project Management System**
1. **Auto-Detection**: Saat minta AI buat aplikasi, sistem otomatis meminta lokasi proyek
2. **Location Selection**: Popup muncul untuk memilih folder penyimpanan (Desktop, Home, atau custom)
3. **Persistent Storage**: Lokasi tersimpan per session chat
4. **Smart File Organization**: Semua file aplikasi otomatis tersimpan di lokasi yang sama
5. **Security**: Hanya允许 lokasi di user home directory untuk keamanan

**Contoh Penggunaan:**
```
User: "Buat aplikasi React dengan login system"
Sistem: 📁 Pilih lokasi proyek:
       • 🏠 Folder Home  
       • 🖥️ Desktop
       • 📂 Custom folder
       
Output: 📁 Project Location: /home/user/Desktop
       ✓ Successfully wrote to src/App.jsx
       ✓ Successfully wrote to src/Login.jsx
```

### 🤖 **Telegram Integration**
1. Setup bot token di **Integrations** menu
2. Chat dengan AI langsung di Telegram
3. Support untuk gambar dan dokumen
4. 2FA verification via Telegram

---

## 🛠️ Script Utility

```bash
# Installation & Setup
bash scripts/install.sh           # Install semua dependencies
bash scripts/install-rag.sh       # Setup RAG dengan ChromaDB
bash scripts/setup-cloudflare.sh  # Setup Cloudflare tunnel

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
bash scripts/update.sh            # Update aplikasi
```

---

## 🔧 Troubleshooting

### Gambar Tidak Bisa Diupload
- Pastikan file < 10MB
- Format yang didukung: JPG, PNG, GIF, WebP
- Check logs: `tail -f logs/app.log`

### Vision Analysis Tidak Berfungsi
- Pastikan model vision tersedia (GPT-4o, Gemini, dll)
- Check API keys di menu **Integrations**
- Lihat status model di **Monitoring** dashboard

### RAG Tidak Menggunakan Knowledge Base
- Pastikan dokumen sudah ter-index
- Check ChromaDB status: `bash scripts/check-rag.sh`
- Re-index jika perlu: `bash scripts/reindex-rag.sh`

### Telegram Bot Tidak Merespon
- Verify bot token di @BotFather
- Check webhook URL di **Integrations**
- Lihat logs Telegram: `tail -f logs/telegram.log`

Lihat **TROUBLESHOOTING.md** untuk panduan lengkap.

---

## 📖 Dokumentasi Lengkap

Lihat file **AI ORCHESTRATOR_Dokumentasi.docx** untuk panduan lengkap:
- Instalasi step-by-step dengan screenshots
- Konfigurasi semua fitur (Vision, RAG, Workflow)
- Panduan setiap menu dan fitur
- Setup 2FA & enterprise security
- API documentation untuk developers
- Troubleshooting guide lengkap

---

## 🔐 Keamanan & Compliance

- **Brute Force Protection**: 5x gagal login → kunci 5 menit
- **Two-Factor Authentication**: TOTP (Google Authenticator) + Telegram OTP
- **API Rate Limiting**: Redis-backed rate limiting (30 requests/min) untuk endpoint chat
- **Network Security**: Smart CORS Middleware dinamis & JWT Expiry ketat (24 jam)
- **Agent Sandbox**: Eksekusi perintah bash dibatasi regex multi-layer, pemblokiran path absolut berbahaya (mis. `/etc/shadow`)
- **System Hardening**: Auto-chmod 600 untuk `.env` dan log, filter masking Token Telegram pada log
- **Secure OTA Updates**: Verifikasi SSL wajib, pencegahan RCE & Zip Slip, limit ukuran update 200MB

---

## 🤝 Contributing

1. Fork repository
2. Buat feature branch: `git checkout -b feature/nama-fitur`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push ke branch: `git push origin feature/nama-fitur`
5. Buat Pull Request

---

## 📄 License

**All Rights Reserved.** This project is proprietary and closed-source. See the `LICENSE` file for details.

---

## 🆘 Support

- **Issues**: Buat issue di GitHub repository
- **Documentation**: Baca TROUBLESHOOTING.md
- **Community**: Join our Telegram group (link di dokumentasi)

---

## Copyright & Legal

Copyright (c) 2026 maztfajarwahyudi. All rights reserved.

This source code is licensed strictly for viewing purposes only. You may not use, copy, modify, merge, publish, distribute, sublicense, or sell copies of the Software without explicit written permission from the author. Any unauthorized use, reproduction, or distribution is strictly prohibited and may result in severe civil and criminal penalties.


*AI ORCHESTRATOR v2.1 — Self-Hosted AI Assistant with Vision & Multimodal Intelligence*  
*Built with ❤️ using FastAPI, React, and cutting-edge AI models*

## 🆕 **Recent Updates (v2.4)**
- 🧠 **Mandatory Planning Phase**: AI Orchestrator kini diwajibkan melakukan fase perencanaan (Arsitektur, Dependencies, Integrasi, & DoD) sebelum menulis kode aplikasi.
- ⚙️ **App Verification Loop**: Proses pre-flight check otomatis (status server, port, HTTP, log) sebelum aplikasi ditampilkan ke *user*.
- 👁️ **Aggressive Context Injection**: AI secara agresif mendeteksi daftar file dan status port yang berjalan secara real-time agar tidak menulis ulang file secara redundan.
- 🛡️ **Smart Error Hinting**: Analisis & injeksi *hint* otomatis pada `<observation>` untuk error umum (mis. `EADDRINUSE`, `ENOENT`, `SyntaxError`) agar AI langsung tahu cara memperbaikinya.
- ✅ **Strict Quality Standards**: Standarisasi mutu aplikasi (*responsive, error handling, CORS, deployment check*) sebagai *Definition of Done* pasti bagi AI.
- ♻️ **Token Efficiency via File Cache**: Aturan cache file di memori AI untuk mencegah pembacaan `read_file` berulang-ulang, sangat menghemat pemakaian *token*.

## 🆕 **Previous Updates (v2.3)**
- 🧠 **Procedural Memory**: AI kini otomatis menyimpan "Buku Resep" dari tugas-tugas sukses sebelumnya untuk mempercepat pengerjaan tugas serupa.
- ♻️ **Self-Correction Loop**: Validasi otomatis di *sandbox* internal. AI mengoreksi error kode atau logika sendiri sebelum memberikannya ke pengguna.
- 👁️ **Project-Wide Awareness**: Fitur `ProjectIndexer` yang membaca seluruh struktur kode di latar belakang, membuat AI jauh lebih paham keterkaitan antar-file.
- 🎯 **Optimized Core Routing**: Peralihan mesin pengambil keputusan (Router, Voting, Decomposer) agar secara *native* mendukung model andalan seperti `deepseek-v3-2`, `qwen3.6-flash`, dan `gemini-2.5-flash-lite`.

## 🆕 **Previous Updates (v2.2)**
- 🔒 **Enterprise Security Hardening**: Smart CORS, Zip Slip protection, Rate Limiting API, Regex Agent Sandboxing.
- 🧠 **Context-Aware Preprocessor**: Router pesan AI kini membaca konteks riwayat percakapan secara cerdas.
- 🛡️ **Telegram Watchdog**: Sistem *auto-restart* di *background* untuk mencegah bot Telegram berhenti merespons secara diam-diam.
- ✅ **Project Management System**: Auto-deteksi lokasi proyek untuk aplikasi.
- ✅ **Enhanced Session Reliability**: Timeout improvements dengan partial responses.
- ✅ **Smart File Organization**: Path relatif otomatis ke lokasi proyek.
