@echo off
chcp 65001 >nul
echo.
echo ============================================
echo   ITS Multi-Agent System - Stopping...
echo ============================================
echo.

echo Stopping all services on ports 8000, 8001, 5173, 3000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1

echo.
echo ============================================
echo   All services stopped.
echo ============================================
echo.
pause
