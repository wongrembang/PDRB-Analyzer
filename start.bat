@echo off
title PDRB Analyser - Jawa Tengah
color 0A

echo ================================================
echo   PDRB Analyser - Dashboard Jawa Tengah
echo ================================================
echo.

REM Cek apakah Python tersedia
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python 3.9+ dari https://python.org
    echo Pastikan centang "Add Python to PATH" saat instalasi.
    pause
    exit /b 1
)

REM Cek apakah streamlit sudah terinstall
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Menginstall dependencies... (proses ini hanya sekali)
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Gagal menginstall dependencies!
        pause
        exit /b 1
    )
)

echo [INFO] Menjalankan aplikasi...
echo [INFO] Buka browser dan akses: http://localhost:8501
echo [INFO] Untuk akses dari komputer lain di jaringan: http://[IP-KOMPUTER]:8501
echo [INFO] Tekan Ctrl+C untuk menghentikan aplikasi.
echo.

REM Buka browser otomatis setelah 3 detik
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8501"

REM Jalankan streamlit dengan python -m (aman di semua konfigurasi PATH)
python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0

pause
