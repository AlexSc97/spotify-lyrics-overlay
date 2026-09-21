@echo off
cd /d "%~dp0"
echo Iniciando Spotify Lyrics Overlay...

set "PY_EXE="
if exist "%LocalAppData%\Programs\Python\Python312\pythonw.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python312\pythonw.exe"
) else (
    where pythonw >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PY_EXE=pythonw"
    ) else (
        set "PY_EXE=python"
    )
)

start "" "%PY_EXE%" main.py

