@echo off
title Spotify Lyrics Overlay (Consola de Diagnostico)
cd /d "%~dp0"
echo ===================================================
echo   Spotify Lyrics Overlay - Modo Depuracion
echo ===================================================
echo.

set "PY_EXE="
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
) else if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
) else (
    set "PY_EXE=python"
)

echo [INFO] Utilizando ejecutable: %PY_EXE%
echo [INFO] Iniciando aplicacion con salida en consola...
echo.
"%PY_EXE%" main.py
echo.
echo [INFO] La aplicacion ha finalizado.
pause
