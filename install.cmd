@echo off
title CHROMA-AGENT-ALPHA Installer
echo ========================================================
echo  CHROMA-AGENT-ALPHA - Installer Bootstrapper
echo ========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Administrative privileges confirmed. Starting installation...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
) else (
    echo Requesting Administrator privileges to configure folder junctions...
    powershell -Command "Start-Process -FilePath '%0' -Verb RunAs"
    exit /b
)
