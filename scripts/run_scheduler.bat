@echo off
REM Local Ingestion Pipeline Scheduler for Windows
REM Runs all phases 4.0 -> 4.1 -> 4.2 -> 4.3 with logging

echo ============================================
echo Local Ingestion Pipeline Scheduler
echo ============================================
echo.

REM Check if we're in the right directory
if not exist "runtime\phase_4_scrape\__init__.py" (
    echo Error: Please run this script from the project root directory
    echo Current directory: %CD%
    exit /b 1
)

REM Get current timestamp for default run ID
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set RUN_ID=%datetime:~0,8%-%datetime:~8,6%

REM Parse arguments
set VERBOSE=
set CUSTOM_RUN_ID=

:parse_args
if "%~1"=="" goto run_pipeline
if "%~1"=="--verbose" (
    set VERBOSE=--verbose
    shift
    goto parse_args
)
if "%~1"=="-v" (
    set VERBOSE=--verbose
    shift
    goto parse_args
)
if "%~1"=="--run-id" (
    set CUSTOM_RUN_ID=%~2
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:run_pipeline
if not "%CUSTOM_RUN_ID%"=="" (
    set RUN_ID=%CUSTOM_RUN_ID%
)

echo Run ID: %RUN_ID%
echo Log File: logs\scheduler_%RUN_ID%.log
echo.

REM Create logs directory
if not exist "logs" mkdir logs

REM Run the scheduler
python scripts\local_scheduler.py --run-id %RUN_ID% %VERBOSE%

REM Check result
if %ERRORLEVEL% neq 0 (
    echo.
    echo ============================================
    echo Pipeline FAILED with exit code %ERRORLEVEL%
    echo Check log file: logs\scheduler_%RUN_ID%.log
    echo ============================================
    exit /b %ERRORLEVEL%
)

echo.
echo ============================================
echo Pipeline COMPLETED SUCCESSFULLY
echo Log file: logs\scheduler_%RUN_ID%.log
echo Results: logs\results_%RUN_ID%.json
echo ============================================

exit /b 0
