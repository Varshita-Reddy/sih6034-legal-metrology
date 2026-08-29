@echo off

cd /d "%~dp0"

echo ================================================================
echo SIH OCR - STAGE 13 AUTO RUNNER SETUP
echo ================================================================
echo.

echo Checking Python environment...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv Python was not found.
    echo.
    pause
    exit /b 1
)

echo Python environment found.
echo.

echo Testing run_pipeline import...
echo.

".venv\Scripts\python.exe" -c "from run_pipeline import run; print('RUN_PIPELINE IMPORT OK')"

if errorlevel 1 (
    echo.
    echo ERROR: run_pipeline import failed.
    echo.
    pause
    exit /b 1
)

echo.
echo Creating Stage 13 folders...

if not exist "stage13\incoming" mkdir "stage13\incoming"
if not exist "stage13\processed" mkdir "stage13\processed"
if not exist "stage13\retake" mkdir "stage13\retake"
if not exist "stage13\results" mkdir "stage13\results"

echo.
echo Stage 13 folders ready.
echo.

echo Creating Windows Task Scheduler task...
echo.

schtasks /Create /TN "SIH OCR Stage13 Auto Runner" /TR "\"%~dp0.venv\Scripts\python.exe\" \"%~dp0stage13\auto_runner.py\"" /SC ONLOGON /RL LIMITED /F

if errorlevel 1 (
    echo.
    echo ERROR: Could not create scheduled task.
    echo.
    echo Try running this file as Administrator.
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo SETUP COMPLETE
echo ================================================================
echo.
echo Stage 13 will start automatically when you log into Windows.
echo.
echo Watch folder:
echo %~dp0stage13\incoming
echo.

pause