@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed or is not available in PATH.
    pause
    exit /b 1
)
python server.py
pause
