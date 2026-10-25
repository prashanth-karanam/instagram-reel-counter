@echo off
title Instagram Reel Counter & Super-Toolkit
cls

echo ========================================================
echo   Instagram Reel Counter & Privacy-First Toolkit
echo ========================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and tick "Add to PATH".
    pause
    exit /b 1
)

:: Install required dependencies if needed
python -c "import instagrapi, rich, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing required lightweight dependencies...
    pip install instagrapi rich requests
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Launch the unified app
python "%~dp0app.py"

pause
