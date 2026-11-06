# 1-Click PowerShell Launcher for Live Institutional Signal Bot
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "🚀 Launching Institutional Signal Bot on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$pythonExe = "C:\Users\Sri\AppData\Local\Programs\Python\Python314\python.exe"

if (Test-Path $pythonExe) {
    Start-Process "http://127.0.0.1:8000"
    Set-Location -Path $PSScriptRoot
    & $pythonExe server.py
} else {
    Start-Process "http://127.0.0.1:8000"
    Set-Location -Path $PSScriptRoot
    python server.py
}
