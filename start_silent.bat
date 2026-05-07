@echo off
echo Starting ITS Multi-Agent System...
echo.

echo [1/3] Starting Backend (port 8000)...
start /B "ITS-Backend" cmd /c "cd /d D:\projects\its_multi_agent\backend\app && set PYTHONPATH=D:\projects\its_multi_agent\backend\app && python -m api.main > nul 2>&1"
timeout /t 5 /nobreak > nul

echo [2/3] Starting Agent Web UI (port 5173)...
start /B "ITS-AgentUI" cmd /c "cd /d D:\projects\its_multi_agent\front\agent_web_ui && npm run dev > nul 2>&1"
timeout /t 2 /nobreak > nul

echo [3/3] Starting Knowledge Platform UI (port 3000)...
start /B "ITS-KnowledgeUI" cmd /c "cd /d D:\projects\its_multi_agent\front\knowlege_platform_ui && npm run dev > nul 2>&1"
timeout /t 2 /nobreak > nul

echo.
echo All services started in background!
echo.
echo Backend API:        http://127.0.0.1:8000
echo API Docs:           http://127.0.0.1:8000/docs
echo Agent Web UI:       http://localhost:5173
echo Knowledge UI:       http://localhost:3000
echo.
echo Press any key to exit this window (services will keep running)...
pause >nul
