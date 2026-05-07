# ITS Multi-Agent System - Shutdown Script
$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ITS Multi-Agent System - Stopping..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Stop processes by window title
$services = @(
    @{Name="Knowledge Service"; Title="ITS-Knowledge"},
    @{Name="Backend API"; Title="ITS-Backend"},
    @{Name="Agent Web UI"; Title="ITS-AgentUI"},
    @{Name="Knowledge Platform UI"; Title="ITS-KnowledgeUI"}
)

foreach ($svc in $services) {
    Write-Host "Stopping $($svc.Name)..." -ForegroundColor Yellow
    $killed = taskkill /FI "WINDOWTITLE eq $($svc.Title)*" /F 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] $($svc.Name) stopped" -ForegroundColor Green
    } else {
        Write-Host "  [--] $($svc.Name) not running" -ForegroundColor DarkGray
    }
}

# Also kill any remaining python/uvicorn processes on our ports
$ports = @(8000, 8001, 5173, 3000)
foreach ($port in $ports) {
    $connections = netstat -ano | Select-String ":$port " | Select-String "LISTENING"
    foreach ($conn in $connections) {
        $pid = ($conn -split '\s+')[-1]
        if ($pid -match '^\d+$' -and $pid -ne 0) {
            taskkill /PID $pid /F 2>&1 | Out-Null
        }
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  All services stopped." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
