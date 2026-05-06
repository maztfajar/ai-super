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

# Install Playwright and its dependencies
RUN pip install playwright && \
    playwright install --with-deps chromium

# Copy backend requirements
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# --- PROTEKSI KODE SUMBER ---
# Kompilasi semua file .py menjadi bytecode .pyc dan hapus file aslinya
RUN python3 -m compileall -b /app/backend || (echo "Compilation failed!" && exit 1) && \
    find /app/backend -name "*.py" -delete
# ----------------------------

# Copy frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy other necessary files
COPY .env.example .env

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/chroma_db /app/data/logs /app/rag_documents

# Expose the application port
EXPOSE 7860

# Volume for persistent data
VOLUME ["/app/data", "/app/rag_documents"]

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV HOST=0.0.0.0
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Healthcheck to monitor API status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/api/health || exit 1

# Run the application using the compiled main.pyc
CMD ["python", "backend/main.pyc"]

