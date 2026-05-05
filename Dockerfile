# --- TAHAP 1: Build ---
FROM node:18-alpine AS builder
WORKDIR /app

# Install dependensi
COPY package*.json ./
RUN npm install

# Salin seluruh source code
COPY . .

# Build aplikasi (Ubah jika perintah build Anda berbeda)
RUN npm run build 

# --- TAHAP 2: Produksi ---
FROM node:18-alpine
WORKDIR /app

# Salin hasil build dan file package
COPY --from=builder /app/dist ./dist
COPY package*.json ./

# Install dependensi khusus produksi
RUN npm install --production

# Jalankan aplikasi (Sesuaikan lokasi file utama Anda)
CMD ["node", "dist/index.js"]
