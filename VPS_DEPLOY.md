## Step 1: Secure Installation di VPS

Gunakan installer otomatis untuk mengunduh konfigurasi tanpa mengekspos *source code* mentah:

```bash
curl -fsSL https://raw.githubusercontent.com/maztfajar/repo-installer-publik/main/install.sh | bash
```

---

## Step 2: Konfigurasi .env

```bash
cd ~/ai-super/frontend
npm install --legacy-peer-deps
npm run build
cd ..
```

---

## Step 3: Restart Services (Manual)

```bash
bash scripts/stop.sh
sleep 2
bash scripts/start.sh
```

---

## 🐳 Step 4: Docker Deployment (Recommended)

Jika Anda ingin menggunakan Docker untuk kemudahan manajemen dan update otomatis:

```bash
cd ~/ai-super

# 1. Jalankan dengan Docker Compose
docker-compose up -d

# 2. Check logs
docker logs -f ai-orchestrator
```

**Update otomatis dengan Watchtower:**
Docker Compose sudah dikonfigurasi dengan Watchtower yang akan mengecek update image di Docker Hub setiap 5 menit. Cukup `push` ke GitHub, dan VPS Anda akan terupdate otomatis.

---

## 🧪 Test Deployment

```bash
# Check API
curl http://localhost:7860 -I

# Check chat endpoint exists
curl -X POST http://localhost:7860/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' 2>/dev/null | head -50
```

---

## 📋 Changedlog dari Master

Sejak VPS deployment awal, kami sudah add:

1. **Thinking Process Feature** ⭐
   - Expandable thinking section like Claude AI
   - User bisa klik icon untuk lihat model's thinking steps
   - Status messages di-collect dan di-display hidden

2. **Database Migration**
   - Tambah `thinking_process` column ke messages table
   - Auto-migrated saat startup

3. **Frontend Improvements**
   - Better error handling untuk dashboard
   - Drag & drop image support
   - Auto-focus input setelah send

4. **Git Tracking Fix** (CRITICAL)
   - Removed binary chroma.sqlite3 dari tracking
   - Prevent future merge conflicts
   - Each environment maintains own RAG data

---

## ⚠️ Important Notes

- Binary database files (chroma.sqlite3) tidak lagi ter-track
- Setiap environment (dev, prod) punya sendiri copy
- `git pull` di masa depan akan smooth tanpa conflicts
- RAG indices tetap intact di local environment

---

## 🆘 Troubleshooting

**Jika git masih stuck:**
```bash
cd ~/ai-super
git fetch origin
git reset --hard origin/main
# Then rebuild & restart
```

**Jika frontend error:**
```bash
rm -rf frontend/node_modules frontend/dist
npm install --legacy-peer-deps
npm run build
```

**Jika API won't start:**
```bash
lsof -i :7860  # Find process using port
kill -9 <PID>
bash scripts/start.sh
```
