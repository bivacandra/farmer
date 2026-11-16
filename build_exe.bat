@echo off
title Build Tantra Farmer Executable
echo ========================================================
echo       TANTRA FARMER - BUILD EXECUTABLE (PYINSTALLER)
echo ========================================================
echo.

:: Cek Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di PATH! Silakan install Python 3.10+ terlebih dahulu.
    pause
    exit /b 1
)

echo [1/3] Menginstall dependensi dan PyInstaller...
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [2/3] Membangun TantraFarmer.exe dengan PyInstaller...
pyinstaller --clean tantra_farmer.spec

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build gagal! Periksa pesan error di atas.
    pause
    exit /b 1
)

echo.
echo [3/3] Mengompresi paket rilis ke ZIP...
powershell -Command "Compress-Archive -Path dist\TantraFarmer\* -DestinationPath dist\TantraFarmer-Windows.zip -Force"

echo.
echo ========================================================
echo [SUKSES] Build selesai!
echo File executable: dist\TantraFarmer\TantraFarmer.exe
echo File rilis zip: dist\TantraFarmer-Windows.zip
echo ========================================================
pause
