# 🧠 AI ORCHESTRATOR v4.1.21
### *High-Autonomy Execution, Hardened Resilience & Execution Continuity*

<p align="center">
  <img src="https://img.shields.io/badge/Status-Production--Ready-brightgreen?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/Arch-Multi--Agent--DAG-blue?style=for-the-badge" alt="Architecture">
  <img src="https://img.shields.io/badge/Routing-Zero--Hardcode-orange?style=for-the-badge" alt="Routing">
  <img src="https://img.shields.io/badge/Memory-Semantic--Procedural-blueviolet?style=for-the-badge" alt="Memory">
  <img src="https://img.shields.io/badge/Security-2FA--Audited-red?style=for-the-badge" alt="Security">
  <img src="https://img.shields.io/badge/AI_Core-Auto--Generate-ff69b4?style=for-the-badge" alt="AI Core">
</p>

---

## 📖 Overview

**AI ORCHESTRATOR** adalah platform orkestrasi AI mandiri (Self-Hosted) yang dirancang untuk mengeksekusi tugas-tugas kompleks melalui sistem multi-agent yang terkoordinasi. Berbeda dengan chat UI standar, sistem ini berfokus pada **Execution & Autonomy**, didukung oleh lapisan memori prosedural dan **Dynamic Model Routing** yang memungkinkannya memilih model AI terbaik secara otomatis untuk setiap jenis tugas — tanpa perlu menyentuh kode keras (Zero-Hardcode).

---

## 🌟 Core Features & Capabilities

Seluruh fitur mutakhir dari pembaruan sebelumnya (v3.8 hingga v4.1) kini telah disatukan dalam infrastruktur inti yang solid:

### 1. ⚡ High-Autonomy Execution & Scalability
*   **Native Function Calling (v4.1):** Orkestrasi kini didorong secara asli (*natively*) oleh standar JSON Schema bawaan dari penyedia model (OpenAI, Anthropic, Gemini, dll), memastikan akurasi pemanggilan alat (tool call) 95% bebas *syntax error* dan menghilangkan ketergantungan pada *regex parsing*.
*   **Browser Automation Tools (v4.1.21):** Agen dilengkapi kemampuan navigasi web otonom (`browser_navigate`), interaksi elemen (`browser_click`, `browser_type`), ekstraksi teks (`browser_extract_text`), dan penangkapan halaman secara visual (`browser_screenshot`).
*   **AI Image Generation (v4.1.21):** Integrasi pembuatan gambar (`generate_image`) dari instruksi teks dengan opsi resolusi dinamis (landscape, portrait, square) dan tingkat kualitas.
*   **Infinite Sub-Task Decomposition:** Sistem sanggup memecah instruksi skala besar (*Fullstack App*, *Deployment*, *Database*) menjadi belasan langkah operasional tanpa terpotong oleh batasan sewenang-wenang (hard-limit).
*   **True Parallel Execution:** Menggunakan arsitektur Directed Acyclic Graph (DAG) di `Command Center`, agen-agen beroperasi secara bersamaan (paralel) untuk tugas-tugas yang tidak saling mengunci (*non-blocking*).
*   **Smart Botleneck Bypass:** Agen otomatis menyelesaikan path file yang salah, menimpa file (*overwrite*), dan membuat direktori secara mandiri. Intervensi manusia hanya diperlukan pada aksi destruktif tingkat sistem.

