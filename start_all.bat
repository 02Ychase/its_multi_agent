@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   ITS Multi-Agent System - Starting All...
echo ============================================
echo.

set PROJECT_ROOT=%~dp0

echo [1/4] Starting Knowledge Service (port 8001)...
start "ITS-Knowledge" cmd /k "cd /d %PROJECT_ROOT%backend\knowledge && python -m api.main"
timeout /t 3 /nobreak > nul

echo [2/4] Starting Backend API (port 8000)...
start "ITS-Backend" cmd /k "cd /d %PROJECT_ROOT%backend\app && set PYTHONPATH=%PROJECT_ROOT%backend\app && python -m api.main"
timeout /t 5 /nobreak > nul

echo [3/4] Starting Agent Web UI (port 5173)...
start "ITS-AgentUI" cmd /k "cd /d %PROJECT_ROOT%front\agent_web_ui && npm run dev"
timeout /t 2 /nobreak > nul

echo [4/4] Starting Knowledge Platform UI (port 3000)...
start "ITS-KnowledgeUI" cmd /k "cd /d %PROJECT_ROOT%front\knowlege_platform_ui && npm run dev"
timeout /t 2 /nobreak > nul

echo.
echo ============================================
echo   All services started!
echo ============================================
echo.
echo   Backend API:       http://127.0.0.1:8000
echo   API Docs:          http://127.0.0.1:8000/docs
echo   Knowledge Service: http://127.0.0.1:8001
echo   Agent Web UI:      http://localhost:5173
echo   Knowledge UI:      http://localhost:3000
echo.
pause
