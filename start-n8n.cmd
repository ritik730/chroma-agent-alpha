@echo off
title CHROMA-AGENT-ALPHA // n8n Start Wrapper
echo ========================================
echo  n8n START WRAPPER (Enabling Local File Trigger)
echo ========================================
echo.
echo Setting environment variables to enable filesystem nodes...
set NODES_EXCLUDE=[]
echo Starting n8n...
n8n start
