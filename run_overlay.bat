@echo off
title Spotify Lyrics Overlay
cd /d "%~dp0"

echo [1/2] Localizando Python...
set "PY_EXE="
if exist "%LocalAppData%\Programs\Python\Python312\pythonw.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
) else (
    where pythonw >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PY_EXE=pythonw"
    ) else (
        where python >nul 2>nul
        if %ERRORLEVEL% equ 0 (
            set "PY_EXE=python"
        )
    )
)

if "%PY_EXE%"=="" (
    echo.
    echo [ERROR] No se encontro Python en el sistema.
    echo Asegurate de que Python 3.12 este instalado.
    echo.
    pause
    exit /b 1
)

echo [2/2] Lanzando Spotify Lyrics Overlay...
start "" "%PY_EXE%" main.py
