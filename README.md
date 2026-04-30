# 🧠 AI ORCHESTRATOR — Platform AI Self-Hosted v2.5

Platform AI Self-Hosted tercanggih dengan **Multi-AI Parallel Voting**, **Agent Scorer Engine**, knowledge base RAG, workflow otomatis, dan keamanan enterprise.

---

## ✨ Fitur Utama

### 🤖 **Multi-AI & Orchestration Engine**
- **Multi-AI Parallel Voting (v2.5)**: Verifikasi jawaban melalui eksekusi paralel beberapa model (DeepSeek, Qwen, Gemini) untuk akurasi maksimal.
- **Agent Scorer & Selection Engine**: Pemilihan model dinamis berdasarkan skor kapabilitas, performa historis, dan ketersediaan real-time.
- **Smart Routing**: Auto-routing cerdas untuk coding, analisis, vision, dan creative writing.
- **Dynamic AI Role Mapping**: Personalisasi model untuk peran spesifik (Coding, Reasoning, Chat) langsung dari UI.

### 🔍 **Smart Search & Vision**
- **Tavily Web Search Integration**: Akses internet real-time untuk riset mendalam dan data terbaru.
- **VISION_GATE Engine**: Analisis gambar lengkap - objek, aktivitas, situasi, dan konteks dengan dukungan OCR.
- **Multimodal Chat**: Interaksi teks, gambar, dan dokumen dalam satu sesi percakapan.

### 🛠️ **AI Execution Pipeline (Agentic Workflow)**
- **Mandatory Planning Phase**: AI merencanakan arsitektur dan langkah eksekusi secara mendetail sebelum menulis kode.
- **Process Step Tracking**: Pantau proses *thinking*, *planning*, *execution*, dan *verification* secara real-time.
- **Execution Sandbox**: Lingkungan terisolasi untuk eksekusi kode/bash dengan *auto-correction* saat error.
- **App Verification Loop**: Pre-flight check otomatis untuk memastikan aplikasi hasil generate benar-benar berjalan.

### 🗄️ **RAG & Knowledge Management**
- **Knowledge Base RAG**: Unggah PDF, DOC, TXT dengan indexing otomatis menggunakan vector search.
- **Context-Aware Responses**: Jawaban cerdas yang merujuk pada dokumen internal Anda.
- **Persistent Project Storage**: Manajemen folder proyek otomatis yang tersimpan per sesi chat.

### 🔒 **Enterprise Security & Multi-Channel**
- **Two-Factor Authentication (2FA)**: Keamanan ekstra dengan TOTP dan Telegram OTP.
- **Multi-Channel Integration**: Akses melalui Web Interface, Telegram Bot, dan WhatsApp (experimental).
- **PostgreSQL Support**: Pilihan database skala enterprise untuk stabilitas data yang lebih baik.

---

## ⚡ Instalasi Cepat

```bash
# Clone repository
git clone https://github.com/maztfajar/ai-super.git
cd ai-super

# Jalankan installer interaktif
bash install.sh

# Mulai layanan
bash update_and_restart.sh
```

Buka: **http://localhost:7860**  
Login default: `admin` / `admin`

> ⚠️ **PENTING**: Segera ganti password default dan aktifkan 2FA di menu Profile setelah login pertama.

---

## 📋 System Requirements

| Komponen | Minimum | Rekomendasi |
|---|---|---|
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| RAM | 4 GB | 16 GB+ (untuk multi-model) |
| CPU | 2 cores | 8+ cores |
| Storage | 10 GB | 50 GB+ (SSD recommended) |
| Python | 3.10+ | 3.11 |
| Node.js | 18+ | 20 LTS |

---

## ⚙️ Konfigurasi (.env)

```env
# Basic
APP_NAME="AI ORCHESTRATOR"
SECRET_KEY=ganti-dengan-string-random-32-karakter

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
TAVILY_API_KEY=tvly-...  # Untuk fitur Web Search

# Database (Pilih salah satu)
# SQLite (Default)
DATABASE_URL=sqlite:///./data/app.db
# PostgreSQL (Recommended for Production)
# DATABASE_URL=postgresql://user:pass@localhost/dbname

# Telegram Bot (2FA & Notifications)
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=123456789
```

---

## 🆕 **Update Terbaru (v2.5)**
- 🗳️ **Voting Engine**: Integrasi sistem voting antar-model untuk meningkatkan reliabilitas jawaban kompleks.
- 📈 **Agent Scorer**: Algoritma baru untuk memilih model terbaik berdasarkan beban kerja dan tingkat kesuksesan sebelumnya.
- 🌐 **Web Search Integration**: Pencarian web otonom menggunakan Tavily API untuk menjawab pertanyaan berbasis data terkini.
- 🎭 **Role Mapping UI**: Antarmuka baru di menu Integrations untuk memetakan model ke peran (misal: DeepSeek untuk Coding, Gemini untuk Reasoning).
- ⚡ **Response Stability**: Perbaikan logika streaming untuk mencegah coupling karakter ("teks gandeng") pada koneksi lambat.
- 🐘 **PostgreSQL Ready**: Dukungan penuh untuk PostgreSQL sebagai backend database utama.

## 🆕 **Update Sebelumnya (v2.4)**
- 🧠 **Mandatory Planning**: AI wajib membuat rencana langkah demi langkah sebelum eksekusi kode.
- ✅ **Verification Loop**: Auto-check port dan status aplikasi setelah proses pembuatan selesai.
- 👁️ **Aggressive Context**: Deteksi file proyek secara otomatis untuk mengurangi redundansi penulisan kode.
- 🛡️ **Smart Error Hinting**: Injeksi saran perbaikan otomatis saat AI menemui error sistem (EADDRINUSE, etc).

---

## 🗂️ Struktur Folder Utama

- `backend/`: FastAPI core, orchestrator, dan integrasi AI.
- `frontend/`: React + Vite UI components.
- `scripts/`: Kumpulan utility untuk instalasi, update, dan maintenance.
- `data/`: Lokasi penyimpanan database, dokumen RAG, dan log.
- `rag_documents/`: Folder default untuk dokumen yang akan di-index.

---

## 🔧 Troubleshooting

Jika menemui kendala, gunakan script troubleshooter:
```bash
bash troubleshoot-vps.sh
```

Masalah umum:
- **Blank Screen (Tunnel)**: Pastikan CORS dikonfigurasi dengan URL tunnel Anda di `.env`.
- **Database Locked**: Jika menggunakan SQLite, pastikan tidak ada proses backend ganda yang berjalan.
- **Model Timeout**: Gunakan model "flash" (seperti Gemini Flash) jika koneksi internet terbatas.

---

## 📖 Dokumentasi
Panduan lengkap tersedia dalam format:
- `VPS_DEPLOY.md`: Panduan khusus deployment di VPS.
- `Laporan_Evaluasi_AI_Orchestrator.md`: Analisis performa dan kapabilitas sistem.

---

## 📄 Lisensi & Legal
Copyright (c) 2026 maztfajarwahyudi. All rights reserved.
**Proprietary Software**: Penggunaan, penggandaan, atau distribusi tanpa izin tertulis dari pemilik sah sangat dilarang.

---
*Built with ❤️ by maztfajarwahyudi*
