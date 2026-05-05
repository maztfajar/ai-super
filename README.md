# 🧠 AI ORCHESTRATOR

Platform AI Self-Hosted dengan **VISION_GATE Engine**, multi-model orchestration, knowledge base RAG, workflow otomatis, integrasi Telegram/WhatsApp, dan keamanan 2FA — kini diperkuat dengan **10 Autonomous Skills** yang bekerja bersama sebagai tim digital.

> **Stack:** FastAPI · React · Vite · ChromaDB · SQLite WAL · Playwright

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
- Scheduled tasks dan background processing
- Visual workflow builder

### 📁 Project Management System
- **Smart Project Location** — Auto-deteksi saat pembuatan aplikasi
- **Persistent Storage** — Lokasi proyek tersimpan per session
- **File Browser** — Popup untuk memilih folder penyimpanan
- **Auto-Organization** — Semua file aplikasi tersimpan di lokasi yang sama
- **Security Validation** — Hanya mengizinkan lokasi di user home directory

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

## 🚀 Autonomous Skills Suite

AI Orchestrator dilengkapi **10 Autonomous Skills** yang terbagi dalam dua kategori. Setiap skill bekerja di belakang layar secara otomatis, **tanpa perlu konfigurasi tambahan**.

### 🔧 Background Skills (Selalu Aktif)

Skill-skill ini berjalan otomatis, mengoptimasi setiap interaksi tanpa perlu intervensi pengguna.

| # | Skill | Fungsi | Status |
|---|-------|--------|--------|
| 1 | ⚡ **QMD — The Token Killer** | Menghemat biaya API hingga 80% dengan hanya mengambil potongan teks paling relevan dari history percakapan panjang sebelum dikirim ke AI | 🟢 Selalu Aktif |
| 2 | 🧠 **Capability Evolver** | Self-improvement otomatis — menganalisis 200 record eksekusi terakhir setiap 30 menit dan menghasilkan aturan routing model yang lebih optimal | 🟢 Selalu Aktif |
| 3 | ✍️ **Humanizer (Anti AI Slop)** | Mendeteksi pola bahasa mesin (kata dramatis berlebihan, struktur terlalu rapi) dan mengubahnya menjadi gaya tulisan yang lebih natural dan kasual | 🟢 Selalu Aktif |
| 4 | 🧭 **Byte Rover (Long-term Memory)** | Memori jangka panjang — secara otomatis merangkum sesi chat yang idle lalu menyimpannya ke Vector DB, sehingga AI tetap mengingat konteks proyek lama di sesi baru | 🟢 Selalu Aktif |
| 5 | 🏛️ **Command Center** | Pusat koordinasi multi-agent — mengelola eksekusi paralel beberapa AI agent sekaligus dan menyiarkan status sinkronisasi secara real-time ke antarmuka | 🟢 Selalu Aktif |

### 🛠️ On-Demand Skills (Diaktifkan AI Saat Dibutuhkan)

Skill-skill ini dijalankan secara otonom oleh AI ketika tugas membutuhkannya.

| # | Skill | Fungsi | Cara Pakai |
|---|-------|--------|------------|
| 6 | 🌐 **Browser Automation** | Membuka website, mengklik tombol, mengisi form, mengekstrak teks, hingga mengambil screenshot secara headless via Chromium | Perintahkan AI: *"Buka website X dan ambil datanya"* |
| 7 | 📄 **QMD Distillation** | Distilasi context berbasis relevansi semantik untuk tugas multi-subtask yang kompleks | Aktif otomatis saat task complex |
| 8 | 🟢 **GOG CLI — Google Ecosystem** | Kendali penuh ekosistem Google: baca & kirim Gmail, buat event Calendar, baca & tulis Google Sheets, cari file di Drive — semua melalui satu instruksi | Perintahkan AI: *"Cek email baru dari bos saya"* |

---

## 🟢 GOG CLI — Panduan Setup Google Ecosystem

Skill ini membutuhkan otorisasi sekali klik via Google OAuth 2.0.

1. Buka **Google Cloud Console** → buat project baru
2. Aktifkan API: `Gmail`, `Calendar`, `Sheets`, `Drive` di menu Library
3. Buat `OAuth 2.0 Client ID` (tipe: **Desktop App**) → Download JSON
4. Buka menu **Integrations → Tab Google** di aplikasi
5. Tempel isi `credentials.json` → klik **"Otorisasi dengan Google"**
6. Login di popup → salin Authorization Code → selesai 🎉

**Contoh perintah setelah terhubung:**
```
"Cek email baru dari bos saya"
"Jadwalkan meeting besok jam 10 pagi"
"Tambahkan data ini ke Google Sheets kolom A"
"Carikan file laporan Q1 di Drive saya"
```

---

## 🆕 Versi & Changelog

### v3.0 (Terkini) — Autonomous Skills Suite
- ✅ **Byte Rover** — Long-term memory engine berbasis ChromaDB RAG
- ✅ **Command Center** — Koordinator multi-agent paralel dengan real-time UI
- ✅ **Browser Automation** — Playwright headless Chromium untuk otomasi web
- ✅ **GOG CLI** — Integrasi penuh Gmail, Calendar, Sheets, Drive via OAuth 2.0
- ✅ **Dashboard Update** — Semua 8 skill kini terpantau di halaman Pemantauan AI

### v2.5
- ✅ **QMD — The Token Killer** — Distilasi context berbasis relevansi semantik
- ✅ **Capability Evolver** — Sistem self-improvement otomatis berbasis data eksekusi
- ✅ **Humanizer (Anti AI Slop)** — Pemoles bahasa output AI agar lebih natural
- ✅ **Migrasi SQLite WAL** — Zero-config database dengan performa tinggi