### 2. 🧠 Intelligence, Reasoning & Memory
*   **5-Tahap ReAct Reasoning:** Setiap eksekusi didahului dengan 5-tahap penalaran kognitif: *Intent Inference* → *Context Exploration* → *Plan* → *Execute* → *Verify*.
*   **Multi-Model Consensus / Voting Engine (v4.1.21):** Mengaktifkan consensus voting engine (`VotingEngine`) saat kompleksitas tugas tinggi (score ≥ 0.8) untuk menjalankan beberapa model secara paralel dan menyatukan respons terbaik.
*   **Proactive Task Scheduler (v4.1.21):** Penjadwalan otomatis tugas masa depan atau pengingat (`schedule_task`) dengan perulangan berkala (daily, weekly) yang dikelola oleh Celery background worker.
*   **Human Logic Engine & Emotional State (v4.1.14):** Sistem menganalisis kondisi emosional pengguna secara *real-time* (emosi dominan, intensitas emosi, urgensi, niat tersirat, kebutuhan validasi) menggunakan kata kunci bilingual (ID/EN) sebelum melakukan klasifikasi intent teknis. Jika terdeteksi frustrasi atau tekanan waktu, prioritas kualitas otomatis ditingkatkan dan nada disesuaikan secara dinamis.
*   **Humanizer Skill (Anti-Robot Slop):** Modul polesan bahasa dinamis yang menyaring kata/frasa klise mesin yang kaku (*"Penting untuk diingat"*, *"Sebagai model bahasa"*, *"Kesimpulannya"*, dll.) agar gaya komunikasi model lebih natural, asimetris, kasual, dan layaknya manusia.
*   **QMD (Query Memory Distillation):** Algoritma kompresi konteks yang membuang redundansi percakapan sambil tetap menjaga format *whitespace/newline* pada kode secara ketat. Menghasilkan efisiensi token hingga **63%**.
*   **Procedural Memory & Skill Crystallization:** Mengekstraksi graf eksekusi (*tool calls*) yang berhasil ≥5x berturut-turut menjadi *Learned Skill* permanen agar sistem bekerja lebih cepat di kemudian hari.
*   **Auto-Generate AI Core:** Kemampuan menghasilkan profil identitas dan konfigurasi internal (*system prompt*) secara otomatis dari deskripsi bahasa natural pengguna dalam <10 detik.

### 3. 🔀 Dynamic Model Routing (Zero-Hardcode)
*   **Self-Learning Routing (>85% Accuracy):** Sistem menganalisis histori performa agen setiap 5 menit. Jika pengguna tidak menentukan model secara manual, sistem akan mendistribusikan *task* ke model paling kompeten secara dinamis berdasarkan 7-lapis prioritas.
*   **Transparent UI Auto-Fill:** Antarmuka secara jujur (`Real-time 30s`) menampilkan label `🤖 Auto — [Nama Model]` pada panel *Integrations* sehingga keputusan *routing* AI tidak lagi menjadi *black-box*.
*   **Absolute Manual Override:** Pilihan model manual dari pengguna adalah prioritas mutlak yang tidak akan pernah ditimpa oleh sistem otomatis (*auto-routing*).
*   **Built-in Free Image Generation:** Integrasi *native* dengan Pollinations AI yang menjamin pembuatan gambar 100% gratis, super cepat, tanpa perlu registrasi atau memasukkan API key sama sekali.

### 4. 🎤 Voice-to-Voice Interaction (NEW!)
*   **Seamless Voice Chat:** Kirim pesan suara di Telegram → Bot mentranskrip dengan Whisper → AI memproses → Jawaban dikembalikan dalam bentuk voice note + caption teks.
*   **Multi-Language TTS:** Mendukung 5 bahasa (Indonesia, English, Arabic, Japanese, Jawa) dengan edge-tts yang 100% gratis dan unlimited.
*   **Smart Audio Processing:** Otomatis memotong jawaban panjang, fallback ke teks jika TTS gagal, dan tidak menyimpan file audio di server (privacy-first).
*   **AI Role Integration:** Terintegrasi penuh dengan AI Role Mapping — Anda bisa set model khusus untuk `multimodal` (Whisper) dan `audio_gen` (TTS) atau biarkan sistem auto-routing.

### 5. 🎨 UI/UX & Interactive Interface (NEW!)
*   **Default Simple Mode & UI Refinements (v4.1.21):** Default UI kini diset ke Simple Mode (Agent OFF) untuk respons cepat tanpa overhead preprocessor. Tombol **🤖 Agent** didesain ulang dengan indikator status ON/OFF interaktif dan tooltip informatif.
*   **Tavily Web Search Integration:** Simple mode dapat secara otomatis melakukan pencarian web real-time (Tavily API) jika memerlukan informasi terkini.
*   **Expandable Thinking Process:** Antarmuka visual yang menampilkan langkah proses berpikir agen secara transparan ala Claude AI. Pengguna bisa mengklik ikon khusus untuk melihat detail langkah pemikiran model.
*   **Drag & Drop Image Support:** Kemudahan mengirimkan input gambar dengan menyeret dan menjatuhkan file langsung ke area chat UI.
*   **Auto-Focus & Smooth Interaction:** Input chat otomatis fokus kembali setelah mengirim pesan, dilengkapi penanganan error dashboard yang lebih baik untuk pengalaman integrasi yang mulus.

