@echo off
title CHROMA-AGENT-ALPHA Master Service Launcher
echo ========================================================
echo  CHROMA-AGENT-ALPHA - Starting All Services (Hidden Mode)
echo ========================================================
echo.
echo Checking Antigravity Claude Proxy on port 8080...
netstat -ano | findstr :8080 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo Starting Antigravity Claude Proxy...
    call acc start
) else (
    echo Antigravity Claude Proxy is already running.
)
echo.

echo Launching LiteLLM, Pipeline Server, and n8n in hidden background processes...
powershell -WindowStyle Hidden -Command "Start-Process -FilePath 'C:\chroma-agent-alpha\venv\Scripts\litellm.exe' -ArgumentList '--config C:\chroma-agent-alpha\litellm_config.yaml' -WindowStyle Hidden -WorkingDirectory 'C:\chroma-agent-alpha'; Start-Sleep -Seconds 3; Start-Process -FilePath 'C:\chroma-agent-alpha\venv\Scripts\python.exe' -ArgumentList 'C:\chroma-agent-alpha\scripts\pipeline_server.py' -WindowStyle Hidden -WorkingDirectory 'C:\chroma-agent-alpha'; Start-Sleep -Seconds 3; Start-Process -FilePath 'cmd.exe' -ArgumentList '/c set NODES_EXCLUDE=[] && n8n start' -WindowStyle Hidden -WorkingDirectory 'C:\chroma-agent-alpha'"

echo.
echo ========================================================
echo  All services triggered in the background!
echo    - LiteLLM Proxy:     http://localhost:4000
echo    - Pipeline Server:   http://localhost:8001 (Dashboard)
echo    - n8n Workflow:      http://localhost:5678
echo ========================================================
echo.
echo Closing this window in 5 seconds...
timeout /t 5 >nul
