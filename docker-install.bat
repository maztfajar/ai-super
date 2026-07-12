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

:: Salin .env.example ke .env jika belum ada
if not exist ".env" (
    if exist ".env.example" (
        echo [OK] Membuat file konfigurasi .env...
        copy .env.example .env >nul
    ) else (
        echo [WARNING] File .env.example tidak ditemukan. Melewati pembuatan .env.
    )
) else (
    echo [INFO] File .env sudah ada, tidak akan ditimpa.
)

:: Buat folder direktori persistent agar tidak ada masalah permission saat di mount
echo [OK] Membuat folder penyimpanan data (volumes)...
if not exist "data\logs" mkdir data\logs
if not exist "data\uploads" mkdir data\uploads
if not exist "data\chroma_db" mkdir data\chroma_db
if not exist "rag_documents" mkdir rag_documents

echo.
echo ========================================================
echo Menjalankan aplikasi AI Orchestrator...
echo ========================================================
echo Ini mungkin memakan waktu beberapa menit saat pertama kali dijalankan karena harus mengunduh image.
echo.

docker-compose up -d

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
echo 🎉 INSTALASI SELESAI 🎉
echo ========================================================
echo Aplikasi berjalan di belakang layar.
echo Silakan buka browser Anda di: http://localhost:7860
echo.
echo Untuk melihat log, ketik: docker-compose logs -f
echo Untuk menghentikan, ketik: docker-compose down
echo ========================================================
pause
