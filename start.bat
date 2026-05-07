@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   ITS Multi-Agent System - Starting...
echo ============================================
echo.

set PROJECT_ROOT=%~dp0

echo [1/3] Starting Knowledge Service (port 8001)...
start /min "" cmd /c "cd /d %PROJECT_ROOT%backend\knowledge && python -m api.main > %PROJECT_ROOT%logs\knowledge.log 2>&1"
timeout /t 3 /nobreak > nul

echo [2/3] Starting Backend API (port 8000)...
start /min "" cmd /c "cd /d %PROJECT_ROOT%backend\app && set PYTHONPATH=%PROJECT_ROOT%backend\app && python -m api.main > %PROJECT_ROOT%logs\backend.log 2>&1"
timeout /t 5 /nobreak > nul

echo [3/3] Starting Agent Web UI (port 5173)...
start /min "" cmd /c "cd /d %PROJECT_ROOT%front\agent_web_ui && npm run dev > %PROJECT_ROOT%logs\agent_ui.log 2>&1"
timeout /t 2 /nobreak > nul

echo.
echo ============================================
echo   All services started in background!
echo ============================================
echo.
echo   Backend API:       http://127.0.0.1:8000
echo   API Docs:          http://127.0.0.1:8000/docs
echo   Knowledge Service: http://127.0.0.1:8001
echo   Agent Web UI:      http://localhost:5173
echo.
echo   Logs: logs\backend.log, logs\knowledge.log, logs\agent_ui.log
echo.
pause
