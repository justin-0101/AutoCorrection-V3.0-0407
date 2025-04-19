@echo off
chcp 65001

REM ========================================================
REM AutoCorrection System Log Viewer
REM Version: v3.0
REM ========================================================

echo [INFO] Activating Python virtual environment...
call .venv\Scripts\activate.bat

echo [INFO] Setting environment variables...
set "PYTHONPATH=%cd%"

echo [INFO] Viewing correction service logs...
python scripts/utils/view_correction_log.py %1

echo.
echo Press any key to exit...
pause 