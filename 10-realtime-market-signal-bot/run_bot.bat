@echo off
title Institutional Real-Time Signal Bot (HFT WebSocket HUD)
echo ======================================================================
echo 🚀 Launching Institutional Signal Bot on http://127.0.0.1:8000 ...
echo ======================================================================
echo.

set PYTHON_EXE=C:\Users\Sri\AppData\Local\Programs\Python\Python314\python.exe

if exist "%PYTHON_EXE%" (
    echo [✓] Using Python: %PYTHON_EXE%
    start "" http://127.0.0.1:8000
    "%PYTHON_EXE%" server.py
) else (
    echo [!] Python 3.14 not found at standard path. Falling back to system python...
    start "" http://127.0.0.1:8000
    python server.py
)

pause