### 6. 🛡️ Hardened Resilience & Execution Continuity
*   **State Checkpointing & DAG Watchdog:** Eksekusi tugas diamankan di dalam basis data persisten. Jika sistem macet atau progres stagnan lebih dari 5 giliran, Watchdog otomatis memaksa pemulihan tanpa instruksi halusinasi ke *LLM*.
*   **Actionable Error Translator & Circuit Breaker:** Sistem akan mengonversi pesan error teknis menjadi langkah taktis (misal: "Port bentrok, kill PID 1234"). Jika alat (*tool*) terus gagal 3x, ia akan dikenai penangguhan (*suspend*) sesi secara sementara agar tidak memblokir antrean.
*   **Truncation Recovery:** Jika LLM memotong *output* kode akibat limit *max_tokens*, Orchestrator secara otomatis menyuntikkan *prompt* pelanjut dan merekatkan hasilnya di balik layar.
*   **Dead Letter Queue (DLQ):** Setiap tugas gagal yang tidak tertolong (*unrecoverable*) akan masuk ke DLQ selama 14 hari untuk tujuan peninjauan manual, sehingga tidak ada pekerjaan yang lenyap tanpa jejak.

### 7. 🚀 Performance & Scalability Optimizations (v4.1.21)
*   **Concurrent Module Startup:** Menginisialisasi komponen backend opsional (RAG, Model Manager, Memory) secara paralel menggunakan `asyncio.gather` sehingga memangkas waktu start server secara masif.
*   **Non-Blocking Model Discovery:** Proses interview kemampuan model (`Capability Map`) dimigrasi sepenuhnya ke background thread, memuat data cache disk instan saat startup tanpa menghalangi peluncuran server API.
*   **Aggressive Asset Caching & Compression:** Penerapan `GZipMiddleware` pada respons API dan custom static files handler (`CachedStaticFiles`) dengan header `Cache-Control` permanen (`immutable`) untuk aset frontend.
*   **Thread-Safe WAL Mode SQLite:** Konfigurasi `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` pada sinkronisasi DB engine (`SessionLocal`) guna mencegah kunci basis data (*database locks*) saat Celery worker beroperasi.
*   **Dynamic Token Pricing & Cost Tracking:** Konfigurasi kustom token pricing via `data/pricing_overrides.json`, dynamic token pricing resolver (`get_pricing`) dengan support provider prefix stripping, serta pencatatan otomatis input/output token dan biaya eksekusi (USD) ke database metrics.

---

## 🏛️ System Architecture

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#ffffff',
    'primaryTextColor': '#1e293b',
    'primaryBorderColor': '#cbd5e1',
    'lineColor': '#64748b',
    'secondaryColor': '#f8fafc',
    'tertiaryColor': '#f1f5f9'
  }
}}%%

graph TB
    %% Styling Global Toko / Node
    classDef entry fill:#e2e8f0,stroke:#94a3b8,stroke-width:1px,rx:5px,ry:5px;
    classDef process fill:#ffffff,stroke:#cbd5e1,stroke-width:1px,rx:6px,ry:6px;
    classDef router fill:#0f172a,textColor:#ffffff,stroke:#0f172a,stroke-width:1px,rx:4px,ry:4px;
    classDef engine fill:#38bdf8,stroke:#0284c7,stroke-width:1px,rx:4px,ry:4px;
    classDef agent fill:#f0fdf4,stroke:#bbf7d0,textColor:#166534,stroke-width:1px;
    classDef db fill:#f8fafc,stroke:#94a3b8,stroke-dasharray: 3 3,rx:8px,ry:8px;
    classDef output fill:#0ea5e9,textColor:#ffffff,stroke:#0284c7,stroke-width:1px,rx:20px;

    %% --- ENTRY POINTS LAYER ---
    subgraph EP ["📥 Entry Points"]
        CB[Celery Beat / Worker] -->|Poll Due Tasks| ST[(Scheduled Tasks DB)]
        ST -->|Trigger Task| AG[API Gateway / UI]
        UR[User Request] --> AG
    end
    class CB,ST,UR,AG entry;

    %% --- ORCHESTRATION & ROUTING ---
    subgraph OR ["🧠 Orchestration & Routing"]
        AG --> RP{Request Preprocessor}
        
        %% Agent Mode Path
        RP -->|Agent Mode| TD[Task Decomposer]
        TD --> DB[DAG Builder]
        DB --> AS[Agent Scorer]
        AS -->|Zero-Hardcode| DR[Dynamic Routing Engine]
        
        %% Simple Mode Path
        RP -->|Simple Mode Bypass| DR
        RP -->|Complexity >= 0.8| DR
        RP -->|Inject Context| AU[Auto-Fill UI Badge]
    end
    class RP router;
    class TD,DB,AS,AU process;
    class DR engine;

    %% --- EXECUTION LAYER & CONSENSUS ---
    subgraph EX ["⚡ Execution Layer & Consensus"]
        DR --> SA[System Agent]
        DR --> RA[Research Agent]
        DR --> CA[Coding Agent]
        
        SA & RA & CA --> SS[Secure Sandbox]
        SA & RA & CA --> MC[Multi-Model Consensus]
    end
    class SA,RA,CA agent;
    class SS,MC process;

    %% --- INTELLIGENCE & MEMORY ---
    subgraph IM ["💾 Intelligence & Memory"]
        QE[Quality Engine]
        RAg[Result Aggregator]
        
        PM[(Procedural Memory)]
        BRM[(Byte Rover Memory)]
    end
    class QE,RAg process;
    class PM,BRM db;

    %% --- ALUR INTER-LAYER ---
    SS --> QE
    MC --> RAg
    AU --> PM
    
    PM --> RAg
    BRM --> RAg
    
    %% --- OUTPUT LAYER ---
    RAg -->|Tavily Search| RWS[Real-time Web Search]
    RWS --> FR((Final Response))
    MC -->|Simple Path| FR
    
    class RWS process;
    class FR output;

    %% Layout Adjustment
    style EP fill:#f8fafc,stroke:#e2e8f0,stroke-width:1px;
    style OR fill:#f8fafc,stroke:#e2e8f0,stroke-width:1px;
    style EX fill:#f8fafc,stroke:#e2e8f0,stroke-width:1px;
    style IM fill:#f8fafc,stroke:#e2e8f0,stroke-width:1px;
