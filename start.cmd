@echo off
if exist "%~dp0.env" (
    for /f "usebackq eol=# tokens=1* delims==" %%i in ("%~dp0.env") do (
        set %%i=%%j
    )
)
title CHROMA-AGENT-ALPHA v5
echo ========================================
echo  CHROMA-AGENT-ALPHA // TRI-STACK v5
echo ========================================
echo.
echo [1/4] Checking Antigravity Claude Proxy on port 8080...
netstat -ano | findstr :8080 | findstr LISTENING >nul
if %errorlevel% neq 0 (
    echo Starting Antigravity Claude Proxy...
    call acc start
) else (
    echo Antigravity Claude Proxy is already running.
)
echo.

echo [2/4] Starting LiteLLM proxy on port 4000...
start "LiteLLM Proxy" /d "C:\chroma-agent-alpha" "C:\chroma-agent-alpha\venv\Scripts\litellm.exe" --config C:\chroma-agent-alpha\litellm_config.yaml
timeout /t 4 /nobreak >nul

echo [3/4] Starting Pipeline Server on port 8001...
start "Pipeline Server" "C:\chroma-agent-alpha\venv\Scripts\python.exe" C:\chroma-agent-alpha\scripts\pipeline_server.py
timeout /t 3 /nobreak >nul

echo [4/4] Wiring Claude Code to LiteLLM...
set ANTHROPIC_BASE_URL=http://localhost:4000
set ANTHROPIC_API_KEY=sk-litellm-1234
set ANTHROPIC_AUTH_TOKEN=
set CLAUDE_CODE_AUTO_COMPACT_WINDOW=40000
echo.
echo ========================================
echo  STACK READY:
echo    T1 = gemini-2.5-flash-lite  (scout)
echo    T2 = deepseek-v4-flash:free (analyst, FREE)
echo    T3 = deepseek-v4-flash      (architect)
echo    Pipeline Server: http://localhost:8001
echo    Pipeline Docs:   http://localhost:8001/docs
echo    n8n workflow:    n8n\chroma_workflow.json
echo ========================================
echo.
echo  Switch model in Claude Code:
echo    /model claude-t1    T1 Scout
echo    /model claude-t2    T2 Analyst (DEFAULT)
echo    /model claude-t3    T3 Architect
echo.
echo  n8n: run 'start-n8n.cmd' in a separate window to enable local file nodes
echo  then import n8n\chroma_workflow.json
echo.
claude --model claude-t2
