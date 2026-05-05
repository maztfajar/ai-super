# Build Stage 1: Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Build Stage 2: Backend & Final Image
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN pip install playwright && playwright install-deps chromium

# Copy backend requirements
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# --- PROTEKSI KODE SUMBER ---
# Kompilasi semua file .py menjadi bytecode .pyc dan hapus file aslinya
# Ini mempersulit pengguna untuk melacak atau memodifikasi logika bisnis Anda.
RUN python -m compileall -b /app/backend && \
    find /app/backend -name "*.py" -delete
# ----------------------------

# Copy frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy other necessary files
COPY .env.example .env

# Expose the application port
EXPOSE 7860

# Volume for persistent data
VOLUME ["/app/data"]

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV HOST=0.0.0.0
ENV PORT=7860

# Run the application (Python akan otomatis menjalankan file .pyc)
CMD ["python", "backend/main.pyc"]