```


---

## 💻 Hardware & AI Model Requirements

Untuk performa optimal terutama saat menjalankan **15+ agent secara paralel**:

| Komponen | Minimum | Rekomendasi |
|----------|---------|-------------|
| **RAM**  | 4 GB*   | 16 GB+      |
| **CPU**  | 2 Cores | 8 Cores+    |
| **Disk** | 20 GB   | 100 GB (SSD)|

*\*Catatan: Minimum 4GB disarankan untuk beban terbatas (~5-8 agent). Untuk kapasitas paralel maksimum, setidaknya dibutuhkan 8GB-16GB RAM.*

### ⚠️ Syarat Model AI (Penting!)
Sistem menggunakan **Native Function Calling** untuk eksekusi tanpa batas dan toleransi *error* maksimal. Gunakan tombol **Zap Test (⚡)** di menu *Integrations* untuk memeriksa kompatibilitas model.
*   **Model yang Didukung:** GPT-4o, gpt-4o-mini, Claude 3.5 Sonnet, Gemini 1.5/2.5 Pro/Flash, Llama 3/3.1, Qwen 2.5, Mistral-Nemo.
*   **TIDAK Didukung:** Model lawas (pra-2024), Llama 2, atau AI yang tidak mendukung kapabilitas penggunaan alat (*Tool Use*).

---

## 🔒 Security Model & Data Privacy

*   **Network Isolation:** Mode pekerja (*worker*) diisolasi penuh dalam kontainer Docker, sehingga tidak dapat mengakses OS *Host* maupun melakukan eksploitasi *kernel*.
*   **Privacy-Safe Prompting:** Nama asli LLM komersial disembunyikan menggunakan pelindung tiga lapis (*Prompt Alias*, *Post-processing Regex*, dan *Audit Log*) sehingga identitas LLM tidak bocor ke antarmuka klien.
*   **Wipe & Export:** Anda memiliki kontrol penuh. Memori dapat dihapus total (*wipe*) kapan saja lewat CLI atau UI. Riwayat percakapan dapat diekspor menjadi format PDF, DOCX, TXT, dan XLSX.
*   **Independent Local RAG (Git Tracking Fix):** Pelacakan repositori mengabaikan database binary (`chroma.sqlite3`) secara default. Setiap environment (dev/prod) memiliki data RAG lokal masing-masing untuk menghindari merge conflict saat melakukan update.

---

## 🚀 Real Execution Trace (Example)

**Input:** *"Bangun landing page produk kopi, tambahkan form kontak, dan siapkan script deploy ke VPS."*

1.  **Decomposition:** Sistem memecah belasan instruksi, dikelompokkan ke 4 sub-task utama: (A) Desain UI, (B) Backend Form, (C) Dockerization, (D) Deployment Script.
2.  **Dynamic Routing:** Agent Scorer mendeteksi AI Roles Mapping kosong → menggunakan *Performance Cache* → memilih AI paling jago *front-end* untuk (A) dan spesialis *devops* untuk (D).
3.  **Parallel Execution:** Agent-1 menulis HTML/CSS, Agent-2 merakit skrip Python/Node.js secara **bersamaan**.
4.  **Resilience:** Terjadi interupsi *Token Limit* di baris ke-150 CSS. *Truncation Recovery* menyambungnya otomatis di latar belakang.
5.  **Validation:** Terjadi error `EADDRINUSE` saat agen mencoba mengetes server. *Error Translator* memerintahkan `execute_bash` untuk mencari dan membunuh proses port terkait, lalu uji ulang sukses.
6.  **Crystallization:** Seluruh urutan sukses ini direkam ke *Procedural Memory*. Jika diminta hal serupa besok, sistem akan mengeksekusinya lebih instan.

---

## ⚡ Instalasi

### 1. Prasyarat Sistem
Pastikan sistem Anda (Linux/VPS) telah memiliki:
*   **Docker** (versi 24.0+) & **Docker Compose**
*   Port **7860** (Web UI & Orchestrator API) tidak terblokir oleh Firewall (UFW).

### 2. Kloning Repositori & Konfigurasi
```bash
git clone https://github.com/maztfajarwahyudi/ai-super.git
cd ai-super

