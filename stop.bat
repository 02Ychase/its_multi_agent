@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   ITS Multi-Agent System - Stopping...
echo ============================================
echo.

echo [1/3] Stopping Knowledge Service...
taskkill /FI "WINDOWTITLE eq ITS-Knowledge*" /F >nul 2>&1
if %errorlevel%==0 (echo   [OK] Knowledge Service stopped) else (echo   [--] Knowledge Service not running)

echo [2/3] Stopping Backend API...
taskkill /FI "WINDOWTITLE eq ITS-Backend*" /F >nul 2>&1
if %errorlevel%==0 (echo   [OK] Backend API stopped) else (echo   [--] Backend API not running)

echo [3/3] Stopping Agent Web UI...
taskkill /FI "WINDOWTITLE eq ITS-AgentUI*" /F >nul 2>&1
if %errorlevel%==0 (echo   [OK] Agent Web UI stopped) else (echo   [--] Agent Web UI not running)

echo.
echo ============================================
echo   All services stopped.
echo ============================================
echo.
pause
