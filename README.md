# 🧠 AI ORCHESTRATOR v3.7
### *The Next-Gen Autonomous Multi-Agent Engine with Hardened Resilience*

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Engine-VISION__GATE-blue?style=for-the-badge" alt="Engine">
  <img src="https://img.shields.io/badge/Security-2FA--Enabled-red?style=for-the-badge" alt="Security">
  <img src="https://img.shields.io/badge/Skills-Self--Evolving-blueviolet?style=for-the-badge" alt="Self-Evolving">
</p>

**AI ORCHESTRATOR** adalah platform orkestrasi AI mandiri (Self-Hosted) yang dirancang untuk mengubah tugas kompleks menjadi workflow otomatis yang mulus. Ditenagai oleh **VISION_GATE Engine**, sistem ini tidak hanya menjawab teks, tetapi "melihat", "berpikir", dan "bertindak" secara otonom menggunakan **10+ Core Autonomous Skills** — dan yang paling penting, ia **belajar dari pengalaman** untuk menjadi semakin pintar dan efisien setiap kali digunakan.

---

## 🏛️ Perbandingan Mendalam dengan Platform Lain

Bagaimana AI Orchestrator dibandingkan dengan platform AI self-hosted populer lainnya? Berikut perbandingan berdasarkan **fakta fitur yang ada** di masing-masing platform:

### 🧠 AI Orchestrator vs 🦞 OpenClaw

| Aspek | 🧠 AI Orchestrator | 🦞 OpenClaw |
| :--- | :--- | :--- |
| **Arsitektur** | Monolith terintegrasi (FastAPI + React) — satu container, langsung jalan | Node.js gateway terpisah — perlu setup skill manual per-komponen |
| **Self-Evolving Skills** | ✅ **Otomatis.** Pola tugas yang berhasil 5x dikristalisasi menjadi Skill permanen. | ❌ Tidak ada. Skills bersifat statis, ditambah manual via folder `/skills` |
| **Resilience Engine** | ✅ **Hardened.** Auto-continue pada output terpotong & boost token 8k | ❌ Manual retry. Sering terhenti di tengah task panjang |
| **Token Efficiency** | ✅ **QMD (Token Killer)** — hemat hingga 80% token per request | ❌ Tidak ada mekanisme penghematan token bawaan |
| **Security** | ✅ 2FA (TOTP + Telegram), brute force protection, **CVE Scanner otomatis** | ⚠️ Hanya API Key. Risiko keamanan tinggi |
| **Self-Healing** | ✅ Deteksi & perbaikan error otomatis (restart service, fix deps) | ❌ Tidak ada |

### 🧠 AI Orchestrator vs 🤖 OpenDevin (All Hands)

| Aspek | 🧠 AI Orchestrator | 🤖 OpenDevin |
| :--- | :--- | :--- |
| **Fokus Utama** | **Platform AI serba guna** — chat, coding, riset, otomasi sistem | **Coding agent saja** — fokus software engineering |
| **Task Completion** | ✅ **Mandatory Completion.** AI dipaksa selesaikan task tanpa instruksi user tambahan | ⚠️ Sering "stuck" atau minta bantuan user di tengah proses |
| **Stability** | ✅ Production-ready, **Never-Stop Engine** untuk output panjang | ⚠️ Eksperimental, sering terputus pada file besar |
| **Self-Evolving Skills** | ✅ Belajar dari eksekusi berulang → hemat token & waktu | ❌ Tidak ada. Setiap task dimulai dari nol |
| **Deployment** | ✅ Satu container Docker, plug & play | ⚠️ Setup kompleks, sandbox container terpisah |

---

## 🧬 Self-Evolving Skills — Fitur Revolusioner

Fitur yang **tidak dimiliki platform manapun**: AI Orchestrator belajar dari pengalaman dan membentuk Skill permanen secara otomatis.

### Cara Kerjanya:
```
Penggunaan ke-1  → ProceduralMemory simpan "resep" (langkah + tools)
Penggunaan ke-2~4 → Recall resep, confidence naik, eksekusi lebih cepat
Penggunaan ke-5  → 🧬 KRISTALISASI → AI generate nama & template Skill
                   → Simpan ke LearnedSkill (permanen)
Penggunaan ke-6+ → ⚡ Skill langsung aktif, hemat ~800 token/request
```

---

## 🛡️ Stability Hardening — The "Never-Stop" Engine

Versi terbaru (v3.7) memperkenalkan **Resilience Layer** yang memastikan tugas berat tidak pernah terhenti di tengah jalan karena batasan teknis LLM.

### 1. ⚡ Auto-Continuation (Seamless Logic)
Sistem sekarang memiliki **Truncation Detector** yang memantau output AI secara real-time. Jika AI terhenti di tengah kode (backtick ganjil), tag HTML menggantung, atau kalimat tidak selesai:
- **Deteksi Otomatis:** Sistem mengenali pola terputus tanpa campur tangan user.
- **Seamless Resume:** Mengirimkan perintah internal untuk melanjutkan tepat dari karakter terakhir.
- **Continuation Mandate:** Instruksi sistem yang memaksa AI menyelesaikan blok kode sebelum berhenti.

