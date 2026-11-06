@echo off
title Institutional Real-Time Signal Bot (Port 8080)
echo ======================================================================
echo Launching Real-Time Instruction Terminal on http://127.0.0.1:8080 ...
echo ======================================================================
echo.

set PYTHON_EXE=C:\Users\Sri\AppData\Local\Programs\Python\Python314\python.exe

if exist "%PYTHON_EXE%" (
    echo [OK] Using Python: %PYTHON_EXE%
    start "" http://127.0.0.1:8080
    "%PYTHON_EXE%" server.py
) else (
    start "" http://127.0.0.1:8080
    python server.py
)

pause