### v2.0
- ✅ **Project Management System** — Auto-deteksi lokasi proyek untuk aplikasi
- ✅ **Enhanced Session Reliability** — Timeout improvements dengan partial responses
- ✅ **Fixed Model Management** — Mencegah deleted models muncul di monitoring
- ✅ **Better Error Recovery** — Increased iterations dan timeout handling

---

## ⚡ Instalasi Cepat

```bash
git clone https://github.com/maztfajar/ai-super.git
cd ai-super
bash install.sh
```

Buka: **http://localhost:7860**

> ⚠️ Saat instalasi, wizard akan meminta username dan password admin. **Jangan gunakan password lemah.** `SECRET_KEY` akan di-generate otomatis.

---

## 📋 System Requirements

|           | Minimum        | Rekomendasi              |
|-----------|----------------|--------------------------| 
| OS        | Ubuntu 20.04+  | Ubuntu 22.04 LTS         |
| RAM       | 2 GB           | 8 GB+ (untuk vision models) |
| CPU       | 2 cores        | 4+ cores                 |
| Storage   | 5 GB           | 20 GB+ (untuk knowledge base & memory) |
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
│   │   ├── integrations.py   # OAuth & platform integrations
│   │   └── tts.py            # Text-to-speech
│   ├── core/                 # Core services & skills
│   │   ├── orchestrator.py   # AI orchestration engine
│   │   ├── model_manager.py  # Multi-model management
│   │   ├── request_preprocessor.py # Intent classification
│   │   ├── vision_gate.py    # Image analysis engine
│   │   ├── qmd.py            # ⚡ QMD — The Token Killer
│   │   ├── capability_evolver.py # 🧠 Self-improvement engine
│   │   ├── humanizer.py      # ✍️ Anti AI Slop filter
│   │   ├── byte_rover.py     # 🧭 Long-term Memory engine
│   │   └── command_center.py # 🏛️ Multi-agent coordinator
│   ├── agents/               # Agent system
│   │   ├── agent_registry.py # Agent capabilities & skills
│   │   ├── executor.py       # Agent task executor
│   │   └── tools/            # Tool registry
│   │       ├── core_tools.py        # Shell, file, model tools
│   │       ├── browser_automation.py # 🌐 Playwright browser tools
│   │       └── google_tools.py      # 🟢 GOG CLI Google tools
│   ├── rag/                  # RAG engine (ChromaDB)
│   ├── db/                   # Database models & migrations
│   └── integrations/         # External integrations
├── frontend/                 # React + Vite frontend
│   └── src/
│       ├── pages/            # Main application pages
│       │   ├── Integrations.jsx  # Includes Google OAuth setup UI
│       │   ├── Monitoring.jsx    # Skill status dashboard
│       │   └── ...
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
SUMOPOD_API_KEY=...                 # Provider utama (recommended)

# Opsional: Telegram Bot
TELEGRAM_BOT_TOKEN=...
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

### 🧭 Byte Rover (Long-term Memory)
1. Tidak perlu setup! Bekerja otomatis setiap 1 jam
2. Sesi chat yang tidak aktif >1 jam akan dirangkum secara otomatis
3. Ringkasan tersimpan ke Vector DB (ChromaDB)
4. Di sesi baru, AI otomatis "mengingat" proyek & konteks lama

### 🌐 Browser Automation
```
"Tolong buka google.com dan cari berita AI terbaru"
"Buka website kompetitor dan ambil daftar produk mereka"
"Screenshot tampilan website X dan analisis UI-nya"
```

### 🟢 GOG CLI — Google Ecosystem
Setup sekali di menu **Integrations → Tab Google**, lalu cukup perintahkan:
```
"Cek email baru hari ini"
"Jadwalkan rapat review project besok jam 14:00"
"Tulis hasil rapat ini ke Sheet laporan bulan Mei"
"Carikan proposal yang saya simpan di Drive bulan lalu"
```

### 🏛️ Command Center
Otomatis aktif saat AI perlu menjalankan beberapa tugas paralel:
```
"Sekaligus riset tentang FastAPI DAN buatkan artikel blog-nya"
→ Command Center akan mendeploy Research Agent & Writer Agent secara bersamaan
```

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

**Browser Automation tidak berjalan**
- Pastikan Playwright sudah terinstall: `playwright install chromium`
- Cek apakah VPS mendukung headless browser
- Pastikan Chromium binary tersedia

**GOG CLI tidak bisa connect ke Google**
- Pastikan OAuth 2.0 Client ID sudah dibuat dengan tipe Desktop App
- Aktifkan semua API yang diperlukan di Google Cloud Console
- Klik "Putuskan Koneksi" lalu otorisasi ulang jika token expired

**Byte Rover tidak merangkum sesi**
- Memory engine bekerja otomatis setiap 1 jam untuk sesi idle
- Pastikan RAG Engine aktif (ChromaDB harus berjalan)
- Cek logs untuk error terkait `byte_rover`

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
- **Isolated Browser Context** — Browser Automation menggunakan isolated context per session
- **OAuth Token Encryption** — Google credentials disimpan aman di server

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

*AI ORCHESTRATOR v3.0 — Autonomous Skills Suite dengan 8 Built-in Intelligence Skills*  
*Built with ❤️ using FastAPI, React, Playwright, ChromaDB, and cutting-edge AI models*
