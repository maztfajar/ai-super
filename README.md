# 🧠 AI ORCHESTRATOR v3.5
### *The Next-Gen Autonomous Multi-Agent Engine*

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Engine-VISION__GATE-blue?style=for-the-badge" alt="Engine">
  <img src="https://img.shields.io/badge/Security-2FA--Enabled-red?style=for-the-badge" alt="Security">
</p>

**AI ORCHESTRATOR** adalah platform orkestrasi AI mandiri (Self-Hosted) yang dirancang untuk mengubah tugas kompleks menjadi workflow otomatis yang mulus. Ditenagai oleh **VISION_GATE Engine**, sistem ini tidak hanya menjawab teks, tetapi "melihat", "berpikir", dan "bertindak" secara otonom menggunakan **10+ Core Autonomous Skills**.

---

## 🏛️ AI Orchestrator vs. Aplikasi Lainnya
Mengapa memilih AI Orchestrator? Berikut adalah perbandingan mendalam dengan platform populer lainnya seperti OpenClaw, OpenWebUI, dan OpenDevin:

| Fitur Utama | 🧠 AI Orchestrator | 🦞 Aplikasi Sejenis (OpenClaw / OpenWebUI / OpenDevin) |
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

### 🐳 Instalasi Manual dengan Docker Compose (Rekomendasi)

Jika Anda tidak ingin menggunakan skrip otomatis di atas, Anda bisa mengaturnya secara manual menggunakan Docker Compose. Metode ini jauh lebih aman dari salah ketik dan sangat mudah untuk proses *update* ke depannya.

**1. Buat file konfigurasi (`docker-compose.yml`)**
Buat folder baru dan buat file konfigurasi:
```bash
mkdir ai-orchestrator && cd ai-orchestrator
nano docker-compose.yml
```
Masukkan konfigurasi berikut ke dalam file tersebut:
```yaml
services:
  ai-orchestrator:
    image: nyepetke/ai-super:latest
    container_name: ai-orchestrator
    restart: always
    ports:
      - "7860:7860"
    volumes:
      - ./data:/app/data
      - ./rag_documents:/app/rag_documents
      - ./.env:/app/.env
    env_file:
      - .env
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7860/api/health"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 40s

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: always
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      - ai-orchestrator
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: always
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 300 --cleanup --label-enable
```

**2. Siapkan file `.env`**
```bash
nano .env
```
Isikan kredensial dasar Anda:
```env
ADMIN_USERNAME=admin
# Ganti dengan password yang kuat, minimal 8 karakter!
ADMIN_PASSWORD=password_rahasia_saya123
```

**3. Jalankan Aplikasi**
```bash
docker compose up -d
```

Setelah dijalankan, akses **Dashboard UI** langsung di: `http://<IP_VPS_ANDA>:7860`.

> [!IMPORTANT]
> **Kredensial Login Default:**
> - **Username:** `admin`
> - **Password:** `admin123` *(jika `ADMIN_PASSWORD` di `.env` belum diisi atau masih kosong)*
>
> Jika Anda sudah mengisi `ADMIN_PASSWORD` di file `.env`, gunakan password yang Anda buat sendiri tersebut.
> **Segera ganti password setelah berhasil masuk pertama kali** melalui menu Settings di Dashboard!

> [!TIP]
> **Cara Melakukan Update (Pembaruan Versi):**
> Sangat mudah! Anda hanya perlu masuk ke folder `ai-orchestrator` lalu jalankan:
> `docker compose pull` kemudian `docker compose up -d`. Sistem akan otomatis memperbarui tanpa menghilangkan data Anda.


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
