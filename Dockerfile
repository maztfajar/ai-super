# Build Stage 1: Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Build Stage 2: Backend & Final Image
FROM python:3.12-slim
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
RUN python3 - <<'PYEOF'
import compileall, sys, os

dirs = [
    "/app/backend/agents",
    "/app/backend/api",
    "/app/backend/core",
    "/app/backend/db",
    "/app/backend/integrations",
    "/app/backend/memory",
    "/app/backend/rag",
    "/app/backend/workflow",
]
files = ["/app/backend/main.py"]

print("=== Compiling Python files ===")
ok = True
for d in dirs:
    if os.path.isdir(d):
        result = compileall.compile_dir(d, force=True, quiet=0, legacy=True)
        if not result:
            print(f"ERROR: Failed to compile directory: {d}", file=sys.stderr)
            ok = False
    else:
        print(f"WARNING: Directory not found, skipping: {d}")

for f in files:
    if os.path.isfile(f):
        result = compileall.compile_file(f, force=True, quiet=0, legacy=True)
        if not result:
            print(f"ERROR: Failed to compile file: {f}", file=sys.stderr)
            ok = False
    else:
        print(f"WARNING: File not found, skipping: {f}")

if not ok:
    print("COMPILATION FAILED", file=sys.stderr)
    sys.exit(1)

print("=== Compilation OK ===")
PYEOF
RUN echo "=== Removing .py source files ===" && \
    find /app/backend -name "*.py" -not -path "*/scripts/*" -delete && \
    echo "=== Done ==="
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
ENV PYTHONDONTWRITEBYTECODE=0

# Healthcheck to monitor API status
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7860/api/health || exit 1

# Run the application using the compiled main.pyc
CMD ["python", "backend/main.pyc"]

