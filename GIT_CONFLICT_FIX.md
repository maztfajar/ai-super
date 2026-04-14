# 🔧 VPS Git Conflict Resolution Guide

## Problem Status
```
CONFLICT (content): Merge conflict in backend/data/chroma_db/chroma.sqlite3
Changes to be committed: modified capability_map.json
Unmerged paths: both modified chroma.sqlite3
```

## ⚡ Quick Fix (Copy & Paste)

Run ini di VPS anda (satu kali):

```bash
cd ~/ai-super

# 1. Abort merge + clear stash
git merge --abort 2>/dev/null || true
git stash drop 2>/dev/null || true

# 2. Remove binary conflict file
git rm --cached backend/data/chroma_db/chroma.sqlite3 2>/dev/null || true
rm -f backend/data/chroma_db/chroma.sqlite3

# 3. Ensure .gitignore has chroma.sqlite3 (already done)
grep -q "backend/data/chroma_db/chroma.sqlite3" .gitignore || echo "backend/data/chroma_db/chroma.sqlite3" >> .gitignore
git add .gitignore
git commit -m "ignore: chroma database" || true

# 4. Clean untracked files
rm -f backend/hasil_suara.mp3 deploy.sh scripts/package*.json 2>/dev/null || true

# 5. Pull latest
git pull

echo "✅ Git fixed!"
```

Atau gunakan script yang sudah disiapkan:

```bash
cd ~/ai-super
chmod +x scripts/fix-git-conflict.sh
bash scripts/fix-git-conflict.sh
```

---

## 🚀 Setelah Git Fixed, Deploy:

```bash
cd ~/ai-super

# 1. Frontend rebuild
cd frontend
npm install --legacy-peer-deps
npm run build
cd ..

# 2. Restart services
bash scripts/stop.sh
sleep 2
bash scripts/start.sh
```

---

## ℹ️ Penjelasan

**Kenapa terjadi conflict?**
- `chroma.sqlite3` adalah binary file (ChromaDB vector store)
- File ini tidak seharusnya di-track dalam git
- Setiap environment (local dev, VPS) punya database mereka sendiri
- Ketika cherry-pick changes, binary file mengalami merge conflict

**Solusi permanent:**
- File sudah di `.gitignore` di repo
- Untuk VPS yang sudah punya conflict, jalankan fix script
- Di masa depan tidak akan ada conflict lagi

---

## ✅ Verify Setelah Fix

```bash
# Check git status clean
git status
# Should show: "On branch main, Your branch is up to date"

# Check services running
curl http://localhost:7860 -I
# Should return: HTTP 200

# Check database
ls -lah backend/data/ai-super-assistant.db
# Should exist and have reasonable size
```

---

## 🆘 Jika Masih Error

Jika `scripts/fix-git-conflict.sh` tidak work, manual steps:

```bash
cd ~/ai-super

# 1. Hard reset to remote
git fetch origin
git reset --hard origin/main

# 2. Rebuild frontend
cd frontend
npm install --legacy-peer-deps
npm run build
cd ..

# 3. Restart
bash scripts/stop.sh
sleep 2
bash scripts/start.sh
```

**Warning:** `git reset --hard` akan menghilangkan local changes. Only use jika truly stuck.
