@echo off
chcp 65001

REM ========================================================
REM AutoCorrection System Shutdown Script
REM Version: v3.0
REM ========================================================

echo [INFO] Stopping all services...

echo [INFO] Terminating Flask process...
taskkill /FI "WINDOWTITLE eq Flask App*" /F

echo [INFO] Terminating Celery worker processes...
taskkill /FI "WINDOWTITLE eq Celery Main Worker*" /F
taskkill /FI "WINDOWTITLE eq Celery Priority Worker*" /F

echo [INFO] Terminating Auto Correction Service...
taskkill /FI "WINDOWTITLE eq Auto Correction Service*" /F

echo [INFO] Redis service remains running...

echo [INFO] All services have been stopped!
echo [NOTE] Redis service is still running in the background.
echo.
echo Press any key to exit...
pause 