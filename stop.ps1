# ITS Multi-Agent System - Stop All Services
$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ITS Multi-Agent System - Stopping..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$ports = @(8000, 8001, 5173, 3000)
$stopped = 0

foreach ($port in $ports) {
    $connections = netstat -ano 2>$null | Select-String ":$port\s" | Select-String "LISTENING"
    foreach ($conn in $connections) {
        $parts = ($conn -split '\s+') | Where-Object { $_ -ne '' }
        $pid = $parts[-1]
        if ($pid -match '^\d+$' -and [int]$pid -ne 0) {
            $procName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  [OK] Stopped PID $pid ($procName) on port $port" -ForegroundColor Green
            $stopped++
        }
    }
}

if ($stopped -eq 0) {
    Write-Host "  [--] No services found running" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Done. Stopped $stopped process(es)." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"
