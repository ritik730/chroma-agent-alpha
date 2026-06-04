@echo off
title CHROMA-AGENT-ALPHA Service Stopper
echo ========================================================
echo  CHROMA-AGENT-ALPHA - Stopping All Services
echo ========================================================
echo.

echo [1/4] Stopping LiteLLM Proxy...
taskkill /f /im litellm.exe >nul 2>&1

echo [2/4] Stopping n8n Workflow Engine (node.exe)...
taskkill /f /im node.exe >nul 2>&1

echo [3/4] Stopping Chromatography Pipeline Server (python.exe)...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*pipeline_server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo [4/4] Stopping Antigravity Claude Proxy...
call acc stop >nul 2>&1


echo.
echo ========================================================
echo  All services have been stopped successfully!
echo ========================================================
echo.
echo Closing this window in 5 seconds...
timeout /t 5 >nul
