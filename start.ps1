# ITS Multi-Agent System - Startup Script
$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ITS Multi-Agent System - Starting..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Knowledge Service
Write-Host "[1/3] Starting Knowledge Service (port 8001)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\backend\knowledge'; python -m api.main" -WindowStyle Normal
Start-Sleep -Seconds 3

# 2. Backend API
Write-Host "[2/3] Starting Backend API (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='$ProjectRoot\backend\app'; cd '$ProjectRoot\backend\app'; python -m api.main" -WindowStyle Normal
Start-Sleep -Seconds 5

# 3. Agent Web UI
Write-Host "[3/3] Starting Agent Web UI (port 5173)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot\front\agent_web_ui'; npm run dev" -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API:       http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  API Docs:          http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Knowledge Service: http://127.0.0.1:8001" -ForegroundColor White
Write-Host "  Agent Web UI:      http://localhost:5173" -ForegroundColor White
Write-Host ""

$open = Read-Host "Open Agent Web UI? (y/n)"
if ($open -eq "y") {
    Start-Process "http://localhost:5173"
}
