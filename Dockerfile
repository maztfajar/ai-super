# ==========================================
# TAHAP 1: Build Frontend (Node.js)
# ==========================================
FROM node:18-alpine AS frontend-builder
# Masuk khusus ke folder frontend
WORKDIR /app/frontend 

# Salin dan install dependensi frontend
COPY frontend/package*.json ./
RUN npm install

# Salin source code frontend dan jalankan build
COPY frontend/ ./
RUN npm run build 
# (Pastikan perintah build Anda benar, biasanya menghasilkan folder 'dist' atau 'build')

# ==========================================
# TAHAP 2: Setup Backend Akhir (Python)
# ==========================================
FROM python:3.10-slim
WORKDIR /app

# Install dependensi sistem yang mungkin dibutuhkan AI
RUN apt-get update && apt-get install -y gcc g++ make && rm -rf /var/lib/apt/lists/*

# Salin konfigurasi Python dari folder backend
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Salin seluruh source code backend
COPY backend/ ./backend/

# Salin hasil kompilasi UI dari Tahap 1 ke dalam folder backend
# (Sesuaikan 'dist' dengan nama folder output build frontend Anda)
COPY --from=frontend-builder /app/frontend/dist ./backend/static

# Masuk ke direktori backend untuk menjalankan server
WORKDIR /app/backend

# Jalankan server AI Anda (Sesuaikan main.py dengan file utama backend Anda)
CMD ["python", "main.py"]