### 2. 🚀 Intelligent Token Boosting
Untuk tugas-tugas berat (**Coding**, **Web Development**, **System Admin**), orkestrator secara otomatis menaikkan batas output hingga **8.192 token** per iterasi. Ini memberikan ruang bernapas bagi AI untuk menulis komponen besar dalam satu tarikan napas.

### 3. 🛠️ Dependency Self-Healing
Sistem secara otomatis mendeteksi dan menyelesaikan konflik versi paket (seperti konflik `litellm` & `python-dotenv`) untuk memastikan server tetap berjalan stabil di berbagai lingkungan Linux.

---

## 🚀 Autonomous Skills Suite (The Digital Team)

AI Orchestrator bekerja dengan "Intelligence Units" yang beroperasi secara otomatis di belakang layar.

### ⚡ Background Optimization Skills
- **⚡ QMD — The Token Killer**: Algoritma distilasi cerdas yang memangkas biaya API hingga 80%.
- **🧠 Capability Evolver**: Menganalisis 200 eksekusi terakhir untuk mengevolusikan aturan routing model.
- **🧬 Skill Evolution Engine**: Mengkristalisasi pola tugas berulang menjadi Skill permanen.
- **✍️ Humanizer (Anti-Slop)**: Mengubah output AI menjadi bahasa yang natural dan manusiawi.
- **🛡️ Self-Healing Core**: Mendeteksi kegagalan sistem dan melakukan perbaikan otomatis.
- **🔒 Security Scanner**: Memindai kerentanan (CVE) di semua dependency secara otomatis (24 jam).

### 🛠️ On-Demand Execution Skills
- **🌐 Browser Automation**: Kendali penuh Chromium via Playwright untuk riset & otomasi web.
- **🟢 GOG CLI**: Jembatan langsung ke Google Gmail, Calendar, Sheets, dan Drive.
- **👁️ VISION_GATE Engine**: Analisis gambar tingkat lanjut yang memahami konteks visual.
- **🏛️ Command Center**: Koordinator multi-agent untuk eksekusi paralel.

---

## ✨ Fitur Unggulan

### 🤖 AI Orchestration Engine
- **Multi-Model Routing**: Router otomatis memilih model terbaik (OpenAI, Anthropic, Gemini, Ollama, dll).
- **Parallel Execution**: DAG-based task decomposition dengan eksekusi multi-agent paralel.
- **Resilience Layer**: Mekanisme auto-continue untuk menjamin penyelesaian tugas panjang.

### 🗄️ Knowledge Base (RAG)
- **Semantic Search**: Menggunakan ChromaDB untuk pencarian dokumen cerdas.
- **Auto-Indexing**: Cukup upload file, dan AI langsung memiliki akses ke pengetahuan tersebut.

### 🔒 Enterprise-Grade Security
- **Identity Protection**: Autentikasi 2FA terintegrasi (TOTP + Telegram).
- **CVE Scanner & Auto-Fix**: Pemindaian kerentanan otomatis dengan laporan Telegram real-time.

---

## ⚡ Instalasi & Setup

### Metode 1: Instalasi Otomatis (Satu Perintah)
```bash
curl -fsSL https://raw.githubusercontent.com/maztfajar/repo-installer-publik/main/install.sh | bash
```

### Metode 2: Setup Manual dengan Docker Compose
Buka folder project dan jalankan:
```bash
docker compose pull && docker compose up -d
```

---

## 📋 Struktur Sistem
```text
ai-super/
├── 🧠 backend/         # FastAPI Engine & Autonomous Skills
├── 🎨 frontend/        # React Dashboard & Real-time Monitoring
├── 🗃️ data/            # Persistence (SQLite WAL + ChromaDB + Skills)
└── 📜 scripts/         # Automation & Maintenance scripts
```

---

## 🛠️ Persyaratan Sistem
| Komponen | Minimum | Rekomendasi |
| :--- | :--- | :--- |
| **RAM** | 2 GB | 8 GB+ (untuk Vision & RAG) |
| **CPU** | 2 Cores | 4+ Cores |
| **Storage** | 10 GB | 50 GB+ |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |

---

## 📄 Lisensi & Hak Cipta
Copyright (c) 2026 **maztfajarwahyudi**. Seluruh hak cipta dilindungi undang-undang.
Kode sumber ini disediakan untuk keperluan peninjauan saja.

---

<p align="center">
  <i>Built with ❤️ using FastAPI, React, Playwright, ChromaDB, and Advanced AI Orchestration.</i><br>
  <b>AI ORCHESTRATOR — Powering Your Digital Autonomy.</b>
</p>