# 1. Salin file environment
cp .env.example .env

# 2. Buka file .env dan atur kredensial Admin Anda (WAJIB)
# nano .env
# Ubah bagian ADMIN_USERNAME dan ADMIN_PASSWORD sesuai keinginan Anda
```

### 3. Build & Jalankan
Cukup satu perintah untuk membangkitkan seluruh arsitektur *Microservices*:
```bash
docker compose up -d --build
```
Sistem akan mulai merakit *container* backend, frontend, basis data vektor, dan lapisan *cache*.

---

## 🎮 Panduan Penggunaan (Quick Start)

Setelah instalasi selesai, ikuti langkah berikut untuk mengoperasikan AI Orchestrator:

1.  **Akses Dashboard:** Buka peramban web dan navigasi ke `http://localhost:7860` (atau IP VPS Anda).
    *   Sistem akan meminta **Login**. Gunakan `ADMIN_USERNAME` dan `ADMIN_PASSWORD` yang telah Anda atur di file `.env` sebelumnya.
2.  **Konfigurasi Kunci API (Wajib):** 
    *   Buka menu ⚙️ **Integrations**.
    *   Masukkan API Key dari penyedia LLM pilihan Anda (misal: OpenAI, Anthropic, Gemini, Groq, atau endpoint lokal Ollama).
    *   *(Opsional)* Aktifkan **🎨 Pollinations AI** jika Anda ingin menggunakan fitur pembuatan gambar *tanpa batas dan tanpa API key*.
    *   Klik **Simpan**.
3.  **Verifikasi Native Tools:**
    *   Masih di menu Integrations, klik tombol petir **Zap Test (⚡)** di samping model AI pilihan Anda.
    *   Pastikan notifikasi memunculkan indikator warna **Hijau** (Mendukung *Native Tools*). Jika merah/kuning, AI tersebut tidak kompatibel dengan orkestrasi lanjutan.
4.  **Atur AI Roles (Opsional):**
    *   Buka menu 🤖 **AI Roles Mapping**.
    *   Anda bisa mengatur model spesifik untuk tugas tertentu (misal: *Claude 3.5 Sonnet* untuk Coding, *Gemini 1.5 Pro* untuk Riset). Jika dikosongkan, fitur *Auto-Routing* akan menanganinya untuk Anda.
5.  **Mulai Memberi Perintah:**
    *   Kembali ke Dashboard/Chat. Berikan instruksi kompleks seperti: *"Deploy aplikasi Express.js sederhana di port 8080 dengan endpoint /ping."*
    *   Duduk santai dan perhatikan agen merencanakan DAG, menulis *source code*, mengeksekusi *bash*, memperbaiki *error* secara otonom, dan mengembalikan tautan yang sudah siap pakai!

---

## 📄 Lisensi
Copyright (c) 2026 **maztfajarwahyudi**. Proprietary - View Only.

<br>
<p align="center">
  <i>Focus on Execution. Built for Engineers.</i><br>
  <b>AI ORCHESTRATOR v4.1.21 — A True High-Autonomy Engineering Agent.</b>
</p>
