# 🧠 AI SUPER ASSISTANT — AI Super Assistant

Platform AI Self-Hosted dengan multi-model, knowledge base, workflow otomatis, integrasi Telegram/WhatsApp, dan keamanan 2FA.

---

## ⚡ Instalasi Cepat

```bash
cd ai-super-assistant
bash scripts/install.sh
bash scripts/start.sh
```

Buka: **http://localhost:7860**  
Login default: `admin` / `ai-super-assistant2024`

> ⚠️ Segera ganti password default setelah login pertama!

---

## 📋 System Requirements

| | Minimum | Rekomendasi |
|---|---|---|
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| RAM | 1 GB | 4 GB+ |
| Python | 3.10+ | 3.11 |
| Node.js | 18+ | 20 LTS |

---

## 🗂️ Struktur Folder

```
ai-super-assistant/
├── backend/          # FastAPI Python backend
│   ├── api/          # Endpoint API
│   ├── core/         # Auth, config, services
│   ├── db/           # Models & database
│   └── data/         # Database & uploads (auto-created)
├── frontend/         # React + Vite frontend
│   ├── src/
│   │   ├── pages/    # Halaman aplikasi
│   │   ├── components/
│   │   └── hooks/
│   └── public/
├── scripts/          # Script utility
│   ├── install.sh    # Installer otomatis
│   ├── start.sh      # Jalankan aplikasi
│   ├── stop.sh       # Hentikan aplikasi
│   └── migrate-db.sh # Migrasi database
├── .env.example      # Template konfigurasi
└── README.md
```

---

## ⚙️ Konfigurasi (.env)

```env
APP_NAME=NamaAplikasi         # Nama tampil di sidebar
SECRET_KEY=random-32-chars    # WAJIB diganti untuk keamanan
ADMIN_USERNAME=admin
ADMIN_PASSWORD=passwordbaru

# AI Providers (isi minimal satu)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
OLLAMA_HOST=http://localhost:11434

# SMTP untuk reset password via email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=email@gmail.com
SMTP_PASS=app-password
```

---

## 🛠️ Script Utility

```bash
bash scripts/install.sh       # Install semua dependencies
bash scripts/start.sh         # Jalankan aplikasi
bash scripts/stop.sh          # Hentikan aplikasi
bash scripts/migrate-db.sh    # Perbaiki/update database
bash scripts/reset-password.sh # Reset password darurat
```

---

## 📖 Dokumentasi Lengkap

Lihat file **AI SUPER ASSISTANT_Dokumentasi.docx** untuk panduan lengkap:
- Instalasi step-by-step
- Konfigurasi semua fitur
- Panduan setiap menu
- Setup 2FA & keamanan
- Troubleshooting

---

## 🔐 Keamanan

- Brute force protection (5x gagal → kunci 5 menit)
- Two-Factor Auth: TOTP (Google Authenticator) + Telegram OTP
- JWT token dengan expiry 7 hari
- Recovery password: Email / Telegram OTP / Token Recovery / Manual
- Mode gelap & terang

---

*AI SUPER ASSISTANT v1.0 — Self-Hosted AI Assistant*
