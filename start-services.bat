@echo off
chcp 65001

REM ========================================================
REM AutoCorrection System Startup Script
REM Version: v3.0
REM ========================================================

echo [INFO] Activating Python virtual environment...
call .venv\Scripts\activate.bat

echo [INFO] Setting environment variables...
set "PYTHONPATH=%cd%"
set FLASK_APP=app
set FLASK_ENV=development
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/0

echo [INFO] Redis service is running as a Windows service.

echo [INFO] Starting Flask application...
start "Flask App" cmd /k "python run.py"

timeout /t 5 /nobreak > nul

echo [INFO] Starting Celery main worker process...
start "Celery Main Worker" cmd /k "celery -A app.tasks.celery_app:celery_app worker --pool=solo --concurrency=1 --loglevel=info -Q default,correction,email,periodic,analytics,backup -n worker1@%%computername%%"

timeout /t 2 /nobreak > nul

echo [INFO] Starting Celery priority worker process...
start "Celery Priority Worker" cmd /k "celery -A app.tasks.celery_app:celery_app worker --pool=solo --concurrency=1 --loglevel=info -Q correction.priority -n priority_worker@%%computername%%"

timeout /t 2 /nobreak > nul

echo [INFO] Starting automatic essay correction service...
start "Auto Correction Service" cmd /k "python scripts/utils/process_pending_corrections.py"
timeout /t 3 /nobreak > nul
echo [INFO] Checking if correction service is running properly...
echo [INFO] If you see 'waiting for essays to correct' below, the service is running correctly.

echo [INFO] All services have been started!
echo.
echo Redis: Running as a Windows service
echo Flask: Running in a new window
echo Celery Main Worker: Running in a new window
echo Celery Priority Worker: Running in a new window
echo Auto Correction Service: Running in a new window
echo.
echo [USAGE]
echo 1. The system is now running. Access via browser.
echo 2. High-priority essays will be processed first.
echo 3. To stop all services, run stop-services.bat
echo.
echo Press any key to exit...
pause 