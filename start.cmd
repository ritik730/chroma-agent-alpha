@echo off
title CHROMA-AGENT-ALPHA v5
echo ========================================
echo  CHROMA-AGENT-ALPHA // TRI-STACK v5
echo ========================================
echo.
echo [1/2] Starting LiteLLM proxy on port 4000...
start "LiteLLM Proxy" "C:\chroma-agent-alpha\venv\Scripts\litellm.exe" --config C:\chroma-agent-alpha\litellm_config.yaml
timeout /t 5 /nobreak >nul
echo [OK] LiteLLM starting on port 4000

echo [2/2] Wiring Claude Code to LiteLLM...
set ANTHROPIC_BASE_URL=http://localhost:4000
set ANTHROPIC_API_KEY=sk-litellm-1234
set ANTHROPIC_AUTH_TOKEN=
echo.
echo ========================================
echo  STACK READY:
echo    T1 = gemini-2.5-flash-lite  (scout, ~Rs1/100 calls)
echo    T2 = deepseek-v4-flash:free (analyst, FREE)
echo    T3 = deepseek-v4-flash      (architect, ~Rs0.9/call)
echo    AG = Claude via proxy :8080 (manual only)
echo ========================================
echo.
echo  Switch model in Claude Code:
echo    /model claude-t1    T1 Scout
echo    /model claude-t2    T2 Analyst (DEFAULT)
echo    /model claude-t3    T3 Architect
echo.
claude --model claude-t2
