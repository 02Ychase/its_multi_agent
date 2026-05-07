@echo off
echo Stopping ITS Multi-Agent System...
echo.

echo Stopping backend service...
taskkill /F /FI "WINDOWTITLE eq ITS-Backend*" >nul 2>&1

echo Stopping Agent Web UI...
taskkill /F /FI "WINDOWTITLE eq ITS-AgentUI*" >nul 2>&1

echo Stopping Knowledge Platform UI...
taskkill /F /FI "WINDOWTITLE eq ITS-KnowledgeUI*" >nul 2>&1

echo.
echo All services stopped!
echo.
pause
