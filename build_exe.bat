@echo off
title Construir Ejecutable SpotifyLyricsOverlay
cd /d "%~dp0"
echo ===================================================
echo   Compilando SpotifyLyricsOverlay.exe con PyInstaller
echo ===================================================
echo.
pyinstaller SpotifyLyricsOverlay.spec
if %ERRORLEVEL% equ 0 (
    copy /y dist\SpotifyLyricsOverlay.exe SpotifyLyricsOverlay.exe
    echo.
    echo [EXITO] Ejecutable generado correctamente: SpotifyLyricsOverlay.exe
) else (
    echo.
    echo [ERROR] Ocurrio un problema al compilar.
)
pause
