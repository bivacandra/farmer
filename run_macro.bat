@echo off
title Tantra Farmer Macro Launcher

:: Gunakan pushd agar UNC path (\\wsl.localhost\...) otomatis dimount ke temporary drive letter di Windows
pushd "%~dp0"

echo ========================================================
echo         TANTRA FARMER - INVENTORY ^& SELLER MACRO
echo ========================================================
echo Direktori Aktif: %CD%
echo.

set PYTHON_CMD=python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        echo [ERROR] Python tidak terdeteksi di PATH Windows Anda!
        echo Silakan install Python 3.10+ dari python.org dan pastikan
        echo mencentang "Add Python to PATH" saat instalasi.
        echo.
        pause
        popd
        exit /b 1
    )
)

echo Memeriksa dan menginstall dependensi...
%PYTHON_CMD% -m pip install -r requirements.txt --quiet --disable-pip-version-check

echo.
echo Membuka GUI Makro...
%PYTHON_CMD% gui.py

if %errorlevel% neq 0 (
    echo.
    echo Terjadi kendala saat menjalankan gui.py.
    pause
)

popd
