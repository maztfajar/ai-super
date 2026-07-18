@echo off
title AI ORCHESTRATOR - Docker Installation
echo ========================================================
echo        AI ORCHESTRATOR - DOCKER INSTALLER (WINDOWS)
echo ========================================================
echo.

:: Cek apakah Docker terinstall
docker --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker tidak ditemukan!
    echo Silakan install Docker Desktop terlebih dahulu dari:
    echo https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)

:: Cek status Docker daemon
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker Engine belum berjalan!
    echo Tolong buka aplikasi "Docker Desktop" dan tunggu hingga siap, lalu jalankan script ini lagi.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker terdeteksi dan berjalan.
echo.

:: Buat folder direktori persistent
echo [OK] Membuat folder penyimpanan data (volumes)...
if not exist "data\logs" mkdir data\logs
if not exist "data\uploads" mkdir data\uploads
if not exist "data\chroma_db" mkdir data\chroma_db
if not exist "rag_documents" mkdir rag_documents

echo.
echo ========================================================
echo   Menjalankan AI Orchestrator...
echo ========================================================
echo   Mengunduh image dari DockerHub (mungkin butuh beberapa menit)
echo.

docker compose up -d 2>nul || docker-compose up -d

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Terjadi kesalahan saat menjalankan docker-compose.
    echo Pastikan tidak ada aplikasi lain yang menggunakan port 7860.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   INSTALASI SELESAI!
echo ========================================================
echo.
echo   Buka browser: http://localhost:7860
echo.
echo   +-----------------------------------------------+
echo   ^|        KREDENSIAL LOGIN DEFAULT               ^|
echo   ^|                                               ^|
echo   ^|   Username : admin                            ^|
echo   ^|   Password : admin123                         ^|
echo   ^|                                               ^|
echo   ^|   SEGERA ganti password setelah login!        ^|
echo   +-----------------------------------------------+
echo.
echo   Untuk menambahkan API key (OpenAI, Gemini, dll):
echo     Login -^> Settings -^> API Keys
echo.
echo   Perintah berguna:
echo     docker compose logs -f              -^> Lihat log
echo     docker compose down                 -^> Hentikan
echo     docker compose pull ^&^& docker compose up -d  -^> Update
echo ========================================================
pause
