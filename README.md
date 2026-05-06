# 🧠 AI ORCHESTRATOR v3.5
### *The Next-Gen Autonomous Multi-Agent Engine with Self-Evolving Skills*

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
| **Self-Evolving Skills** | ✅ **Otomatis.** Pola tugas yang berhasil 5x dikristalisasi menjadi Skill permanen oleh AI. Semakin sering dipakai = semakin cepat & hemat | ❌ Tidak ada. Skills bersifat statis, ditambah manual via folder `/skills` |
| **Token Efficiency** | ✅ **QMD (Token Killer)** — hemat hingga 80% token per request via distilasi konteks cerdas | ❌ Tidak ada mekanisme penghematan token bawaan |
| **Memory Engine** | ✅ **Byte Rover** — memori semantik jangka panjang + **ProceduralMemory** (buku resep tugas sukses) | ❌ Memori plain text/YAML, tidak ada semantic recall |
| **Self-Improvement** | ✅ **Capability Evolver** — otomatis analisis 200 eksekusi terakhir tiap 30 menit, evolusi routing model | ❌ Konfigurasi model statis, harus diatur manual |
| **Vision Analysis** | ✅ **VISION_GATE** — analisis kontekstual gambar (bukan sekadar OCR) | ⚠️ Tergantung plugin pihak ketiga |
| **Security** | ✅ 2FA (TOTP + Telegram), brute force protection, audit log, **CVE Scanner otomatis** | ⚠️ Hanya API Key. Risiko keamanan tinggi karena akses sistem penuh tanpa guardrail bawaan |
| **Eksekusi** | Multi-agent **paralel** dengan DAG dependency & Command Center | Sequential ReAct loop (satu langkah per waktu) |
| **Notifikasi** | ✅ Telegram real-time (skill baru, error, self-healing, CVE) | ❌ Tidak ada notifikasi bawaan |
| **Auto-Update** | ✅ Watchtower — container update otomatis tanpa downtime | ❌ Manual update |
| **Self-Healing** | ✅ Deteksi & perbaikan error otomatis (restart service, clear cache) | ❌ Tidak ada |
| **Heartbeat Daemon** | ❌ Tidak ada (event-driven) | ✅ Agent berjalan di background secara persisten |
| **Cross-Platform Chat** | ✅ Web + Telegram + WhatsApp | ✅ WhatsApp, Telegram, Slack, Discord, Signal |

### 🧠 AI Orchestrator vs 🌐 Open WebUI

