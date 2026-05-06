# 🧠 AI ORCHESTRATOR v3.5
### *The Next-Gen Autonomous Multi-Agent Engine*

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Engine-VISION__GATE-blue?style=for-the-badge" alt="Engine">
  <img src="https://img.shields.io/badge/Security-2FA--Enabled-red?style=for-the-badge" alt="Security">
</p>

**AI ORCHESTRATOR** adalah platform orkestrasi AI mandiri (Self-Hosted) yang dirancang untuk mengubah tugas kompleks menjadi workflow otomatis yang mulus. Ditenagai oleh **VISION_GATE Engine**, sistem ini tidak hanya menjawab teks, tetapi "melihat", "berpikir", dan "bertindak" secara otonom menggunakan **10+ Core Autonomous Skills**.

---

## 🏛️ Orchestrator vs. OpenClaw
Mengapa memilih AI Orchestrator? Berikut adalah perbandingan mendalam dengan platform populer lainnya:

| Fitur | 🧠 AI Orchestrator | 🦞 OpenClaw |
| :--- | :--- | :--- |
| **Fokus Utama** | Optimasi & Efisiensi Skala Enterprise | Modularitas & Komunitas (Local-first) |
| **Memory Engine** | **Byte Rover** (Semantic RAG Context) | Plain Text / YAML based |
| **Token Efficiency** | **QMD (Token Killer)** - Hemat hingga 80% | Standard context management |
| **Self-Improvement** | **Capability Evolver** (Auto-learn routing) | Manual skill configuration |
| **Vision Analysis** | **VISION_GATE** (Context-aware vision) | Standard OCR / Image captioning |
| **Security** | 2FA (TOTP + Telegram) & Brute Force Protection | Standard API Key auth |
| **UI/UX** | Integrated React Dashboard + Real-time Timeline | Web UI + Terminal focus |
| **Execution** | Multi-agent parallel coordination | Sequential ReAct Loop |

---

## 🚀 Autonomous Skills Suite (The Digital Team)

AI Orchestrator bekerja dengan "Intelligence Units" yang beroperasi secara otomatis di belakang layar.

### ⚡ Background Optimization Skills
*Skills yang bekerja tanpa henti untuk memastikan performa maksimal.*

- **⚡ QMD — The Token Killer**: Algoritma distilasi cerdas yang memangkas biaya API hingga 80% dengan mengirimkan hanya informasi paling relevan dari riwayat chat panjang.
- **🧠 Capability Evolver**: Otak di balik sistem. Menganalisis 200 eksekusi terakhir setiap 30 menit untuk mengevolusikan aturan routing model secara otomatis.
- **✍️ Humanizer (Anti-Slop)**: Mengubah output AI yang kaku menjadi bahasa yang natural, hangat, dan manusiawi tanpa kehilangan akurasi data.
- **🧭 Byte Rover**: Memori jangka panjang yang secara otonom merangkum sesi chat idle dan menyimpannya ke Vector DB untuk diingat di masa depan.
- **🛡️ Self-Healing Core**: Mendeteksi kegagalan sistem atau error runtime dan melakukan perbaikan otomatis (restart service, pembersihan cache, dll).
- **🔒 Security Scanner (CVE Scan)**: Memindai kerentanan (CVE) di semua dependency Python dan Node.js secara terjadwal (24 jam) atau manual. Auto-fix dengan upgrade otomatis dan laporan langsung ke Telegram — didukung oleh **pip-audit**, **npm audit**, dan **OSV.dev API**.

### 🛠️ On-Demand Execution Skills
*Skills yang aktif seketika saat Anda memberikan perintah spesifik.*

- **🌐 Browser Automation**: Kendali penuh Chromium via Playwright. AI bisa riset web, ambil data, hingga debugging UI secara visual.
- **🟢 GOG CLI (Google Ecosystem)**: Jembatan langsung ke Gmail, Calendar, Sheets, dan Drive Anda melalui satu instruksi bahasa alami.
- **👁️ VISION_GATE Engine**: Analisis gambar tingkat lanjut. Bukan sekadar OCR, tapi memahami konteks, aktivitas, dan situasi dalam visual.
- **🏛️ Command Center**: Koordinator multi-agent yang memungkinkan eksekusi beberapa tugas berat secara paralel tanpa konflik.

---

## ✨ Fitur Unggulan

### 🤖 AI Orchestration Engine
- **Multi-Model Routing**: Mendukung berbagai vendor AI secara bersamaan — **OpenAI** (GPT series), **Anthropic** (Claude series), **Google** (Gemini series), **Ollama** (model lokal), **Sumopod**, dan penyedia custom OpenAI-compatible lainnya. Router otomatis memilih model terbaik berdasarkan kompleksitas tugas, biaya, dan ketersediaan.
- **Multimodal Workflow**: Gabungkan teks, gambar, dan file dalam satu instruksi yang kompleks.

