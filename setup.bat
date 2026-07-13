@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title One Tap Translate - Setup

echo ============================================
echo   One Tap Translate - Cai dat tu dong
echo ============================================
echo.

REM --- 1. Tim Python 3.12 ---
set "PYCMD="
py -3.12 --version >nul 2>nul && set "PYCMD=py -3.12"
if not defined PYCMD (
  for /f "delims=" %%v in ('python --version 2^>^&1') do echo %%v | findstr /r "3\.12\." >nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo [X] Khong tim thay Python 3.12.
  echo     Tai o: https://www.python.org/downloads/  ^(nho tick "Add Python to PATH"^)
  echo     Roi chay lai setup.bat.
  echo.
  pause
  exit /b 1
)
echo [OK] Python 3.12: %PYCMD%
echo.

REM --- 2. Tao moi truong ao ---
if not exist ".venv\Scripts\python.exe" (
  echo [..] Tao moi truong ao .venv ...
  %PYCMD% -m venv .venv || ( echo [X] Tao venv that bai & pause & exit /b 1 )
)

REM --- 3. Cai PaddlePaddle theo phan cung ---
echo.
echo Ban co card do hoa NVIDIA khong? (GPU giup OCR nhanh hon nhieu)
set /p "GPU=  Go Y neu co, N neu chi CPU [Y/N]: "
echo.
echo [..] Dang cai PaddlePaddle (nang, tai vai tram MB - vui long doi)...
if /i "!GPU!"=="Y" (
  .venv\Scripts\python -m pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
) else (
  .venv\Scripts\python -m pip install paddlepaddle
)
if errorlevel 1 ( echo [X] Cai paddle that bai & pause & exit /b 1 )

REM --- 4. Cai cac thu vien con lai ---
echo.
echo [..] Dang cai cac thu vien con lai...
.venv\Scripts\python -m pip install -r requirements.txt || ( echo [X] Cai requirements that bai & pause & exit /b 1 )

echo.
echo ============================================
echo   Xong! Nhan doi run.bat de mo app.
echo   (Lan chay dau se tu tai model PP-OCRv5 ~22MB)
echo ============================================
pause