| Aspek | 🧠 AI Orchestrator | 🌐 Open WebUI |
| :--- | :--- | :--- |
| **Fokus Utama** | **Orkestrasi & Eksekusi Otonom** — AI bisa *bertindak* (run code, browse web, kelola file) | **Chat Interface** — UI cantik untuk *ngobrol* dengan model lokal/remote |
| **Self-Evolving Skills** | ✅ Skill dikristalisasi otomatis dari pengalaman | ❌ Tidak ada fitur pembelajaran mandiri |
| **Tool Execution** | ✅ 10+ tools bawaan (browser, CLI, file ops, Google integration) | ⚠️ Terbatas pada Pipelines (perlu koding custom) |
| **Token Efficiency** | ✅ QMD hemat 80% token | ❌ Tidak ada |
| **RAG** | ✅ ChromaDB + auto-indexing | ✅ RAG bawaan (kuat) |
| **Multi-Model** | ✅ OpenAI, Anthropic, Google, Ollama, Sumopod, custom | ✅ Ollama-centric + OpenAI-compatible |
| **Security** | ✅ 2FA, CVE scanner, brute force protection | ⚠️ Basic auth, tidak ada 2FA bawaan |
| **Lisensi** | Proprietary (viewing only) | Custom license (branding requirement untuk deployment besar) |
| **Komunitas** | Ekosistem tertutup | ✅ Komunitas besar, development velocity tinggi |
| **Ollama Integration** | ✅ Didukung | ✅ Sangat kuat (raison d'être) |

### 🧠 AI Orchestrator vs 🤖 OpenDevin (All Hands)

| Aspek | 🧠 AI Orchestrator | 🤖 OpenDevin |
| :--- | :--- | :--- |
| **Fokus Utama** | **Platform AI serba guna** — chat, coding, riset, otomasi sistem | **Coding agent saja** — fokus software engineering |
| **Self-Evolving Skills** | ✅ Belajar dari eksekusi berulang → hemat token & waktu | ❌ Tidak ada. Setiap task dimulai dari nol |
| **Multi-Purpose** | ✅ Chat casual, analisis data, riset web, system admin, coding | ❌ Hanya coding/software engineering |
| **UI/UX** | ✅ React Dashboard terintegrasi + monitoring real-time | ⚠️ UI dasar, fokus terminal |
| **Stabilitas** | ✅ Production-ready, self-healing, auto-recovery | ⚠️ Eksperimental, sering stuck dalam loop |
| **Deployment** | ✅ Satu container Docker, plug & play | ⚠️ Setup kompleks, sandbox container terpisah |
| **Performa AI** | ✅ Setara senior dev (multi-agent, paralel, quality validation) | ⚠️ Setara junior dev (sequential, perlu oversight) |
| **Context Management** | ✅ QMD + ProceduralMemory + Skill Evolution = konteks efisien | ⚠️ Kesulitan pada task panjang/multi-hari |
| **Browser Automation** | ✅ Playwright terintegrasi | ✅ Playwright terintegrasi |
| **Sandbox** | Di dalam container Docker | ✅ Linux container terisolasi |

### 🧠 AI Orchestrator vs Ringkasan Platform Lain

| Aspek | 🧠 AI Orchestrator | LibreChat | LobeChat | AnythingLLM |
| :--- | :--- | :--- | :--- | :--- |
| **Self-Evolving Skills** | ✅ | ❌ | ❌ | ❌ |
| **Token Efficiency** | ✅ QMD | ❌ | ❌ | ❌ |
| **Tool Execution** | ✅ 10+ built-in | ⚠️ Code interpreter | ⚠️ MCP skills | ❌ |
| **Multi-Model** | ✅ 6 provider | ✅ Banyak provider | ✅ Banyak provider | ✅ |
| **RAG** | ✅ ChromaDB | ⚠️ Basic | ⚠️ Basic | ✅ Sangat kuat |
| **2FA Security** | ✅ | ⚠️ OIDC/SSO | ❌ | ❌ |
| **Self-Healing** | ✅ | ❌ | ❌ | ❌ |
| **Telegram Bot** | ✅ | ❌ | ❌ | ❌ |

> **Kesimpulan:** AI Orchestrator unggul di area **otonomi, efisiensi, dan kemampuan belajar mandiri**. Platform lain umumnya berfokus pada satu aspek saja (chat UI, coding, atau dokumen). AI Orchestrator menggabungkan semuanya dalam satu platform terintegrasi yang terus berevolusi.

---

## 🧬 Self-Evolving Skills — Fitur Revolusioner

Fitur yang **tidak dimiliki platform manapun**: AI Orchestrator belajar dari pengalaman dan membentuk Skill permanen secara otomatis.

### Cara Kerjanya:

```
Penggunaan ke-1  → ProceduralMemory simpan "resep" (langkah + tools)
Penggunaan ke-2~4 → Recall resep, confidence naik, eksekusi lebih cepat
Penggunaan ke-5  → 🧬 KRISTALISASI → AI generate nama & template Skill
                   → Simpan ke LearnedSkill (permanen)
                   → Notifikasi Telegram: "Skill baru terbentuk!"
Penggunaan ke-6+ → ⚡ Skill langsung aktif, hemat ~800 token/request
                   → AI tidak perlu reasoning dari nol
Penggunaan ke-10 → 🔄 AI improve Skill ke versi 2, lebih efisien
Seterusnya       → Semakin pintar, semakin hemat, semakin cepat
```

### Contoh Nyata:
1. **Pertama kali** diminta "buat REST API dengan Express" → 15 langkah, trial-error → berhasil → resep disimpan
2. **Kedua kali** permintaan serupa → recall resep → 10 langkah → lebih cepat
3. **Kelima kali** → sistem kristalisasi pola → Skill `create_express_api` terbentuk
4. **Selanjutnya** → Skill langsung aktif, eksekusi instan tanpa reasoning ulang

### API Dashboard:
- `GET /api/monitoring/skills` — Lihat semua skill yang telah dipelajari
- `DELETE /api/monitoring/skills/{id}` — Nonaktifkan skill yang tidak relevan

### 🛡️ Safety Guards — Mencegah AI "Belajar Hal Buruk"

Sistem Self-Evolving Skills dilengkapi **4 lapis proteksi** agar AI tidak mengkristalisasi pola yang salah (bad habit):

```
┌──────────────────────────────────────────────────────────┐
│           QUALITY GATES (Saat Kristalisasi)               │
├──────────────────────────────────────────────────────────┤
│  ① Confidence Gate  → Hanya pola dengan confidence ≥ 70% │
│                       yang boleh menjadi Skill.           │
│                       Pola "berhasil tapi ragu" = ditolak │
│                                                          │
│  ② Brute-Force Gate → Pola dengan > 20 langkah ditolak.  │
│                       Terlalu banyak langkah = tanda      │
│                       trial-error, bukan pola efisien.    │
├──────────────────────────────────────────────────────────┤
│        AUTO-DEGRADATION (Saat Skill Digunakan)            │
├──────────────────────────────────────────────────────────┤
│  ③ Success Rate      → Jika success rate turun < 60%     │
│     Monitor            setelah 5+ penggunaan → Skill     │
│                        otomatis DINONAKTIFKAN.            │
│                                                          │
│  ④ Failure Streak    → 3x gagal berturut-turut →         │
│     Breaker            Skill langsung DINONAKTIFKAN.      │
│                        Mencegah skill rusak terus dipakai │
└──────────────────────────────────────────────────────────┘
```

> **Hasilnya:** Hanya skill berkualitas tinggi yang bertahan. Skill yang mulai "rusak" akan otomatis dimatikan sebelum menyebabkan kerusakan berulang.

### 🔒 Anti Infinite-Loop — 5 Lapis Pertahanan Token

AI agent yang mengeksekusi kode memiliki risiko terjebak dalam loop tak terbatas. AI Orchestrator memiliki **5 lapis pertahanan** untuk mencegah pemborosan token:

```
Lapis 1 ─ MAX_ITERATIONS (15)
│         Batas keras: maksimal 15 iterasi per sesi eksekusi.
│
Lapis 2 ─ TOKEN BUDGET (50.000)
│         Hard limit token. Jika estimasi token > 50k → paksa berhenti.
│         Mencegah AI memakan biaya tanpa batas.
│
Lapis 3 ─ LOOP BREAKER
│         Tool call identik 3x berturut-turut → paksa ganti strategi.
│         AI dipaksa evaluasi ulang, bukan mengulangi hal yang sama.
│
Lapis 4 ─ STALL DETECTOR
│         Output teks identik 3x berturut-turut (tanpa tool call)
│         → abort. Menangkap AI yang "berputar" dalam reasoning.
│
Lapis 5 ─ CIRCUIT BREAKER
          2 error beruntun → berhenti total dengan pesan jelas.
          Mencegah cascading failure.
```

> **Contoh kasus yang dicegah:**
> - AI mencoba memperbaiki bug logika di kodenya sendiri → terjebak loop → **Lapis 3** mendeteksi tool call berulang → paksa ganti strategi
> - AI berpikir berputar-putar tanpa mengambil aksi → **Lapis 4** mendeteksi output repetitif → abort
> - Bug tak terduga menghasilkan error terus-menerus → **Lapis 5** memutus sirkuit setelah 2x error

---

## 🚀 Autonomous Skills Suite (The Digital Team)

AI Orchestrator bekerja dengan "Intelligence Units" yang beroperasi secara otomatis di belakang layar.

### ⚡ Background Optimization Skills
*Skills yang bekerja tanpa henti untuk memastikan performa maksimal.*

- **⚡ QMD — The Token Killer**: Algoritma distilasi cerdas yang memangkas biaya API hingga 80% dengan mengirimkan hanya informasi paling relevan dari riwayat chat panjang.
- **🧠 Capability Evolver**: Otak di balik sistem. Menganalisis 200 eksekusi terakhir setiap 30 menit untuk mengevolusikan aturan routing model secara otomatis.
- **🧬 Skill Evolution Engine**: Mengkristalisasi pola tugas berulang menjadi Skill permanen. Semakin sering dipakai = semakin pintar & hemat token.
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
- **Parallel Execution**: DAG-based task decomposition dengan eksekusi multi-agent secara paralel.

### 🗄️ Knowledge Base (RAG)
- **Semantic Search**: Menggunakan ChromaDB untuk pencarian dokumen yang cerdas.
- **Auto-Indexing**: Cukup upload PDF/Doc/Txt, dan AI akan langsung memiliki akses ke pengetahuan tersebut.

### 🔒 Enterprise-Grade Security
- **Identity Protection**: Autentikasi dua faktor terintegrasi (Google Authenticator + Telegram).
- **Session Isolation**: Setiap sesi memiliki context dan sandbox browser yang terisolasi.
- **Audit Logs**: Rekaman lengkap setiap tindakan agent untuk keamanan dan kepatuhan.
- **CVE Scanner & Auto-Fix**: Pemindaian kerentanan dependency otomatis (terjadwal 24 jam) dengan auto-fix dan laporan Telegram real-time.

### 📊 Monitoring & Observability
- **Real-time Dashboard**: Pantau status agent, task execution, dan performa model secara langsung.
- **Skill Evolution Tracker**: Lihat skill apa yang telah dipelajari orchestra dan berapa token yang dihemat.
- **Self-Healing Events**: Log otomatis setiap perbaikan yang dilakukan sistem secara mandiri.

---

## ⚡ Instalasi & Setup

### Prasyarat
- **Docker** dan **Docker Compose** terinstall di VPS/server Anda
- Minimal **2 GB RAM** (rekomendasi 8 GB+ untuk Vision & RAG)
- **Ubuntu 20.04+** (atau Linux distro lain yang mendukung Docker)

### Metode 1: Instalasi Otomatis (Satu Perintah)

```bash
curl -fsSL https://raw.githubusercontent.com/maztfajar/repo-installer-publik/main/install.sh | bash
```

*(Sistem akan otomatis memasang Docker, mengunduh file konfigurasi yang diperlukan, dan menarik Image AI Orchestrator terbaru.)*

### Metode 2: Setup Manual dengan Docker Compose (Rekomendasi)

#### Langkah 1 — Buat Direktori & File Konfigurasi

```bash
mkdir ai-orchestrator && cd ai-orchestrator
```

Buat file `docker-compose.yml` (copy-paste seluruh blok ini di terminal):

```bash
cat << 'EOF' > docker-compose.yml
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
EOF
```

#### Langkah 2 — Buat File `.env`

```bash
cat << 'EOF' > .env
# ── Kredensial Admin ────────────────────────────────────
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ganti_dengan_password_kuat_anda

# ── Keamanan ────────────────────────────────────────────
# Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=ganti_dengan_string_acak_32_karakter

# ── Cloudflare Tunnel (opsional) ────────────────────────
CLOUDFLARE_TUNNEL_TOKEN=

# ── API Keys AI (isi via GUI setelah login) ─────────────
# Anda TIDAK perlu mengisi API Key di sini.
# Cukup login ke Dashboard → Settings → isi API Key di GUI.
# Semua pengaturan akan tersimpan permanen.
EOF
```

#### Langkah 3 — Jalankan

```bash
docker compose pull
docker compose up -d
```

#### Langkah 4 — Akses Dashboard

Buka browser: `http://<IP_VPS_ANDA>:7860`

> [!IMPORTANT]
> **Login dengan kredensial yang Anda atur di `.env`:**
> - **Username:** `admin` (atau sesuai `ADMIN_USERNAME`)
> - **Password:** sesuai `ADMIN_PASSWORD` di file `.env`

#### Langkah 5 — Konfigurasi API Key (Satu Kali Saja)

1. Login ke Dashboard
2. Buka **Settings** → **Integrations**
3. Masukkan API Key untuk provider AI yang Anda gunakan (OpenAI, Anthropic, Google, dll)
4. Klik **Save**

> [!TIP]
> **Data Anda aman dan permanen!** Semua konfigurasi (API Key, riwayat chat, skill yang dipelajari) tersimpan di volume `./data` dan `./.env` di VPS Anda. Data **tidak akan hilang** saat update container atau restart server.

---

## 🔄 Update & Maintenance

### Update Manual
```bash
cd ai-orchestrator
docker compose pull
docker compose up -d
```

### Update Otomatis (Sudah Aktif)
**Watchtower** secara otomatis mengecek Docker registry setiap 5 menit. Jika ada image baru, container akan diperbarui tanpa downtime dan tanpa kehilangan data.

---

## 📋 Struktur Sistem

```text
ai-super/
├── 🧠 backend/         # FastAPI Engine & Autonomous Skills
│   ├── agents/         # Executor, Tool Registry, Scorer
│   ├── core/           # QMD, Evolver, VisionGate, SkillEvolution, CommandCenter
│   └── integrations/   # Telegram, Google, WhatsApp
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
| **Storage** | 10 GB | 50 GB+ (untuk RAG documents) |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| **Docker** | 20.10+ | Latest stable |

---

## 📄 Lisensi & Hak Cipta

Copyright (c) 2026 **maztfajarwahyudi**. Seluruh hak cipta dilindungi undang-undang.

Kode sumber ini disediakan untuk keperluan **peninjauan (viewing only)**. Penggunaan komersial, modifikasi, atau pendistribusian ulang tanpa izin tertulis dari pemilik adalah dilarang keras.

---

<p align="center">
  <i>Built with ❤️ using FastAPI, React, Playwright, ChromaDB, and Advanced AI Orchestration.</i><br>
  <b>AI ORCHESTRATOR — Powering Your Digital Autonomy.</b>
</p>