### 🗄️ Knowledge Base (RAG)
- **Semantic Search**: Menggunakan ChromaDB untuk pencarian dokumen yang cerdas.
- **Auto-Indexing**: Cukup upload PDF/Doc/Txt, dan AI akan langsung memiliki akses ke pengetahuan tersebut.

### 🔒 Enterprise-Grade Security
- **Identity Protection**: Autentikasi dua faktor terintegrasi (Google Authenticator + Telegram).
- **Session Isolation**: Setiap sesi memiliki context dan sandbox browser yang terisolasi.
- **Audit Logs**: Rekaman lengkap setiap tindakan agent untuk keamanan dan kepatuhan.
- **CVE Scanner & Auto-Fix**: Pemindaian kerentanan dependency otomatis (terjadwal 24 jam) dengan auto-fix dan laporan Telegram real-time.

---

## ⚡ Instalasi Cepat (Otomatis)

Kami menggunakan sistem instalasi aman. Anda tidak perlu mengunduh *source code* mentah secara manual untuk menjaga keamanan sistem. Cukup jalankan perintah ini di terminal VPS atau server lokal Anda:

```bash
curl -fsSL https://raw.githubusercontent.com/maztfajar/repo-installer-publik/main/install.sh | bash
```

*(Sistem akan otomatis memasang Docker, mengunduh file konfigurasi yang diperlukan, dan menarik Image AI Orchestrator terbaru yang sudah terproteksi).*

### 🐳 Menjalankan dengan Docker Compose (Rekomendasi)

Gunakan Docker Compose untuk manajemen container yang lebih mudah, lengkap dengan **Watchtower** untuk update otomatis:

```bash
# Jalankan aplikasi dan watchtower
docker-compose up -d
```

Setelah dijalankan, akses **Dashboard UI** langsung di: `http://localhost:7860`. Port ini melayani antarmuka React (frontend) dan API (backend) secara terintegrasi.

### 🛡️ Proteksi Kode Sumber
Image Docker ini telah di-build dengan **Bytecode Compilation**. Semua file `.py` telah dihapus dan diganti dengan `.pyc` (Python Compiled). Ini memberikan lapisan keamanan tambahan agar logika bisnis Anda sulit untuk dilacak atau dimodifikasi oleh pengguna akhir.

Anda juga bisa menjalankan AI Orchestrator menggunakan Docker tanpa perlu install dependencies secara manual:

```bash
# Pull image dari Docker Hub
docker pull nyepetke/ai-super:latest

# Jalankan container
docker run -d \
  -p 7860:7860 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/rag_documents:/app/rag_documents \
  --env-file .env \
  --name ai-orchestrator \
  nyepetke/ai-super:latest
```

> [!TIP]
> Pastikan file `.env` sudah dikonfigurasi sebelum menjalankan container. Jika Anda menggunakan VPS, pastikan port 7860 terbuka di firewall.

---

## 📋 Struktur Sistem

```text
ai-super/
├── 🧠 backend/         # FastAPI Engine & Autonomous Skills
│   ├── agents/         # Executor, Tool Registry, Scorer
│   ├── core/           # QMD, Evolver, VisionGate, CommandCenter
│   └── integrations/   # Telegram, Google, WhatsApp
├── 🎨 frontend/        # React Dashboard & Real-time Monitoring
├── 🗃️ data/            # Persistence (SQLite WAL + ChromaDB)
└── 📜 scripts/         # Automation & Maintenance scripts
```

---

## 🛠️ Persyaratan Sistem

| Komponen | Minimum | Rekomendasi |
| :--- | :--- | :--- |
| **RAM** | 2 GB | 8 GB+ (untuk Vision & RAG) |
| **CPU** | 2 Cores | 4+ Cores |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **Python** | 3.12+ | 3.12 |

---

## 📄 Lisensi & Hak Cipta

Copyright (c) 2026 **maztfajarwahyudi**. Seluruh hak cipta dilindungi undang-undang.

Kode sumber ini disediakan untuk keperluan **peninjauan (viewing only)**. Penggunaan komersial, modifikasi, atau pendistribusian ulang tanpa izin tertulis dari pemilik adalah dilarang keras.

---

<p align="center">
  <i>Built with ❤️ using FastAPI, React, Playwright, ChromaDB, and Advanced AI Orchestration.</i><br>
  <b>AI ORCHESTRATOR — Powering Your Digital Autonomy.</b>
</p>
