@echo off
chcp 65001

REM ========================================================
REM AutoCorrection System Restart Script
REM Version: v1.0
REM ========================================================

echo [INFO] Restarting all services...

REM Stop all services first
echo [INFO] Calling stop-services.bat...
call stop-services.bat

REM Wait a few seconds to ensure processes are terminated
echo [INFO] Waiting for 5 seconds...
timeout /t 5 /nobreak > nul

REM Start all services
echo [INFO] Calling start-services.bat...
call start-services.bat

echo [INFO] All services have been restarted!
echo.
echo Press any key to exit...
pause 