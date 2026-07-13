@echo off
REM Bam dup file nay de cai One Tap Translate tu dong.
REM No goi installer PowerShell (tu do Python 3.12, cai thu vien, tao shortcut).
cd /d "%~dp0"
title One Tap Translate - Cai dat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if errorlevel 1 (
  echo.
  echo Co loi xay ra khi cai. Xem thong bao ben tren.
  pause
)
