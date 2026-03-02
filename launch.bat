@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   Matrix Game Engine
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)

echo [1/3] Checking dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [2/3] Installing dependencies...
    pip install -r server\requirements-web.txt
) else (
    echo [2/3] Dependencies already installed
)

echo [3/3] Starting server...
echo.
echo ============================================
echo  Server starting...
echo  Visit http://localhost:8000
echo  API docs: http://localhost:8000/docs
echo ============================================
echo.
echo Press Ctrl+C to stop
echo.

cd server
python start_server.py

pause
