# 1-Click PowerShell Launcher for Live Institutional Signal Bot (Port 8080)
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Launching Real-Time Instruction Terminal on http://127.0.0.1:8080 ..." -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan

$pythonExe = "C:\Users\Sri\AppData\Local\Programs\Python\Python314\python.exe"

if (Test-Path $pythonExe) {
    Start-Process "http://127.0.0.1:8080"
    Set-Location -Path $PSScriptRoot
    & $pythonExe server.py
} else {
    Start-Process "http://127.0.0.1:8080"
    Set-Location -Path $PSScriptRoot
    python server.py
}
