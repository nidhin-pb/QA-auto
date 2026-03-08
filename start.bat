@echo off
echo ==========================================
echo  CVA QA Testing Automation Platform
echo ==========================================
echo.

:: Check if Python is available
python --version 2>NUL
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Check if Node.js is available
node --version 2>NUL
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/5] Installing Python dependencies...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

echo [2/5] Installing Playwright browsers...
python -m playwright install chromium
if errorlevel 1 (
    echo ERROR: Failed to install Playwright browsers
    pause
    exit /b 1
)

echo [3/5] Installing frontend dependencies...
cd ..\frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)

echo [4/5] Building frontend...
call npm run build
if errorlevel 1 (
    echo WARNING: Frontend build failed, will use dev server
)

echo [5/5] Starting backend server...
cd ..\backend
echo.
echo ==========================================
echo  Server starting on http://localhost:8000
echo  Frontend on http://localhost:3000
echo ==========================================
echo.

:: Start backend
start "CVA Backend" cmd /c "cd /d %~dp0backend && python main.py"

:: Start frontend dev server (if build failed or for dev)
timeout /t 3 /nobreak >NUL
start "CVA Frontend" cmd /c "cd /d %~dp0frontend && npm start"

echo.
echo Both servers starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all servers...
pause

:: Kill servers
taskkill /FI "WINDOWTITLE eq CVA Backend" /F 2>NUL
taskkill /FI "WINDOWTITLE eq CVA Frontend" /F 2>NUL
