@echo off
REM Start Backend + Frontend locally for testing
REM Usage: scripts\start-local.bat

echo ============================================
echo MF FAQ Assistant - Local Development
echo ============================================
echo.

REM Check if we're in the right directory
if not exist "runtime\phase_9_api\__main__.py" (
    echo Error: Please run this script from the project root directory
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo Warning: .env file not found
    echo Copy .env.example to .env and add your GROQ_API_KEY
    pause
)

REM Check if node_modules exists
if not exist "web\node_modules" (
    echo Installing frontend dependencies...
    cd web && npm install && cd ..
)

echo.
echo Starting Backend (FastAPI) on http://localhost:8000
echo.

REM Start backend in background using PowerShell
start "Backend API" powershell -WindowStyle Minimized -Command "cd '%CD%'; python -m runtime.phase_9_api; pause"

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak > nul

REM Check if backend is running
curl -s http://localhost:8000/health > nul
if %ERRORLEVEL% neq 0 (
    echo Backend not responding yet, waiting 5 more seconds...
    timeout /t 5 /nobreak > nul
)

echo.
echo Starting Frontend (Next.js) on http://localhost:3000
echo.

REM Start frontend
cd web
start "Frontend UI" powershell -WindowStyle Normal -Command "npm run dev"

echo.
echo ============================================
echo Both services started!
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to stop all services...
echo ============================================

pause > nul

REM Kill processes
echo Stopping services...
taskkill /FI "WINDOWTITLE eq Backend API" /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend UI" /F > nul 2>&1
taskkill /F /IM node.exe > nul 2>&1

echo.
echo Services stopped.
pause
